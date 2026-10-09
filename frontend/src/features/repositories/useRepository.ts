import { useQuery } from '@tanstack/vue-query'
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { usePreference } from '@/features/preferences/usePreference'
import { useTasks } from '@/features/tasks'
import { libraryApi } from '@/shared/api/client'
import { repoImageUrl } from '@/shared/api/queries'
import type { DirectoryNode } from '@/shared/api/types'
import { useAction } from '@/shared/lib/useAction'

export function useRepository() {
  const route = useRoute()
  const router = useRouter()
  const tasks = useTasks()
  const columns = usePreference('viewerColumns')
  const pageSize = usePreference('viewerPageSize')
  const viewMode = usePreference('viewerViewMode')
  const selectedDirectories = usePreference('selectedDirectories')
  const { busy, error: actionError, run } = useAction()
  const repoName = computed(() => String(route.params.repoName))
  const page = ref(1)
  const updateMode = ref('index')
  const dialog = ref<'rename' | 'path' | 'delete' | null>(null)
  const dialogOpen = computed({
    get: () => dialog.value !== null,
    set: (value: boolean) => {
      if (!value) dialog.value = null
    },
  })
  const newName = ref('')
  const newPath = ref('')
  const confirmation = ref('')
  const { data, isPending, error, refetch } = useQuery({
    queryKey: computed(() => ['repos', repoName.value, 'detail']),
    queryFn: () => libraryApi.detail(repoName.value),
  })
  function flattened(nodes: DirectoryNode[]): DirectoryNode[] {
    return nodes.flatMap((node) => [node, ...flattened(node.children)])
  }
  const directories = computed(() => flattened(data.value?.directories ?? []))
  const selected = computed(() => {
    const saved = selectedDirectories.value[repoName.value]
    return (
      directories.value.find((node) => node.key === saved)?.key ??
      directories.value.find((node) => node.count > 0)?.key ??
      directories.value[0]?.key ??
      ''
    )
  })
  watch([selected, pageSize, repoName], () => {
    page.value = 1
  })
  const {
    data: images,
    isPending: imagesPending,
    error: imagesError,
    refetch: reloadImages,
  } = useQuery({
    queryKey: computed(() => [
      'repos',
      repoName.value,
      'images',
      selected.value,
      page.value,
      pageSize.value,
    ]),
    enabled: computed(() => !!selected.value),
    queryFn: () => libraryApi.images(repoName.value, selected.value, page.value, pageSize.value),
  })
  watch(images, (value) => {
    if (value) page.value = value.page
  })
  const gallery = computed(
    () =>
      images.value?.items.map((image) => ({
        src: repoImageUrl(repoName.value, image.relative_path),
        alt: image.relative_path,
      })) ?? [],
  )
  const pages = computed(() => Math.max(1, Math.ceil((images.value?.total ?? 0) / pageSize.value)))
  const labelMax = computed(() => data.value?.labels[0]?.count ?? 1)
  async function enqueue(kind: 'repo.update' | 'repo.purge' | 'repo.deduplicate' | 'repo.flatten') {
    await run(async () => {
      await tasks.submit(
        kind === 'repo.update'
          ? {
              kind,
              repo_name: repoName.value,
              ccip: ['ccip', 'all'].includes(updateMode.value),
              dreamsim: ['dreamsim', 'all'].includes(updateMode.value),
            }
          : { kind, repo_name: repoName.value },
      )
    })
  }

  function openDialog(kind: 'rename' | 'path' | 'delete') {
    newName.value = repoName.value
    newPath.value = data.value?.info.path ?? ''
    confirmation.value = ''
    actionError.value = ''
    dialog.value = kind
  }

  function refreshPage() {
    void refetch()
    void reloadImages()
  }

  function selectDirectory(name: string, directory: string) {
    selectedDirectories.value = { ...selectedDirectories.value, [name]: directory }
  }

  function forgetRepository(name: string) {
    selectedDirectories.value = Object.fromEntries(
      Object.entries(selectedDirectories.value).filter(([repo]) => repo !== name),
    )
  }

  async function confirm() {
    const operation = dialog.value
    if (!operation) return
    await run(async () => {
      const name = repoName.value
      const directory = selected.value
      const payload =
        operation === 'rename'
          ? { kind: 'repo.rename' as const, repo_name: name, new_name: newName.value.trim() }
          : operation === 'path'
            ? { kind: 'repo.path' as const, repo_name: name, path: newPath.value.trim() }
            : { kind: 'repo.delete' as const, repo_name: name, confirmation: confirmation.value }
      const task = await tasks.submit(payload)
      await tasks.wait(task.id)
      dialog.value = null
      if (payload.kind === 'repo.rename') {
        selectDirectory(payload.new_name, directory)
        forgetRepository(name)
        await router.push(`/repo/${encodeURIComponent(payload.new_name)}`)
      } else if (payload.kind === 'repo.delete') {
        forgetRepository(name)
        await router.push('/')
      } else {
        await refetch()
        await reloadImages()
      }
    })
  }

  return {
    repoName,
    columns,
    pageSize,
    viewMode,
    busy,
    actionError,
    page,
    updateMode,
    dialog,
    dialogOpen,
    newName,
    newPath,
    confirmation,
    data,
    isPending,
    error,
    refetch,
    directories,
    selected,
    images,
    imagesPending,
    imagesError,
    reloadImages,
    gallery,
    pages,
    labelMax,
    enqueue,
    openDialog,
    refreshPage,
    selectDirectory,
    confirm,
  }
}
