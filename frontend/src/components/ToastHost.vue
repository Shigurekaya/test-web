<script setup>
import AppIcon from './AppIcon.vue'
import { toast } from '../stores/toast'
</script>

<template>
  <div class="toast-host" aria-live="polite">
    <TransitionGroup name="toast">
      <div v-for="item in toast.state.items" :key="item.id" class="toast" :class="`toast--${item.type}`">
        <span class="toast__icon">
          <AppIcon :name="item.type === 'error' ? 'warning' : item.type === 'success' ? 'check' : 'info'" :size="18" />
        </span>
        <span>{{ item.message }}</span>
        <button class="icon-button icon-button--small" aria-label="关闭提示" @click="toast.remove(item.id)">
          <AppIcon name="close" :size="15" />
        </button>
      </div>
    </TransitionGroup>
  </div>
</template>
