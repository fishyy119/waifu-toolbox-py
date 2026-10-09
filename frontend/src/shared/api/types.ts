import type { z } from 'zod'

import type {
  fileListingSchema,
  imagePageSchema,
  repoDetailSchema,
  repoInfoSchema,
  searchResultSchema,
  taskInfoSchema,
} from './schemas'

export type { DirectoryNode } from './schemas'
export type RepoInfo = z.infer<typeof repoInfoSchema>
export type RepoDetail = z.infer<typeof repoDetailSchema>
export type ImagePage = z.infer<typeof imagePageSchema>
export type TaskInfo = z.infer<typeof taskInfoSchema>
export type SearchResult = z.infer<typeof searchResultSchema>
export type FileListing = z.infer<typeof fileListingSchema>

export type TaskRequest =
  | { kind: 'repo.create'; repo_name: string; path: string; ccip: boolean; dreamsim: boolean }
  | { kind: 'repo.update'; repo_name: string; ccip: boolean; dreamsim: boolean }
  | { kind: 'repo.purge' | 'repo.deduplicate' | 'repo.flatten'; repo_name: string }
  | { kind: 'repo.rename'; repo_name: string; new_name: string }
  | { kind: 'repo.path'; repo_name: string; path: string }
  | { kind: 'repo.delete'; repo_name: string; confirmation: string }
  | { kind: 'classify.reference'; repo_name: string; path: string; num_references: number }
  | { kind: 'classify.cluster'; path: string; inplace: boolean }
  | { kind: 'sort'; path: string; avoid_sorted: boolean }
  | { kind: 'convert'; path: string; source_format: string; replace: boolean }
  | { kind: 'search'; repo_name: string; path: string; top_k: number; skip_update: boolean }
  | { kind: 'cache.clear'; ccip: boolean; dreamsim: boolean }
