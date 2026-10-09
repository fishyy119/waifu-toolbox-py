<script setup lang="ts">
import { Check, Minus } from '@lucide/vue'
import { CheckboxIndicator, CheckboxRoot } from 'reka-ui'

withDefaults(defineProps<{ disabled?: boolean }>(), { disabled: false })
const model = defineModel<boolean | 'indeterminate'>({ default: false })
</script>

<template>
  <CheckboxRoot
    v-model="model"
    :class="[
      'grid size-5 cursor-pointer place-items-center rounded-md',
      'border border-input bg-background shadow-sm',
      'data-[state=checked]:border-primary data-[state=checked]:bg-primary data-[state=checked]:text-primary-foreground',
      'data-[state=indeterminate]:border-primary data-[state=indeterminate]:bg-primary data-[state=indeterminate]:text-primary-foreground',
      'disabled:cursor-not-allowed disabled:opacity-50',
    ]"
    :disabled="disabled"
  >
    <CheckboxIndicator>
      <Minus v-if="model === 'indeterminate'" :size="13" :stroke-width="3" />
      <Check v-else :size="13" :stroke-width="3" />
    </CheckboxIndicator>
  </CheckboxRoot>
</template>
