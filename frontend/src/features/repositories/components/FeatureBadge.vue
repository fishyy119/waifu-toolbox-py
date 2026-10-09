<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{ label: string; count: number; total: number }>()
const color = computed(() =>
  props.total === 0
    ? 'bg-muted text-muted-foreground'
    : props.count === props.total
      ? 'bg-success/10 text-success'
      : props.count > 0
        ? 'bg-warning/10 text-warning'
        : 'bg-destructive/10 text-destructive',
)
</script>

<template>
  <span class="inline-flex rounded-md px-2 py-1 text-xs font-medium tabular-nums" :class="color">
    {{ label }} {{ count }}/{{ total }}
  </span>
</template>
