<script setup>
import AppIcon from './AppIcon.vue'

defineProps({
  icon: { type: String, default: 'document' },
  label: { type: String, required: true },
  value: { type: [String, Number], default: '—' },
  hint: { type: String, default: '' },
  tone: { type: String, default: 'blue' }
})
</script>

<template>
  <article class="stat-card" :class="`stat-card--${tone}`">
    <div class="stat-card__icon"><AppIcon :name="icon" :size="22" /></div>
    <div>
      <p>{{ label }}</p>
      <strong>{{ value }}</strong>
      <span v-if="hint">{{ hint }}</span>
    </div>
  </article>
</template>
