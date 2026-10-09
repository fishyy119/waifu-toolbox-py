import { useQueryClient } from '@tanstack/vue-query'
import { watch } from 'vue'

import { useTasks } from '@/features/tasks'
import type { TaskInfo } from '@/shared/api/types'
import { toast } from '@ui/toast'

export function useTaskEffects() {
  const tasks = useTasks()
  const queryClient = useQueryClient()
  let previous = new Map<string, TaskInfo['status']>()
  let initialized = false

  watch(
    () => tasks.items,
    (items) => {
      let completed = false
      for (const task of items) {
        if (previous.get(task.id) === task.status || !['completed', 'failed'].includes(task.status))
          continue
        completed = true
        if (initialized) {
          if (task.status === 'failed') toast.error(task.name, { description: task.error })
          else toast.success(task.name, { description: task.result_text || '任务已完成' })
        }
      }
      if (completed) void queryClient.invalidateQueries({ queryKey: ['repos'] })
      previous = new Map(items.map((task) => [task.id, task.status]))
      initialized = true
    },
  )
}
