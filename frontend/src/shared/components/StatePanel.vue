<script setup lang="ts">
import { LoaderCircle } from '@lucide/vue'

import Button from '@ui/Button.vue'

defineProps<{ loading?: boolean; error?: Error | null; empty?: boolean; emptyText?: string }>()
defineEmits<{ retry: [] }>()
</script>

<template>
  <div
    v-if="loading"
    class="flex min-h-40 items-center justify-center gap-3 text-sm text-muted-foreground"
  >
    <LoaderCircle class="animate-spin" :size="18" />加载中…
  </div>
  <div
    v-else-if="error"
    class="grid justify-items-start gap-3 rounded-xl border border-destructive/25 bg-destructive/5 p-5"
  >
    <p class="text-sm text-destructive">{{ error.message }}</p>
    <Button size="small" variant="secondary" @click="$emit('retry')">重新加载</Button>
  </div>
  <div
    v-else-if="empty"
    class="rounded-xl border border-dashed p-10 text-center text-sm text-muted-foreground"
  >
    {{ emptyText ?? '暂无数据' }}
  </div>
  <slot v-else />
</template>
