/**
 * get_business_profile — reference tool A (level 0, read-only).
 *
 * Reads the tenant's business profile out of the SharedContext the data plane
 * already assembled for this turn. No network, no database, no credentials: a
 * pure read of the request's own read model, which is why it is level 0 and
 * needs no approval.
 *
 * It reports `missingFields` alongside `profile` on purpose. An agent that knows
 * the phone number is absent can say so, instead of inventing one — the same
 * honest-load rule the reasoning trace enforces (`agents/_trace.ts`).
 */

import { z } from "zod";
import { defineTool } from "../define-tool.ts";
import { RISK_READ_ONLY } from "../types.ts";
import type { BusinessProfileData } from "../../types/agent.ts";

/** Profile fields a caller may ask for. Mirrors BusinessProfileData. */
const PROFILE_FIELDS = [
  "businessName",
  "ownerName",
  "industry",
  "industryCluster",
  "businessType",
  "city",
  "state",
  "phone",
  "email",
  "website",
  "hoursSummary",
  "timezone",
  "reviewLinkGoogle",
  "reviewLinkYelp",
  "reviewLinkFacebook",
  "paymentLink",
] as const;

export type ProfileField = (typeof PROFILE_FIELDS)[number];

const Input = z.object({
  /** Restrict the read to these fields. Omit for the whole profile. */
  fields: z.array(z.enum(PROFILE_FIELDS)).optional(),
});

const Output = z.object({
  profile: z.record(z.string(), z.string()),
  presentFields: z.array(z.string()),
  missingFields: z.array(z.string()),
});

export type GetBusinessProfileInput = z.infer<typeof Input>;
export type GetBusinessProfileOutput = z.infer<typeof Output>;

export const getBusinessProfile = defineTool({
  id: "get_business_profile",
  displayName: "Get business profile",
  description:
    "Reads the business's profile (name, owner, contact details, hours, review and payment links) and reports which fields are filled in and which are missing.",
  requiredConnectors: [],
  riskLevel: RISK_READ_ONLY,
  mutating: false,
  requiresApproval: false,
  inputSchema: Input,
  outputSchema: Output,
  async execute({ input, context }): Promise<GetBusinessProfileOutput> {
    const profile = context.sharedContext.businessProfile as BusinessProfileData;
    const wanted: readonly ProfileField[] = input.fields?.length ? input.fields : PROFILE_FIELDS;

    const present: Record<string, string> = {};
    const presentFields: string[] = [];
    const missingFields: string[] = [];

    for (const field of wanted) {
      const value = profile[field];
      if (typeof value === "string" && value.trim().length > 0) {
        present[field] = value.trim();
        presentFields.push(field);
      } else {
        missingFields.push(field);
      }
    }

    return { profile: present, presentFields, missingFields };
  },
});
