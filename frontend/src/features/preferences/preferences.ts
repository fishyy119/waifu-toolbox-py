export interface PreferenceConfig {
  viewerColumns: number
  viewerPageSize: number
  viewerViewMode: 'grid' | 'masonry'
  selectedDirectories: Record<string, string>
}

export const PREFERENCE_DEFAULTS: PreferenceConfig = {
  viewerColumns: 5,
  viewerPageSize: 50,
  viewerViewMode: 'grid',
  selectedDirectories: {},
}

export type PreferenceKey = keyof PreferenceConfig
export type PreferenceValue<Key extends PreferenceKey> = PreferenceConfig[Key]

const STORAGE_PREFIX = 'waifu-toolbox.preferences.'

function storageKey(key: PreferenceKey) {
  return `${STORAGE_PREFIX}${key}`
}

function parseStoredValue<Key extends PreferenceKey>(
  stored: string,
  fallback: PreferenceValue<Key>,
): PreferenceValue<Key> {
  if (typeof fallback === 'number') {
    return Number(stored) as PreferenceValue<Key>
  }
  if (typeof fallback === 'object') {
    return JSON.parse(stored) as PreferenceValue<Key>
  }
  return stored as PreferenceValue<Key>
}

export function setPreference<Key extends PreferenceKey>(key: Key, value: PreferenceValue<Key>) {
  try {
    const stored = typeof value === 'object' ? JSON.stringify(value) : String(value)
    localStorage.setItem(storageKey(key), stored)
  } catch {
    // 浏览器拒绝持久化时仍允许当前页面继续使用偏好。
  }
}

export function getPreference<Key extends PreferenceKey>(key: Key): PreferenceValue<Key> {
  const fallback = PREFERENCE_DEFAULTS[key]
  try {
    const stored = localStorage.getItem(storageKey(key))
    return stored === null ? fallback : parseStoredValue(stored, fallback)
  } catch {
    return fallback
  }
}
