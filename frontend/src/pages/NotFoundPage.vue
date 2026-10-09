<script setup lang="ts">
import { RouterLink } from 'vue-router'

import Button from '@ui/Button.vue'
</script>

<template>
  <main class="grid min-h-dvh place-content-center justify-items-center gap-4 p-6">
    <p class="text-5xl font-semibold text-muted-foreground">404</p>
    <h1 class="text-lg font-medium">页面不存在</h1>
    <RouterLink to="/"><Button>返回仓库列表</Button></RouterLink>
  </main>
</template>
