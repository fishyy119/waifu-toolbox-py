import { api } from './http'
import {
  clearTasksSchema,
  fileListingSchema,
  imagePageSchema,
  parseResponse,
  repoDetailSchema,
  repositoriesSchema,
  taskInfoSchema,
  tasksSchema,
} from './schemas'
import type { TaskInfo, TaskRequest } from './types'

export const libraryApi = {
  async list() {
    return parseResponse(repositoriesSchema, await api.get('/api/repos'))
  },
  async detail(name: string) {
    return parseResponse(repoDetailSchema, await api.get(`/api/repos/${encodeURIComponent(name)}`))
  },
  async images(name: string, directory: string, page: number, pageSize: number) {
    const params = new URLSearchParams({
      directory,
      page: String(page),
      page_size: String(pageSize),
    })
    return parseResponse(
      imagePageSchema,
      await api.get(`/api/repos/${encodeURIComponent(name)}/images?${params}`),
    )
  },
}

export const taskApi = {
  subscribe(
    onSnapshot: (tasks: TaskInfo[]) => void,
    onConnection: (connected: boolean, invalid?: boolean) => void,
  ) {
    const source = new EventSource('/api/tasks/events')
    source.onopen = () => onConnection(true)
    source.onerror = () => onConnection(false)
    source.addEventListener('snapshot', (event: MessageEvent<string>) => {
      try {
        onSnapshot(parseResponse(tasksSchema, JSON.parse(event.data)))
        onConnection(true)
      } catch {
        onConnection(false, true)
      }
    })
    return source
  },
  async list() {
    return parseResponse(tasksSchema, await api.get('/api/tasks'))
  },
  async submit(payload: TaskRequest) {
    return parseResponse(taskInfoSchema, await api.post('/api/tasks', payload))
  },
  async get(id: string) {
    return parseResponse(taskInfoSchema, await api.get(`/api/tasks/${encodeURIComponent(id)}`))
  },
  async clearCompleted() {
    return parseResponse(clearTasksSchema, await api.delete('/api/tasks/completed'))
  },
}

export const fileApi = {
  async browse(path: string, mode: 'directory' | 'file') {
    const params = new URLSearchParams({ path, mode })
    return parseResponse(fileListingSchema, await api.get(`/api/files?${params}`))
  },
}
