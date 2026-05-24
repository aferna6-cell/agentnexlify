export const FIELD_TYPES = [
  { value: "text", label: "Text" },
  { value: "email", label: "Email" },
  { value: "phone", label: "Phone" },
  { value: "textarea", label: "Text Area" },
  { value: "select", label: "Dropdown" },
  { value: "radio", label: "Radio Buttons" },
  { value: "checkbox", label: "Checkbox" },
  { value: "number", label: "Number" },
  { value: "date", label: "Date" },
];

export const EMBED_BASE =
  import.meta.env.VITE_API_BASE_URL ||
  "https://agentnexlify-production.up.railway.app";

export function formatDate(dateStr) {
  if (!dateStr) return "";
  const d = new Date(dateStr);
  return d.toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

export function makeFieldId(fields) {
  const maxNum = fields.reduce((max, f) => {
    const match = (f.id || "").match(/^field_(\d+)$/);
    return match ? Math.max(max, parseInt(match[1], 10)) : max;
  }, 0);
  return `field_${maxNum + 1}`;
}

export function newEmptyField(fields) {
  return {
    id: makeFieldId(fields),
    type: "text",
    label: "",
    placeholder: "",
    required: false,
    options: [],
  };
}

export const emptyFormData = {
  name: "",
  description: "",
  fields: [],
  settings: {
    success_message: "Thank you for your submission!",
    redirect_url: "",
    is_active: true,
  },
};

export function getEmbedIframe(form) {
  const url = `${EMBED_BASE}/api/v1/forms/public/${form.public_token || form.id}/embed`;
  return `<iframe src="${url}" width="100%" height="500" frameborder="0" style="border:none;border-radius:12px;"></iframe>`;
}

export function getDirectLink(form) {
  return `${EMBED_BASE}/api/v1/forms/public/${form.public_token || form.id}/embed`;
}
