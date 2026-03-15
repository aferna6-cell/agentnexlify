// AgentNexLiFy Review Responder — Popup Logic

const $ = (sel) => document.querySelector(sel);

let currentRating = 5;
let apiKey = "";
let apiBase = "";
let businessName = "";

// --- Init ---

document.addEventListener("DOMContentLoaded", async () => {
  const stored = await chrome.storage.local.get(["apiKey", "apiBase", "businessName"]);
  if (stored.apiKey && stored.businessName) {
    apiKey = stored.apiKey;
    apiBase = stored.apiBase || "https://agentnexlify-production.up.railway.app";
    businessName = stored.businessName;
    showMainView();
  }

  // Star rating
  document.querySelectorAll(".star").forEach((star) => {
    star.addEventListener("click", () => {
      currentRating = parseInt(star.dataset.rating);
      updateStars();
    });
  });
  updateStars();

  // Buttons
  $("#connect-btn").addEventListener("click", handleConnect);
  $("#draft-btn").addEventListener("click", handleDraft);
  $("#copy-btn").addEventListener("click", handleCopy);
  $("#regenerate-btn").addEventListener("click", handleDraft);
  $("#disconnect-btn").addEventListener("click", handleDisconnect);
});

function updateStars() {
  document.querySelectorAll(".star").forEach((star) => {
    const r = parseInt(star.dataset.rating);
    star.style.color = r <= currentRating ? "#f59e0b" : "#555";
  });
}

function showMainView() {
  $("#settings-view").style.display = "none";
  $("#main-view").style.display = "block";
  $("#biz-name").textContent = businessName;
}

function showSettingsView() {
  $("#settings-view").style.display = "block";
  $("#main-view").style.display = "none";
}

// --- Connect ---

async function handleConnect() {
  const key = $("#api-key").value.trim();
  const base = $("#api-base").value.trim();
  if (!key) return;

  $("#connect-btn").disabled = true;
  $("#connect-btn").textContent = "Connecting...";

  try {
    // Verify the API key by fetching dashboard data
    const res = await fetch(`${base}/api/v1/widget/config/${key}`);
    if (!res.ok) throw new Error("Invalid API key");
    const data = await res.json();

    apiKey = key;
    apiBase = base;
    businessName = data.agent_name || data.bot_name || "Your Business";

    await chrome.storage.local.set({ apiKey, apiBase, businessName });
    showMainView();
  } catch (err) {
    $("#connect-status").innerHTML = `<div class="status status-error">${err.message}</div>`;
  } finally {
    $("#connect-btn").disabled = false;
    $("#connect-btn").textContent = "Connect";
  }
}

// --- Draft Response ---

async function handleDraft() {
  const reviewText = $("#review-text").value.trim();
  if (!reviewText) {
    $("#draft-status").innerHTML = '<div class="status status-error">Please enter the review text</div>';
    return;
  }

  $("#draft-btn").disabled = true;
  $("#draft-btn").textContent = "Generating...";
  $("#draft-status").innerHTML = "";

  try {
    // Use the reviews AI draft endpoint
    // First, we need a review ID. For the extension, we'll use a direct Claude call approach
    // by hitting a generic endpoint or the widget chat with a system prompt override.
    // For v1, we call the reviews AI draft endpoint with a temporary review.

    const res = await fetch(`${apiBase}/api/v1/widget/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        api_key: apiKey,
        session_id: `review_responder_${Date.now()}`,
        message: `SYSTEM: You are a review response writer for ${businessName}. Draft a professional response to this ${currentRating}-star review. Be warm for positive reviews, empathetic for negative ones. Never be defensive. Keep it under 100 words.\n\nREVIEW (${currentRating}/5 stars): ${reviewText}`,
      }),
    });

    if (!res.ok) throw new Error("Failed to generate response");
    const data = await res.json();

    $("#draft-text").textContent = data.response || "Could not generate response.";
    $("#draft-result").style.display = "block";
  } catch (err) {
    $("#draft-status").innerHTML = `<div class="status status-error">${err.message}</div>`;
  } finally {
    $("#draft-btn").disabled = false;
    $("#draft-btn").textContent = "Draft AI Response";
  }
}

// --- Copy ---

function handleCopy() {
  const text = $("#draft-text").textContent;
  navigator.clipboard.writeText(text).then(() => {
    $("#copy-btn").textContent = "Copied!";
    setTimeout(() => { $("#copy-btn").textContent = "Copy"; }, 2000);
  });
}

// --- Disconnect ---

async function handleDisconnect() {
  await chrome.storage.local.remove(["apiKey", "apiBase", "businessName"]);
  apiKey = "";
  apiBase = "";
  businessName = "";
  showSettingsView();
}
