// @ts-check

/**
 * @typedef {{
 *   layoutMasonry: (selector: string) => void,
 *   showLightbox: (src: string) => void,
 * }} WaifuImageViewerApi
 */

/** @type {Window & typeof globalThis & { WaifuImageViewer?: WaifuImageViewerApi }} */
const waifuWindow = window;

(function () {
  if (waifuWindow.WaifuImageViewer) {
    return;
  }

  /**
   * @param {string} selector
   * @returns {void}
   */
  function layoutMasonry(selector) {
    /** @type {HTMLElement | null} */
    const grid = document.querySelector(selector);
    if (!grid) {
      return;
    }

    const computed = getComputedStyle(grid);
    const rowHeight = parseFloat(computed.gridAutoRows) || 8;
    const gap = parseFloat(computed.rowGap || computed.gap) || 0;

    const relayout = () => {
      for (const item of grid.querySelectorAll(".masonry-item")) {
        /** @type {HTMLElement | null} */
        const masonryItem = item instanceof HTMLElement ? item : null;
        if (!masonryItem) {
          continue;
        }
        const img = item.querySelector("img");
        const height = img?.getBoundingClientRect().height || masonryItem.getBoundingClientRect().height;
        const span = Math.max(1, Math.ceil((height + gap) / (rowHeight + gap)));
        masonryItem.style.gridRowEnd = `span ${span}`;
      }
    };

    for (const img of grid.querySelectorAll("img")) {
      if (!(img instanceof HTMLImageElement)) {
        continue;
      }
      if (img.dataset.waifuMasonryBound === "1") {
        continue;
      }
      img.dataset.waifuMasonryBound = "1";
      img.addEventListener("load", () => requestAnimationFrame(relayout));
    }

    requestAnimationFrame(relayout);
  }

  /**
   * @param {string} src
   * @returns {void}
   */
  function showLightbox(src) {
    /** @type {HTMLDivElement} */
    const overlay = document.createElement("div");
    overlay.style.cssText = [
      "position:fixed",
      "inset:0",
      "z-index:99999",
      "background:rgba(0,0,0,0.85)",
      "display:flex",
      "align-items:center",
      "justify-content:center",
      "cursor:zoom-out",
    ].join(";");

    /** @type {HTMLImageElement} */
    const image = document.createElement("img");
    image.src = src;
    image.style.cssText = [
      "max-width:90vw",
      "max-height:90vh",
      "object-fit:contain",
      "border-radius:4px",
    ].join(";");

    overlay.appendChild(image);
    overlay.onclick = () => overlay.remove();
    document.body.appendChild(overlay);
  }

  waifuWindow.WaifuImageViewer = {
    layoutMasonry,
    showLightbox,
  };
})();
