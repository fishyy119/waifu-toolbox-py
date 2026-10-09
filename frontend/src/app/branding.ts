// 沿用原界面随机选择两张 favicon 的行为，侧栏与浏览器图标保持一致。
export const favicon = `/favicons/${Math.random() < 0.5 ? 'kano' : 'katan'}.png`
