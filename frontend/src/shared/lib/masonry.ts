export function masonryLayout(ratios: readonly number[], width: number, columns: number, gap = 8) {
  const heights = Array.from({ length: columns }, () => 0)
  const itemWidth = Math.max(1, (width - gap * (columns - 1)) / columns)
  const positions = ratios.map((ratio, index) => {
    // 第一排保持横向优先；之后每个 item 放进当前最短列。
    const column = index < columns ? index : heights.indexOf(Math.min(...heights))
    const top = heights[column] ?? 0
    // 图片未加载完成时不猜真实比例，但仍先占一个列宽正方形位置。
    const height = itemWidth * ratio
    heights[column] = top + height + gap
    return { x: column * (itemWidth + gap), y: top, width: itemWidth, height }
  })
  return { positions, height: Math.max(0, Math.max(...heights) - gap) }
}
