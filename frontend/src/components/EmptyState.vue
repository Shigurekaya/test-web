<script setup>
import AppIcon from './AppIcon.vue'

defineProps({
  icon: { type: String, default: 'document' },
  title: { type: String, default: '暂无内容' },
  description: { type: String, default: '当前条件下没有可显示的数据。' }
})
</script>

<template>
  <div class="empty-state">
    <div class="empty-state__icon"><AppIcon :name="icon" :size="28" /></div>
    <h3>{{ title }}</h3>
    <p>{{ description }}</p>
    <slot />
  </div>
</template>
