<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import AppIcon from '../components/AppIcon.vue'
import BaseChart from '../components/BaseChart.vue'
import PageHeader from '../components/PageHeader.vue'
import { api } from '../api/client'
import { session } from '../stores/session'
import { escapeHtml } from '../utils/html'
import { toast } from '../stores/toast'

const router = useRouter()
const graph = ref({ nodes: [], links: [], categories: [] })
const loading = ref(true)
const error = ref('')
const manageOpen = ref(false)
const manageData = ref(null)
const manageLoading = ref(false)
const saving = ref(false)
const nodeForm = reactive({ name: '', node_type: 'concept', description: '' })
const edgeForm = reactive({ source_name: '', target_name: '', relation: '关联' })

const typeLabels = {
  document: '文档',
  department: '部门',
  project: '项目',
  keyword: '关键词',
  concept: '概念'
}
const typeColors = {
  document: '#2f5fad',
  department: '#0c7a66',
  project: '#b7791f',
  keyword: '#4d5d73',
  concept: '#b33a32'
}

const categoryIndex = computed(() => {
  const result = {}
  graph.value.categories.forEach((item, index) => { result[item.name] = index })
  return result
})

const graphOption = computed(() => ({
  tooltip: {
    formatter: (params) => {
      if (params.dataType === 'node') {
        return `<b>${escapeHtml(params.data.name)}</b><br/>类型：${escapeHtml(typeLabels[params.data.nodeType] || params.data.nodeType)}`
      }
      return escapeHtml(params.data.relation || '关联')
    }
  },
  legend: [{
    data: Object.values(typeLabels),
    bottom: 8,
    textStyle: { color: '#5e6b80' },
    itemWidth: 10,
    itemHeight: 10
  }],
  animationDurationUpdate: 700,
  animationEasingUpdate: 'quinticInOut',
  series: [{
    type: 'graph',
    layout: 'force',
    data: graph.value.nodes.map((node) => ({
      ...node,
      name: node.name,
      nodeType: node.category,
      category: categoryIndex.value[node.category] ?? 0,
      value: node.symbolSize,
      label: { show: ['document', 'department'].includes(node.category) },
      itemStyle: { color: typeColors[node.category] || '#8996a8' }
    })),
    links: graph.value.links.map((link) => ({ ...link, value: link.relation })),
    categories: graph.value.categories.map((item) => ({ name: typeLabels[item.name] || item.name })),
    roam: true,
    draggable: true,
    label: {
      show: true,
      position: 'right',
      color: '#344156',
      fontSize: 11,
      formatter: ({ data }) => data.name?.replace(/^文档:/, '')
    },
    labelLayout: { hideOverlap: true },
    force: { repulsion: 520, edgeLength: [90, 160], gravity: 0.08 },
    emphasis: { focus: 'adjacency', lineStyle: { width: 2.5 }, label: { show: true } },
    lineStyle: { color: 'source', curveness: 0.08, opacity: 0.24, width: 0.8 },
    edgeSymbol: ['none', 'arrow'],
    edgeSymbolSize: 5
  }]
}))

const summary = computed(() => {
  const counts = {}
  for (const node of graph.value.nodes) counts[node.category] = (counts[node.category] || 0) + 1
  return counts
})

async function load() {
  loading.value = true
  error.value = ''
  try {
    graph.value = await api.get('/graph')
  } catch (err) {
    error.value = err.message
  } finally {
    loading.value = false
  }
}

function handleNodeClick(params) {
  if (params.dataType !== 'node') return
  const raw = graph.value.nodes.find((node) => node.id === params.data.id)
  if (raw?.document_id) router.push(`/documents/${raw.document_id}`)
}

async function openManage() {
  manageOpen.value = true
  manageLoading.value = true
  try {
    manageData.value = await api.get('/graph/manage')
  } catch (err) {
    toast.error(err.message)
    manageOpen.value = false
  } finally {
    manageLoading.value = false
  }
}

async function addNode() {
  if (!nodeForm.name.trim()) return toast.warning('请输入节点名称')
  saving.value = true
  try {
    await api.post('/graph/nodes', nodeForm)
    toast.success('节点已添加')
    nodeForm.name = ''
    nodeForm.description = ''
    manageData.value = await api.get('/graph/manage')
    await load()
  } catch (err) {
    toast.error(err.message)
  } finally {
    saving.value = false
  }
}

async function addEdge() {
  if (!edgeForm.source_name.trim() || !edgeForm.target_name.trim()) return toast.warning('请输入起点和终点')
  saving.value = true
  try {
    await api.post('/graph/edges', edgeForm)
    toast.success('关系已添加')
    edgeForm.source_name = ''
    edgeForm.target_name = ''
    manageData.value = await api.get('/graph/manage')
    await load()
  } catch (err) {
    toast.error(err.message)
  } finally {
    saving.value = false
  }
}

onMounted(load)
</script>

