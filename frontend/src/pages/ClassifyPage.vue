<script setup lang="ts">
import { Play } from '@lucide/vue'
import { computed, ref, watch } from 'vue'

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
import NumberInput from '@ui/NumberInput.vue'
import Select from '@ui/Select.vue'

const tasks = useTasks()
const { data, isPending, error, refetch } = useRepositories()
const { busy, error: actionError, run } = useAction()
const mode = ref('reference')
const repoName = ref('')
const path = ref('')
const numReferences = ref(20)
const inplace = ref(false)
const options = computed(
  () => data.value?.map((repo) => ({ value: repo.name, label: repo.name })) ?? [],
)
watch(
  data,
  (repos) => {
    if (!repos?.some((repo) => repo.name === repoName.value))
      repoName.value = repos?.[0]?.name ?? ''
  },
  { immediate: true },
)

async function submit() {
  await run(async () => {
    await tasks.submit(
      mode.value === 'reference'
        ? {
            kind: 'classify.reference',
            repo_name: repoName.value,
            path: path.value,
            num_references: numReferences.value,
          }
        : { kind: 'classify.cluster', path: path.value, inplace: inplace.value },
    )
  })
}
</script>

<template>
  <div>
    <PageHeader title="图片分类" description="使用 CCIP 特征聚类，将未标注图片按角色整理。" />
    <Card as="form" class="space-y-6 p-5 sm:p-6" @submit.prevent="submit">
      <div class="flex flex-wrap gap-2">
        <Button
          :variant="mode === 'reference' ? 'primary' : 'secondary'"
          @click="mode = 'reference'"
          >参考仓库分类</Button
        ><Button :variant="mode === 'cluster' ? 'primary' : 'secondary'" @click="mode = 'cluster'"
          >独立聚类</Button
        >
      </div>
      <p class="text-sm leading-6 text-muted-foreground">
        {{
          mode === 'reference'
            ? '参考仓库中已提取 CCIP 特征的图片，为待整理图片寻找角色标签，结果输出到报告目录。'
            : '不依赖参考仓库，按角色特征将图片聚集到不同目录。'
        }}
      </p>
      <StatePanel
        v-if="mode === 'reference'"
        :loading="isPending"
        :error="error"
        :empty="options.length === 0"
        empty-text="暂无参考仓库，请先创建仓库并提取 CCIP 特征，或使用独立聚类。"
        @retry="refetch()"
      >
        <div class="grid gap-5 sm:grid-cols-2">
          <Field label="参考仓库"><Select v-model="repoName" :options="options" /></Field
          ><Field label="每类参考数量" hint="数量越多，计算所需时间越长"
            ><NumberInput v-model="numReferences" :min="5" :max="100" :step="5"
          /></Field>
        </div>
      </StatePanel>
      <PathPicker v-model="path" label="待分类图片文件夹" />
      <label v-if="mode === 'cluster'" class="flex items-center gap-2 text-sm"
        ><Checkbox v-model="inplace" />原地分类（移动文件而非复制）</label
      >
      <p v-if="actionError" class="text-sm text-destructive">{{ actionError }}</p>
      <div class="border-t pt-5">
        <Button type="submit" :disabled="busy || !path || (mode === 'reference' && !repoName)"
          ><Play :size="16" />{{
            busy ? '提交中…' : mode === 'reference' ? '开始分类' : '开始聚类'
          }}</Button
        >
      </div>
    </Card>
  </div>
</template>
