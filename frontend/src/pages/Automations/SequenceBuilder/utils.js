import DOMPurify from "dompurify";
import { SAMPLE_CONTEXT, SAMPLE_DATA } from "./constants";

export function emptyStep(order) {
  return {
    step_order: order,
    delay_minutes: 0,
    delay_value: 0,
    delay_unit: 1,
    action_type: "email",
    subject_template: "",
    body_template: "",
  };
}

export function renderWithSampleData(text) {
  let result = text || "";
  for (const [k, v] of Object.entries(SAMPLE_CONTEXT)) {
    result = result.split(k).join(v);
  }
  return result;
}

export function sanitizeHtml(html) {
  if (!html) return "";
  return DOMPurify.sanitize(html, { USE_PROFILES: { html: true } });
}

export function resolveTemplateVars(text) {
  if (!text) return text;
  const sanitized = sanitizeHtml(text);
  return sanitized.replace(/\{\{(\w+)\}\}/g, (match, key) => {
    const val = SAMPLE_DATA[key];
    if (val !== undefined)
      return `<span style="background:#dbeafe;color:#1e40af;padding:1px 4px;border-radius:3px;font-size:0.9em;" title="Sample: {{${key}}}">${val}</span>`;
    return `<span style="background:#fef3c7;color:#92400e;padding:1px 4px;border-radius:3px;font-size:0.9em;" title="Unknown variable">{{${key}}}</span>`;
  });
}
