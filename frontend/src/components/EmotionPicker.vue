<template>
  <div class="emotion-grid">
    <button
      v-for="item in EMOTIONS"
      :key="item.value"
      type="button"
      class="emotion-chip"
      :class="{ 'is-active': modelValue === item.value }"
      :aria-pressed="modelValue === item.value"
      @click="$emit('update:modelValue', item.value)"
    >
      <div class="emotion-icon" :style="{ filter: 'saturate(1.05)' }">{{ item.icon }}</div>
      <div class="emotion-name">{{ item.label }}</div>
    </button>
  </div>
</template>

<script setup>
import { EMOTIONS } from '@/stores/dict'

defineProps({
  modelValue: { type: String, default: '' }
})
defineEmits(['update:modelValue'])
</script>
