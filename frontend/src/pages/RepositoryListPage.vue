<script setup lang="ts">
import { FolderOpen, Plus, RefreshCw } from '@lucide/vue'
import { computed, ref } from 'vue'
import { RouterLink } from 'vue-router'

import FeatureBadge from '@/features/repositories/components/FeatureBadge.vue'
import { useTasks } from '@/features/tasks'
import { useRepositories } from '@/shared/api/queries'
import Field from '@/shared/components/Field.vue'
import PageHeader from '@/shared/components/PageHeader.vue'
import PathPicker from '@/shared/components/PathPicker.vue'
import StatePanel from '@/shared/components/StatePanel.vue'
import { useAction } from '@/shared/lib/useAction'
import Button from '@ui/Button.vue'
import Card from '@ui/Card.vue'
import Checkbox from '@ui/Checkbox.vue'
import Dialog from '@ui/Dialog.vue'
import Input from '@ui/Input.vue'

const { data, isPending, error, refetch } = useRepositories()
const tasks = useTasks()
const { busy, error: actionError, run } = useAction()
const createOpen = ref(false)
const name = ref('')
const path = ref('')
const ccip = ref(false)
const dreamsim = ref(false)
const totalImages = computed(
  () => data.value?.reduce((sum, repo) => sum + repo.total_images, 0) ?? 0,
)

async function createRepo() {
  await run(async () => {
    await tasks.submit({
      kind: 'repo.create',
      repo_name: name.value.trim(),
      path: path.value.trim(),
      ccip: ccip.value,
      dreamsim: dreamsim.value,
    })
    createOpen.value = false
    name.value = ''
    path.value = ''
  })
}
</script>

<template>
  <PageHeader
    title="仓库管理"
    description="将已分类的图片建立索引，作为浏览、分类与相似搜索的基础。"
  >
    <template #actions
      ><Button variant="secondary" title="刷新仓库" @click="refetch()"
        ><RefreshCw :size="16" /></Button
      ><Button @click="createOpen = true"><Plus :size="17" />创建仓库</Button></template
    >
  </PageHeader>
  <div class="mb-6 grid gap-4 sm:grid-cols-3">
    <Card class="p-5"
      ><p class="text-xs text-muted-foreground">仓库总数</p>
      <p class="mt-2 text-3xl font-semibold tabular-nums">{{ data?.length ?? 0 }}</p></Card
    >
    <Card class="p-5"
      ><p class="text-xs text-muted-foreground">已建立索引的图片</p>
      <p class="mt-2 text-3xl font-semibold tabular-nums">
        {{ totalImages.toLocaleString() }}
      </p></Card
    >
    <Card class="p-5"
      ><p class="text-xs text-muted-foreground">当前任务</p>
      <p class="mt-2 text-3xl font-semibold tabular-nums">{{ tasks.activeCount }}</p></Card
    >
  </div>
  <StatePanel :loading="isPending" :error="error" @retry="refetch()">
    <Card v-if="!data?.length" class="grid justify-items-center gap-4 border-dashed px-6 py-16">
      <FolderOpen :size="36" class="text-muted-foreground" />
      <div class="text-center">
        <h2 class="font-semibold">从第一个图片仓库开始</h2>
        <p class="mt-2 text-sm text-muted-foreground">
          仓库的一级子目录会作为图片标签，根目录中的图片不会加入索引。
        </p>
      </div>
      <Button @click="createOpen = true"><Plus :size="16" />创建仓库</Button>
    </Card>
    <div v-else class="grid grid-cols-[repeat(auto-fit,minmax(min(100%,24rem),1fr))] gap-4">
      <RouterLink
        v-for="repo in data"
        :key="repo.name"
        :to="`/repo/${encodeURIComponent(repo.name)}`"
        class="group"
      >
        <Card class="h-full p-5 transition group-hover:border-primary/40 group-hover:shadow-sm">
          <div class="flex items-center gap-3">
            <div class="grid size-10 place-items-center rounded-xl bg-primary/10 text-primary">
              <FolderOpen :size="20" />
            </div>
            <div class="min-w-0">
              <h2 class="truncate font-semibold">{{ repo.name }}</h2>
              <p class="mt-1 truncate font-mono text-xs text-muted-foreground" :title="repo.path">
                {{ repo.path }}
              </p>
            </div>
          </div>
          <div class="mt-5 flex flex-wrap items-center gap-2">
            <span class="mr-2 text-xs text-muted-foreground"
              >{{ repo.total_images.toLocaleString() }} 张图片 · {{ repo.label_count }} 个标签</span
            ><FeatureBadge
              label="CCIP"
              :count="repo.ccip_count"
              :total="repo.total_images"
            /><FeatureBadge
              label="DreamSim"
              :count="repo.dreamsim_count"
              :total="repo.total_images"
            />
          </div>
        </Card>
      </RouterLink>
    </div>
  </StatePanel>
  <Dialog
    v-model:open="createOpen"
    title="创建仓库"
    description="从已分类的图片文件夹创建仓库索引。"
  >
    <form class="mt-5 space-y-5" @submit.prevent="createRepo">
      <Field label="仓库名称" hint="仅允许英文字母、数字和下划线"
        ><Input
          v-model="name"
          required
          pattern="[A-Za-z0-9_]+"
          maxlength="100"
          placeholder="例如 characters"
      /></Field>
      <PathPicker v-model="path" label="图片文件夹" />
      <div class="flex flex-wrap gap-5 text-sm">
        <label class="flex items-center gap-2"><Checkbox v-model="ccip" />提取 CCIP 特征</label
        ><label class="flex items-center gap-2"
          ><Checkbox v-model="dreamsim" />提取 DreamSim 特征</label
        >
      </div>
      <p v-if="actionError" class="text-sm text-destructive">{{ actionError }}</p>
      <div class="flex justify-end gap-2">
        <Button variant="secondary" :disabled="busy" @click="createOpen = false">取消</Button
        ><Button type="submit" :disabled="busy">{{ busy ? '提交中…' : '创建仓库' }}</Button>
      </div>
    </form>
  </Dialog>
</template>
