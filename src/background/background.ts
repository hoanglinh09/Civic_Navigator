chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
  if (msg?.type !== "capture_screenshot") return;

  chrome.tabs.captureVisibleTab(
    // null is allowed at runtime, but the type expects a windowId.
    chrome.windows.WINDOW_ID_CURRENT,
    {
      format: "png",
    },
    (dataUrl) => {
      if (!dataUrl) {
        sendResponse({ ok: false });
        return;
      }
      const comma = dataUrl.indexOf(",");
      const b64 = comma === -1 ? "" : dataUrl.slice(comma + 1);
      // Width/height are not directly available; caller can ignore.
      sendResponse({ ok: true, data: b64, width: 0, height: 0 });
    }
  );

  return true;
});
