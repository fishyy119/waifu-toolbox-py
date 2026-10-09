<script setup lang="ts">
import { ArrowUp, FileImage, Folder, FolderOpen } from '@lucide/vue'
import { useQuery } from '@tanstack/vue-query'
import { computed, ref } from 'vue'

import { fileApi } from '@/shared/api/client'
import Field from '@/shared/components/Field.vue'
import StatePanel from '@/shared/components/StatePanel.vue'
import Button from '@ui/Button.vue'
import Dialog from '@ui/Dialog.vue'
import Input from '@ui/Input.vue'

const props = withDefaults(defineProps<{ label: string; mode?: 'directory' | 'file' }>(), {
  mode: 'directory',
})
const model = defineModel<string>({ default: '' })
const open = ref(false)
const path = ref('')
const typedPath = ref('')
const queryKey = computed(() => ['files', props.mode, path.value])
const { data, isPending, error, refetch } = useQuery({
  queryKey,
  enabled: open,
  queryFn: () => fileApi.browse(path.value, props.mode),
})

function browse() {
  let initial = model.value.trim()
  if (props.mode === 'file' && /\.[a-z0-9]+$/i.test(initial)) {
    initial = initial.slice(0, Math.max(initial.lastIndexOf('/'), initial.lastIndexOf('\\')))
  }
  path.value = initial
  typedPath.value = initial
  open.value = true
}

function navigate(value: string) {
  path.value = value
  typedPath.value = value
}

function select(value: string) {
  model.value = value
  open.value = false
}
</script>

<template>
  <Field :label="label">
    <div class="flex min-w-0 gap-2">
      <Input
        v-model="model"
        :placeholder="mode === 'directory' ? '输入文件夹路径' : '输入图片路径'"
      />
      <Button variant="secondary" title="浏览文件" @click="browse"
        ><FolderOpen :size="17" /><span class="hidden sm:inline">浏览</span></Button
      >
    </div>
  </Field>
  <Dialog
    v-model:open="open"
    :title="mode === 'directory' ? '选择文件夹' : '选择图片'"
    description="浏览服务所在计算机上的文件"
    content-class="max-w-2xl"
  >
    <div class="mt-5 space-y-3">
      <form class="flex gap-2" @submit.prevent="navigate(typedPath)">
        <Input v-model="typedPath" placeholder="输入目录路径后按回车" />
        <Button type="submit" variant="secondary">前往</Button>
      </form>
      <div class="flex flex-wrap items-center gap-2">
        <Button
          size="small"
          variant="ghost"
          :disabled="!data || data.path === data.parent"
          @click="navigate(data?.parent ?? '')"
          ><ArrowUp :size="15" />上一级</Button
        >
        <Button
          v-for="root in data?.roots"
          :key="root"
          size="small"
          variant="ghost"
          @click="navigate(root)"
          >{{ root }}</Button
        >
      </div>
      <p class="font-mono text-xs break-all text-muted-foreground">{{ data?.path ?? path }}</p>
      <div class="h-72 overflow-y-auto rounded-xl border bg-background p-2">
        <StatePanel
          :loading="isPending"
          :error="error"
          :empty="data?.entries.length === 0"
          empty-text="当前目录没有可选择的内容"
          @retry="refetch()"
        >
          <Button
            v-for="entry in data?.entries"
            :key="entry.path"
            variant="ghost"
            class="w-full justify-start text-left"
            @click="entry.is_dir ? navigate(entry.path) : select(entry.path)"
          >
            <Folder v-if="entry.is_dir" :size="17" class="shrink-0 text-primary" /><FileImage
              v-else
              :size="17"
              class="shrink-0 text-muted-foreground"
            />
            <span class="truncate">{{ entry.name }}</span>
          </Button>
        </StatePanel>
      </div>
      <div class="flex justify-end gap-2">
        <Button variant="secondary" @click="open = false">取消</Button>
        <Button
          v-if="mode === 'directory'"
          :disabled="!data || !!error"
          @click="select(data?.path ?? '')"
          >选择当前文件夹</Button
        >
      </div>
    </div>
  </Dialog>
</template>
