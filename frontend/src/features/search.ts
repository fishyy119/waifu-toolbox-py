import { defineStore } from 'pinia'
import { reactive, ref } from 'vue'

import { useTasks } from '@/features/tasks'
import type { SearchResult } from '@/shared/api/types'
import { errorMessage } from '@/shared/lib/useAction'

export const useSearch = defineStore('search', () => {
  const form = reactive({ repo_name: '', path: '', top_k: 10, skip_update: true })
  const results = ref<SearchResult[]>([])
  const loading = ref(false)
  const error = ref('')
  const taskId = ref('')

  async function search() {
    if (loading.value) return
    loading.value = true
    error.value = ''
    try {
      const tasks = useTasks()
      const task = await tasks.submit({ kind: 'search', ...form })
      taskId.value = task.id
      const completed = await tasks.wait(task.id)
      results.value = completed.result?.search_results ?? []
    } catch (cause) {
      results.value = []
      error.value = errorMessage(cause)
    } finally {
      loading.value = false
    }
  }

  return { form, results, loading, error, taskId, search }
})
