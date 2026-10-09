<script setup lang="ts">
import { LoaderCircle, RefreshCw, Trash2 } from '@lucide/vue'
import { computed } from 'vue'

import { useTasks } from '@/features/tasks'
import PageHeader from '@/shared/components/PageHeader.vue'
import { useAction } from '@/shared/lib/useAction'
import Button from '@ui/Button.vue'
import Card from '@ui/Card.vue'

const tasks = useTasks()
const { busy, run } = useAction()
const clearable = computed(() =>
  tasks.items.some((task) => ['completed', 'failed'].includes(task.status)),
)
const statuses = {
  pending: { text: '等待中', color: 'bg-muted text-muted-foreground' },
  running: { text: '运行中', color: 'bg-warning/10 text-warning' },
  completed: { text: '已完成', color: 'bg-success/10 text-success' },
  failed: { text: '失败', color: 'bg-destructive/10 text-destructive' },
}

function createdAt(value: string) {
  return new Date(value).toLocaleString()
}
</script>

<template>
  <div>
    <PageHeader title="任务队列" description="操作按提交顺序执行，进度和结果会实时更新。">
      <template #actions
        ><Button variant="secondary" title="刷新任务" @click="tasks.refresh"
          ><RefreshCw :size="16" /></Button
        ><Button
          variant="secondary"
          :disabled="busy || !clearable"
          @click="run(tasks.clearCompleted)"
          ><Trash2 :size="16" />清除已完成</Button
        ></template
      >
    </PageHeader>
    <p v-if="tasks.error" class="mb-4 text-sm text-warning">{{ tasks.error }}</p>
    <Card
      v-if="!tasks.items.length"
      class="border-dashed p-12 text-center text-sm text-muted-foreground"
      >暂无任务。创建仓库或提交图片处理操作后，任务会显示在这里。</Card
    >
    <div class="space-y-3">
      <Card v-for="task in tasks.items" :key="task.id" class="space-y-4 p-5">
        <div class="flex flex-wrap items-start justify-between gap-3">
          <div class="min-w-0">
            <h2 class="flex items-center gap-2 text-sm font-semibold wrap-anywhere">
              <LoaderCircle
                v-if="task.status === 'running'"
                :size="15"
                class="shrink-0 animate-spin text-primary"
              />{{ task.name }}
            </h2>
            <p class="mt-1.5 text-xs text-muted-foreground">{{ createdAt(task.created_at) }}</p>
          </div>
          <span
            class="rounded-md px-2 py-1 text-xs font-medium"
            :class="statuses[task.status].color"
            >{{ statuses[task.status].text }}</span
          >
        </div>
        <div v-if="task.status === 'running'" class="space-y-2">
          <div class="flex justify-between text-xs text-muted-foreground">
            <span>{{ task.progress_desc || '处理中' }}</span
            ><span class="tabular-nums">{{ Math.min(100, Math.round(task.progress * 100)) }}%</span>
          </div>
          <div class="h-2 overflow-hidden rounded-full bg-muted">
            <div
              class="h-full rounded-full bg-primary transition-all"
              :style="{ width: `${Math.min(100, task.progress * 100)}%` }"
            />
          </div>
          <p v-if="task.progress_text" class="text-xs break-all text-muted-foreground">
            {{ task.progress_text }}
          </p>
        </div>
        <p v-if="task.status === 'pending'" class="text-xs text-muted-foreground">
          已加入队列，等待前面的任务完成。
        </p>
        <p
          v-if="task.status === 'failed'"
          class="text-sm wrap-anywhere whitespace-pre-wrap text-destructive"
        >
          {{ task.error }}
        </p>
        <template v-if="task.status === 'completed'"
          ><p class="text-sm whitespace-pre-wrap text-success">
            {{ task.result_text || '任务已完成' }}
          </p>
          <p
            v-if="task.result?.output_path"
            class="font-mono text-xs break-all text-muted-foreground"
          >
            输出目录：{{ task.result.output_path }}
          </p>
          <ul
            v-if="task.result?.details.length"
            class="max-h-64 space-y-1 overflow-auto rounded-lg bg-muted p-3 text-xs leading-5 text-muted-foreground"
          >
            <li v-for="(line, index) in task.result.details" :key="index" class="break-all">
              {{ line }}
            </li>
          </ul></template
        >
      </Card>
    </div>
  </div>
</template>
