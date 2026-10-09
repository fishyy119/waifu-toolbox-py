<script setup lang="ts">
import 'vue-sonner/style.css'

import { Toaster, type ToasterProps } from 'vue-sonner'

const toastOptions = {
  unstyled: true,
  classes: {
    toast: 'flex w-[var(--width)] items-center gap-3 rounded-xl border p-4 shadow-lg',
    default: 'border-border bg-popover text-popover-foreground',
    loading: [
      'border-border border-l-4 border-l-primary',
      'bg-popover text-popover-foreground [&_[data-icon]]:text-primary',
    ].join(' '),
    success: [
      'border-border border-l-4 border-l-success',
      'bg-popover text-popover-foreground [&_[data-icon]]:text-success',
    ].join(' '),
    info: [
      'border-border border-l-4 border-l-primary',
      'bg-popover text-popover-foreground [&_[data-icon]]:text-primary',
    ].join(' '),
    warning: [
      'border-border border-l-4 border-l-warning',
      'bg-popover text-popover-foreground [&_[data-icon]]:text-warning',
    ].join(' '),
    error: [
      'border-border border-l-4 border-l-destructive',
      'bg-popover text-popover-foreground [&_[data-icon]]:text-destructive',
    ].join(' '),
    content: 'grid flex-1 gap-1',
    title: 'text-sm font-medium text-popover-foreground',
    description: 'text-sm text-muted-foreground',
    icon: 'relative flex size-4 shrink-0 items-center justify-start [&_svg]:size-4',
    actionButton: [
      'shrink-0 self-center rounded-lg px-2.5 py-1.5 text-xs font-medium',
      'bg-primary text-primary-foreground hover:bg-primary/90',
    ].join(' '),
    cancelButton: [
      'shrink-0 self-center rounded-lg px-2.5 py-1.5 text-xs font-medium',
      'bg-secondary text-secondary-foreground hover:bg-secondary/80',
    ].join(' '),
  },
} satisfies NonNullable<ToasterProps['toastOptions']>
</script>

<template>
  <Toaster
    theme="system"
    position="top-right"
    :duration="5000"
    :visible-toasts="4"
    :toast-options="toastOptions"
    :style="{ fontFamily: 'inherit' }"
  />
</template>
