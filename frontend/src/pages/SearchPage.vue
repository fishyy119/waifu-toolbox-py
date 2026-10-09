<script setup lang="ts">
import { LoaderCircle, Search } from '@lucide/vue'
import { computed, watch } from 'vue'

import { useSearch } from '@/features/search'
import { fileImageUrl, useRepositories } from '@/shared/api/queries'
import Field from '@/shared/components/Field.vue'
import PageHeader from '@/shared/components/PageHeader.vue'
import PathPicker from '@/shared/components/PathPicker.vue'
import StatePanel from '@/shared/components/StatePanel.vue'
import Button from '@ui/Button.vue'
import Card from '@ui/Card.vue'
import Checkbox from '@ui/Checkbox.vue'
import LightboxGallery from '@ui/LightboxGallery.vue'
import NumberInput from '@ui/NumberInput.vue'
import Select from '@ui/Select.vue'

const search = useSearch()
const { data, isPending, error, refetch } = useRepositories()
const options = computed(
  () => data.value?.map((repo) => ({ value: repo.name, label: repo.name })) ?? [],
)
watch(
  data,
  (repos) => {
    if (!repos?.some((repo) => repo.name === search.form.repo_name))
      search.form.repo_name = repos?.[0]?.name ?? ''
  },
  { immediate: true },
)
const gallery = computed(() =>
  search.results.map((item) => ({ src: fileImageUrl(item.path), alt: item.path })),
)
</script>

<template>
  <PageHeader
    title="相似图片搜索"
    description="基于 DreamSim 特征，在仓库中寻找与查询图片最相似的结果。"
  />
  <Card as="form" class="mb-6 space-y-5 p-5 sm:p-6" @submit.prevent="search.search">
    <StatePanel
      :loading="isPending"
      :error="error"
      :empty="options.length === 0"
      empty-text="暂无可搜索的仓库，请先创建仓库并提取 DreamSim 特征。"
      @retry="refetch()"
    >
      <div class="grid gap-5 md:grid-cols-2">
        <Field label="搜索仓库"
          ><Select v-model="search.form.repo_name" :options="options"
        /></Field>
        <Field label="结果数量"
          ><NumberInput v-model="search.form.top_k" :min="1" :max="50"
        /></Field>
      </div>
    </StatePanel>
    <PathPicker v-model="search.form.path" label="查询图片" mode="file" />
    <div class="flex flex-wrap items-center justify-between gap-4">
      <label class="flex items-center gap-2 text-sm"
        ><Checkbox v-model="search.form.skip_update" />跳过自动更新索引</label
      ><Button
        type="submit"
        :disabled="search.loading || !search.form.repo_name || !search.form.path"
        ><LoaderCircle v-if="search.loading" class="animate-spin" :size="16" /><Search
          v-else
          :size="16"
        />{{ search.loading ? '搜索中…' : '搜索' }}</Button
      >
    </div>
  </Card>
  <p v-if="search.loading" class="mb-5 text-sm text-muted-foreground">
    搜索已加入任务队列，正在等待或执行。切换页面后仍会保留结果。
  </p>
  <p
    v-if="search.error"
    class="mb-5 rounded-xl border border-destructive/25 bg-destructive/5 p-4 text-sm text-destructive"
  >
    {{ search.error }}
  </p>
  <p v-if="search.results.length" class="mb-4 text-sm font-medium">
    Top {{ search.results.length }} 结果
  </p>
  <LightboxGallery v-if="search.results.length" :items="gallery">
    <template #default="{ open }"
      ><div class="grid grid-cols-[repeat(auto-fit,minmax(min(100%,16rem),1fr))] gap-4">
        <Card
          v-for="(result, index) in search.results"
          :key="`${result.rank}-${result.path}`"
          class="overflow-hidden"
          ><div class="relative">
            <img
              :src="fileImageUrl(result.path)"
              :alt="result.label"
              class="aspect-square w-full cursor-zoom-in bg-muted object-cover"
              loading="lazy"
              @click="open(index)"
            /><span
              class="absolute top-3 left-3 rounded-lg bg-overlay/65 px-2 py-1 text-xs text-overlay-foreground"
              >#{{ result.rank }}</span
            >
          </div>
          <div class="space-y-2 p-4">
            <div class="flex items-center justify-between gap-2">
              <p class="truncate text-sm font-semibold">{{ result.label }}</p>
              <span class="rounded-md bg-primary/10 px-2 py-1 text-xs text-primary tabular-nums">{{
                result.similarity.toFixed(4)
              }}</span>
            </div>
            <p class="text-xs leading-5 break-all text-muted-foreground">{{ result.path }}</p>
          </div></Card
        >
      </div></template
    >
  </LightboxGallery>
  <div
    v-else-if="!search.loading && !search.error"
    class="rounded-xl border border-dashed p-12 text-center text-sm text-muted-foreground"
  >
    选择仓库和查询图片，开始寻找相似图片。
  </div>
</template>
