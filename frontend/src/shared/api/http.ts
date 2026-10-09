import type { z } from 'zod'

import { apiErrorSchema } from './schemas'

type ApiErrorBody = z.infer<typeof apiErrorSchema>

export class ApiError extends Error {
  readonly code: string
  readonly status: number
  readonly details: unknown

  constructor(status: number, body: ApiErrorBody) {
    super(body.error?.message ?? `请求失败（HTTP ${String(status)}）`)
    this.name = 'ApiError'
    this.status = status
    this.code = body.error?.code ?? 'http_error'
    this.details = body.error?.details
  }
}

interface RequestOptions extends Omit<RequestInit, 'body'> {
  body?: unknown
}

async function request(url: string, options: RequestOptions = {}): Promise<unknown> {
  const { body, ...init } = options
  const headers = new Headers(init.headers)
  if (body !== undefined) headers.set('Content-Type', 'application/json')
  const response = await fetch(url, {
    ...init,
    headers,
    ...(body === undefined ? {} : { body: JSON.stringify(body) }),
  })
  if (!response.ok) {
    let body: ApiErrorBody = {}
    try {
      const parsed = apiErrorSchema.safeParse(await response.json())
      if (parsed.success) body = parsed.data
    } catch {
      // 非 JSON 错误仍由统一 ApiError 表示。
    }
    throw new ApiError(response.status, body)
  }
  if (response.status === 204 || response.headers.get('content-length') === '0') {
    return undefined
  }
  return response.json()
}

export const api = {
  get(url: string): Promise<unknown> {
    return request(url)
  },
  post(url: string, body?: unknown): Promise<unknown> {
    return request(url, { method: 'POST', body })
  },
  put(url: string, body?: unknown): Promise<unknown> {
    return request(url, { method: 'PUT', body })
  },
  delete(url: string): Promise<unknown> {
    return request(url, { method: 'DELETE' })
  },
}
