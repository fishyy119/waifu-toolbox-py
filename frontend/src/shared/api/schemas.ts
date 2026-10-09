import { z } from 'zod'

const count = z.number().int().nonnegative()

export const repoInfoSchema = z.object({
  name: z.string(),
  path: z.string(),
  total_images: count,
  label_count: count,
  ccip_count: count,
  dreamsim_count: count,
})
export const repositoriesSchema = z.array(repoInfoSchema)

export interface DirectoryNode {
  key: string
  label: string
  count: number
  children: DirectoryNode[]
}

export const directoryNodeSchema: z.ZodType<DirectoryNode> = z.lazy(() =>
  z.object({
    key: z.string(),
    label: z.string(),
    count,
    children: z.array(directoryNodeSchema),
  }),
)

export const repoDetailSchema = z.object({
  info: repoInfoSchema,
  directories: z.array(directoryNodeSchema),
  labels: z.array(z.object({ label: z.string(), count })),
})

export const imagePageSchema = z.object({
  items: z.array(z.object({ relative_path: z.string(), label: z.string() })),
  total: count,
  page: z.number().int().positive(),
  page_size: z.number().int().min(10).max(500),
})

export const searchResultSchema = z.object({
  rank: z.number().int().positive(),
  path: z.string(),
  label: z.string(),
  similarity: z.number(),
})

export const taskInfoSchema = z.object({
  id: z.string(),
  name: z.string(),
  kind: z.enum([
    'repo.create',
    'repo.update',
    'repo.purge',
    'repo.deduplicate',
    'repo.flatten',
    'repo.rename',
    'repo.path',
    'repo.delete',
    'classify.reference',
    'classify.cluster',
    'sort',
    'convert',
    'search',
    'cache.clear',
  ]),
  status: z.enum(['pending', 'running', 'completed', 'failed']),
  progress: z.number(),
  progress_desc: z.string(),
  progress_text: z.string(),
  result_text: z.string(),
  error: z.string(),
  result: z
    .object({
      details: z.array(z.string()),
      output_path: z.string().nullable(),
      counts: z.record(z.string(), count),
      search_results: z.array(searchResultSchema),
    })
    .nullable(),
  created_at: z.string(),
})
export const tasksSchema = z.array(taskInfoSchema)
export const clearTasksSchema = z.object({ removed: count })

export const fileListingSchema = z.object({
  path: z.string(),
  parent: z.string(),
  roots: z.array(z.string()),
  entries: z.array(z.object({ name: z.string(), path: z.string(), is_dir: z.boolean() })),
})

export const apiErrorSchema = z.object({
  error: z
    .object({ code: z.string().optional(), message: z.string().optional(), details: z.unknown() })
    .optional(),
})

export function parseResponse<T>(schema: z.ZodType<T>, value: unknown): T {
  const result = schema.safeParse(value)
  if (!result.success) throw new Error('服务返回的数据不符合预期，请刷新后重试')
  return result.data
}
