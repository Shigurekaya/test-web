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
const filtersOpen = ref(false)
const quickSearches = ['年假', '报销', '权限', '培训', '合同']
const visibilityLabels = { public: '公开', internal: '内部', secret: '机密' }
const filters = reactive({
  q: '',
  category_id: '',
  department: '',
  visibility: '',
  sort: 'updated'
})

const queryTokens = computed(() => filters.q.trim().split(/\s+/).filter(Boolean))

const categoryName = computed(() => (
  data.value?.categories?.find((category) => String(category.id) === String(filters.category_id))?.name || '分类'
))

const activeChips = computed(() => {
  const chips = []
  if (filters.q) chips.push({ key: 'q', label: `关键词：${filters.q}` })
  if (favoritesOnly.value) chips.push({ key: 'favorite', label: '仅看收藏' })
  if (filters.category_id) chips.push({ key: 'category_id', label: `分类：${categoryName.value}` })
  if (filters.department) chips.push({ key: 'department', label: `部门：${filters.department}` })
  if (filters.visibility) chips.push({ key: 'visibility', label: `密级：${visibilityLabels[filters.visibility]}` })
  if (filters.sort !== 'updated') {
    const labels = { title: '标题顺序', department: '部门分组' }
    chips.push({ key: 'sort', label: `排序：${labels[filters.sort] || filters.sort}` })
  }
  return chips
})

const hasFilters = computed(() => activeChips.value.length > 0)

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
  filters.q = filters.q.trim()
  filtersOpen.value = false
  updateQuery(1)
}

function resetFilters() {
  filters.q = ''
  filters.category_id = ''
  filters.department = ''
  filters.visibility = ''
  filters.sort = 'updated'
  favoritesOnly.value = false
  filtersOpen.value = false
  router.push({ name: 'documents' })
}

function runQuickSearch(term) {
  filters.q = term
  updateQuery(1)
}

