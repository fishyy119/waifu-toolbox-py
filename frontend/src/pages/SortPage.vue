<script setup lang="ts">
import { Play } from '@lucide/vue'
import { ref } from 'vue'

import { useTasks } from '@/features/tasks'
import PageHeader from '@/shared/components/PageHeader.vue'
import PathPicker from '@/shared/components/PathPicker.vue'
import { useAction } from '@/shared/lib/useAction'
import Button from '@ui/Button.vue'
import Card from '@ui/Card.vue'
import Checkbox from '@ui/Checkbox.vue'

const tasks = useTasks()
const { busy, error, run } = useAction()
const path = ref('')
const avoidSorted = ref(true)
async function submit() {
  await run(async () => {
    await tasks.submit({ kind: 'sort', path: path.value, avoid_sorted: avoidSorted.value })
  })
}
</script>

<template>
  <div>
    <PageHeader title="图片排序" description="基于 DreamSim 感知相似度排序，使相似的图片相邻。" />
    <Card as="form" class="space-y-6 p-5 sm:p-6" @submit.prevent="submit">
      <PathPicker v-model="path" label="图片文件夹" />
      <label class="flex items-center gap-2 text-sm"
        ><Checkbox v-model="avoidSorted" />跳过已排序目录</label
      >
      <div class="rounded-xl bg-muted p-4 text-sm leading-6 text-muted-foreground">
        <p>每个包含图片的目录分别排序，并将图片重命名为目录名前缀和连续编号。</p>
        <p class="mt-1">存在 .nosort 文件的目录会被忽略；子目录仍会分别处理。</p>
      </div>
      <p v-if="error" class="text-sm text-destructive">{{ error }}</p>
      <div class="border-t pt-5">
        <Button type="submit" :disabled="busy || !path"
          ><Play :size="16" />{{ busy ? '提交中…' : '开始排序' }}</Button
        >
      </div>
    </Card>
  </div>
</template>
