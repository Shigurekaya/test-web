<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import AppIcon from '../components/AppIcon.vue'
import EmptyState from '../components/EmptyState.vue'
import PageHeader from '../components/PageHeader.vue'
import { api } from '../api/client'
import { toast } from '../stores/toast'

const route = useRoute()
const router = useRouter()
const data = ref(null)
const loading = ref(true)
const error = ref('')
const favoritesOnly = ref(false)
const filters = reactive({
  q: '',
  category_id: '',
  department: '',
  visibility: '',
  sort: 'updated'
})

const hasFilters = computed(() => Boolean(
  filters.q || filters.category_id || filters.department || filters.visibility || filters.sort !== 'updated'
))

function readQuery() {
  filters.q = typeof route.query.q === 'string' ? route.query.q : ''
  favoritesOnly.value = route.query.favorite === '1'
  filters.category_id = typeof route.query.category === 'string' ? route.query.category : ''
  filters.department = typeof route.query.department === 'string' ? route.query.department : ''
  filters.visibility = typeof route.query.visibility === 'string' ? route.query.visibility : ''
  filters.sort = typeof route.query.sort === 'string' ? route.query.sort : 'updated'
}

function updateQuery(page = 1) {
  const query = {}
  if (filters.q) query.q = filters.q
  if (filters.category_id) query.category = filters.category_id
  if (filters.department) query.department = filters.department
  if (filters.visibility) query.visibility = filters.visibility
  if (filters.sort !== 'updated') query.sort = filters.sort
  if (favoritesOnly.value) query.favorite = '1'
  if (page > 1) query.page = String(page)
  router.push({ name: 'documents', query })
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    if (favoritesOnly.value) {
      const result = await api.get('/documents/favorites')
      data.value = { items: result.items, categories: [], departments: [], pagination: { page: 1, pages: 1, total: result.items.length } }
    } else {
      const params = new URLSearchParams()
      params.set('page', String(Number(route.query.page) || 1))
      params.set('per_page', '9')
      if (filters.q) params.set('q', filters.q)
      if (filters.category_id) params.set('category_id', filters.category_id)
      if (filters.department) params.set('department', filters.department)
      if (filters.visibility) params.set('visibility', filters.visibility)
      if (filters.sort) params.set('sort', filters.sort)
      data.value = await api.get(`/documents?${params}`)
    }
  } catch (err) {
    error.value = err.message
    toast.error(err.message)
  } finally {
    loading.value = false
  }
}

function applyFilters() {
  updateQuery(1)
}

function resetFilters() {
  filters.q = ''
  filters.category_id = ''
  filters.department = ''
  filters.visibility = ''
  filters.sort = 'updated'
  favoritesOnly.value = false
  router.push({ name: 'documents' })
}

function toggleFavorites() {
  favoritesOnly.value = !favoritesOnly.value
  updateQuery(1)
}

async function toggleFavorite(doc, event) {
  event.preventDefault()
  event.stopPropagation()
  try {
    const result = await api.post(`/documents/${doc.id}/favorite`)
    doc.is_favorite = result.is_favorite
    toast.success(result.message)
  } catch (err) {
    toast.error(err.message)
  }
}

watch(() => route.fullPath, () => {
  readQuery()
  load()
})

onMounted(() => {
  readQuery()
  load()
})
</script>

