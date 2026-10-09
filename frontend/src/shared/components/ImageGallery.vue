<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from 'vue'

import { masonryLayout } from '@/shared/lib/masonry'
import LightboxGallery from '@ui/LightboxGallery.vue'

const props = withDefaults(
  defineProps<{
    items: { src: string; alt: string }[]
    columns?: number
    mode?: 'grid' | 'masonry'
  }>(),
  { columns: 5, mode: 'grid' },
)
const container = ref<HTMLDivElement>()
const width = ref(0)
const ratios = ref<Record<string, number>>({})
const columns = computed(() => Math.max(1, Math.min(20, props.columns)))
const layout = computed(() =>
  masonryLayout(
    props.items.map((item) => ratios.value[item.src] ?? 1),
    width.value,
    columns.value,
  ),
)
let observer: ResizeObserver | undefined

watch(container, (element) => {
  observer?.disconnect()
  if (!element) return
  width.value = element.clientWidth
  // 列数、窗口宽度、侧栏开合都会改变列宽；列宽变化后需要重新计算坐标。
  observer = new ResizeObserver(() => {
    width.value = element.clientWidth
  })
  observer.observe(element)
})
onBeforeUnmount(() => {
  observer?.disconnect()
})

function loaded(event: Event, src: string) {
  const image = event.currentTarget
  if (image instanceof HTMLImageElement && image.naturalWidth > 0)
    ratios.value[src] = image.naturalHeight / image.naturalWidth
}
</script>

<template>
  <LightboxGallery :items="items">
    <template #default="{ open }">
      <div
        v-if="mode === 'grid'"
        class="grid gap-2"
        :style="{ gridTemplateColumns: `repeat(${columns}, minmax(0, 1fr))` }"
      >
        <img
          v-for="(item, index) in items"
          :key="item.src"
          :src="item.src"
          :alt="item.alt"
          class="aspect-square w-full cursor-zoom-in rounded-lg bg-muted object-cover"
          loading="lazy"
          decoding="async"
          @load="loaded($event, item.src)"
          @click="open(index)"
        />
      </div>
      <div v-else ref="container" class="relative w-full" :style="{ height: `${layout.height}px` }">
        <!-- 完全自绘，不用框架封装后的 img。 -->
        <img
          v-for="(item, index) in items"
          :key="item.src"
          :src="item.src"
          :alt="item.alt"
          class="absolute top-0 left-0 cursor-zoom-in rounded-lg bg-muted object-cover"
          decoding="async"
          :style="{
            width: `${layout.positions[index]?.width ?? 1}px`,
            height: `${layout.positions[index]?.height ?? 1}px`,
            transform: `translate(${layout.positions[index]?.x ?? 0}px, ${layout.positions[index]?.y ?? 0}px)`,
          }"
          @load="loaded($event, item.src)"
          @click="open(index)"
        />
      </div>
    </template>
  </LightboxGallery>
</template>
