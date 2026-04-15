import { useState, useEffect, useCallback } from "react";
import { useAuth } from "../context/AuthContext";
import { notify } from "../utils/notify";
import {
  createRepurposeJob,
  listRepurposeJobs,
  getRepurposeJob,
  connectRepurposeOutputs,
  deleteRepurposeJob,
} from "../utils/api/repurpose";

const SOURCE_TYPES = [
  {
    key: "text",
    label: "Text / Article",
    icon: "📝",
    placeholder:
      "Paste your blog post, article, or any long-form content here...",
  },
  {
    key: "url",
    label: "Blog URL",
    icon: "🔗",
    placeholder: "https://yourblog.com/article-title",
  },
  {
    key: "youtube",
    label: "YouTube",
    icon: "▶️",
    placeholder: "https://youtube.com/watch?v=...",
  },
  {
    key: "podcast",
    label: "Podcast Transcript",
    icon: "🎙️",
    placeholder: "Paste the full podcast transcript here...",
  },
];

const TONES = [
  { key: "professional", label: "Professional" },
  { key: "engaging", label: "Engaging" },
  { key: "casual", label: "Casual" },
  { key: "indie_hacker", label: "Indie Hacker" },
];

const FORMAT_OPTIONS = [
  { key: "x_thread", label: "X/Twitter Thread" },
  { key: "linkedin_carousel", label: "LinkedIn Carousel" },
  { key: "email_sequence", label: "Email Sequence" },
  { key: "tiktok_scripts", label: "TikTok/Reels Scripts" },
  { key: "social_posts", label: "Social Posts" },
];

const TABS = [
  { key: "x_thread", label: "X Thread" },
  { key: "linkedin_carousel", label: "LinkedIn" },
  { key: "email_sequence", label: "Email Sequence" },
  { key: "tiktok_scripts", label: "TikTok Scripts" },
  { key: "social_posts", label: "Social Posts" },
];

function StatusBadge({ status }) {
  const styles = {
    processing: { color: "var(--accent)", bg: "var(--accent-dim)" },
    completed: { color: "var(--green)", bg: "var(--green-dim)" },
    failed: { color: "#ef4444", bg: "rgba(239,68,68,0.15)" },
  };
  const s = styles[status] || styles.processing;
  return (
    <span
      style={{
        padding: "2px 10px",
        borderRadius: 12,
        fontSize: "0.75rem",
        fontWeight: 600,
        color: s.color,
        background: s.bg,
      }}
    >
      {status}
    </span>
  );
}

function timeAgo(dateStr) {
  if (!dateStr) return "";
  const diff = Date.now() - new Date(dateStr).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "Just now";
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  return `${Math.floor(hours / 24)}d ago`;
}

