<script setup lang="ts">
import { RouterView } from 'vue-router'

import UiProvider from '@ui/UiProvider.vue'
</script>

<template>
  <UiProvider>
    <RouterView />
  </UiProvider>
</template>
