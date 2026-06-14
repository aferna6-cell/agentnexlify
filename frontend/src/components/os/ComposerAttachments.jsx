/* Composer attachments for Agent OS - file/image upload + image generation.
 *
 * Uploads go to POST /api/v1/os/uploads (10MB cap, rate-limited server-side).
 * "Generate image" sends the current composer text as the prompt to
 * POST /api/v1/os/images/generate (503 until a provider key is configured).
 * Attached/generated items become chips; on send the parent appends their
 * URLs + vision summaries to the message so the AI staff sees the context
 * and the thread keeps a durable reference.
 */
import { useRef, useState } from "react";
import { BASE } from "../../utils/api/_client";

const ACCEPT = ".png,.jpg,.jpeg,.webp,.gif,.pdf";
const MAX_BYTES = 10 * 1024 * 1024;

export default function ComposerAttachments({
  token,
  attachments,
  setAttachments,
  composerText,
  disabled,
}) {
  const fileRef = useRef(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const friendly = (status, body) => {
    if (status === 413) return "File is too large (10MB max).";
    if (status === 415 || status === 400) return "That file type isn't supported.";
    if (status === 429)
      return body?.detail?.message || body?.detail || "Upload limit reached - try again later.";
    if (status === 503)
      return "Image generation isn't configured yet - ask your admin to add a provider key.";
    return "Something went wrong - try again.";
  };

  const handleFile = async (event) => {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file) return;
    if (file.size > MAX_BYTES) {
      setError("File is too large (10MB max).");
      return;
    }
    setError("");
    setBusy(true);
    try {
      const form = new FormData();
      form.append("file", file);
      const res = await fetch(`${BASE}/api/v1/os/uploads`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
        body: form,
      });
      const body = await res.json().catch(() => ({}));
      if (!res.ok) {
        setError(friendly(res.status, body));
        return;
      }
      setAttachments((prev) => [...prev, body]);
    } catch {
      setError("Upload failed - check your connection.");
    } finally {
      setBusy(false);
    }
  };

  const handleGenerate = async () => {
    const prompt = (composerText || "").trim();
    if (!prompt) {
      setError("Type what you want the image to show, then press Generate image.");
      return;
    }
    setError("");
    setBusy(true);
    try {
      const res = await fetch(`${BASE}/api/v1/os/images/generate`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ prompt }),
      });
      const body = await res.json().catch(() => ({}));
      if (!res.ok) {
        setError(friendly(res.status, body));
        return;
      }
      setAttachments((prev) => [
        ...prev,
        { ...body, content_type: "image/png", filename: "generated-image.png" },
      ]);
    } catch {
      setError("Image generation failed - try again.");
    } finally {
      setBusy(false);
    }
  };

  const remove = (id) =>
    setAttachments((prev) => prev.filter((a) => a.id !== id));

  return (
    <div style={{ padding: "0 14px" }}>
      {attachments.length > 0 && (
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap", paddingTop: 8 }}>
          {attachments.map((a) => (
            <div
              key={a.id}
              style={{
                display: "flex",
                alignItems: "center",
                gap: 6,
                background: "var(--bg-secondary)",
                border: "1px solid var(--border)",
                borderRadius: 8,
                padding: "4px 8px",
                fontSize: "0.75rem",
                color: "var(--text-secondary)",
              }}
            >
              {a.content_type?.startsWith("image/") && (
                <img
                  src={a.public_url}
                  alt={a.filename}
                  style={{ width: 28, height: 28, objectFit: "cover", borderRadius: 4 }}
                />
              )}
              <span style={{ maxWidth: 160, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                {a.filename}
              </span>
              <button
                onClick={() => remove(a.id)}
                aria-label={`Remove ${a.filename}`}
                style={{
                  background: "none",
                  border: "none",
                  color: "var(--text-muted)",
                  cursor: "pointer",
                  fontSize: "0.85rem",
                  padding: 0,
                }}
              >
                ×
              </button>
            </div>
          ))}
        </div>
      )}
      <div style={{ display: "flex", gap: 10, alignItems: "center", paddingTop: 6 }}>
        <input
          ref={fileRef}
          type="file"
          accept={ACCEPT}
          onChange={handleFile}
          style={{ display: "none" }}
        />
        <button
          type="button"
          onClick={() => fileRef.current?.click()}
          disabled={disabled || busy}
          style={{
            background: "none",
            border: "1px solid var(--border)",
            borderRadius: 6,
            color: "var(--text-secondary)",
            cursor: disabled || busy ? "default" : "pointer",
            fontSize: "0.75rem",
            padding: "4px 10px",
          }}
        >
          {busy ? "Working..." : "Attach file"}
        </button>
        <button
          type="button"
          onClick={handleGenerate}
          disabled={disabled || busy || !(composerText || "").trim()}
          title="Generates an image from the text in the composer"
          style={{
            background: "none",
            border: "1px solid var(--border)",
            borderRadius: 6,
            color: "var(--text-secondary)",
            cursor: disabled || busy ? "default" : "pointer",
            fontSize: "0.75rem",
            padding: "4px 10px",
          }}
        >
          Generate image
        </button>
        {error && (
          <span style={{ fontSize: "0.75rem", color: "var(--red, #f87171)" }}>{error}</span>
        )}
      </div>
    </div>
  );
}
