// AgentNexLiFy Review Responder — Background Service Worker

// Listen for messages from content script
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.type === "DRAFT_REVIEW") {
    // Open the popup with pre-filled review data
    // Note: Chrome doesn't allow programmatic popup opening,
    // so we store the data and the popup reads it on open
    chrome.storage.local.set({
      pendingReview: {
        text: message.reviewText,
        rating: message.rating,
        businessName: message.businessName,
        timestamp: Date.now(),
      },
    });

    // Show a notification that draft is ready
    chrome.action.setBadgeText({ text: "1" });
    chrome.action.setBadgeBackgroundColor({ color: "#3b82f6" });

    sendResponse({ success: true });
  }
  return true;
});

// Clear badge when popup opens
chrome.action.onClicked.addListener(() => {
  chrome.action.setBadgeText({ text: "" });
});
