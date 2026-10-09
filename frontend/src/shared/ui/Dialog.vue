<script setup lang="ts">
import {
  DialogContent,
  DialogDescription,
  DialogOverlay,
  DialogPortal,
  DialogRoot,
  DialogTitle,
  DialogTrigger,
} from 'reka-ui'
import { computed } from 'vue'

const props = withDefaults(
  defineProps<{
    title?: string
    description?: string
    position?: 'center' | 'top'
    modal?: boolean
    contentClass?: string
    overlayClass?: string
    titleClass?: string
  }>(),
  {
    title: '',
    description: '',
    position: 'center',
    modal: true,
    contentClass: '',
    overlayClass: '',
    titleClass: '',
  },
)

const open = defineModel<boolean>('open', { default: false })
const contentClasses = computed(() =>
  props.position === 'center'
    ? 'border-border bg-card text-card-foreground fixed top-1/2 left-1/2 z-50 w-[calc(100%-2rem)] max-w-lg max-h-[calc(100dvh-2rem)] overflow-y-auto -translate-x-1/2 -translate-y-1/2 rounded-xl border p-6 shadow-2xl'
    : 'border-border bg-popover text-popover-foreground fixed top-16 right-0 left-0 z-50 max-h-[calc(100vh-4rem)] overflow-y-auto border-b shadow-2xl',
)

function close() {
  open.value = false
}
</script>

<template>
  <DialogRoot v-model:open="open" :modal="modal">
    <DialogTrigger v-if="$slots.trigger" as-child>
      <slot name="trigger" />
    </DialogTrigger>
    <DialogPortal>
      <Transition
        enter-active-class="transition duration-150 ease-out"
        enter-from-class="opacity-0"
        enter-to-class="opacity-100"
        leave-active-class="transition duration-100 ease-in"
        leave-from-class="opacity-100"
        leave-to-class="opacity-0"
      >
        <DialogOverlay
          v-if="open"
          force-mount
          class="fixed inset-0 z-40"
          :class="[position === 'center' ? 'bg-overlay/55' : 'bg-overlay/20', overlayClass]"
        />
      </Transition>
      <Transition
        enter-active-class="transition duration-150 ease-out"
        enter-from-class="opacity-0"
        enter-to-class="opacity-100"
        leave-active-class="transition duration-100 ease-in"
        leave-from-class="opacity-100"
        leave-to-class="opacity-0"
      >
        <DialogContent v-if="open" force-mount :class="[contentClasses, contentClass]">
          <DialogTitle v-if="title || $slots.title" class="font-semibold" :class="titleClass">
            <slot name="title">{{ title }}</slot>
          </DialogTitle>
          <DialogDescription
            v-if="description || $slots.description"
            class="mt-2 text-sm leading-6 text-muted-foreground"
          >
            <slot name="description">{{ description }}</slot>
          </DialogDescription>
          <slot :close="close" />
        </DialogContent>
      </Transition>
    </DialogPortal>
  </DialogRoot>
</template>
