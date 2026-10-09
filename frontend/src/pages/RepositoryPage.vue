<script setup lang="ts">
import { ChevronDown, ChevronLeft, ChevronRight, FolderOpen, RefreshCw } from '@lucide/vue'
import { ref } from 'vue'

import DirectoryTree from '@/features/repositories/components/DirectoryTree.vue'
import FeatureBadge from '@/features/repositories/components/FeatureBadge.vue'
import { useRepository } from '@/features/repositories/useRepository'
import Field from '@/shared/components/Field.vue'
import ImageGallery from '@/shared/components/ImageGallery.vue'
import PageHeader from '@/shared/components/PageHeader.vue'
import PathPicker from '@/shared/components/PathPicker.vue'
import StatePanel from '@/shared/components/StatePanel.vue'
import Button from '@ui/Button.vue'
import Card from '@ui/Card.vue'
import Dialog from '@ui/Dialog.vue'
import Input from '@ui/Input.vue'
import NumberInput from '@ui/NumberInput.vue'
import Select from '@ui/Select.vue'

const {
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
} = useRepository()
const showLabels = ref(false)
const updateOptions = [
  { value: 'index', label: '仅同步索引' },
  { value: 'ccip', label: '同步 + CCIP' },
  { value: 'dreamsim', label: '同步 + DreamSim' },
  { value: 'all', label: '同步 + 全部特征' },
]
const viewOptions = [
  { value: 'grid', label: '网格' },
  { value: 'masonry', label: '瀑布流' },
]
</script>

