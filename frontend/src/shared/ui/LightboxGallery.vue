<script lang="ts">
export interface LightboxItem {
  src: string
  alt: string
}
</script>

<script setup lang="ts">
import {
  DialogContent,
  DialogDescription,
  DialogOverlay,
  DialogPortal,
  DialogRoot,
  DialogTitle,
} from 'reka-ui'
import { computed, ref, watch } from 'vue'

const WHEEL_NAVIGATION_THRESHOLD_PX = 40

const props = withDefaults(
  defineProps<{
    items: readonly LightboxItem[]
    activeIndex?: number
  }>(),
  { activeIndex: 0 },
)

defineSlots<{
  default(props: { open: (index?: number) => void }): unknown
}>()

const emit = defineEmits<{
  change: [index: number]
}>()

const lightboxOpen = ref(false)
const currentIndex = ref(0)
const currentItem = computed(() => props.items[currentIndex.value])

let wheelDelta = 0
let wheelDirection = 0

function normalizedIndex(index: number) {
  if (!Number.isInteger(index)) return 0
  return Math.min(Math.max(index, 0), Math.max(props.items.length - 1, 0))
}

function openLightbox(index = 0) {
  if (props.items.length === 0) return

  const nextIndex = normalizedIndex(index)
  currentIndex.value = nextIndex
  lightboxOpen.value = true

  if (nextIndex !== normalizedIndex(props.activeIndex)) emit('change', nextIndex)
}

function closeLightbox() {
  lightboxOpen.value = false
}

function resetWheelNavigation() {
  wheelDelta = 0
  wheelDirection = 0
}

function normalizedWheelDelta(event: WheelEvent) {
  if (event.deltaMode === WheelEvent.DOM_DELTA_LINE) return event.deltaY * 16
  if (event.deltaMode === WheelEvent.DOM_DELTA_PAGE) return event.deltaY * window.innerHeight
  return event.deltaY
}

function handleWheel(event: WheelEvent) {
  if (props.items.length <= 1 || event.deltaY === 0) return

  event.preventDefault()

  const delta = normalizedWheelDelta(event)
  const direction = Math.sign(delta)
  if (direction !== wheelDirection) {
    wheelDelta = 0
    wheelDirection = direction
  }

  wheelDelta += delta
  if (Math.abs(wheelDelta) < WHEEL_NAVIGATION_THRESHOLD_PX) return

  const nextIndex = currentIndex.value + (wheelDelta < 0 ? -1 : 1)
  resetWheelNavigation()
  if (nextIndex < 0 || nextIndex >= props.items.length) return

  currentIndex.value = nextIndex
  emit('change', nextIndex)
}

watch(
  () => props.activeIndex,
  (index) => {
    currentIndex.value = normalizedIndex(index)
  },
)

watch(
  () => props.items,
  () => {
    if (props.items.length === 0) {
      closeLightbox()
      return
    }

    currentIndex.value = normalizedIndex(props.activeIndex)
  },
)

watch(lightboxOpen, (open) => {
  if (!open) resetWheelNavigation()
})
</script>

<template>
  <DialogRoot v-model:open="lightboxOpen">
    <slot :open="openLightbox" />

    <DialogPortal>
      <DialogOverlay class="fixed inset-0 z-40 bg-overlay/80" />
      <DialogContent
        class="artwork-lightbox fixed inset-0 z-50 overflow-hidden text-overlay-foreground outline-none"
      >
        <DialogTitle class="sr-only">作品预览</DialogTitle>
        <DialogDescription class="sr-only">全屏查看当前作品</DialogDescription>
        <div
          class="relative flex size-full items-center justify-center p-4 sm:p-8"
          @click.self="closeLightbox"
          @wheel="handleWheel"
        >
          <img
            v-if="currentItem"
            class="block h-auto max-h-full w-auto max-w-full object-contain"
            :src="currentItem.src"
            :alt="currentItem.alt"
            decoding="async"
            draggable="false"
          />
          <output
            class="absolute top-4 left-4 rounded-full bg-overlay/65 px-3 py-1 text-sm text-overlay-foreground tabular-nums sm:top-6 sm:left-6"
          >
            {{ currentIndex + 1 }} / {{ items.length }}
          </output>
        </div>
      </DialogContent>
    </DialogPortal>
  </DialogRoot>
</template>
