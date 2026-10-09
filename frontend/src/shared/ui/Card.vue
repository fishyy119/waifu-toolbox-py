<script setup lang="ts">
withDefaults(
  defineProps<{
    as?: 'div' | 'section' | 'article' | 'aside' | 'form' | 'button'
  }>(),
  { as: 'div' },
)
</script>

<template>
  <component :is="as" class="rounded-xl border border-border bg-card text-card-foreground">
    <slot />
  </component>
</template>
