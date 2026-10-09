<script setup lang="ts">
import {
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogOverlay,
  AlertDialogPortal,
  AlertDialogRoot,
  AlertDialogTitle,
} from 'reka-ui'

import Button from '@ui/Button.vue'

defineProps<{
  open: boolean
  title: string
  description: string
  confirmText?: string
  busy?: boolean
}>()

const emit = defineEmits<{ close: []; confirm: [] }>()

function updateOpen(open: boolean) {
  if (!open) emit('close')
}
</script>

<template>
  <AlertDialogRoot :open="open" @update:open="updateOpen">
    <AlertDialogPortal>
      <Transition
        enter-active-class="transition duration-150 ease-out"
        enter-from-class="opacity-0"
        enter-to-class="opacity-100"
        leave-active-class="transition duration-100 ease-in"
        leave-from-class="opacity-100"
        leave-to-class="opacity-0"
      >
        <AlertDialogOverlay v-if="open" force-mount class="fixed inset-0 z-40 bg-overlay/55" />
      </Transition>
      <Transition
        enter-active-class="transition duration-150 ease-out"
        enter-from-class="scale-[0.98] opacity-0"
        enter-to-class="scale-100 opacity-100"
        leave-active-class="transition duration-100 ease-in"
        leave-from-class="scale-100 opacity-100"
        leave-to-class="scale-[0.98] opacity-0"
      >
        <AlertDialogContent
          v-if="open"
          force-mount
          :class="[
            'fixed top-1/2 left-1/2 z-50 w-[calc(100%-2rem)] max-w-md',
            '-translate-x-1/2 -translate-y-1/2',
            'rounded-xl border border-border bg-card p-6 text-card-foreground shadow-2xl',
          ]"
        >
          <AlertDialogTitle class="text-lg font-semibold">{{ title }}</AlertDialogTitle>
          <AlertDialogDescription class="mt-2 text-sm leading-6 text-muted-foreground">
            {{ description }}
          </AlertDialogDescription>
          <div class="mt-6 flex justify-end gap-2">
            <AlertDialogCancel as-child>
              <Button variant="secondary" :disabled="busy">取消</Button>
            </AlertDialogCancel>
            <Button variant="danger" :disabled="busy" @click="emit('confirm')">
              {{ busy ? '处理中…' : (confirmText ?? '确认') }}
            </Button>
          </div>
        </AlertDialogContent>
      </Transition>
    </AlertDialogPortal>
  </AlertDialogRoot>
</template>
