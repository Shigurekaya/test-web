<script setup>
import AppIcon from './AppIcon.vue'

defineProps({
  icon: { type: String, default: 'search' },
  title: { type: String, required: true },
  description: { type: String, default: '' }
})
</script>

<template>
  <div class="empty-state">
    <div class="empty-state__icon"><AppIcon :name="icon" :size="22" /></div>
    <h3>{{ title }}</h3>
    <p v-if="description">{{ description }}</p>
    <slot />
  </div>
</template>
