import { ref } from 'vue'

import { toast } from '@ui/toast'

export function errorMessage(error: unknown) {
  return error instanceof Error ? error.message : '操作失败，请重试'
}

export function useAction() {
  const busy = ref(false)
  const error = ref('')

  async function run<T>(action: () => Promise<T>): Promise<T | undefined> {
    if (busy.value) return undefined
    busy.value = true
    error.value = ''
    try {
      return await action()
    } catch (cause) {
      error.value = errorMessage(cause)
      toast.error(error.value)
      return undefined
    } finally {
      busy.value = false
    }
  }

  return { busy, error, run }
}
