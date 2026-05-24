import { useState } from "react";
import {
  sendLeadEmail,
  sendLeadSms,
  requestReviewForLead,
} from "../../../utils/api/leads";

export default function QuickFollowupSection({ lead, form, tenantId, token }) {
  const [showEmail, setShowEmail] = useState(false);
  const [emailSubject, setEmailSubject] = useState("");
  const [emailBody, setEmailBody] = useState("");
  const [sendingEmail, setSendingEmail] = useState(false);
  const [emailStatus, setEmailStatus] = useState(null);
  const [showSms, setShowSms] = useState(false);
  const [smsBody, setSmsBody] = useState("");
  const [sendingSms, setSendingSms] = useState(false);
  const [smsStatus, setSmsStatus] = useState(null);
  const [sendingReview, setSendingReview] = useState(false);
  const [reviewStatus, setReviewStatus] = useState(null);

  if (!form.email && !form.phone) return null;

  const handleSendEmail = async () => {
    if (!emailSubject.trim() || !emailBody.trim()) return;
    setSendingEmail(true);
    setEmailStatus(null);
    try {
      await sendLeadEmail(tenantId, token, lead.id, {
        subject: emailSubject,
        message: emailBody,
      });
      setEmailStatus("sent");
      setEmailSubject("");
      setEmailBody("");
      setShowEmail(false);
    } catch (err) {
      setEmailStatus(err.body?.detail || err.message || "Failed to send");
    } finally {
      setSendingEmail(false);
    }
  };

  const handleSendSms = async () => {
    if (!smsBody.trim()) return;
    setSendingSms(true);
    setSmsStatus(null);
    try {
      await sendLeadSms(tenantId, token, lead.id, smsBody);
      setSmsStatus("sent");
      setSmsBody("");
      setShowSms(false);
    } catch (err) {
      setSmsStatus(err.body?.detail || err.message || "Failed to send");
    } finally {
      setSendingSms(false);
    }
  };

  const handleRequestReview = async () => {
    setSendingReview(true);
    setReviewStatus(null);
    try {
      const result = await requestReviewForLead(tenantId, token, lead.id);
      setReviewStatus(`Review request sent via ${result.sent_via.join(" & ")}`);
    } catch (err) {
      setReviewStatus(
        err.body?.detail || err.message || "Failed to send review request",
      );
    } finally {
      setSendingReview(false);
    }
  };

  return (
    <div className="intel-section">
      <div
        className="intel-title"
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
        }}
      >
        Quick Follow-up
        <div style={{ display: "flex", gap: 6 }}>
          {form.email && !showEmail && !showSms && (
            <button
              className="btn-sm"
              onClick={() => {
                setShowEmail(true);
                setShowSms(false);
              }}
            >
              Email
            </button>
          )}
          {form.phone && !showSms && !showEmail && (
            <button
              className="btn-sm"
              onClick={() => {
                setShowSms(true);
                setShowEmail(false);
              }}
              style={{ background: "var(--green, #22c55e)" }}
            >
              SMS
            </button>
          )}
          {!showEmail && !showSms && (
            <button
              className="btn-sm"
              onClick={handleRequestReview}
              disabled={sendingReview}
              style={{ background: "var(--purple, #8b5cf6)" }}
              title="Send a review request via email and/or SMS"
            >
              {sendingReview ? "Sending..." : "Request Review"}
            </button>
          )}
        </div>
      </div>
      {emailStatus === "sent" && (
        <div
          style={{
            color: "var(--green, #22c55e)",
            fontSize: "0.85rem",
            marginBottom: 8,
          }}
        >
          Email sent successfully
        </div>
      )}
      {emailStatus && emailStatus !== "sent" && (
        <div
          style={{
            color: "var(--red, #ef4444)",
            fontSize: "0.85rem",
            marginBottom: 8,
          }}
        >
          {emailStatus}
        </div>
      )}
      {smsStatus === "sent" && (
        <div
          style={{
            color: "var(--green, #22c55e)",
            fontSize: "0.85rem",
            marginBottom: 8,
          }}
        >
          SMS sent successfully
        </div>
      )}
      {smsStatus && smsStatus !== "sent" && (
        <div
          style={{
            color: "var(--red, #ef4444)",
            fontSize: "0.85rem",
            marginBottom: 8,
          }}
        >
          {smsStatus}
        </div>
      )}
      {reviewStatus && (
        <div
          style={{
            color: reviewStatus.startsWith("Review request sent")
              ? "var(--green, #22c55e)"
              : "var(--red, #ef4444)",
            fontSize: "0.85rem",
            marginBottom: 8,
          }}
        >
          {reviewStatus}
        </div>
      )}
      {showEmail && (
        <>
          <div className="drawer-field">
            <label className="drawer-label">Subject</label>
            <input
              className="drawer-input"
              value={emailSubject}
              onChange={(e) => setEmailSubject(e.target.value)}
              placeholder="Follow-up on your inquiry"
            />
          </div>
          <div className="drawer-field">
            <label className="drawer-label">Message</label>
            <textarea
              className="drawer-textarea"
              value={emailBody}
              onChange={(e) => setEmailBody(e.target.value)}
              placeholder="Write your message..."
              rows={4}
            />
          </div>
          <div style={{ display: "flex", gap: 8, marginTop: 4 }}>
            <button
              className="btn-sm"
              onClick={handleSendEmail}
              disabled={
                sendingEmail || !emailSubject.trim() || !emailBody.trim()
              }
            >
              {sendingEmail ? "Sending..." : "Send Email"}
            </button>
            <button
              className="btn-sm"
              onClick={() => setShowEmail(false)}
              style={{ background: "var(--bg-darker, #1a1a2e)" }}
            >
              Cancel
            </button>
          </div>
        </>
      )}
      {showSms && (
        <>
          <div className="drawer-field">
            <label className="drawer-label">Text Message</label>
            <textarea
              className="drawer-textarea"
              value={smsBody}
              onChange={(e) => setSmsBody(e.target.value)}
              placeholder="Hi, just following up on your inquiry..."
              rows={3}
              maxLength={1600}
            />
          </div>
          <div style={{ display: "flex", gap: 8, marginTop: 4 }}>
            <button
              className="btn-sm"
              onClick={handleSendSms}
              disabled={sendingSms || !smsBody.trim()}
              style={{ background: "var(--green, #22c55e)" }}
            >
              {sendingSms ? "Sending..." : "Send SMS"}
            </button>
            <button
              className="btn-sm"
              onClick={() => setShowSms(false)}
              style={{ background: "var(--bg-darker, #1a1a2e)" }}
            >
              Cancel
            </button>
          </div>
        </>
      )}
    </div>
  );
}
