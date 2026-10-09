import { defineStore } from 'pinia'
import { computed, ref } from 'vue'

import { taskApi } from '@/shared/api/client'
import type { TaskInfo, TaskRequest } from '@/shared/api/types'
import { toast } from '@ui/toast'

export const useTasks = defineStore('tasks', () => {
  const items = ref<TaskInfo[]>([])
  const connected = ref(false)
  const error = ref('')
  const activeCount = computed(
    () => items.value.filter((task) => ['pending', 'running'].includes(task.status)).length,
  )
  const running = computed(() => items.value.find((task) => task.status === 'running'))
  let source: EventSource | undefined
  let poll: ReturnType<typeof setInterval> | undefined

  function accept(tasks: TaskInfo[]) {
    items.value = tasks
    error.value = ''
  }

  async function refresh() {
    try {
      accept(await taskApi.list())
    } catch {
      error.value = '无法连接任务队列，正在重试'
    }
  }

  function connect() {
    if (source) return
    source = taskApi.subscribe(accept, (isConnected, invalid) => {
      connected.value = isConnected
      if (invalid) error.value = '任务状态数据异常，正在重新获取'
    })
    // SSE 断线时继续获取状态；浏览器会自动重连事件流。
    poll = setInterval(() => {
      if (!connected.value) void refresh()
    }, 3000)
  }

  function disconnect() {
    source?.close()
    source = undefined
    if (poll) clearInterval(poll)
    poll = undefined
    connected.value = false
  }

  async function submit(payload: TaskRequest) {
    const task = await taskApi.submit(payload)
    const index = items.value.findIndex((item) => item.id === task.id)
    if (index < 0) items.value.unshift(task)
    toast.info('任务已提交', { description: task.name })
    return task
  }

  async function wait(taskId: string): Promise<TaskInfo> {
    for (;;) {
      const task = await taskApi.get(taskId)
      if (task.status === 'failed') throw new Error(task.error || '任务执行失败')
      if (task.status === 'completed') return task
      await new Promise<void>((resolve) => setTimeout(resolve, 700))
    }
  }

  async function clearCompleted() {
    await taskApi.clearCompleted()
    await refresh()
  }

  return {
    items,
    connected,
    error,
    activeCount,
    running,
    connect,
    disconnect,
    refresh,
    submit,
    wait,
    clearCompleted,
  }
})
