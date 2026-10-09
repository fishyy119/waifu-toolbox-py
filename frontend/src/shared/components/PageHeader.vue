<script setup lang="ts">
defineProps<{ title: string; description?: string }>()
</script>

<template>
  <header class="mb-6 flex flex-wrap items-start justify-between gap-4">
    <div class="min-w-0 flex-1 space-y-1.5">
      <h1 class="text-2xl font-semibold tracking-tight wrap-anywhere">{{ title }}</h1>
      <p v-if="description" class="text-sm leading-6 wrap-anywhere text-muted-foreground">
        {{ description }}
      </p>
    </div>
    <div v-if="$slots.actions" class="flex flex-wrap items-center gap-2">
      <slot name="actions" />
    </div>
  </header>
</template>
