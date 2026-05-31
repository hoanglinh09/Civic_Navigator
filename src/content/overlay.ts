type BBox = { x: number; y: number; width: number; height: number };

function ensureContainer() {
  let el = document.getElementById("civic-nav-overlay-container");
  if (el) return el;
  el = document.createElement("div");
  el.id = "civic-nav-overlay-container";
  Object.assign(el.style, {
    position: "fixed",
    inset: "0",
    zIndex: "2147483647",
    pointerEvents: "none",
  } as CSSStyleDeclaration);

  const style = document.createElement("style");
  style.dataset.civicNav = "1";
  style.textContent = `
  @keyframes civic-nav-pulse { 0%{ box-shadow: 0 0 0 rgba(74,222,128,0.0);} 50%{ box-shadow: 0 0 24px rgba(74,222,128,0.55);} 100%{ box-shadow: 0 0 0 rgba(74,222,128,0.0);} }
  .civic-nav-highlight{ position: absolute; border: 2px solid #4ade80; border-radius: 10px; animation: civic-nav-pulse 1.5s ease-in-out infinite; }
  .civic-nav-highlight-label{ position: absolute; top: -28px; left: 0; padding: 4px 8px; font-size: 12px; line-height: 16px; color: #fff; background: rgba(0,0,0,0.65); border: 1px solid rgba(255,255,255,0.12); border-radius: 8px; white-space: nowrap; }
  `;
  document.documentElement.appendChild(style);

  document.documentElement.appendChild(el);
  return el;
}

function getTargetRect(selector?: string | null, bbox?: BBox | null): DOMRect | null {
  if (bbox && Number.isFinite(bbox.x) && Number.isFinite(bbox.y)) {
    const r = new DOMRect(bbox.x, bbox.y, bbox.width, bbox.height);
    return r;
  }
  if (selector) {
    const node = document.querySelector(selector);
    if (node && node instanceof Element) {
      return node.getBoundingClientRect();
    }
  }
  return null;
}

export function clearOverlay() {
  const container = document.getElementById("civic-nav-overlay-container");
  if (container) container.remove();
  document.querySelectorAll("style[data-civic-nav='1']").forEach((s) => s.remove());
}

export function injectOverlay({
  selector,
  bbox,
  label,
}: {
  selector?: string | null;
  bbox?: BBox | null;
  label: string;
}) {
  clearOverlay();
  const container = ensureContainer();
  const rect = getTargetRect(selector, bbox);
  if (!rect) return;
  const highlight = document.createElement("div");
  highlight.className = "civic-nav-highlight";
  Object.assign(highlight.style, {
    left: `${Math.max(0, rect.left - 4)}px`,
    top: `${Math.max(0, rect.top - 4)}px`,
    width: `${Math.max(0, rect.width + 8)}px`,
    height: `${Math.max(0, rect.height + 8)}px`,
  } as CSSStyleDeclaration);
  const lab = document.createElement("div");
  lab.className = "civic-nav-highlight-label";
  lab.textContent = label || "Nhấn vào đây";
  highlight.appendChild(lab);
  container.appendChild(highlight);
}
