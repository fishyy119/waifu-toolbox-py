import { useQuery } from '@tanstack/vue-query'

import { libraryApi } from '@/shared/api/client'

export function useRepositories() {
  return useQuery({ queryKey: ['repos'], queryFn: () => libraryApi.list() })
}

export function repoUrl(name: string) {
  return `/api/repos/${encodeURIComponent(name)}`
}

export function repoImageUrl(name: string, relativePath: string) {
  return `${repoUrl(name)}/image?${new URLSearchParams({ relative_path: relativePath })}`
}

export function fileImageUrl(path: string) {
  return `/api/files/image?${new URLSearchParams({ path })}`
}
