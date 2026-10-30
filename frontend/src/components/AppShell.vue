<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { RouterLink, RouterView, useRoute, useRouter } from 'vue-router'
import AppIcon from './AppIcon.vue'
import { session } from '../stores/session'

const route = useRoute()
const router = useRouter()
const mobileOpen = ref(false)
const search = ref('')
const searchInput = ref(null)

const navGroups = computed(() => {
  const groups = [
    {
      label: '知识工作台',
      items: [
        { to: '/dashboard', label: '工作台', icon: 'dashboard' },
        { to: '/documents', label: '知识文档', icon: 'document' },
        { to: '/qa', label: '智能问答', icon: 'spark' },
        { to: '/graph', label: '知识关系图', icon: 'graph' }
      ]
    }
  ]
  if (session.store.user?.is_admin) {
    groups.push({
      label: '系统管理',
      items: [
        { to: '/admin/users', label: '用户管理', icon: 'users' },
        { to: '/admin/audits', label: '审计日志', icon: 'audit' }
      ]
    })
  }
  groups.push({
    label: '系统',
    items: [{ to: '/about', label: '关于系统', icon: 'info' }]
  })
  return groups
})

const pageTitle = computed(() => route.meta.title || '智慧企业知识财富库')
const initials = computed(() => session.store.user?.display_name?.slice(0, 1) || '知')

function submitSearch() {
  const q = search.value.trim()
  router.push({ name: 'documents', query: q ? { q } : {} })
}

function clearSearch() {
  search.value = ''
  if (route.name === 'documents') router.push({ name: 'documents' })
}

function handleSearchShortcut(event) {
  if ((event.ctrlKey || event.metaKey) && event.key.toLocaleLowerCase() === 'k') {
    event.preventDefault()
    searchInput.value?.focus()
  }
}

async function signOut() {
  await session.logout()
  router.push({ name: 'login' })
}

watch(() => [route.name, route.query.q], ([name, q]) => {
  search.value = name === 'documents' && typeof q === 'string' ? q : ''
}, { immediate: true })

watch(() => route.fullPath, () => {
  mobileOpen.value = false
})

onMounted(() => window.addEventListener('keydown', handleSearchShortcut))
onBeforeUnmount(() => window.removeEventListener('keydown', handleSearchShortcut))
</script>

<template>
  <div class="shell">
    <div v-if="mobileOpen" class="shell__overlay" @click="mobileOpen = false" />
    <aside class="sidebar" :class="{ 'sidebar--open': mobileOpen }">
      <div class="brand">
        <div class="brand__mark"><AppIcon name="book" :size="23" /></div>
        <div>
          <strong>知识财富库</strong>
          <span>Knowledge Wealth</span>
        </div>
      </div>

      <nav class="sidebar__nav" aria-label="主导航">
        <section v-for="group in navGroups" :key="group.label" class="nav-group">
          <p>{{ group.label }}</p>
          <RouterLink
            v-for="item in group.items"
            :key="item.to"
            :to="item.to"
            class="nav-link"
            :class="{ 'nav-link--active': route.path.startsWith(item.to) }"
          >
            <AppIcon :name="item.icon" :size="19" />
            <span>{{ item.label }}</span>
            <span class="nav-link__dot" />
          </RouterLink>
        </section>
      </nav>

      <div class="sidebar__footer">
        <div class="user-card">
          <div class="avatar">{{ initials }}</div>
          <div class="user-card__body">
            <strong>{{ session.store.user?.display_name }}</strong>
            <span>{{ session.store.user?.department }} · {{ session.store.user?.role_label }}</span>
          </div>
          <button class="icon-button" title="退出登录" aria-label="退出登录" @click="signOut">
            <AppIcon name="logout" :size="18" />
          </button>
        </div>
        <p class="version">V{{ session.store.meta?.version }} · 课程大作业</p>
      </div>
    </aside>

    <div class="shell__main">
      <header class="topbar">
        <button class="icon-button topbar__menu" aria-label="打开导航" @click="mobileOpen = true">
          <AppIcon name="menu" :size="22" />
        </button>
        <div class="topbar__title">
          <span>智慧企业知识财富库</span>
          <h1>{{ pageTitle }}</h1>
        </div>
        <form class="global-search" @submit.prevent="submitSearch">
          <AppIcon name="search" :size="18" />
          <input ref="searchInput" v-model="search" type="search" placeholder="搜索制度、手册或关键词…" aria-label="全局搜索" />
          <button v-if="search" type="button" class="global-search__clear" aria-label="清空搜索" @click="clearSearch">
            <AppIcon name="close" :size="14" />
          </button>
          <kbd>Ctrl K</kbd>
        </form>
        <RouterLink to="/documents/new" class="button button--primary topbar__action">
          <AppIcon name="plus" :size="17" />
          <span>新建文档</span>
        </RouterLink>
      </header>

      <main class="page-stage">
        <RouterView v-slot="{ Component }">
          <Transition name="page" mode="out-in">
            <component :is="Component" />
          </Transition>
        </RouterView>
      </main>
    </div>
  </div>
</template>
