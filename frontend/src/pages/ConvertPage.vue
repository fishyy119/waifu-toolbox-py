<script setup lang="ts">
import { Play } from '@lucide/vue'
import { ref } from 'vue'

import { useTasks } from '@/features/tasks'
import Field from '@/shared/components/Field.vue'
import PageHeader from '@/shared/components/PageHeader.vue'
import PathPicker from '@/shared/components/PathPicker.vue'
import { useAction } from '@/shared/lib/useAction'
import Button from '@ui/Button.vue'
import Card from '@ui/Card.vue'
import Checkbox from '@ui/Checkbox.vue'
import Select from '@ui/Select.vue'

const tasks = useTasks()
const { busy, error, run } = useAction()
const path = ref('')
const sourceFormat = ref('bmp')
const replace = ref(false)
const formats = ['bmp', 'jpg', 'jpeg', 'png'].map((value) => ({
  value,
  label: value.toUpperCase(),
}))
async function submit() {
  await run(async () => {
    await tasks.submit({
      kind: 'convert',
      path: path.value,
      source_format: sourceFormat.value,
      replace: replace.value,
    })
  })
}
</script>

<template>
  <div>
    <PageHeader
      title="格式转换"
      description="将图片批量转换为 WebP，递归处理所选文件夹中的源格式图片。"
    />
    <Card as="form" class="space-y-6 p-5 sm:p-6" @submit.prevent="submit">
      <div class="grid gap-6 md:grid-cols-2">
        <PathPicker v-model="path" label="图片文件夹" />
        <Field label="源格式"><Select v-model="sourceFormat" :options="formats" /></Field>
      </div>
      <label class="flex items-center gap-2 text-sm"
        ><Checkbox v-model="replace" />转换成功后删除原文件</label
      >
      <p class="rounded-xl bg-muted p-4 text-sm leading-6 text-muted-foreground">
        输出文件使用相同文件名和 .webp
        扩展名，保存在原图片所在目录。转换失败的文件会保留，并在任务结果中记录。
      </p>
      <p v-if="error" class="text-sm text-destructive">{{ error }}</p>
      <div class="border-t pt-5">
        <Button type="submit" :disabled="busy || !path"
          ><Play :size="16" />{{ busy ? '提交中…' : '开始转换' }}</Button
        >
      </div>
    </Card>
  </div>
</template>