<template>
  <PageHeader :title="repoName" :description="data?.info.path ?? ''">
    <template #actions
      ><Button variant="secondary" :disabled="busy" @click="refreshPage"
        ><RefreshCw :size="16" />刷新</Button
      ></template
    >
  </PageHeader>
  <StatePanel :loading="isPending" :error="error" @retry="refetch()">
    <div v-if="data" class="space-y-5">
      <Card class="space-y-5 p-5">
        <div class="flex flex-wrap items-center gap-3 text-sm">
          <span>{{ data.info.total_images.toLocaleString() }} 张图片</span
          ><span class="text-muted-foreground">{{ data.info.label_count }} 个标签</span
          ><FeatureBadge
            label="CCIP"
            :count="data.info.ccip_count"
            :total="data.info.total_images"
          /><FeatureBadge
            label="DreamSim"
            :count="data.info.dreamsim_count"
            :total="data.info.total_images"
          />
        </div>
        <div class="flex flex-wrap items-center gap-2 border-t pt-4">
          <Select v-model="updateMode" :options="updateOptions" size="small" />
          <Button size="small" variant="secondary" :disabled="busy" @click="enqueue('repo.update')"
            >更新仓库</Button
          >
          <Button
            size="small"
            variant="secondary"
            :disabled="busy"
            title="移除磁盘上已不存在的图片索引"
            @click="enqueue('repo.purge')"
            >清理失效</Button
          >
          <Button
            size="small"
            variant="secondary"
            :disabled="busy"
            title="基于文件哈希删除重复图片"
            @click="enqueue('repo.deduplicate')"
            >去重</Button
          >
          <Button
            size="small"
            variant="secondary"
            :disabled="busy"
            title="将各类别的子目录展平，输出目录会先清空"
            @click="enqueue('repo.flatten')"
            >扁平化</Button
          >
          <div class="ml-auto flex flex-wrap gap-1">
            <Button size="small" variant="ghost" :disabled="busy" @click="openDialog('rename')"
              >重命名</Button
            ><Button size="small" variant="ghost" :disabled="busy" @click="openDialog('path')"
              >修改路径</Button
            ><Button
              size="small"
              variant="ghost"
              class="text-destructive"
              :disabled="busy"
              @click="openDialog('delete')"
              >删除仓库</Button
            >
          </div>
        </div>
      </Card>
      <Card v-if="data.labels.length" class="p-5">
        <Button
          variant="ghost"
          size="small"
          class="w-full justify-between px-0"
          @click="showLabels = !showLabels"
          ><span>标签分布 · {{ data.labels.length }} 个标签</span
          ><ChevronDown :size="16" :class="showLabels ? 'rotate-180' : ''"
        /></Button>
        <div v-if="showLabels" class="mt-4 grid gap-3 sm:grid-cols-2">
          <div
            v-for="label in data.labels.slice(0, 30)"
            :key="label.label"
            class="flex items-center gap-3 text-xs"
            :title="`${label.label}: ${label.count} 张`"
          >
            <span class="w-24 shrink-0 truncate">{{ label.label }}</span>
            <div class="h-2 flex-1 overflow-hidden rounded-full bg-muted">
              <div
                class="h-full rounded-full bg-primary/70"
                :style="{ width: `${(label.count / labelMax) * 100}%` }"
              />
            </div>
            <span class="w-10 text-right text-muted-foreground tabular-nums">{{
              label.count
            }}</span>
          </div>
          <p v-if="data.labels.length > 30" class="text-xs text-muted-foreground sm:col-span-2">
            仅显示数量最多的 30 个标签，共 {{ data.labels.length }} 个。
          </p>
        </div>
      </Card>
      <div class="grid items-start gap-5 xl:grid-cols-[230px_minmax(0,1fr)]">
        <Card class="p-3 xl:sticky xl:top-21"
          ><h2 class="mb-3 flex items-center gap-2 px-2 text-sm font-semibold">
            <FolderOpen :size="16" />目录
          </h2>
          <div class="max-h-72 overflow-y-auto xl:max-h-[calc(100dvh-10rem)]">
            <DirectoryTree
              :nodes="data.directories"
              :selected="selected"
              @select="selectDirectory(repoName, $event)"
            />
            <p v-if="!directories.length" class="p-2 text-xs text-muted-foreground">
              当前索引中暂无可浏览目录。
            </p>
          </div></Card
        >
        <section class="min-w-0 space-y-4">
          <div class="flex flex-wrap items-end gap-3">
            <div class="min-w-0 flex-1">
              <h2 class="truncate text-sm font-semibold">{{ selected || '图片浏览' }}</h2>
              <p class="mt-1 text-xs text-muted-foreground">
                共 {{ images?.total ?? 0 }} 张直属图片
              </p>
            </div>
            <Field label="列数" class="w-20"
              ><NumberInput v-model="columns" :min="1" :max="20"
            /></Field>
            <Field label="每页" class="w-24"
              ><NumberInput v-model="pageSize" :min="10" :max="500" :step="10"
            /></Field>
            <Select v-model="viewMode" :options="viewOptions" class="min-w-28" />
          </div>
          <StatePanel
            :loading="!!selected && imagesPending"
            :error="imagesError"
            :empty="!gallery.length"
            :empty-text="
              selected ? '当前目录无直属图片，请继续选择子目录。' : '当前索引中暂无可浏览目录。'
            "
            @retry="reloadImages()"
            ><ImageGallery :items="gallery" :columns="columns" :mode="viewMode"
          /></StatePanel>
          <div
            v-if="pages > 1"
            class="flex items-center justify-center gap-4 border-t pt-4 text-sm"
          >
            <Button
              variant="secondary"
              size="iconSmall"
              :disabled="page <= 1"
              title="上一页"
              @click="page--"
              ><ChevronLeft :size="16" /></Button
            ><span class="text-muted-foreground tabular-nums">{{ page }} / {{ pages }}</span
            ><Button
              variant="secondary"
              size="iconSmall"
              :disabled="page >= pages"
              title="下一页"
              @click="page++"
              ><ChevronRight :size="16"
            /></Button>
          </div>
        </section>
      </div>
    </div>
  </StatePanel>
  <Dialog
    v-model:open="dialogOpen"
    :title="dialog === 'rename' ? '重命名仓库' : dialog === 'path' ? '修改仓库路径' : '删除仓库'"
    :description="
      dialog === 'delete' ? '仅删除仓库索引和关联图片记录，磁盘上的原始文件会保留。' : ''
    "
  >
    <form class="mt-5 space-y-5" @submit.prevent="confirm">
      <Field v-if="dialog === 'rename'" label="新名称"
        ><Input v-model="newName" required pattern="[A-Za-z0-9_]+" maxlength="100"
      /></Field>
      <PathPicker v-else-if="dialog === 'path'" v-model="newPath" label="新路径" />
      <Field v-else :label="`输入仓库名称以确认：${repoName}`"
        ><Input v-model="confirmation" required autocomplete="off"
      /></Field>
      <p v-if="actionError" class="text-sm text-destructive">{{ actionError }}</p>
      <div class="flex justify-end gap-2">
        <Button variant="secondary" :disabled="busy" @click="dialog = null">取消</Button
        ><Button
          type="submit"
          :variant="dialog === 'delete' ? 'danger' : 'primary'"
          :disabled="
            busy ||
            (dialog === 'delete' && confirmation !== repoName) ||
            (dialog === 'rename' && newName.trim() === repoName)
          "
          >{{ busy ? '处理中…' : dialog === 'delete' ? '删除仓库' : '确认' }}</Button
        >
      </div>
    </form>
  </Dialog>
</template>
