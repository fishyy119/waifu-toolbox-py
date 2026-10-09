<script setup lang="ts">
import { ChevronDown, ChevronRight, Folder, FolderOpen } from '@lucide/vue'
import { ref, watch } from 'vue'

import type { DirectoryNode } from '@/shared/api/types'
import Button from '@ui/Button.vue'

const props = defineProps<{ nodes: DirectoryNode[]; selected: string }>()
const emit = defineEmits<{ select: [key: string] }>()
const expanded = ref(new Set<string>())

watch(
  () => props.selected,
  (selected) => {
    for (const node of props.nodes)
      if (selected.startsWith(`${node.key}/`)) expanded.value.add(node.key)
  },
  { immediate: true },
)

function toggle(key: string) {
  if (expanded.value.has(key)) expanded.value.delete(key)
  else expanded.value.add(key)
}

function select(node: DirectoryNode) {
  emit('select', node.key)
  if (node.children.length > 0) toggle(node.key)
}
</script>

<template>
  <div class="space-y-0.5">
    <div v-for="node in nodes" :key="node.key">
      <div
        class="flex min-w-0 items-center rounded-lg"
        :class="selected === node.key ? 'bg-accent text-accent-foreground' : ''"
      >
        <Button
          variant="ghost"
          size="iconSmall"
          :disabled="node.children.length === 0"
          @click="toggle(node.key)"
        >
          <ChevronDown v-if="expanded.has(node.key)" :size="13" /><ChevronRight v-else :size="13" />
        </Button>
        <Button
          variant="ghost"
          size="small"
          class="min-w-0 flex-1 justify-start px-1 text-left"
          :title="node.key"
          @click="select(node)"
        >
          <FolderOpen v-if="selected === node.key" :size="15" class="shrink-0" /><Folder
            v-else
            :size="15"
            class="shrink-0 text-muted-foreground"
          />
          <span class="min-w-0 flex-1 truncate">{{ node.label }}</span
          ><span class="text-[11px] text-muted-foreground tabular-nums">{{ node.count }}</span>
        </Button>
      </div>
      <DirectoryTree
        v-if="expanded.has(node.key) && node.children.length"
        class="ml-3 border-l pl-1"
        :nodes="node.children"
        :selected="selected"
        @select="emit('select', $event)"
      />
    </div>
  </div>
</template>