<template>
  <div class="view graph-view">
    <PageHeader
      eyebrow="Graph"
      title="知识关系图"
      description="拖拽与缩放浏览结构；点击文档节点进入详情。关系由部门、分类与关键词生成，并按权限过滤。"
    >
      <template #actions>
        <button class="button button--ghost" :disabled="loading" @click="load"><AppIcon name="refresh" :size="16" /> 刷新图谱</button>
        <button v-if="session.store.user?.is_admin" class="button button--primary" @click="openManage"><AppIcon name="plus" :size="16" /> 维护图谱</button>
      </template>
    </PageHeader>

    <div v-if="error" class="inline-alert inline-alert--error"><AppIcon name="warning" />{{ error }}</div>

    <div class="graph-layout">
      <section class="panel graph-canvas-panel">
        <div v-if="loading" class="skeleton skeleton--graph" />
        <BaseChart v-else-if="graph.nodes.length" :option="graphOption" height="650px" @chart-click="handleNodeClick" />
        <div v-else class="empty-mini">当前权限范围内暂无可视图谱。</div>
      </section>

      <aside class="graph-aside">
        <section class="panel graph-stats">
          <p class="eyebrow">GRAPH OVERVIEW</p>
          <h3>图谱概览</h3>
          <div class="graph-stats__hero">
            <div><strong>{{ graph.nodes.length }}</strong><span>节点</span></div>
            <i />
            <div><strong>{{ graph.links.length }}</strong><span>关系</span></div>
          </div>
          <div class="graph-legend">
            <div v-for="(label, type) in typeLabels" :key="type" class="graph-legend__item">
              <span :style="{ background: typeColors[type] }" />
              <p>{{ label }}</p>
              <b>{{ summary[type] || 0 }}</b>
            </div>
          </div>
        </section>

        <section class="panel">
          <p class="eyebrow">INTERACTION</p>
          <h3>操作说明</h3>
          <ul class="instruction-list">
            <li><span>拖动</span>平移画布或拖动节点</li>
            <li><span>滚轮</span>放大与缩小图谱</li>
            <li><span>点击</span>文档节点打开详情</li>
            <li><span>悬停</span>高亮相邻节点与关系</li>
          </ul>
        </section>

        <section class="panel graph-note">
          <AppIcon name="shield" :size="22" />
          <div>
            <h3>权限过滤</h3>
            <p>图谱从你有权查看的文档节点出发，只展示与这些文档直接相连的部门、分类和关键词。</p>
          </div>
        </section>
      </aside>
    </div>

    <div v-if="manageOpen" class="modal-backdrop" @click.self="manageOpen = false">
      <section class="modal modal--wide">
        <button class="icon-button modal__close" aria-label="关闭" @click="manageOpen = false"><AppIcon name="close" :size="18" /></button>
        <p class="eyebrow">ADMIN ONLY</p>
        <h2>维护知识图谱</h2>
        <p class="muted">新增概念节点，或建立两个节点之间的语义关系。</p>

        <div v-if="manageLoading" class="skeleton skeleton--card" />
        <div v-else class="manage-grid">
          <form class="manage-form" @submit.prevent="addNode">
            <h3><AppIcon name="plus" :size="17" /> 新增节点</h3>
            <label class="field"><span>节点名称</span><input v-model="nodeForm.name" placeholder="例如：数字化转型" /></label>
            <label class="field"><span>节点类型</span>
              <select v-model="nodeForm.node_type">
                <option v-for="type in manageData?.node_types || []" :key="type" :value="type">{{ typeLabels[type] || type }}</option>
              </select>
            </label>
            <label class="field"><span>说明</span><textarea v-model="nodeForm.description" rows="3" /></label>
            <button class="button button--primary button--wide" :disabled="saving">添加节点</button>
          </form>
          <form class="manage-form" @submit.prevent="addEdge">
            <h3><AppIcon name="graph" :size="17" /> 新增关系</h3>
            <label class="field"><span>起点节点</span><input v-model="edgeForm.source_name" placeholder="已有或新节点名称" /></label>
            <label class="field"><span>终点节点</span><input v-model="edgeForm.target_name" placeholder="已有或新节点名称" /></label>
            <label class="field"><span>关系名称</span><input v-model="edgeForm.relation" placeholder="关联 / 属于 / 含有" /></label>
            <button class="button button--primary button--wide" :disabled="saving">添加关系</button>
          </form>
        </div>

        <div v-if="manageData" class="manage-list">
          <div>
            <h3>最近节点</h3>
            <span v-for="node in manageData.nodes.slice(0, 12)" :key="node.id" class="tag">{{ node.name }}</span>
          </div>
          <div>
            <h3>最近关系</h3>
            <p v-for="edge in manageData.edges.slice(0, 8)" :key="edge.id" class="manage-edge">
              {{ edge.source }} <b>{{ edge.relation }}</b> {{ edge.target }}
            </p>
          </div>
        </div>
      </section>
    </div>
  </div>
</template>
