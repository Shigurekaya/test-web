<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import AppIcon from '../components/AppIcon.vue'
import BaseChart from '../components/BaseChart.vue'
import PageHeader from '../components/PageHeader.vue'
import StatCard from '../components/StatCard.vue'
import { api } from '../api/client'
import { session } from '../stores/session'
import { toast } from '../stores/toast'

const router = useRouter()
const data = ref(null)
const loading = ref(true)
const error = ref('')

const greeting = computed(() => {
  const hour = new Date().getHours()
  if (hour < 6) return '夜深了'
  if (hour < 11) return '早上好'
  if (hour < 14) return '中午好'
  if (hour < 18) return '下午好'
  return '晚上好'
})

const deptOption = computed(() => ({
  tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
  grid: { left: 8, right: 18, top: 12, bottom: 4, containLabel: true },
  xAxis: {
    type: 'value',
    splitLine: { lineStyle: { color: '#e8edf4' } },
    axisLabel: { color: '#7b879d' }
  },
  yAxis: {
    type: 'category',
    data: (data.value?.charts.departments || []).map((item) => item.name).reverse(),
    axisLine: { show: false },
    axisTick: { show: false },
    axisLabel: { color: '#46536a', fontWeight: 600 }
  },
  series: [{
    type: 'bar',
    data: (data.value?.charts.departments || []).map((item) => item.value).reverse(),
    barWidth: 12,
    itemStyle: { color: '#1d9b83', borderRadius: [0, 8, 8, 0] },
    showBackground: true,
    backgroundStyle: { color: '#f0f3f8', borderRadius: 8 }
  }]
}))

const categoryOption = computed(() => ({
  tooltip: { trigger: 'item', formatter: '{b}<br/>{c} 篇（{d}%）' },
  legend: {
    orient: 'vertical',
    right: 0,
    top: 'center',
    icon: 'circle',
    itemWidth: 8,
    itemHeight: 8,
    textStyle: { color: '#5e6b80', fontSize: 12 }
  },
  color: ['#1d9b83', '#3976d9', '#7c5ce5', '#e9a23b', '#e76b67', '#3ca8b8', '#8996a8', '#9c7a50'],
  series: [{
    type: 'pie',
    radius: ['48%', '72%'],
    center: ['33%', '50%'],
    avoidLabelOverlap: true,
    itemStyle: { borderColor: '#fff', borderWidth: 3 },
    label: { show: false },
    data: data.value?.charts.categories || []
  }]
}))

function formatToday() {
  return new Intl.DateTimeFormat('zh-CN', {
    year: 'numeric', month: 'long', day: 'numeric', weekday: 'long'
  }).format(new Date())
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    data.value = await api.get('/dashboard')
  } catch (err) {
    error.value = err.message
    toast.error(err.message)
  } finally {
    loading.value = false
  }
}

function ask(question) {
  router.push({ name: 'qa', query: { q: question } })
}

onMounted(load)
</script>

