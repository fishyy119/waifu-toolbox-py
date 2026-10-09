<script setup lang="ts">
import { ref, watch } from 'vue'

const props = withDefaults(
  defineProps<{
    min: number
    max: number
    step?: number
    disabled?: boolean
  }>(),
  { step: 1, disabled: false },
)

const model = defineModel<number>({ required: true })
const emit = defineEmits<{ commit: [value: number] }>()
const inputValue = ref(String(model.value))

watch(model, (value) => {
  inputValue.value = String(value)
})

function updateInputValue(event: Event) {
  const input = event.currentTarget
  if (input instanceof HTMLInputElement) inputValue.value = input.value
}

function commitInputValue(event: FocusEvent) {
  const input = event.currentTarget
  if (!(input instanceof HTMLInputElement)) return

  const value = input.valueAsNumber
  if (!input.validity.valid || !Number.isFinite(value)) {
    inputValue.value = String(model.value)
    return
  }
  if (Object.is(value, model.value)) return

  model.value = value
  inputValue.value = String(value)
  emit('commit', value)
}

function commitOnEnter(event: KeyboardEvent) {
  const input = event.currentTarget
  if (input instanceof HTMLInputElement) input.blur()
}
</script>

<template>
  <input
    :value="inputValue"
    type="number"
    class="min-h-10 w-full rounded-xl border border-input bg-background px-3 py-2 text-foreground disabled:cursor-not-allowed disabled:opacity-50"
    :min="props.min"
    :max="props.max"
    :step="props.step"
    :disabled="props.disabled"
    @input="updateInputValue"
    @blur="commitInputValue"
    @keydown.enter.prevent="commitOnEnter"
  />
</template>
