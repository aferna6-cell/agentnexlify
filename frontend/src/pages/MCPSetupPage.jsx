import { useState, useEffect, useCallback } from "react";
import { useAuth } from "../context/AuthContext";
import { fetchDashboard } from "../utils/api/dashboard";
import SkeletonLoader from "../components/SkeletonLoader";

const MCP_TOOLS = [
  {
    name: "list_recent_leads",
    description: "See your recent leads with scores and interests",
    color: "#3b82f6",
  },
  {
    name: "list_today_appointments",
    description: "Check today's schedule",
    color: "#22c55e",
  },
  {
    name: "get_unread_conversations",
    description: "See conversations that need attention",
    color: "#f59e0b",
  },
  {
    name: "get_action_items",
    description: "View AI-extracted tasks from conversations",
    color: "#8b5cf6",
  },
  {
    name: "get_analytics_summary",
    description: "Get a quick overview of your business metrics",
    color: "#ec4899",
  },
  {
    name: "reply_to_conversation",
    description: "Send a reply to a chat conversation",
    color: "#14b8a6",
  },
];

const EXAMPLE_PROMPTS = [
  "What leads came in this week?",
  "Do I have any appointments today?",
  "What action items are pending?",
  "How are my conversion rates?",
  "Reply to the latest conversation with: Thanks for your interest!",
];

function buildConfigJson(apiKey) {
  return JSON.stringify(
    {
      mcpServers: {
        agentnexlify: {
          command: "npx",
          args: ["-y", "mcp-remote", "https://agentnexlify-production.up.railway.app/mcp"],
          env: {
            API_KEY: apiKey || "YOUR_API_KEY_HERE",
          },
        },
      },
    },
    null,
    2
  );
}