export default function ContentRepurposePage() {
  const { user } = useAuth();
  const tenantId = user?.tenantId;
  const plan = user?.plan || "free";
  const isEligible = plan === "professional" || plan === "enterprise";

  const [jobs, setJobs] = useState([]);
  const [selectedJob, setSelectedJob] = useState(null);
  const [activeTab, setActiveTab] = useState("x_thread");
  const [loading, setLoading] = useState(false);
  const [creating, setCreating] = useState(false);
  const [connecting, setConnecting] = useState({});

  // Input state
  const [sourceType, setSourceType] = useState("text");
  const [sourceInput, setSourceInput] = useState("");
  const [tone, setTone] = useState("professional");
  const [formats, setFormats] = useState(FORMAT_OPTIONS.map((f) => f.key));

  const loadJobs = useCallback(async () => {
    if (!tenantId || !isEligible) return;
    try {
      const data = await listRepurposeJobs(tenantId);
      setJobs(data.jobs || []);
    } catch {
      /* non-critical */
    }
  }, [tenantId, isEligible]);

  useEffect(() => {
    loadJobs();
  }, [loadJobs]);

  const loadJob = useCallback(
    async (jobId) => {
      if (!tenantId) return;
      setLoading(true);
      try {
        const data = await getRepurposeJob(tenantId, jobId);
        setSelectedJob(data);
        if (data.outputs) {
          const firstAvailable = TABS.find((t) => data.outputs[t.key]);
          if (firstAvailable) setActiveTab(firstAvailable.key);
        }
      } catch {
        /* non-critical */
      } finally {
        setLoading(false);
      }
    },
    [tenantId],
  );

  const handleCreate = async () => {
    if (!sourceInput.trim() || creating) return;
    setCreating(true);
    try {
      const data = await createRepurposeJob(tenantId, {
        source_type: sourceType,
        source_input: sourceInput,
        tone,
        formats,
      });
      setSourceInput("");
      await loadJobs();
      // Poll for completion
      const pollId = setInterval(async () => {
        try {
          const job = await getRepurposeJob(tenantId, data.id);
          if (job.status !== "processing") {
            clearInterval(pollId);
            setSelectedJob(job);
            loadJobs();
          }
        } catch {
          clearInterval(pollId);
        }
      }, 3000);
    } catch (err) {
      notify.error(err.message || "Failed to create repurpose job");
    } finally {
      setCreating(false);
    }
  };

  const handleConnect = async (target) => {
    if (!selectedJob || connecting[target]) return;
    setConnecting((prev) => ({ ...prev, [target]: true }));
    try {
      await connectRepurposeOutputs(tenantId, selectedJob.id, [target]);
      notify.error(`Pushed to ${target.replace("_", " ")} successfully!`);
    } catch (err) {
      notify.error(err.message || `Failed to push to ${target}`);
    } finally {
      setConnecting((prev) => ({ ...prev, [target]: false }));
    }
  };

  const handleDelete = async (jobId) => {
    if (!confirm("Delete this repurpose job?")) return;
    try {
      await deleteRepurposeJob(tenantId, jobId);
      if (selectedJob?.id === jobId) setSelectedJob(null);
      loadJobs();
    } catch {
      /* non-critical */
    }
  };

  const toggleFormat = (key) => {
    setFormats((prev) =>
      prev.includes(key) ? prev.filter((f) => f !== key) : [...prev, key],
    );
  };

  // Upgrade prompt for non-eligible plans
  if (!isEligible) {
    return (
      <div style={{ padding: 40, textAlign: "center" }}>
        <div style={{ fontSize: "2rem", marginBottom: 12 }}>
          Content Repurposer
        </div>
        <p
          style={{
            color: "var(--text-secondary)",
            marginBottom: 24,
            maxWidth: 500,
            margin: "0 auto 24px",
          }}
        >
          Turn any blog post, YouTube video, or podcast into X threads, LinkedIn
          carousels, email sequences, TikTok scripts, and social posts — all in
          one click.
        </p>
        <div
          style={{
            padding: 24,
            background: "var(--card-bg)",
            borderRadius: 12,
            border: "1px solid var(--border)",
            maxWidth: 400,
            margin: "0 auto",
          }}
        >
          <div style={{ fontSize: "1.1rem", fontWeight: 600, marginBottom: 8 }}>
            Professional Plan Required
          </div>
          <p
            style={{
              color: "var(--text-secondary)",
              fontSize: "0.9rem",
              marginBottom: 16,
            }}
          >
            Content Repurposer is available on Professional ($499/mo) and
            Enterprise ($899/mo) plans.
          </p>
          <button
            className="btn-primary"
            onClick={() =>
              window.dispatchEvent(
                new CustomEvent("navigate", { detail: "billing" }),
              )
            }
          >
            Upgrade Now
          </button>
        </div>
      </div>
    );
  }

  const sourceConfig =
    SOURCE_TYPES.find((s) => s.key === sourceType) || SOURCE_TYPES[0];
  const outputs = selectedJob?.outputs || {};

  return (
    <div style={{ display: "flex", gap: 24, height: "100%" }}>
      {/* Left: Input + History */}
      <div
        style={{
          width: 340,
          flexShrink: 0,
          display: "flex",
          flexDirection: "column",
          gap: 16,
        }}
      >
        {/* Input Card */}
        <div
          style={{
            background: "var(--card-bg)",
            borderRadius: 12,
            border: "1px solid var(--border)",
            padding: 20,
          }}
        >
          <div
            style={{ fontSize: "1.1rem", fontWeight: 600, marginBottom: 16 }}
          >
            Repurpose Content
          </div>

          {/* Source type tabs */}
          <div
            style={{
              display: "flex",
              gap: 4,
              marginBottom: 12,
              flexWrap: "wrap",
            }}
          >
            {SOURCE_TYPES.map((s) => (
              <button
                key={s.key}
                onClick={() => setSourceType(s.key)}
                style={{
                  padding: "6px 12px",
                  borderRadius: 8,
                  border: "1px solid var(--border)",
                  cursor: "pointer",
                  fontSize: "0.8rem",
                  background:
                    sourceType === s.key ? "var(--accent)" : "transparent",
                  color:
                    sourceType === s.key ? "#fff" : "var(--text-secondary)",
                }}
              >
                {s.icon} {s.label}
              </button>
            ))}
          </div>

          {/* Input */}
          {sourceType === "url" || sourceType === "youtube" ? (
            <input
              type="url"
              value={sourceInput}
              onChange={(e) => setSourceInput(e.target.value)}
              placeholder={sourceConfig.placeholder}
              style={{
                width: "100%",
                padding: "10px 12px",
                borderRadius: 8,
                border: "1px solid var(--border)",
                background: "var(--input-bg)",
                color: "var(--text-primary)",
                fontSize: "0.9rem",
                marginBottom: 12,
              }}
            />
          ) : (
            <textarea
              value={sourceInput}
              onChange={(e) => setSourceInput(e.target.value)}
              placeholder={sourceConfig.placeholder}
              rows={6}
              style={{
                width: "100%",
                padding: "10px 12px",
                borderRadius: 8,
                border: "1px solid var(--border)",
                background: "var(--input-bg)",
                color: "var(--text-primary)",
                fontSize: "0.9rem",
                resize: "vertical",
                marginBottom: 12,
              }}
            />
          )}

          {/* Tone */}
          <div style={{ marginBottom: 12 }}>
            <label
              style={{
                fontSize: "0.8rem",
                color: "var(--text-secondary)",
                marginBottom: 4,
                display: "block",
              }}
            >
              Tone
            </label>
            <select
              value={tone}
              onChange={(e) => setTone(e.target.value)}
              style={{
                width: "100%",
                padding: "8px 12px",
                borderRadius: 8,
                border: "1px solid var(--border)",
                background: "var(--input-bg)",
                color: "var(--text-primary)",
                fontSize: "0.85rem",
              }}
            >
              {TONES.map((t) => (
                <option key={t.key} value={t.key}>
                  {t.label}
                </option>
              ))}
            </select>
          </div>

          {/* Formats */}
          <div style={{ marginBottom: 16 }}>
            <label
              style={{
                fontSize: "0.8rem",
                color: "var(--text-secondary)",
                marginBottom: 6,
                display: "block",
              }}
            >
              Output Formats
            </label>
            <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
              {FORMAT_OPTIONS.map((f) => (
                <label
                  key={f.key}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: 8,
                    fontSize: "0.85rem",
                    color: "var(--text-primary)",
                    cursor: "pointer",
                  }}
                >
                  <input
                    type="checkbox"
                    checked={formats.includes(f.key)}
                    onChange={() => toggleFormat(f.key)}
                  />
                  {f.label}
                </label>
              ))}
            </div>
          </div>

          <button
            className="btn-primary"
            onClick={handleCreate}
            disabled={!sourceInput.trim() || creating || formats.length === 0}
            style={{ width: "100%" }}
          >
            {creating ? "Repurposing..." : "Repurpose"}
          </button>
        </div>

        {/* Job History */}
        <div
          style={{
            background: "var(--card-bg)",
            borderRadius: 12,
            border: "1px solid var(--border)",
            padding: 16,
            flex: 1,
            overflow: "auto",
          }}
        >
          <div
            style={{
              fontSize: "0.9rem",
              fontWeight: 600,
              marginBottom: 12,
              color: "var(--text-secondary)",
            }}
          >
            History
          </div>
          {jobs.length === 0 ? (
            <div
              style={{
                color: "var(--text-muted)",
                fontSize: "0.85rem",
                textAlign: "center",
                padding: 20,
              }}
            >
              No repurpose jobs yet. Create your first one above!
            </div>
          ) : (
            jobs.map((job) => (
              <div
                key={job.id}
                onClick={() => loadJob(job.id)}
                style={{
                  padding: "10px 12px",
                  borderRadius: 8,
                  cursor: "pointer",
                  marginBottom: 4,
                  background:
                    selectedJob?.id === job.id
                      ? "var(--hover-overlay)"
                      : "transparent",
                  border:
                    selectedJob?.id === job.id
                      ? "1px solid var(--accent)"
                      : "1px solid transparent",
                }}
              >
                <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                  }}
                >
                  <span
                    style={{
                      fontSize: "0.85rem",
                      fontWeight: 500,
                      color: "var(--text-primary)",
                    }}
                  >
                    {job.source_title || `${job.source_type} content`}
                  </span>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      handleDelete(job.id);
                    }}
                    style={{
                      background: "none",
                      border: "none",
                      color: "var(--text-muted)",
                      cursor: "pointer",
                      fontSize: "0.8rem",
                    }}
                  >
                    ×
                  </button>
                </div>
                <div
                  style={{
                    display: "flex",
                    gap: 8,
                    marginTop: 4,
                    alignItems: "center",
                  }}
                >
                  <StatusBadge status={job.status} />
                  <span
                    style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}
                  >
                    {timeAgo(job.created_at)}
                  </span>
                </div>
              </div>
            ))
          )}
        </div>
      </div>

      {/* Right: Output viewer */}
      <div
        style={{
          flex: 1,
          background: "var(--card-bg)",
          borderRadius: 12,
          border: "1px solid var(--border)",
          display: "flex",
          flexDirection: "column",
          overflow: "hidden",
        }}
      >
        {!selectedJob ? (
          <div
            style={{
              flex: 1,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              color: "var(--text-muted)",
            }}
          >
            <div style={{ textAlign: "center" }}>
              <div style={{ fontSize: "2rem", marginBottom: 8 }}>🔄</div>
              <div>Select a job or create a new one to see results</div>
            </div>
          </div>
        ) : loading ? (
          <div
            style={{
              flex: 1,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              color: "var(--text-muted)",
            }}
          >
            Loading...
          </div>
        ) : selectedJob.status === "processing" ? (
          <div
            style={{
              flex: 1,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              color: "var(--accent)",
            }}
          >
            <div style={{ textAlign: "center" }}>
              <div style={{ fontSize: "1.5rem", marginBottom: 8 }}>⏳</div>
              <div>Repurposing in progress... This may take 30-60 seconds.</div>
            </div>
          </div>
        ) : selectedJob.status === "failed" ? (
          <div
            style={{
              flex: 1,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              color: "#ef4444",
            }}
          >
            <div style={{ textAlign: "center" }}>
              <div style={{ fontSize: "1.5rem", marginBottom: 8 }}>❌</div>
              <div>Repurposing failed. Try again with different content.</div>
            </div>
          </div>
        ) : (
          <>
            {/* Tabs */}
            <div
              style={{
                display: "flex",
                borderBottom: "1px solid var(--border)",
                padding: "0 16px",
              }}
            >
              {TABS.filter((t) => outputs[t.key]).map((tab) => (
                <button
                  key={tab.key}
                  onClick={() => setActiveTab(tab.key)}
                  style={{
                    padding: "12px 16px",
                    background: "none",
                    border: "none",
                    cursor: "pointer",
                    fontSize: "0.85rem",
                    fontWeight: 500,
                    color:
                      activeTab === tab.key
                        ? "var(--accent)"
                        : "var(--text-secondary)",
                    borderBottom:
                      activeTab === tab.key
                        ? "2px solid var(--accent)"
                        : "2px solid transparent",
                  }}
                >
                  {tab.label}
                </button>
              ))}
            </div>

            {/* Tab Content */}
            <div style={{ flex: 1, overflow: "auto", padding: 20 }}>
              {activeTab === "x_thread" && outputs.x_thread && (
                <div>
                  <div
                    style={{
                      display: "flex",
                      justifyContent: "space-between",
                      alignItems: "center",
                      marginBottom: 16,
                    }}
                  >
                    <h3 style={{ margin: 0, fontSize: "1rem" }}>
                      X/Twitter Thread ({outputs.x_thread.length} tweets)
                    </h3>
                    <button
                      className="btn-primary"
                      onClick={() => handleConnect("x_thread")}
                      disabled={connecting.x_thread}
                      style={{ fontSize: "0.8rem", padding: "6px 14px" }}
                    >
                      {connecting.x_thread ? "Posting..." : "Post Thread"}
                    </button>
                  </div>
                  {outputs.x_thread.map((tweet, i) => (
                    <div
                      key={i}
                      style={{
                        padding: 16,
                        background: "var(--hover-overlay)",
                        borderRadius: 10,
                        marginBottom: 8,
                        border: "1px solid var(--border)",
                      }}
                    >
                      <div
                        style={{
                          fontSize: "0.75rem",
                          color: "var(--text-muted)",
                          marginBottom: 6,
                        }}
                      >
                        Tweet {tweet.tweet_num || i + 1}
                      </div>
                      <div
                        style={{
                          fontSize: "0.9rem",
                          color: "var(--text-primary)",
                          whiteSpace: "pre-wrap",
                        }}
                      >
                        {tweet.content}
                      </div>
                      <div
                        style={{
                          fontSize: "0.75rem",
                          color: "var(--text-muted)",
                          marginTop: 6,
                        }}
                      >
                        {tweet.content?.length || 0}/280
                      </div>
                    </div>
                  ))}
                </div>
              )}

              {activeTab === "linkedin_carousel" &&
                outputs.linkedin_carousel && (
                  <div>
                    <h3 style={{ margin: "0 0 16px", fontSize: "1rem" }}>
                      LinkedIn Carousel (
                      {outputs.linkedin_carousel.slides?.length || 0} slides)
                    </h3>
                    {(outputs.linkedin_carousel.slides || []).map(
                      (slide, i) => (
                        <div
                          key={i}
                          style={{
                            padding: 16,
                            background: "var(--hover-overlay)",
                            borderRadius: 10,
                            marginBottom: 8,
                            border: "1px solid var(--border)",
                          }}
                        >
                          <div
                            style={{
                              fontSize: "0.75rem",
                              color: "var(--text-muted)",
                              marginBottom: 6,
                            }}
                          >
                            Slide {slide.slide_num || i + 1}
                          </div>
                          <div
                            style={{
                              fontSize: "0.9rem",
                              color: "var(--text-primary)",
                              marginBottom: 8,
                            }}
                          >
                            {slide.text}
                          </div>
                          {slide.image_suggestion && (
                            <div
                              style={{
                                fontSize: "0.8rem",
                                color: "var(--accent)",
                                fontStyle: "italic",
                              }}
                            >
                              Image: {slide.image_suggestion}
                            </div>
                          )}
                        </div>
                      ),
                    )}
                  </div>
                )}

              {activeTab === "email_sequence" && outputs.email_sequence && (
                <div>
                  <div
                    style={{
                      display: "flex",
                      justifyContent: "space-between",
                      alignItems: "center",
                      marginBottom: 16,
                    }}
                  >
                    <h3 style={{ margin: 0, fontSize: "1rem" }}>
                      Email Sequence ({outputs.email_sequence.length} emails)
                    </h3>
                    <button
                      className="btn-primary"
                      onClick={() => handleConnect("email_sequence")}
                      disabled={connecting.email_sequence}
                      style={{ fontSize: "0.8rem", padding: "6px 14px" }}
                    >
                      {connecting.email_sequence
                        ? "Creating..."
                        : "Create Email Sequence"}
                    </button>
                  </div>
                  {outputs.email_sequence.map((email, i) => (
                    <div
                      key={i}
                      style={{
                        padding: 16,
                        background: "var(--hover-overlay)",
                        borderRadius: 10,
                        marginBottom: 8,
                        border: "1px solid var(--border)",
                      }}
                    >
                      <div
                        style={{
                          display: "flex",
                          justifyContent: "space-between",
                          marginBottom: 8,
                        }}
                      >
                        <span
                          style={{
                            fontSize: "0.75rem",
                            color: "var(--text-muted)",
                          }}
                        >
                          Email {email.email_num || i + 1} — Day {email.day}
                        </span>
                      </div>
                      <div
                        style={{
                          fontSize: "0.9rem",
                          fontWeight: 600,
                          color: "var(--text-primary)",
                          marginBottom: 8,
                        }}
                      >
                        {email.subject}
                      </div>
                      <div
                        style={{
                          fontSize: "0.85rem",
                          color: "var(--text-secondary)",
                          whiteSpace: "pre-wrap",
                        }}
                      >
                        {email.body}
                      </div>
                    </div>
                  ))}
                </div>
              )}

              {activeTab === "tiktok_scripts" && outputs.tiktok_scripts && (
                <div>
                  <div
                    style={{
                      display: "flex",
                      justifyContent: "space-between",
                      alignItems: "center",
                      marginBottom: 16,
                    }}
                  >
                    <h3 style={{ margin: 0, fontSize: "1rem" }}>
                      TikTok/Reels Scripts ({outputs.tiktok_scripts.length})
                    </h3>
                    <button
                      className="btn-primary"
                      onClick={() => handleConnect("tiktok")}
                      disabled={connecting.tiktok}
                      style={{ fontSize: "0.8rem", padding: "6px 14px" }}
                    >
                      {connecting.tiktok ? "Posting..." : "Post to TikTok"}
                    </button>
                  </div>
                  {outputs.tiktok_scripts.map((script, i) => (
                    <div
                      key={i}
                      style={{
                        padding: 16,
                        background: "var(--hover-overlay)",
                        borderRadius: 10,
                        marginBottom: 12,
                        border: "1px solid var(--border)",
                      }}
                    >
                      <div
                        style={{
                          fontSize: "0.75rem",
                          color: "var(--text-muted)",
                          marginBottom: 8,
                        }}
                      >
                        Script {script.script_num || i + 1}
                      </div>
                      <div style={{ marginBottom: 8 }}>
                        <span
                          style={{
                            fontSize: "0.75rem",
                            color: "var(--accent)",
                            fontWeight: 600,
                          }}
                        >
                          HOOK (first 3 sec)
                        </span>
                        <div
                          style={{
                            fontSize: "0.9rem",
                            color: "var(--text-primary)",
                            marginTop: 4,
                          }}
                        >
                          {script.hook}
                        </div>
                      </div>
                      <div style={{ marginBottom: 8 }}>
                        <span
                          style={{
                            fontSize: "0.75rem",
                            color: "var(--text-muted)",
                            fontWeight: 600,
                          }}
                        >
                          BODY
                        </span>
                        <div
                          style={{
                            fontSize: "0.9rem",
                            color: "var(--text-primary)",
                            marginTop: 4,
                          }}
                        >
                          {script.body}
                        </div>
                      </div>
                      <div>
                        <span
                          style={{
                            fontSize: "0.75rem",
                            color: "var(--green)",
                            fontWeight: 600,
                          }}
                        >
                          CTA
                        </span>
                        <div
                          style={{
                            fontSize: "0.9rem",
                            color: "var(--text-primary)",
                            marginTop: 4,
                          }}
                        >
                          {script.cta}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}

              {activeTab === "social_posts" && outputs.social_posts && (
                <div>
                  <div
                    style={{
                      display: "flex",
                      justifyContent: "space-between",
                      alignItems: "center",
                      marginBottom: 16,
                    }}
                  >
                    <h3 style={{ margin: 0, fontSize: "1rem" }}>
                      Social Posts
                    </h3>
                    <button
                      className="btn-primary"
                      onClick={() => handleConnect("social_posts")}
                      disabled={connecting.social_posts}
                      style={{ fontSize: "0.8rem", padding: "6px 14px" }}
                    >
                      {connecting.social_posts
                        ? "Pushing..."
                        : "Push to Social (Draft)"}
                    </button>
                  </div>
                  {Object.entries(outputs.social_posts).map(
                    ([platform, content]) => (
                      <div
                        key={platform}
                        style={{
                          padding: 16,
                          background: "var(--hover-overlay)",
                          borderRadius: 10,
                          marginBottom: 8,
                          border: "1px solid var(--border)",
                        }}
                      >
                        <div
                          style={{
                            fontSize: "0.8rem",
                            fontWeight: 600,
                            color: "var(--accent)",
                            marginBottom: 8,
                            textTransform: "capitalize",
                          }}
                        >
                          {platform.replace("_", " ")}
                        </div>
                        <div
                          style={{
                            fontSize: "0.9rem",
                            color: "var(--text-primary)",
                            whiteSpace: "pre-wrap",
                          }}
                        >
                          {content}
                        </div>
                      </div>
                    ),
                  )}
                </div>
              )}
            </div>
          </>
        )}
      </div>
    </div>
  );
}
