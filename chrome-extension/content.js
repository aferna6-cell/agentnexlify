// AgentNexLiFy Review Responder — Content Script
// Detects reviews on Google Maps and Yelp, adds "Draft Response" buttons.

(function () {
  "use strict";

  if (window.__anxReviewResponder) return;
  window.__anxReviewResponder = true;

  const BUTTON_CLASS = "anx-draft-response-btn";

  function createDraftButton(reviewElement, reviewText, rating) {
    if (reviewElement.querySelector(`.${BUTTON_CLASS}`)) return;

    const btn = document.createElement("button");
    btn.className = BUTTON_CLASS;
    btn.textContent = "Draft AI Response";
    btn.title = "Generate an AI response with AgentNexLiFy";

    btn.addEventListener("click", async (e) => {
      e.stopPropagation();
      e.preventDefault();

      btn.textContent = "Generating...";
      btn.disabled = true;

      try {
        const stored = await chrome.storage.local.get(["apiKey", "apiBase", "businessName"]);
        if (!stored.apiKey) {
          btn.textContent = "Connect first (click extension icon)";
          return;
        }

        // Send review to popup for processing
        chrome.runtime.sendMessage({
          type: "DRAFT_REVIEW",
          reviewText,
          rating,
          businessName: stored.businessName,
        });

        btn.textContent = "Check popup for draft";
      } catch (err) {
        btn.textContent = "Error — try popup";
      } finally {
        setTimeout(() => {
          btn.textContent = "Draft AI Response";
          btn.disabled = false;
        }, 3000);
      }
    });

    reviewElement.appendChild(btn);
  }

  // --- Google Maps Detection ---

  function scanGoogleMaps() {
    // Google Maps review elements
    const reviews = document.querySelectorAll('[data-review-id], .gws-localreviews__google-review');
    reviews.forEach((review) => {
      const textEl = review.querySelector('.wiI7pd, .review-full-text, [data-expandable-section]');
      const starsEl = review.querySelector('[aria-label*="star"], [role="img"][aria-label]');

      if (!textEl) return;

      const reviewText = textEl.textContent.trim();
      let rating = 5;
      if (starsEl) {
        const ariaLabel = starsEl.getAttribute("aria-label") || "";
        const match = ariaLabel.match(/(\d)/);
        if (match) rating = parseInt(match[1]);
      }

      if (reviewText.length > 10) {
        createDraftButton(review, reviewText, rating);
      }
    });
  }

  // --- Yelp Detection ---

  function scanYelp() {
    const reviews = document.querySelectorAll('[class*="review--"]');
    reviews.forEach((review) => {
      const textEl = review.querySelector('[class*="comment__"] p, [lang]');
      const starsEl = review.querySelector('[aria-label*="star"]');

      if (!textEl) return;

      const reviewText = textEl.textContent.trim();
      let rating = 5;
      if (starsEl) {
        const ariaLabel = starsEl.getAttribute("aria-label") || "";
        const match = ariaLabel.match(/(\d)/);
        if (match) rating = parseInt(match[1]);
      }

      if (reviewText.length > 10) {
        createDraftButton(review, reviewText, rating);
      }
    });
  }

  // --- Scan on load and mutations ---

  function scan() {
    if (window.location.hostname.includes("google.com")) {
      scanGoogleMaps();
    } else if (window.location.hostname.includes("yelp.com")) {
      scanYelp();
    }
  }

  // Initial scan
  scan();

  // Watch for dynamic content (Google Maps loads reviews dynamically)
  const observer = new MutationObserver(() => {
    clearTimeout(observer._debounce);
    observer._debounce = setTimeout(scan, 500);
  });

  observer.observe(document.body, { childList: true, subtree: true });
})();
