<script setup lang="ts">
import {
  ArrowUpDown,
  ChevronRight,
  FolderOpen,
  Image,
  Layers,
  ListChecks,
  Menu,
  Search,
  Settings,
  X,
} from '@lucide/vue'
import { onBeforeUnmount, onMounted, ref } from 'vue'
import { RouterLink, RouterView, useRoute } from 'vue-router'

import { favicon } from '@/app/branding'
import { useTaskEffects } from '@/app/useTaskEffects'
import { useTasks } from '@/features/tasks'
import Button from '@ui/Button.vue'

const route = useRoute()
const tasks = useTasks()
useTaskEffects()
const drawer = ref(false)
const navigation = [
  { href: '/', label: '仓库管理', icon: FolderOpen },
  { href: '/classify', label: '图片分类', icon: Layers },
  { href: '/sort', label: '图片排序', icon: ArrowUpDown },
  { href: '/convert', label: '格式转换', icon: Image },
  { href: '/search', label: '相似搜索', icon: Search },
  { href: '/tasks', label: '任务队列', icon: ListChecks },
  { href: '/settings', label: '设置', icon: Settings },
]

function active(href: string) {
  return href === '/' ? route.path === '/' || route.path.startsWith('/repo/') : route.path === href
}

onMounted(() => {
  tasks.connect()
})
onBeforeUnmount(() => {
  tasks.disconnect()
})
</script>

<template>
  <div class="min-h-dvh">
    <div v-if="drawer" class="fixed inset-0 z-30 bg-overlay/40 lg:hidden" @click="drawer = false" />
    <aside
      :class="[
        'fixed inset-y-0 left-0 z-40 flex w-60 flex-col border-r bg-sidebar px-4 py-5',
        'transition-transform lg:translate-x-0',
        drawer ? 'translate-x-0' : '-translate-x-full',
      ]"
    >
      <RouterLink to="/" class="mb-8 flex items-center gap-3 px-2" @click="drawer = false">
        <img :src="favicon" class="size-10 rounded-xl" alt="" />
        <div>
          <p class="text-sm font-semibold">Waifu Toolbox</p>
          <p class="mt-0.5 text-xs text-muted-foreground">图片整理工作台</p>
        </div>
      </RouterLink>
      <nav class="space-y-1">
        <RouterLink
          v-for="item in navigation"
          :key="item.href"
          :to="item.href"
          :class="[
            'flex min-h-11 items-center gap-3 rounded-xl px-3 text-sm font-medium transition',
            active(item.href)
              ? 'bg-sidebar-accent text-sidebar-accent-foreground'
              : 'text-muted-foreground hover:bg-muted hover:text-foreground',
          ]"
          @click="drawer = false"
        >
          <component :is="item.icon" :size="18" /><span class="flex-1">{{ item.label }}</span>
          <span
            v-if="item.href === '/tasks' && tasks.activeCount"
            class="rounded-md bg-primary/10 px-1.5 py-0.5 text-xs tabular-nums"
            >{{ tasks.activeCount }}</span
          >
        </RouterLink>
      </nav>
      <RouterLink to="/tasks" class="mt-auto rounded-xl border bg-background p-3.5">
        <div class="mb-2 flex items-center gap-2 text-xs font-medium">
          <span
            class="size-1.5 rounded-full"
            :class="tasks.connected ? 'bg-success' : 'bg-warning'"
          />
          {{ tasks.activeCount ? `${tasks.activeCount} 项任务进行中` : '任务队列空闲'
          }}<ChevronRight class="ml-auto" :size="14" />
        </div>
        <p class="truncate text-xs text-muted-foreground">
          {{ tasks.running?.name ?? (tasks.connected ? '准备好整理下一组图片' : '正在连接服务…') }}
        </p>
        <div v-if="tasks.running" class="mt-3 h-1.5 overflow-hidden rounded-full bg-muted">
          <div
            class="h-full bg-primary transition-all"
            :style="{ width: `${Math.min(100, tasks.running.progress * 100)}%` }"
          />
        </div>
      </RouterLink>
    </aside>
    <div class="lg:pl-60">
      <header
        class="sticky top-0 z-20 flex h-16 items-center gap-3 border-b bg-background/95 px-5 backdrop-blur sm:px-8"
      >
        <Button
          variant="ghost"
          size="iconSmall"
          class="lg:hidden"
          title="切换导航"
          @click="drawer = !drawer"
          ><X v-if="drawer" :size="19" /><Menu v-else :size="19"
        /></Button>
        <span class="text-xs text-muted-foreground">工作台</span
        ><ChevronRight :size="13" class="text-muted-foreground" />
        <span class="text-sm font-medium">{{ route.meta.title }}</span>
        <RouterLink to="/tasks" class="ml-auto text-xs text-muted-foreground">{{
          tasks.activeCount ? `${tasks.activeCount} 项任务` : '就绪'
        }}</RouterLink>
      </header>
      <main class="p-5 sm:p-8"><RouterView /></main>
    </div>
  </div>
</template>