export default function MCPSetupPage() {
  const { user, token } = useAuth();
  const [apiKey, setApiKey] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [copiedKey, setCopiedKey] = useState(false);
  const [copiedConfig, setCopiedConfig] = useState(false);

  const loadData = useCallback(async () => {
    if (!user?.tenantId) return;
    try {
      const dash = await fetchDashboard(user.tenantId, token);
      setApiKey(dash.widget_api_key || "");
      setError(null);
    } catch (err) {
      console.warn("Failed to load MCP setup data:", err.message);
      setError(err.message || "Failed to load setup data");
    } finally {
      setLoading(false);
    }
  }, [user?.tenantId, token]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const copyToClipboard = async (text, setter) => {
    try {
      await navigator.clipboard.writeText(text);
      setter(true);
      setTimeout(() => setter(false), 2000);
    } catch (err) {
      console.warn("Copy failed:", err.message);
    }
  };

  if (loading) return <SkeletonLoader />;

  const configJson = buildConfigJson(apiKey);

  return (
    <div className="fade-in">
      <div className="page-header">
        <div>
          <h1>MCP Setup</h1>
          <p>
            Connect AgentNexLiFy to Claude Desktop or any MCP-compatible AI
            assistant
          </p>
        </div>
      </div>

      {error && (
        <div
          style={{
            marginBottom: 16,
            padding: "10px 16px",
            background: "rgba(239,68,68,0.1)",
            border: "1px solid rgba(239,68,68,0.3)",
            borderRadius: 8,
            color: "#ef4444",
            fontSize: "0.85rem",
          }}
        >
          {error}
          <button
            onClick={() => setError(null)}
            style={{
              marginLeft: 12,
              background: "none",
              border: "none",
              color: "#ef4444",
              cursor: "pointer",
              fontSize: "0.8rem",
              textDecoration: "underline",
            }}
          >
            dismiss
          </button>
        </div>
      )}

      {/* Section 1: Status Card — API Key */}
      <div
        style={{
          background: "var(--bg-secondary)",
          border: "1px solid var(--border-color)",
          borderRadius: 12,
          padding: 20,
          marginBottom: 20,
        }}
      >
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 10,
            marginBottom: 12,
          }}
        >
          <svg
            width="20"
            height="20"
            viewBox="0 0 24 24"
            fill="none"
            stroke="var(--accent)"
            strokeWidth="1.5"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <path d="M21 2l-2 2m-7.61 7.61a5.5 5.5 0 1 1-7.78 7.78 5.5 5.5 0 0 1 7.78-7.78zm0 0L15.5 7.5m0 0l3 3L22 7l-3-3m-3.5 3.5L19 4" />
          </svg>
          <h3 style={{ margin: 0 }}>Your API Key</h3>
        </div>
        <p
          style={{
            color: "var(--text-secondary)",
            fontSize: "0.85rem",
            marginBottom: 14,
            lineHeight: 1.5,
          }}
        >
          This is the same API key used by your chat widget. You will need it to
          authenticate your MCP connection.
        </p>
        {apiKey ? (
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: 10,
              flexWrap: "wrap",
            }}
          >
            <code
              style={{
                flex: 1,
                minWidth: 200,
                padding: "10px 14px",
                borderRadius: 8,
                background: "var(--bg-primary)",
                border: "1px solid var(--border-color)",
                color: "var(--text-primary)",
                fontSize: "0.85rem",
                fontFamily: "monospace",
                wordBreak: "break-all",
              }}
            >
              {apiKey}
            </code>
            <button
              className="btn-primary"
              onClick={() => copyToClipboard(apiKey, setCopiedKey)}
              style={{
                whiteSpace: "nowrap",
                flexShrink: 0,
              }}
            >
              {copiedKey ? "Copied!" : "Copy API Key"}
            </button>
          </div>
        ) : (
          <div
            style={{
              padding: "16px 20px",
              background: "rgba(245,158,11,0.1)",
              border: "1px solid rgba(245,158,11,0.3)",
              borderRadius: 8,
              color: "#f59e0b",
              fontSize: "0.85rem",
              lineHeight: 1.5,
            }}
          >
            No API key found. Go to the{" "}
            <strong>Widget</strong> page to configure your widget first - your
            API key will be generated automatically.
          </div>
        )}
      </div>

      {/* Section 2: Claude Desktop Setup */}
      <div
        style={{
          background: "var(--bg-secondary)",
          border: "1px solid var(--border-color)",
          borderRadius: 12,
          padding: 20,
          marginBottom: 20,
        }}
      >
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 10,
            marginBottom: 16,
          }}
        >
          <svg
            width="20"
            height="20"
            viewBox="0 0 24 24"
            fill="none"
            stroke="var(--accent)"
            strokeWidth="1.5"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <path d="M20 4H4a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2V6a2 2 0 0 0-2-2zM7 15h0M2 10h20" />
          </svg>
          <h3 style={{ margin: 0 }}>Claude Desktop Setup</h3>
        </div>

        {/* Step 1 */}
        <div style={{ marginBottom: 20 }}>
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: 10,
              marginBottom: 8,
            }}
          >
            <span
              style={{
                display: "inline-flex",
                alignItems: "center",
                justifyContent: "center",
                width: 26,
                height: 26,
                borderRadius: "50%",
                background: "var(--accent-dim)",
                color: "var(--accent)",
                fontSize: "0.8rem",
                fontWeight: 700,
                flexShrink: 0,
              }}
            >
              1
            </span>
            <span
              style={{
                fontWeight: 600,
                color: "var(--text-primary)",
                fontSize: "0.95rem",
              }}
            >
              Open Claude Desktop settings
            </span>
          </div>
          <p
            style={{
              color: "var(--text-secondary)",
              fontSize: "0.85rem",
              marginLeft: 36,
              lineHeight: 1.5,
            }}
          >
            In Claude Desktop, click the menu and go to{" "}
            <strong>Settings</strong> &rarr; <strong>Developer</strong> &rarr;{" "}
            <strong>Edit Config</strong>. This opens your{" "}
            <code
              style={{
                padding: "2px 6px",
                borderRadius: 4,
                background: "var(--bg-primary)",
                fontSize: "0.82rem",
              }}
            >
              claude_desktop_config.json
            </code>{" "}
            file.
          </p>
        </div>

        {/* Step 2 */}
        <div style={{ marginBottom: 20 }}>
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: 10,
              marginBottom: 8,
            }}
          >
            <span
              style={{
                display: "inline-flex",
                alignItems: "center",
                justifyContent: "center",
                width: 26,
                height: 26,
                borderRadius: "50%",
                background: "var(--accent-dim)",
                color: "var(--accent)",
                fontSize: "0.8rem",
                fontWeight: 700,
                flexShrink: 0,
              }}
            >
              2
            </span>
            <span
              style={{
                fontWeight: 600,
                color: "var(--text-primary)",
                fontSize: "0.95rem",
              }}
            >
              Add this to your config file
            </span>
          </div>
          <div style={{ marginLeft: 36 }}>
            <div
              style={{
                position: "relative",
                borderRadius: 8,
                overflow: "hidden",
                border: "1px solid var(--border-color)",
              }}
            >
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  padding: "8px 14px",
                  background: "rgba(59,130,246,0.08)",
                  borderBottom: "1px solid var(--border-color)",
                }}
              >
                <span
                  style={{
                    fontSize: "0.75rem",
                    color: "var(--text-muted)",
                    fontFamily: "monospace",
                  }}
                >
                  claude_desktop_config.json
                </span>
                <button
                  onClick={() => copyToClipboard(configJson, setCopiedConfig)}
                  style={{
                    background: "none",
                    border: "1px solid var(--border-color)",
                    borderRadius: 6,
                    padding: "4px 10px",
                    color: "var(--text-secondary)",
                    cursor: "pointer",
                    fontSize: "0.75rem",
                    fontWeight: 500,
                  }}
                >
                  {copiedConfig ? "Copied!" : "Copy"}
                </button>
              </div>
              <pre
                style={{
                  margin: 0,
                  padding: "14px 16px",
                  background: "var(--bg-primary)",
                  color: "var(--text-primary)",
                  fontSize: "0.82rem",
                  lineHeight: 1.6,
                  overflowX: "auto",
                  fontFamily:
                    "'SF Mono', 'Fira Code', 'Fira Mono', Menlo, Consolas, monospace",
                }}
              >
                {configJson}
              </pre>
            </div>
            {apiKey && (
              <p
                style={{
                  color: "var(--text-muted)",
                  fontSize: "0.78rem",
                  marginTop: 8,
                  lineHeight: 1.4,
                }}
              >
                Your API key has been pre-filled in the config above.
              </p>
            )}
          </div>
        </div>

        {/* Step 3 */}
        <div style={{ marginBottom: 20 }}>
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: 10,
              marginBottom: 8,
            }}
          >
            <span
              style={{
                display: "inline-flex",
                alignItems: "center",
                justifyContent: "center",
                width: 26,
                height: 26,
                borderRadius: "50%",
                background: "var(--accent-dim)",
                color: "var(--accent)",
                fontSize: "0.8rem",
                fontWeight: 700,
                flexShrink: 0,
              }}
            >
              3
            </span>
            <span
              style={{
                fontWeight: 600,
                color: "var(--text-primary)",
                fontSize: "0.95rem",
              }}
            >
              Restart Claude Desktop
            </span>
          </div>
          <p
            style={{
              color: "var(--text-secondary)",
              fontSize: "0.85rem",
              marginLeft: 36,
              lineHeight: 1.5,
            }}
          >
            Close and reopen Claude Desktop to load the new MCP server
            configuration.
          </p>
        </div>

        {/* Step 4 */}
        <div>
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: 10,
              marginBottom: 8,
            }}
          >
            <span
              style={{
                display: "inline-flex",
                alignItems: "center",
                justifyContent: "center",
                width: 26,
                height: 26,
                borderRadius: "50%",
                background: "var(--accent-dim)",
                color: "var(--accent)",
                fontSize: "0.8rem",
                fontWeight: 700,
                flexShrink: 0,
              }}
            >
              4
            </span>
            <span
              style={{
                fontWeight: 600,
                color: "var(--text-primary)",
                fontSize: "0.95rem",
              }}
            >
              Try it out
            </span>
          </div>
          <p
            style={{
              color: "var(--text-secondary)",
              fontSize: "0.85rem",
              marginLeft: 36,
              lineHeight: 1.5,
            }}
          >
            Open a new conversation in Claude Desktop and ask:{" "}
            <em>"What leads came in this week?"</em> - Claude will use your
            AgentNexLiFy MCP tools to fetch the answer.
          </p>
        </div>
      </div>

      {/* Section 3: Available Tools */}
      <div
        style={{
          background: "var(--bg-secondary)",
          border: "1px solid var(--border-color)",
          borderRadius: 12,
          padding: 20,
          marginBottom: 20,
        }}
      >
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 10,
            marginBottom: 16,
          }}
        >
          <svg
            width="20"
            height="20"
            viewBox="0 0 24 24"
            fill="none"
            stroke="var(--accent)"
            strokeWidth="1.5"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z" />
          </svg>
          <h3 style={{ margin: 0 }}>Available Tools</h3>
        </div>
        <p
          style={{
            color: "var(--text-secondary)",
            fontSize: "0.85rem",
            marginBottom: 16,
            lineHeight: 1.5,
          }}
        >
          These tools are available to your AI assistant once connected. It will
          automatically choose the right tool based on your question.
        </p>
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))",
            gap: 12,
          }}
        >
          {MCP_TOOLS.map((tool) => (
            <div
              key={tool.name}
              style={{
                background: "var(--bg-primary)",
                border: "1px solid var(--border-color)",
                borderRadius: 10,
                padding: "14px 16px",
                display: "flex",
                flexDirection: "column",
                gap: 6,
              }}
            >
              <code
                style={{
                  fontSize: "0.82rem",
                  fontFamily: "monospace",
                  color: tool.color,
                  fontWeight: 600,
                }}
              >
                {tool.name}
              </code>
              <span
                style={{
                  fontSize: "0.85rem",
                  color: "var(--text-secondary)",
                  lineHeight: 1.4,
                }}
              >
                {tool.description}
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* Section 4: Example Prompts */}
      <div
        style={{
          background: "var(--bg-secondary)",
          border: "1px solid var(--border-color)",
          borderRadius: 12,
          padding: 20,
          marginBottom: 20,
        }}
      >
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 10,
            marginBottom: 16,
          }}
        >
          <svg
            width="20"
            height="20"
            viewBox="0 0 24 24"
            fill="none"
            stroke="var(--accent)"
            strokeWidth="1.5"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
          </svg>
          <h3 style={{ margin: 0 }}>Example Prompts</h3>
        </div>
        <p
          style={{
            color: "var(--text-secondary)",
            fontSize: "0.85rem",
            marginBottom: 16,
            lineHeight: 1.5,
          }}
        >
          Try these questions in Claude Desktop once your MCP connection is
          active.
        </p>
        <div
          style={{
            display: "flex",
            flexDirection: "column",
            gap: 10,
          }}
        >
          {EXAMPLE_PROMPTS.map((prompt, idx) => (
            <div
              key={idx}
              style={{
                background: "var(--bg-primary)",
                border: "1px solid var(--border-color)",
                borderRadius: 10,
                padding: "12px 16px",
                display: "flex",
                alignItems: "center",
                gap: 12,
              }}
            >
              <span
                style={{
                  display: "inline-flex",
                  alignItems: "center",
                  justifyContent: "center",
                  width: 28,
                  height: 28,
                  borderRadius: "50%",
                  background: "var(--accent-dim)",
                  color: "var(--accent)",
                  fontSize: "0.75rem",
                  fontWeight: 700,
                  flexShrink: 0,
                }}
              >
                {idx + 1}
              </span>
              <span
                style={{
                  fontSize: "0.9rem",
                  color: "var(--text-primary)",
                  fontStyle: "italic",
                  lineHeight: 1.4,
                }}
              >
                "{prompt}"
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
