<script setup lang="ts">
import { Check, ChevronDown } from '@lucide/vue'
import {
  SelectContent,
  SelectItem,
  SelectItemIndicator,
  SelectItemText,
  SelectPortal,
  SelectRoot,
  SelectTrigger,
  SelectValue,
  SelectViewport,
} from 'reka-ui'

export interface SelectOption {
  value: string
  label: string
  disabled?: boolean
}

withDefaults(
  defineProps<{
    options: readonly SelectOption[]
    placeholder?: string
    disabled?: boolean
    size?: 'default' | 'small'
  }>(),
  { placeholder: '请选择', disabled: false, size: 'default' },
)

const model = defineModel<string>({ default: '' })
</script>

<template>
  <SelectRoot v-model="model" :disabled="disabled">
    <SelectTrigger
      class="flex cursor-pointer items-center justify-between border border-input bg-background text-sm text-foreground disabled:cursor-not-allowed disabled:opacity-50"
      :class="
        size === 'small'
          ? 'min-h-9 min-w-24 gap-2 rounded-lg px-3 py-1'
          : 'min-h-10 min-w-40 gap-3 rounded-xl px-3 py-2'
      "
    >
      <SelectValue :placeholder="placeholder" />
      <ChevronDown class="shrink-0 text-muted-foreground" :size="16" />
    </SelectTrigger>
    <SelectPortal>
      <SelectContent
        position="popper"
        :class="[
          'z-50 min-w-(--reka-select-trigger-width) origin-(--reka-select-content-transform-origin) overflow-hidden rounded-xl',
          'border border-border bg-popover p-1 text-popover-foreground shadow-xl',
        ]"
        data-app-floating-content
        :side-offset="4"
      >
        <SelectViewport>
          <SelectItem
            v-for="option in options"
            :key="option.value"
            :value="option.value"
            :disabled="option.disabled === true"
            :class="[
              'relative flex min-h-9 items-center rounded-lg py-1.5 pr-8 pl-3',
              'cursor-pointer text-sm outline-none',
              'data-highlighted:bg-accent data-highlighted:text-accent-foreground',
              'data-disabled:pointer-events-none data-disabled:opacity-50',
            ]"
          >
            <SelectItemText>{{ option.label }}</SelectItemText>
            <SelectItemIndicator class="absolute right-2 inline-flex items-center text-primary">
              <Check :size="15" :stroke-width="2.5" />
            </SelectItemIndicator>
          </SelectItem>
        </SelectViewport>
      </SelectContent>
    </SelectPortal>
  </SelectRoot>
</template>
