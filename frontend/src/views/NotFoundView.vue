<script setup>
import AppIcon from '../components/AppIcon.vue'
</script>

<template>
  <main class="not-found-page">
    <div class="not-found-page__mark"><AppIcon name="search" :size="44" /></div>
    <p class="eyebrow">404 · PAGE NOT FOUND</p>
    <h1>页面走丢了</h1>
    <p>你访问的地址不存在，或已被移动到其他位置。</p>
    <RouterLink to="/dashboard" class="button button--primary"><AppIcon name="arrow" :size="17" /> 返回工作台</RouterLink>
  </main>
</template>