<template>
  <div class="view dashboard-view">
    <section class="welcome-panel">
      <div>
        <p class="eyebrow">{{ formatToday() }}</p>
        <h2>{{ greeting }}，{{ session.store.user?.display_name }}</h2>
        <p>
          当前以 <strong>{{ session.store.user?.department }} · {{ session.store.user?.role_label }}</strong>
          身份访问，统计范围已按你的文档权限自动过滤。
        </p>
      </div>
      <div class="welcome-panel__actions">
        <button class="button button--ghost" :disabled="loading" @click="load">
          <AppIcon name="refresh" :size="17" /> 刷新
        </button>
        <RouterLink to="/qa" class="button button--primary">
          <AppIcon name="spark" :size="17" /> 发起问答
        </RouterLink>
      </div>
    </section>

    <div v-if="error" class="inline-alert inline-alert--error"><AppIcon name="warning" />{{ error }}</div>

    <div v-if="loading" class="stats-grid">
      <div v-for="index in 6" :key="index" class="skeleton skeleton--stat" />
    </div>

    <template v-else-if="data">
      <div class="stats-grid">
        <StatCard icon="document" label="可见文档" :value="data.stats.visible_documents" hint="按权限过滤" tone="blue" />
        <StatCard icon="favorite" label="我的收藏" :value="data.stats.favorites" hint="常用资料" tone="rose" />
        <StatCard icon="spark" label="本周问答" :value="data.stats.qa_week" :hint="`累计 ${data.stats.qa_total} 次`" tone="green" />
        <StatCard icon="graph" label="图谱节点" :value="data.stats.nodes" :hint="`${data.stats.edges} 条关系`" tone="violet" />
      </div>

      <div class="dashboard-main-grid">
        <section class="panel">
          <div class="section-heading">
            <div>
              <p class="eyebrow">DOCUMENT DISTRIBUTION</p>
              <h3>部门知识分布</h3>
            </div>
            <RouterLink to="/documents" class="text-link">查看全部 <AppIcon name="arrow" :size="15" /></RouterLink>
          </div>
          <BaseChart v-if="data.charts.departments.length" :option="deptOption" height="292px" />
          <div v-else class="empty-mini">暂无可统计的部门文档</div>
        </section>

        <section class="panel">
          <div class="section-heading">
            <div>
              <p class="eyebrow">CATEGORY MIX</p>
              <h3>知识分类构成</h3>
            </div>
          </div>
          <BaseChart v-if="data.charts.categories.length" :option="categoryOption" height="292px" />
          <div v-else class="empty-mini">暂无可统计的分类</div>
        </section>
      </div>

      <div class="dashboard-lower-grid">
        <section class="panel panel--flush">
          <div class="section-heading section-heading--padded">
            <div>
              <p class="eyebrow">RECENT DOCUMENTS</p>
              <h3>最近更新</h3>
            </div>
            <RouterLink to="/documents/new" class="button button--soft button--small">
              <AppIcon name="plus" :size="15" /> 新建
            </RouterLink>
          </div>
          <div class="document-list">
            <RouterLink
              v-for="doc in data.recent_documents"
              :key="doc.id"
              :to="`/documents/${doc.id}`"
              class="document-row"
            >
              <span class="document-row__icon"><AppIcon name="document" :size="19" /></span>
              <span class="document-row__main">
                <strong>{{ doc.title }}</strong>
                <small>{{ doc.category }} · {{ doc.department }} · 更新于 {{ doc.updated_at }}</small>
              </span>
              <span class="status-pill" :class="`status-pill--${doc.visibility}`">{{ doc.visibility_label }}</span>
              <AppIcon name="chevron" :size="17" class="muted" />
            </RouterLink>
            <div v-if="!data.recent_documents.length" class="empty-mini">暂无可见文档</div>
          </div>
        </section>

        <section class="panel">
          <div class="section-heading">
            <div>
              <p class="eyebrow">ASK THE KNOWLEDGE BASE</p>
              <h3>快捷提问</h3>
            </div>
          </div>
          <div class="quick-question-list">
            <button v-for="question in data.quick_questions" :key="question" class="quick-question" @click="ask(question)">
              <span>{{ question }}</span>
              <AppIcon name="arrow" :size="16" />
            </button>
          </div>
          <div class="qa-mini">
            <div class="section-heading section-heading--compact">
              <div>
                <h4>最近问答</h4>
                <p>仅显示你本人的记录</p>
              </div>
              <RouterLink to="/qa" class="text-link">问答中心</RouterLink>
            </div>
            <div v-for="item in data.recent_qa.slice(0, 3)" :key="item.id" class="qa-mini__item">
              <span class="qa-mini__dot" />
              <div>
                <strong>{{ item.question }}</strong>
                <small>{{ item.mode_label }} · {{ item.created_at }}</small>
              </div>
            </div>
            <p v-if="!data.recent_qa.length" class="muted small">还没有提问记录。</p>
          </div>
        </section>
      </div>

      <section v-if="data.recent_logs.length" class="panel">
        <div class="section-heading">
          <div>
            <p class="eyebrow">AUDIT TRAIL</p>
            <h3>近期审计动态</h3>
          </div>
          <RouterLink to="/admin/audits" class="text-link">审计中心 <AppIcon name="arrow" :size="15" /></RouterLink>
        </div>
        <div class="audit-strip">
          <div v-for="log in data.recent_logs" :key="log.id" class="audit-strip__item">
            <span class="audit-strip__icon"><AppIcon name="audit" :size="16" /></span>
            <div>
              <strong>{{ log.action_label }}</strong>
              <p>{{ log.detail }}</p>
              <small>{{ log.username }} · {{ log.created_at }}</small>
            </div>
          </div>
        </div>
      </section>
    </template>
  </div>
</template>
