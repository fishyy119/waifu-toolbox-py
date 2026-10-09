<script setup lang="ts">
import { useTasks } from '@/features/tasks'
import PageHeader from '@/shared/components/PageHeader.vue'
import { useAction } from '@/shared/lib/useAction'
import Button from '@ui/Button.vue'
import Card from '@ui/Card.vue'

const tasks = useTasks()
const { busy, error, run } = useAction()

async function clear(ccip = false, dreamsim = false) {
  await run(async () => {
    await tasks.submit({ kind: 'cache.clear', ccip, dreamsim })
  })
}
</script>

<template>
  <div>
    <PageHeader title="设置" description="管理图片特征缓存。" />
    <Card class="space-y-5 p-5 sm:p-6"
      ><div>
        <h2 class="text-sm font-semibold">特征缓存</h2>
        <p class="mt-2 text-sm leading-6 text-muted-foreground">
          清空缓存后，下次提取图片特征时会重新计算。仓库中已保存的索引和特征会保留。
        </p>
      </div>
      <div class="flex flex-wrap gap-2">
        <Button variant="secondary" :disabled="busy" @click="clear(true, false)"
          >清空 CCIP 缓存</Button
        ><Button variant="secondary" :disabled="busy" @click="clear(false, true)"
          >清空 DreamSim 缓存</Button
        ><Button variant="danger" :disabled="busy" @click="clear()">清空全部缓存</Button>
      </div>
      <p v-if="error" class="text-sm text-destructive">{{ error }}</p></Card
    >
  </div>
</template>