<template>
  <div class="view documents-view">
    <PageHeader
      eyebrow="KNOWLEDGE LIBRARY"
      title="知识文档"
      description="按分类、部门与密级筛选企业制度、手册和业务资料。列表只展示你当前有权访问的已发布文档。"
    >
      <template #actions>
        <button class="button" :class="favoritesOnly ? 'button--primary' : 'button--ghost'" @click="toggleFavorites">
          <AppIcon name="favorite" :size="17" /> {{ favoritesOnly ? '正在看收藏' : '我的收藏' }}
        </button>
        <RouterLink to="/documents/new" class="button button--primary">
          <AppIcon name="plus" :size="17" /> 新建文档
        </RouterLink>
      </template>
    </PageHeader>

    <section class="panel filter-panel">
      <form class="filter-grid" @submit.prevent="applyFilters">
        <label class="field filter-grid__search">
          <span>关键词</span>
          <div class="input-shell">
            <AppIcon name="search" :size="17" />
            <input v-model="filters.q" placeholder="搜索标题、摘要、正文或标签" />
          </div>
        </label>
        <label class="field">
          <span>分类</span>
          <select v-model="filters.category_id">
            <option value="">全部分类</option>
            <option v-for="cat in data?.categories || []" :key="cat.id" :value="String(cat.id)">{{ cat.name }}</option>
          </select>
        </label>
        <label class="field">
          <span>部门</span>
          <select v-model="filters.department">
            <option value="">全部部门</option>
            <option v-for="dept in data?.departments || []" :key="dept" :value="dept">{{ dept }}</option>
          </select>
        </label>
        <label class="field">
          <span>密级</span>
          <select v-model="filters.visibility">
            <option value="">全部密级</option>
            <option value="public">公开</option>
            <option value="internal">内部</option>
            <option value="secret">机密</option>
          </select>
        </label>
        <label class="field">
          <span>排序</span>
          <select v-model="filters.sort">
            <option value="updated">最近更新</option>
            <option value="title">标题顺序</option>
            <option value="department">部门分组</option>
          </select>
        </label>
        <div class="filter-actions">
          <button type="submit" class="button button--primary"><AppIcon name="filter" :size="16" /> 应用</button>
          <button type="button" class="button button--ghost" :disabled="!hasFilters && !favoritesOnly" @click="resetFilters">重置</button>
        </div>
      </form>
    </section>

    <div class="result-bar">
      <p v-if="data"><strong>{{ data.pagination.total }}</strong> 篇文档<span v-if="filters.q">，关键词“{{ filters.q }}”</span></p>
      <p v-else>正在加载…</p>
      <span v-if="favoritesOnly" class="filter-chip"><AppIcon name="favorite" :size="14" /> 仅看收藏</span>
    </div>

    <div v-if="error" class="inline-alert inline-alert--error"><AppIcon name="warning" />{{ error }}</div>

    <div v-if="loading" class="document-grid">
      <div v-for="index in 6" :key="index" class="skeleton skeleton--card" />
    </div>

    <template v-else-if="data">
      <div v-if="data.items.length" class="document-grid">
        <article v-for="doc in data.items" :key="doc.id" class="document-card">
          <RouterLink :to="`/documents/${doc.id}`" class="document-card__link">
            <div class="document-card__top">
              <span class="document-type"><AppIcon name="document" :size="19" /></span>
              <div class="document-card__badges">
                <span class="status-pill" :class="`status-pill--${doc.visibility}`">{{ doc.visibility_label }}</span>
                <span class="status-pill status-pill--neutral">{{ doc.status_label }}</span>
              </div>
            </div>
            <p class="document-card__category">{{ doc.category }} · {{ doc.department }}</p>
            <h3>{{ doc.title }}</h3>
            <p class="document-card__summary">{{ doc.summary }}</p>
            <div class="tag-row">
              <span v-for="tag in doc.tags.slice(0, 3)" :key="tag" class="tag"># {{ tag }}</span>
            </div>
            <div class="document-card__footer">
              <span><AppIcon name="clock" :size="14" /> {{ doc.updated_at?.slice(0, 10) }}</span>
              <span>v{{ doc.version }} · {{ doc.chunk_count }} 个知识片段</span>
            </div>
          </RouterLink>
          <button class="favorite-button" :class="{ 'favorite-button--active': doc.is_favorite }" :aria-label="doc.is_favorite ? '取消收藏' : '收藏'" @click="toggleFavorite(doc, $event)">
            <AppIcon name="favorite" :size="18" />
          </button>
        </article>
      </div>

      <EmptyState v-else icon="document" title="没有找到匹配文档" description="可以尝试减少筛选条件，或新建一篇知识文档。">
        <RouterLink to="/documents/new" class="button button--primary"><AppIcon name="plus" :size="17" /> 新建文档</RouterLink>
      </EmptyState>

      <nav v-if="data.pagination.pages > 1" class="pagination" aria-label="文档分页">
        <button class="button button--ghost button--small" :disabled="data.pagination.page <= 1" @click="updateQuery(data.pagination.page - 1)">
          上一页
        </button>
        <span>第 {{ data.pagination.page }} / {{ data.pagination.pages }} 页</span>
        <button class="button button--ghost button--small" :disabled="data.pagination.page >= data.pagination.pages" @click="updateQuery(data.pagination.page + 1)">
          下一页
        </button>
      </nav>
    </template>
  </div>
</template>
