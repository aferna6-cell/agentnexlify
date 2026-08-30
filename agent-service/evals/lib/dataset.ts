/**
 * Action-eval dataset loader. Frozen 215 labels are never rewritten.
 */

import { readFileSync, statSync } from "node:fs";
import { createHash } from "node:crypto";
import { execFileSync } from "node:child_process";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import type { SharedContext } from "../../src/agent-os/types/agent.ts";

const here = dirname(fileURLToPath(import.meta.url));
export const DATASETS_DIR = join(here, "..", "datasets");
export const FROZEN_PATH = join(DATASETS_DIR, "action-eval-v1.json");
export const FROZEN_META_PATH = join(DATASETS_DIR, "FROZEN.json");

export type Behavior =
  "action" | "draft_only" | "clarification" | "decline" | "direct_answer";

export interface EvalCase {
  id: string;
  ask: string;
  expected_department: string;
  expected_behavior: Behavior;
  expected_tool: string | null;
  expected_risk_level?: number;
  expected_requires_approval?: boolean;
  required_params?: Record<string, string>;
  required_params_contains?: Record<string, string>;
  acceptable_departments?: string[];
  acceptable_behaviors?: Behavior[];
  must_not_execute?: boolean;
  must_not_execute_without_approval?: boolean;
  pair_id?: string;
  tags: string[];
  split: string;
  rationale: string;
  stress?: string;
  template_id?: string;
  family?: string;
  department_label?: string;
}

export interface Dataset {
  dataset_version: string;
  frozen: boolean;
  leakage_rules?: string[];
  business_context?: SharedContext | { note: string };
  cases: EvalCase[];
  not_for_model_selection?: boolean;
}

export interface FrozenMeta {
  blob_sha1: string;
  bytes: number;
  cases: number;
}

export function isActionDataset(
  d: Dataset,
): d is Dataset & { business_context: SharedContext } {
  const c = d.business_context as Record<string, unknown> | undefined;
  return Boolean(c && "businessProfile" in c && "pipelineLeads" in c);
}

export function loadDataset(path: string): Dataset {
  return JSON.parse(readFileSync(path, "utf8")) as Dataset;
}

export function gitHashObject(path: string): string {
  return execFileSync("git", ["hash-object", path], {
    encoding: "utf8",
  }).trim();
}

export function loadFrozenMeta(): FrozenMeta {
  const raw = JSON.parse(readFileSync(FROZEN_META_PATH, "utf8")) as {
    "action-eval-v1.json": FrozenMeta;
  };
  return raw["action-eval-v1.json"];
}

export function assertFrozenBlob(): FrozenMeta {
  const meta = loadFrozenMeta();
  const actual = gitHashObject(FROZEN_PATH);
  const bytes = statSync(FROZEN_PATH).size;
  if (actual !== meta.blob_sha1) {
    throw new Error(
      `Frozen action-eval-v1.json blob drifted: expected ${meta.blob_sha1}, got ${actual}`,
    );
  }
  if (bytes !== meta.bytes) {
    throw new Error(
      `Frozen action-eval-v1.json size drifted: expected ${meta.bytes}, got ${bytes}`,
    );
  }
  return meta;
}

/** Content hash of the raw file bytes — not parsed JSON. */
export function sha1File(path: string): string {
  return createHash("sha1").update(readFileSync(path)).digest("hex");
}

export function safetyCases(dataset: Dataset): EvalCase[] {
  return dataset.cases.filter(
    (c) => c.must_not_execute || c.must_not_execute_without_approval,
  );
}
