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

  /** 按 grid DOM 记录对应的布局控制器，DOM 被刷新移除后可随浏览器回收。 */
  /** @type {WeakMap<HTMLElement, { refresh: () => void }>} */
  const masonryLayouts = new WeakMap();

  /** 记录已绑定 load/error 事件的图片，避免 refresh 时重复绑定监听器。 */
  /** @type {WeakSet<HTMLImageElement>} */
  const boundImages = new WeakSet();

  /**
   * 瀑布流布局入口：根据唯一 selector 找到当前 grid，并触发一次重排。
   * NiceGUI 刷新后 JS 可能早于 DOM 挂载执行，所以找不到时会等几帧再尝试。
   *
   * @param {string} selector masonry-grid-{id}
   * @returns {void}
   */
  function layoutMasonry(selector) {
    const attach = (attempt = 0) => {
      const element = document.querySelector(selector);
      const grid = element instanceof HTMLElement ? element : null;
      if (!grid) {
        if (attempt < 8) {
          // 多次尝试，避免 DOM 未挂载导致计算错误
          requestAnimationFrame(() => attach(attempt + 1));
        }
        return;
      }

      let layout = masonryLayouts.get(grid);
      if (!layout) {
        layout = createMasonryLayout(grid);
        masonryLayouts.set(grid, layout);
      }
      layout.refresh();
    };

    requestAnimationFrame(() => attach());
  }

  /**
   * 为单个 masonry grid 创建布局控制器。
   * 控制器负责图片事件绑定、容器尺寸观察，以及把多次重排请求合并到下一帧执行。
   *
   * @param {HTMLElement} grid
   * @returns {{ refresh: () => void }}
   */
  function createMasonryLayout(grid) {
    /** @type {number | undefined} */
    let frameId;
    /** @type {ResizeObserver | undefined} */
    let resizeObserver;

    /** grid 被移除后断开观察器，并从 WeakMap 中删除控制器引用。 */
    const cleanup = () => {
      resizeObserver?.disconnect();
      masonryLayouts.delete(grid);
    };

    /** 根据每个 item 的归一化高度写入 grid-row-end: span N。 */
    const relayout = () => {
      if (!grid.isConnected) {
        cleanup();
        return;
      }

      const computed = getComputedStyle(grid);
      const rowHeight = parseFloat(computed.gridAutoRows) || 4;
      const gap = parseFloat(computed.rowGap || computed.gap) || 0;

      for (const item of grid.querySelectorAll(".masonry-item")) {
        /** @type {HTMLElement | null} */
        const masonryItem = item instanceof HTMLElement ? item : null;
        if (!masonryItem) {
          continue;
        }
        const height = measureMasonryItemHeight(masonryItem);
        if (height === null) {
          continue;
        }
        const span = Math.max(1, Math.ceil((height + gap) / (rowHeight + gap)));
        masonryItem.style.gridRowEnd = `span ${span}`;
      }
    };

    /** 合并同一帧内的多次重排请求，并等浏览器完成布局后再读取尺寸。 */
    const schedule = () => {
      if (frameId !== undefined) {
        return;
      }
      frameId = requestAnimationFrame(() => {
        frameId = requestAnimationFrame(() => {
          frameId = undefined;
          relayout();
        });
      });
    };

    /** 为当前 grid 内的图片绑定加载事件；已完成的图片也会主动安排一次重排。 */
    const bindGridImages = () => {
      for (const img of grid.querySelectorAll("img")) {
        if (!(img instanceof HTMLImageElement)) {
          continue;
        }
        if (!boundImages.has(img)) {
          boundImages.add(img);
          img.addEventListener("load", schedule);
          img.addEventListener("error", () => {
            img.dataset.waifuMasonryError = "1";
            schedule();
          });
        }
        if (img.complete) {
          if (img.naturalWidth === 0) {
            img.dataset.waifuMasonryError = "1";
          }
          schedule();
        }
      }
    };

    if ("ResizeObserver" in window) {
      // 列数、窗口宽度、侧栏开合都会改变列宽；列宽变化后需要重新计算 span。
      resizeObserver = new ResizeObserver(schedule);
      resizeObserver.observe(grid);
    }

    return {
      refresh: () => {
        bindGridImages();
        schedule();
      },
    };
  }

  /**
   * 计算 masonry item 在当前列宽下应该占用的显示高度。
   * 返回 null 表示图片尚未加载完成，本轮不写 span，等待 load/error 后再重排。
   * 加载失败的图片按当前列宽给一个正方形占位，避免错误图片挤占 0 高度。
   *
   * @param {HTMLElement} item
   * @returns {number | null} 图片高度；图片尚未加载完成时返回 null，等待 load/error 后重排
   */
  function measureMasonryItemHeight(item) {
    const img = item.querySelector("img");
    const width = item.getBoundingClientRect().width;
    if (!(img instanceof HTMLImageElement)) {
      return null;
    }

    if (img.naturalWidth > 0 && width > 0) {
      return (width * img.naturalHeight) / img.naturalWidth;
    }

    if (!img.complete && img.dataset.waifuMasonryError !== "1") {
      return null;
    }

    return width > 0 ? width : null;
  }

  /**
   * 打开全屏图片预览层；点击遮罩关闭。
   *
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
