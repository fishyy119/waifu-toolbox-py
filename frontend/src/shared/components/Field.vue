<script setup lang="ts">
defineProps<{ label: string; hint?: string }>()
</script>

<template>
  <label class="grid min-w-0 gap-2 text-sm">
    <span class="font-medium">{{ label }}</span>
    <slot />
    <span v-if="hint" class="text-xs leading-5 text-muted-foreground">{{ hint }}</span>
  </label>
</template>
