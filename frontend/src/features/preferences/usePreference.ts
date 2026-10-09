import { customRef, type Ref } from 'vue'

import {
  getPreference,
  type PreferenceKey,
  type PreferenceValue,
  setPreference,
} from '@/features/preferences/preferences'

const preferenceRefs = new Map<PreferenceKey, unknown>()

function createPreferenceRef<Key extends PreferenceKey>(key: Key) {
  let value = getPreference(key)
  return customRef<PreferenceValue<Key>>((track, trigger) => ({
    get() {
      track()
      return value
    },
    set(nextValue) {
      value = nextValue
      setPreference(key, nextValue)
      trigger()
    },
  }))
}

export function usePreference<Key extends PreferenceKey>(key: Key): Ref<PreferenceValue<Key>> {
  const existing = preferenceRefs.get(key) as Ref<PreferenceValue<Key>> | undefined
  if (existing !== undefined) {
    return existing
  }

  const preference = createPreferenceRef(key)
  preferenceRefs.set(key, preference)
  return preference
}
