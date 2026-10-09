<script setup lang="ts">
const props = withDefaults(
  defineProps<{
    modelValue?: string | number
    modelModifiers?: { number?: boolean; trim?: boolean }
  }>(),
  { modelValue: '', modelModifiers: () => ({}) },
)

const emit = defineEmits<{ 'update:modelValue': [value: string | number] }>()

function updateValue(event: Event) {
  const input = event.currentTarget
  if (!(input instanceof HTMLInputElement)) return

  let value: string | number = props.modelModifiers.trim ? input.value.trim() : input.value
  if (props.modelModifiers.number && value !== '') value = Number(value)
  emit('update:modelValue', value)
}
</script>

<template>
  <input
    :value="modelValue"
    class="min-h-10 w-full rounded-xl border border-input bg-background px-3 py-2 text-foreground disabled:cursor-not-allowed disabled:opacity-50"
    @input="updateValue"
  />
</template>
