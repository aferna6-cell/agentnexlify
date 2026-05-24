import { TABS } from "./constants";

function XThreadOutput({ tweets, connecting, onConnect }) {
  return (
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
          X/Twitter Thread ({tweets.length} tweets)
        </h3>
        <button
          className="btn-primary"
          onClick={() => onConnect("x_thread")}
          disabled={connecting.x_thread}
          style={{ fontSize: "0.8rem", padding: "6px 14px" }}
        >
          {connecting.x_thread ? "Posting..." : "Post Thread"}
        </button>
      </div>
      {tweets.map((tweet, i) => (
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
  );
}

function LinkedInOutput({ carousel }) {
  return (
    <div>
      <h3 style={{ margin: "0 0 16px", fontSize: "1rem" }}>
        LinkedIn Carousel ({carousel.slides?.length || 0} slides)
      </h3>
      {(carousel.slides || []).map((slide, i) => (
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
      ))}
    </div>
  );
}

function EmailSequenceOutput({ emails, connecting, onConnect }) {
  return (
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
          Email Sequence ({emails.length} emails)
        </h3>
        <button
          className="btn-primary"
          onClick={() => onConnect("email_sequence")}
          disabled={connecting.email_sequence}
          style={{ fontSize: "0.8rem", padding: "6px 14px" }}
        >
          {connecting.email_sequence ? "Creating..." : "Create Email Sequence"}
        </button>
      </div>
      {emails.map((email, i) => (
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
              Email {email.email_num || i + 1} - Day {email.day}
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
  );
}

function TikTokOutput({ scripts, connecting, onConnect }) {
  return (
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
          TikTok/Reels Scripts ({scripts.length})
        </h3>
        <button
          className="btn-primary"
          onClick={() => onConnect("tiktok")}
          disabled={connecting.tiktok}
          style={{ fontSize: "0.8rem", padding: "6px 14px" }}
        >
          {connecting.tiktok ? "Posting..." : "Post to TikTok"}
        </button>
      </div>
      {scripts.map((script, i) => (
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
  );
}

function SocialPostsOutput({ posts, connecting, onConnect }) {
  return (
    <div>
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: 16,
        }}
      >
        <h3 style={{ margin: 0, fontSize: "1rem" }}>Social Posts</h3>
        <button
          className="btn-primary"
          onClick={() => onConnect("social_posts")}
          disabled={connecting.social_posts}
          style={{ fontSize: "0.8rem", padding: "6px 14px" }}
        >
          {connecting.social_posts ? "Pushing..." : "Push to Social (Draft)"}
        </button>
      </div>
      {Object.entries(posts).map(([platform, content]) => (
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
      ))}
    </div>
  );
}

export default function OutputViewer({
  selectedJob,
  loading,
  activeTab,
  setActiveTab,
  connecting,
  onConnect,
}) {
  if (!selectedJob) {
    return (
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
    );
  }

  if (loading) {
    return (
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
    );
  }

  if (selectedJob.status === "processing") {
    return (
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
    );
  }

  if (selectedJob.status === "failed") {
    return (
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
    );
  }

  const outputs = selectedJob.outputs || {};

  return (
    <>
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

      <div style={{ flex: 1, overflow: "auto", padding: 20 }}>
        {activeTab === "x_thread" && outputs.x_thread && (
          <XThreadOutput
            tweets={outputs.x_thread}
            connecting={connecting}
            onConnect={onConnect}
          />
        )}
        {activeTab === "linkedin_carousel" && outputs.linkedin_carousel && (
          <LinkedInOutput carousel={outputs.linkedin_carousel} />
        )}
        {activeTab === "email_sequence" && outputs.email_sequence && (
          <EmailSequenceOutput
            emails={outputs.email_sequence}
            connecting={connecting}
            onConnect={onConnect}
          />
        )}
        {activeTab === "tiktok_scripts" && outputs.tiktok_scripts && (
          <TikTokOutput
            scripts={outputs.tiktok_scripts}
            connecting={connecting}
            onConnect={onConnect}
          />
        )}
        {activeTab === "social_posts" && outputs.social_posts && (
          <SocialPostsOutput
            posts={outputs.social_posts}
            connecting={connecting}
            onConnect={onConnect}
          />
        )}
      </div>
    </>
  );
}
