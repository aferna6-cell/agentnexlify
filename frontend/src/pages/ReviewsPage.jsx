import { useState, useEffect, useCallback, useMemo } from "react";
import { useAuth } from "../context/AuthContext";
import { fetchReviews, createReview, updateReview, deleteReview, generateAIDraft } from "../utils/api/reviews";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, LineChart, Line, CartesianGrid } from "recharts";

const PLATFORMS = ["google", "yelp", "facebook"];

function Stars({ rating, size = 16 }) {
  return (
    <span style={{ fontSize: size, letterSpacing: 2 }}>
      {[1, 2, 3, 4, 5].map((i) => (
        <span key={i} style={{ color: i <= rating ? "#FFD700" : "var(--text-muted)" }}>
          &#9733;
        </span>
      ))}
    </span>
  );
}

function timeAgo(dateStr) {
  if (!dateStr) return "";
  const diff = Date.now() - new Date(dateStr).getTime();
  const days = Math.floor(diff / 86400000);
  if (days < 1) return "Today";
  if (days === 1) return "Yesterday";
  if (days < 30) return `${days}d ago`;
  if (days < 365) return `${Math.floor(days / 30)}mo ago`;
  return new Date(dateStr).toLocaleDateString();
}

export default function ReviewsPage() {
  const { user, token } = useAuth();
  const [reviews, setReviews] = useState([]);
  const [stats, setStats] = useState({ total: 0, average_rating: 0, responded: 0, unresponded: 0 });
  const [loading, setLoading] = useState(true);
  const [platformFilter, setPlatformFilter] = useState("");
  const [ratingFilter, setRatingFilter] = useState("");
  const [respondedFilter, setRespondedFilter] = useState("");
  const [selectedReview, setSelectedReview] = useState(null);
  const [responseText, setResponseText] = useState("");
  const [draftLoading, setDraftLoading] = useState(false);
  const [draftTone, setDraftTone] = useState("professional");
  const [error, setError] = useState(null);
  const [showAddForm, setShowAddForm] = useState(false);
  const [showAnalytics, setShowAnalytics] = useState(false);
  const [newReview, setNewReview] = useState({ platform: "google", author_name: "", rating: 5, review_text: "" });

  const load = useCallback(async () => {
    if (!user?.tenantId) return;
    setLoading(true);
    try {
      const res = await fetchReviews(user.tenantId, token, {
        platform: platformFilter || undefined,
        rating: ratingFilter || undefined,
        responded: respondedFilter === "" ? undefined : respondedFilter === "true",
      });
      setReviews(res.reviews || []);
      setStats(res.stats || {});
    } catch {
      setReviews([]);
    } finally {
      setLoading(false);
    }
  }, [user?.tenantId, token, platformFilter, ratingFilter, respondedFilter]);

  useEffect(() => { load(); }, [load]);

  // Analytics: rating distribution bar chart data
  const ratingDistribution = useMemo(() => {
    const counts = [0, 0, 0, 0, 0];
    for (const r of reviews) counts[r.rating - 1]++;
    return [1, 2, 3, 4, 5].map((star) => ({
      rating: `${star}`,
      count: counts[star - 1],
      fill: star >= 4 ? "#4ade80" : star === 3 ? "#facc15" : "#f87171",
    }));
  }, [reviews]);

  // Analytics: monthly average rating trend
  const monthlyTrend = useMemo(() => {
    const buckets = {};
    for (const r of reviews) {
      const d = r.review_date ? new Date(r.review_date) : null;
      if (!d) continue;
      const key = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`;
      if (!buckets[key]) buckets[key] = { sum: 0, count: 0, responded: 0 };
      buckets[key].sum += r.rating;
      buckets[key].count++;
      if (r.responded) buckets[key].responded++;
    }
    return Object.entries(buckets)
      .sort(([a], [b]) => a.localeCompare(b))
      .slice(-12)
      .map(([month, data]) => ({
        month,
        avg: Math.round((data.sum / data.count) * 10) / 10,
        responseRate: Math.round((data.responded / data.count) * 100),
      }));
  }, [reviews]);

  const openReview = (review) => {
    setSelectedReview(review);
    setResponseText(review.owner_response || review.ai_draft_response || "");
    setError(null);
  };

  const handleDraft = async () => {
    if (!selectedReview) return;
    setDraftLoading(true);
    try {
      const res = await generateAIDraft(user.tenantId, token, selectedReview.id, draftTone);
      setResponseText(res.draft);
      setError(null);
    } catch (err) {
      setError(err.body?.detail || "Failed to generate draft");
    } finally {
      setDraftLoading(false);
    }
  };

  const handleSaveResponse = async () => {
    if (!selectedReview || !responseText.trim()) return;
    try {
      await updateReview(user.tenantId, token, selectedReview.id, {
        owner_response: responseText.trim(),
        responded: true,
      });
      setSelectedReview(null);
      load();
    } catch (err) {
      setError(err.body?.detail || "Failed to save response");
    }
  };

  const handleAddReview = async () => {
    if (!newReview.author_name.trim()) return;
    try {
      await createReview(user.tenantId, token, newReview);
      setShowAddForm(false);
      setNewReview({ platform: "google", author_name: "", rating: 5, review_text: "" });
      load();
    } catch (err) {
      setError(err.body?.detail || "Failed to add review");
    }
  };

  const handleDelete = async (reviewId) => {
    try {
      await deleteReview(user.tenantId, token, reviewId);
      setSelectedReview(null);
      load();
    } catch (err) {
      setError(err.body?.detail || "Failed to delete review");
    }
  };

  return (
    <div className="fade-in">
      <div className="page-header">
        <h1>Reviews</h1>
        <p>Manage your online reputation</p>
      </div>

      {/* Stats cards */}
      <div className="stats-row" style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(150px, 1fr))", gap: 12, marginBottom: 20 }}>
        <div className="stat-card" style={{ background: "var(--bg-card)", padding: 16, borderRadius: 10, border: "1px solid var(--border-color)" }}>
          <div style={{ fontSize: "1.8rem", fontWeight: 700, color: "var(--text-primary)" }}>{stats.average_rating || "-"}</div>
          <div style={{ fontSize: "0.8rem", color: "var(--text-muted)" }}>Avg Rating</div>
          <Stars rating={Math.round(stats.average_rating || 0)} />
        </div>
        <div className="stat-card" style={{ background: "var(--bg-card)", padding: 16, borderRadius: 10, border: "1px solid var(--border-color)" }}>
          <div style={{ fontSize: "1.8rem", fontWeight: 700, color: "var(--text-primary)" }}>{stats.total}</div>
          <div style={{ fontSize: "0.8rem", color: "var(--text-muted)" }}>Total Reviews</div>
        </div>
        <div className="stat-card" style={{ background: "var(--bg-card)", padding: 16, borderRadius: 10, border: "1px solid var(--border-color)" }}>
          <div style={{ fontSize: "1.8rem", fontWeight: 700, color: "var(--green, #4ade80)" }}>{stats.responded}</div>
          <div style={{ fontSize: "0.8rem", color: "var(--text-muted)" }}>Responded</div>
        </div>
        <div className="stat-card" style={{ background: "var(--bg-card)", padding: 16, borderRadius: 10, border: "1px solid var(--border-color)" }}>
          <div style={{ fontSize: "1.8rem", fontWeight: 700, color: "var(--yellow, #facc15)" }}>{stats.unresponded}</div>
          <div style={{ fontSize: "0.8rem", color: "var(--text-muted)" }}>Need Response</div>
        </div>
      </div>

      {/* Analytics toggle + charts */}
      {reviews.length > 0 && (
        <div style={{ marginBottom: 16 }}>
          <button
            className={showAnalytics ? "btn-primary btn-sm" : "btn-secondary btn-sm"}
            onClick={() => setShowAnalytics(!showAnalytics)}
            style={{ marginBottom: showAnalytics ? 12 : 0 }}
          >
            {showAnalytics ? "Hide Analytics" : "Show Analytics"}
          </button>
          {showAnalytics && (
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
              {/* Rating distribution */}
              <div style={{ background: "var(--bg-card)", padding: 16, borderRadius: 10, border: "1px solid var(--border-color)" }}>
                <h4 style={{ margin: "0 0 12px", color: "var(--text-primary)", fontSize: "0.9rem" }}>Rating Distribution</h4>
                <ResponsiveContainer width="100%" height={180}>
                  <BarChart data={ratingDistribution} margin={{ top: 0, right: 0, left: -20, bottom: 0 }}>
                    <XAxis dataKey="rating" tick={{ fill: "var(--text-muted)", fontSize: 12 }} tickLine={false} axisLine={false} />
                    <YAxis allowDecimals={false} tick={{ fill: "var(--text-muted)", fontSize: 12 }} tickLine={false} axisLine={false} />
                    <Tooltip contentStyle={{ background: "var(--bg-secondary)", border: "1px solid var(--border-color)", borderRadius: 6, color: "var(--text-primary)" }} />
                    <Bar dataKey="count" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
              {/* Monthly trend */}
              <div style={{ background: "var(--bg-card)", padding: 16, borderRadius: 10, border: "1px solid var(--border-color)" }}>
                <h4 style={{ margin: "0 0 12px", color: "var(--text-primary)", fontSize: "0.9rem" }}>Monthly Avg Rating & Response Rate</h4>
                {monthlyTrend.length > 1 ? (
                  <ResponsiveContainer width="100%" height={180}>
                    <LineChart data={monthlyTrend} margin={{ top: 0, right: 10, left: -20, bottom: 0 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="var(--border-color)" />
                      <XAxis dataKey="month" tick={{ fill: "var(--text-muted)", fontSize: 11 }} tickLine={false} />
                      <YAxis yAxisId="rating" domain={[0, 5]} tick={{ fill: "var(--text-muted)", fontSize: 11 }} tickLine={false} axisLine={false} />
                      <YAxis yAxisId="pct" orientation="right" domain={[0, 100]} tick={{ fill: "var(--text-muted)", fontSize: 11 }} tickLine={false} axisLine={false} />
                      <Tooltip contentStyle={{ background: "var(--bg-secondary)", border: "1px solid var(--border-color)", borderRadius: 6, color: "var(--text-primary)" }} />
                      <Line yAxisId="rating" type="monotone" dataKey="avg" stroke="#4ade80" strokeWidth={2} name="Avg Rating" dot={{ r: 3 }} />
                      <Line yAxisId="pct" type="monotone" dataKey="responseRate" stroke="#818cf8" strokeWidth={2} name="Response %" dot={{ r: 3 }} />
                    </LineChart>
                  </ResponsiveContainer>
                ) : (
                  <div style={{ textAlign: "center", padding: 40, color: "var(--text-muted)", fontSize: "0.85rem" }}>
                    Need reviews from 2+ months to show trends
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Toolbar */}
      <div style={{ display: "flex", gap: 8, marginBottom: 16, flexWrap: "wrap", alignItems: "center" }}>
        <select value={platformFilter} onChange={(e) => setPlatformFilter(e.target.value)}
          style={{ padding: "6px 10px", borderRadius: 6, border: "1px solid var(--border-color)", background: "var(--bg-secondary)", color: "var(--text-primary)", fontSize: "0.85rem" }}>
          <option value="">All Platforms</option>
          {PLATFORMS.map((p) => <option key={p} value={p}>{p.charAt(0).toUpperCase() + p.slice(1)}</option>)}
        </select>
        <select value={ratingFilter} onChange={(e) => setRatingFilter(e.target.value)}
          style={{ padding: "6px 10px", borderRadius: 6, border: "1px solid var(--border-color)", background: "var(--bg-secondary)", color: "var(--text-primary)", fontSize: "0.85rem" }}>
          <option value="">All Ratings</option>
          {[5, 4, 3, 2, 1].map((r) => <option key={r} value={r}>{r} Stars</option>)}
        </select>
        <select value={respondedFilter} onChange={(e) => setRespondedFilter(e.target.value)}
          style={{ padding: "6px 10px", borderRadius: 6, border: "1px solid var(--border-color)", background: "var(--bg-secondary)", color: "var(--text-primary)", fontSize: "0.85rem" }}>
          <option value="">All Status</option>
          <option value="false">Needs Response</option>
          <option value="true">Responded</option>
        </select>
        <button className="btn-primary" onClick={() => setShowAddForm(true)} style={{ marginLeft: "auto" }}>
          Add Review
        </button>
      </div>

      {error && <div className="error-banner" style={{ marginBottom: 12 }}>{error}</div>}

      {/* Reviews list */}
      {loading ? (
        <div style={{ textAlign: "center", padding: 40, color: "var(--text-muted)" }}>Loading reviews...</div>
      ) : reviews.length === 0 ? (
        <div className="empty-card" style={{ textAlign: "center", padding: "3rem 2rem" }}>
          <div style={{ fontSize: "2.5rem", marginBottom: "0.75rem" }}>&#9734;</div>
          <h3 style={{ margin: "0 0 0.5rem", color: "var(--text-primary)" }}>No reviews yet</h3>
          <p style={{ color: "var(--text-muted)", marginBottom: "1rem" }}>
            Add reviews manually or connect Google Business Profile to import them automatically.
          </p>
          <button className="btn-primary" onClick={() => setShowAddForm(true)}>
            Add Your First Review
          </button>
        </div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          {reviews.map((review) => (
            <div key={review.id} onClick={() => openReview(review)}
              style={{
                background: "var(--bg-card)", padding: 16, borderRadius: 10,
                border: `1px solid ${review.responded ? "var(--border-color)" : "var(--yellow, #facc15)"}`,
                cursor: "pointer",
                transition: "border-color 0.2s",
              }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 8 }}>
                <div>
                  <div style={{ fontWeight: 600, color: "var(--text-primary)" }}>{review.author_name}</div>
                  <Stars rating={review.rating} size={14} />
                </div>
                <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
                  <span style={{
                    padding: "2px 8px", borderRadius: 10, fontSize: "0.7rem",
                    background: review.responded ? "var(--green-dim, rgba(74,222,128,0.15))" : "var(--yellow-dim, rgba(250,204,21,0.15))",
                    color: review.responded ? "var(--green, #4ade80)" : "var(--yellow, #facc15)",
                  }}>
                    {review.responded ? "Responded" : "Needs Response"}
                  </span>
                  <span style={{ fontSize: "0.75rem", color: "var(--text-muted)", textTransform: "capitalize" }}>
                    {review.platform}
                  </span>
                  <span style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>
                    {timeAgo(review.review_date)}
                  </span>
                </div>
              </div>
              {review.review_text && (
                <div style={{ color: "var(--text-secondary)", fontSize: "0.9rem", lineHeight: 1.5 }}>
                  {review.review_text.length > 200 ? review.review_text.slice(0, 200) + "..." : review.review_text}
                </div>
              )}
              {review.owner_response && (
                <div style={{ marginTop: 8, padding: "8px 12px", background: "var(--bg-secondary)", borderRadius: 6, fontSize: "0.85rem", color: "var(--text-muted)" }}>
                  <strong>Your response:</strong> {review.owner_response.length > 100 ? review.owner_response.slice(0, 100) + "..." : review.owner_response}
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Review detail / response modal */}
      {selectedReview && (
        <div className="modal-overlay" onClick={() => setSelectedReview(null)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()} style={{ maxWidth: 600, maxHeight: "85vh", overflow: "auto" }}>
            <h3>Review Details</h3>
            <div className="modal-field">
              <label>Author</label>
              <div>{selectedReview.author_name}</div>
            </div>
            <div className="modal-field">
              <label>Rating</label>
              <div><Stars rating={selectedReview.rating} /> ({selectedReview.rating}/5)</div>
            </div>
            <div className="modal-field">
              <label>Platform</label>
              <div style={{ textTransform: "capitalize" }}>{selectedReview.platform}</div>
            </div>
            {selectedReview.review_text && (
              <div className="modal-field">
                <label>Review</label>
                <div style={{ lineHeight: 1.6 }}>{selectedReview.review_text}</div>
              </div>
            )}

            <div className="modal-field" style={{ borderTop: "1px solid var(--border-color)", paddingTop: 12, marginTop: 8 }}>
              <label>Your Response</label>
              <div style={{ display: "flex", gap: 6, marginBottom: 8 }}>
                <select value={draftTone} onChange={(e) => setDraftTone(e.target.value)}
                  style={{ padding: "4px 8px", borderRadius: 6, border: "1px solid var(--border-color)", background: "var(--bg-secondary)", color: "var(--text-primary)", fontSize: "0.8rem" }}>
                  <option value="professional">Professional</option>
                  <option value="friendly">Friendly</option>
                  <option value="casual">Casual</option>
                </select>
                <button className="btn-sm" onClick={handleDraft} disabled={draftLoading}>
                  {draftLoading ? "Generating..." : "AI Draft Response"}
                </button>
              </div>
              <textarea value={responseText} onChange={(e) => setResponseText(e.target.value)}
                className="modal-textarea" rows={4} placeholder="Write your response..." />
            </div>

            {error && <div className="error-banner" style={{ marginBottom: 8 }}>{error}</div>}

            <div className="modal-actions">
              <button className="btn-primary" onClick={handleSaveResponse} disabled={!responseText.trim()}>
                Save Response
              </button>
              <button className="btn-danger" onClick={() => handleDelete(selectedReview.id)}>Delete</button>
              <button className="btn-secondary" onClick={() => setSelectedReview(null)}>Close</button>
            </div>
          </div>
        </div>
      )}

      {/* Add review modal */}
      {showAddForm && (
        <div className="modal-overlay" onClick={() => setShowAddForm(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <h3>Add Review Manually</h3>
            <div className="modal-field">
              <label>Platform</label>
              <select value={newReview.platform} onChange={(e) => setNewReview({ ...newReview, platform: e.target.value })} className="modal-select">
                {PLATFORMS.map((p) => <option key={p} value={p}>{p.charAt(0).toUpperCase() + p.slice(1)}</option>)}
              </select>
            </div>
            <div className="modal-field">
              <label>Author Name</label>
              <input value={newReview.author_name} onChange={(e) => setNewReview({ ...newReview, author_name: e.target.value })}
                className="modal-input" placeholder="John D." />
            </div>
            <div className="modal-field">
              <label>Rating</label>
              <select value={newReview.rating} onChange={(e) => setNewReview({ ...newReview, rating: parseInt(e.target.value) })} className="modal-select">
                {[5, 4, 3, 2, 1].map((r) => <option key={r} value={r}>{r} Stars</option>)}
              </select>
            </div>
            <div className="modal-field">
              <label>Review Text</label>
              <textarea value={newReview.review_text} onChange={(e) => setNewReview({ ...newReview, review_text: e.target.value })}
                className="modal-textarea" rows={3} placeholder="What did they say?" />
            </div>
            <div className="modal-actions">
              <button className="btn-primary" onClick={handleAddReview} disabled={!newReview.author_name.trim()}>Add Review</button>
              <button className="btn-secondary" onClick={() => setShowAddForm(false)}>Cancel</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
