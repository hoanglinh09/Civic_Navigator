import { clearOverlay, injectOverlay } from "./overlay";

chrome.runtime.onMessage.addListener((msg) => {
  if (msg?.type === "inject_overlay") {
    injectOverlay({ selector: msg.selector, bbox: msg.bbox, label: msg.label });
  }
  if (msg?.type === "clear_overlay") {
    clearOverlay();
  }
});