function removeChip(key) {
  if (key === 'favorite') {
    favoritesOnly.value = false
  } else if (key === 'sort') {
    filters.sort = 'updated'
  } else {
    filters[key] = ''
  }
  updateQuery(1)
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

function escapeRegExp(value) {
  return value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
}

function highlightParts(text) {
  const source = String(text || '')
  if (!queryTokens.value.length) return [{ text: source, hit: false }]
  const matcher = new RegExp(`(${queryTokens.value.map(escapeRegExp).join('|')})`, 'gi')
  return source.split(matcher).filter(Boolean).map((part) => ({
    text: part,
    hit: queryTokens.value.some((token) => part.toLocaleLowerCase() === token.toLocaleLowerCase())
  }))
}

function isTitleMatch(doc) {
  const title = String(doc.title || '').toLocaleLowerCase()
  return queryTokens.value.some((token) => title.includes(token.toLocaleLowerCase()))
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
      eyebrow="KNOWLEDGE SEARCH"
      title="搜索知识文档"
      description="从企业制度、业务手册和项目经验中快速定位内容。搜索会覆盖标题、摘要、正文与标签，并自动过滤无权限文档。"
    >
      <template #actions>
        <button class="button" :class="favoritesOnly ? 'button--primary' : 'button--ghost'" @click="toggleFavorites">
          <AppIcon name="favorite" :size="17" /> {{ favoritesOnly ? '正在看收藏' : '我的收藏' }}
        </button>
      </template>
    </PageHeader>

    <form class="knowledge-search" @submit.prevent="applyFilters">
      <section class="search-hero">
        <div class="search-hero__head">
          <div class="search-hero__intro">
            <span class="search-hero__mark"><AppIcon name="search" :size="22" /></span>
            <div>
              <p class="eyebrow">SEARCH & DISCOVER</p>
              <h3>在全库知识中找到答案</h3>
              <p>输入制度名称、业务关键词或一个问题，系统会优先返回最相关的内容。</p>
            </div>
          </div>
          <span class="search-hero__privacy"><AppIcon name="shield" :size="15" /> 权限内检索</span>
        </div>

        <div class="search-hero__bar">
          <AppIcon name="search" :size="21" />
          <input v-model="filters.q" type="search" placeholder="搜索“年假”“报销”“文档权限”…" aria-label="搜索知识文档" />
          <button v-if="filters.q" type="button" class="search-hero__clear" aria-label="清空关键词" @click="filters.q = ''">
            <AppIcon name="close" :size="16" />
          </button>
          <button type="submit" class="button button--primary">
            <AppIcon name="search" :size="16" /> 搜索
          </button>
        </div>

        <div class="search-hero__meta">
          <div class="quick-searches">
            <span>热门搜索</span>
            <button v-for="term in quickSearches" :key="term" type="button" @click="runQuickSearch(term)">{{ term }}</button>
          </div>
          <span class="search-hero__count"><strong>{{ data?.pagination.total ?? '—' }}</strong> {{ filters.q ? '条匹配结果' : '篇可检索文档' }}</span>
        </div>
      </section>

      <section class="panel search-filter-panel">
        <div class="search-filter-panel__head">
          <div class="search-filter-panel__label">
            <span><AppIcon name="filter" :size="16" /> 筛选范围</span>
            <small v-if="activeChips.length">{{ activeChips.length }} 个条件已生效</small>
          </div>
          <button
            type="button"
            class="search-filter-panel__toggle"
            :class="{ 'search-filter-panel__toggle--open': filtersOpen }"
            @click="filtersOpen = !filtersOpen"
          >
            {{ filtersOpen ? '收起筛选' : '展开筛选' }}
            <AppIcon name="chevron" :size="14" />
          </button>
        </div>
        <div class="search-filter-grid" :class="{ 'search-filter-grid--open': filtersOpen }">
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
          <button type="submit" class="button button--soft search-filter-grid__apply">
            <AppIcon name="filter" :size="16" /> 应用筛选
          </button>
        </div>
      </section>
    </form>

    <div v-if="activeChips.length" class="active-filter-row" aria-label="当前筛选条件">
      <span class="active-filter-row__label">当前条件</span>
      <button v-for="chip in activeChips" :key="chip.key" type="button" class="active-filter-chip" @click="removeChip(chip.key)">
        {{ chip.label }} <AppIcon name="close" :size="12" />
      </button>
      <button type="button" class="active-filter-row__clear" @click="resetFilters">清空</button>
    </div>

    <div class="result-bar">
      <div class="result-bar__summary">
        <p v-if="data">
          <strong>{{ data.pagination.total }}</strong> 篇文档
          <span v-if="filters.q">与“{{ filters.q }}”相关</span>
          <span v-else>可供检索</span>
        </p>
        <p v-else>正在加载…</p>
        <span class="result-bar__privacy"><AppIcon name="shield" :size="13" /> 结果已按访问权限过滤</span>
      </div>
      <RouterLink v-if="filters.q" :to="{ name: 'qa', query: { q: filters.q } }" class="text-link">
        用这个问题咨询知识助手 <AppIcon name="arrow" :size="15" />
      </RouterLink>
      <span v-else class="result-bar__mode"><AppIcon name="filter" :size="14" /> 按最近更新排列</span>
    </div>

    <div v-if="error" class="inline-alert inline-alert--error"><AppIcon name="warning" />{{ error }}</div>

    <div v-if="loading" class="document-grid">
      <div v-for="index in 6" :key="index" class="skeleton skeleton--card" />
    </div>

    <template v-else-if="data">
      <div v-if="data.items.length" class="document-grid" :class="{ 'document-grid--search': filters.q }">
        <article v-for="doc in data.items" :key="doc.id" class="document-card">
          <RouterLink :to="`/documents/${doc.id}`" class="document-card__link">
            <div class="document-card__top">
              <span class="document-type"><AppIcon name="document" :size="19" /></span>
              <div class="document-card__badges">
                <span v-if="filters.q && isTitleMatch(doc)" class="search-match-pill">标题匹配</span>
                <span class="status-pill" :class="`status-pill--${doc.visibility}`">{{ doc.visibility_label }}</span>
                <span class="status-pill status-pill--neutral">{{ doc.status_label }}</span>
              </div>
            </div>
            <p class="document-card__category">{{ doc.category }} · {{ doc.department }}</p>
            <h3>
              <template v-for="(part, index) in highlightParts(doc.title)" :key="`title-${doc.id}-${index}`">
                <mark v-if="part.hit">{{ part.text }}</mark><template v-else>{{ part.text }}</template>
              </template>
            </h3>
            <p class="document-card__summary">
              <template v-for="(part, index) in highlightParts(doc.summary)" :key="`summary-${doc.id}-${index}`">
                <mark v-if="part.hit">{{ part.text }}</mark><template v-else>{{ part.text }}</template>
              </template>
            </p>
            <div class="tag-row">
              <span v-for="tag in doc.tags.slice(0, 3)" :key="tag" class="tag">
                #
                <template v-for="(part, index) in highlightParts(tag)" :key="`tag-${doc.id}-${index}`">
                  <mark v-if="part.hit">{{ part.text }}</mark><template v-else>{{ part.text }}</template>
                </template>
              </span>
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

      <EmptyState
        v-else
        icon="search"
        :title="filters.q ? `没有找到“${filters.q}”相关文档` : '没有找到匹配文档'"
        description="可以换一个关键词、减少筛选条件，或新建一篇知识文档。"
      >
        <div class="empty-state__actions">
          <button v-if="hasFilters" type="button" class="button button--ghost" @click="resetFilters">清除筛选</button>
          <RouterLink to="/documents/new" class="button button--primary"><AppIcon name="plus" :size="17" /> 新建文档</RouterLink>
        </div>
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
