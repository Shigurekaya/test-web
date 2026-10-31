<script setup>
import { computed, onBeforeUnmount, onMounted, reactive, ref } from 'vue'
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
const chartRef = ref(null)
const viewMode = ref('core')
const showAllLabels = ref(false)
const selectedNode = ref(null)
const compactViewport = ref(false)
let compactMedia = null

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
  keyword: '#8895a7',
  concept: '#b33a32'
}

const degreeMap = computed(() => {
  const result = {}
  for (const link of graph.value.links) {
    result[link.source] = (result[link.source] || 0) + 1
    result[link.target] = (result[link.target] || 0) + 1
  }
  return result
})

const categoryIndex = computed(() => {
  const result = {}
  graph.value.categories.forEach((item, index) => { result[item.name] = index })
  return result
})

const coreNodeIds = computed(() => {
  const result = new Set()
  for (const node of graph.value.nodes) {
    const degree = degreeMap.value[node.id] || 0
    if (!['keyword', 'concept'].includes(node.category)) result.add(node.id)
    else if (node.category === 'concept' && degree >= 2) result.add(node.id)
  }
  return result
})

const visibleGraph = computed(() => {
  const nodes = viewMode.value === 'core'
    ? graph.value.nodes.filter((node) => coreNodeIds.value.has(node.id))
    : graph.value.nodes
  const ids = new Set(nodes.map((node) => node.id))
  return {
    nodes,
    links: graph.value.links.filter((link) => ids.has(link.source) && ids.has(link.target))
  }
})

const nodeById = computed(() => {
  const result = {}
  for (const node of graph.value.nodes) result[node.id] = node
  return result
})

const coreNodeCount = computed(() => coreNodeIds.value.size)

const corePositions = computed(() => {
  const positions = {}
  const compact = compactViewport.value
  const nodes = visibleGraph.value.nodes
  const nodeMap = {}
  for (const node of nodes) nodeMap[node.id] = node

  const documents = nodes.filter((node) => node.category === 'document')
  const departments = nodes.filter((node) => node.category === 'department')
  const concepts = nodes.filter((node) => node.category === 'concept')
  const project = nodes.find((node) => node.category === 'project')
  const docsByDepartment = new Map(departments.map((node) => [node.id, []]))

  for (const document of documents) {
    const link = visibleGraph.value.links.find((item) => {
      const source = nodeMap[item.source]
      const target = nodeMap[item.target]
      return (source?.id === document.id && target?.category === 'department')
        || (target?.id === document.id && source?.category === 'department')
    })
    const departmentId = link
      ? (nodeMap[link.source]?.category === 'department' ? link.source : link.target)
      : null
    if (departmentId && docsByDepartment.has(departmentId)) docsByDepartment.get(departmentId).push(document)
    else {
      const index = Object.keys(positions).length
      positions[document.id] = {
        x: Math.cos(index * 1.7) * (compact ? 95 : 145),
        y: Math.sin(index * 1.7) * (compact ? 150 : 95)
      }
    }
  }

  if (project) positions[project.id] = { x: 0, y: 0 }

  departments.forEach((department, index) => {
    const angle = -Math.PI / 2 + (Math.PI * 2 * index) / Math.max(departments.length, 1)
    const baseX = Math.cos(angle) * (compact ? 105 : 245)
    const baseY = Math.sin(angle) * (compact ? 185 : 160)
    positions[department.id] = { x: baseX, y: baseY }
    const docs = docsByDepartment.get(department.id) || []
    docs.forEach((document, docIndex) => {
      const ring = docIndex < 6 ? (compact ? 38 : 70) : (compact ? 62 : 112)
      const slot = docIndex % 6
      const spread = Math.PI * 2 / Math.max(Math.min(docs.length, 6), 1)
      const docAngle = angle + slot * spread
      positions[document.id] = {
        x: baseX + Math.cos(docAngle) * ring,
        y: baseY + Math.sin(docAngle) * ring * (compact ? 0.62 : 0.78)
      }
    })
  })

  concepts.forEach((concept, index) => {
    const angle = -Math.PI / 2 + (Math.PI * 2 * index) / Math.max(concepts.length, 1) + 0.2
    positions[concept.id] = {
      x: Math.cos(angle) * (compact ? 48 : 125),
      y: Math.sin(angle) * (compact ? 72 : 82)
    }
  })

  return positions
})

const topDocumentIds = computed(() => new Set(
  graph.value.nodes
    .filter((node) => node.category === 'document')
    .sort((a, b) => (degreeMap.value[b.id] || 0) - (degreeMap.value[a.id] || 0))
    .slice(0, 7)
    .map((node) => node.id)
))

const selectedInfo = computed(() => {
  const node = selectedNode.value
  if (!node) return null
  return {
    ...node,
    typeLabel: typeLabels[node.category] || node.category,
    degree: degreeMap.value[node.id] || 0
  }
})

function nodeSize(node) {
  const degree = degreeMap.value[node.id] || 0
  const scale = compactViewport.value ? 0.72 : 1
  if (node.category === 'department') return Math.min(54, 32 + degree * 2) * scale
  if (node.category === 'project') return 44 * scale
  if (node.category === 'document') return Math.min(34, 22 + Math.sqrt(degree) * 3) * scale
  if (node.category === 'concept') return Math.min(28, 15 + degree) * scale
  return Math.min(17, 9 + degree * 1.5) * scale
}

function shortName(name = '') {
  const value = name.replace(/^文档:/, '')
  return value.length > 16 ? `${value.slice(0, 15)}…` : value
}

function shouldShowLabel(node) {
  if (showAllLabels.value) return true
  if (compactViewport.value && !['department', 'project'].includes(node.category)) return false
  const degree = degreeMap.value[node.id] || 0
  return ['department', 'project'].includes(node.category)
    || (node.category === 'concept' && degree >= 4)
    || topDocumentIds.value.has(node.id)
}

const graphOption = computed(() => {
  const isCore = viewMode.value === 'core'
  return {
    tooltip: {
      confine: true,
      backgroundColor: 'rgba(17, 20, 24, 0.94)',
      borderWidth: 0,
      padding: [10, 12],
      textStyle: { color: '#f2f4f7', fontSize: 12 },
      extraCssText: 'border-radius:10px;box-shadow:0 14px 36px rgba(17,20,24,.24);',
      formatter: (params) => {
        if (params.dataType === 'node') {
          const degree = degreeMap.value[params.data.id] || 0
          const hint = params.data.documentId ? '点击打开文档' : `关联 ${degree} 个节点`
          return `<b style="font-size:13px">${escapeHtml(shortName(params.data.name))}</b><br/>`
            + `<span style="color:#9eabba">${escapeHtml(typeLabels[params.data.nodeType] || params.data.nodeType)} · ${degree} 度</span><br/>`
            + `<span style="color:#6fd0ba">${hint}</span>`
        }
        return `<span style="color:#ffdca8">${escapeHtml(params.data.relation || '关联')}</span>`
      }
    },
    animation: true,
    animationDuration: 850,
    animationDurationUpdate: 560,
    animationEasingUpdate: 'cubicOut',
    series: [{
      type: 'graph',
      layout: isCore ? 'none' : 'force',
      data: visibleGraph.value.nodes.map((node) => {
        const inside = ['department', 'project'].includes(node.category)
        const degree = degreeMap.value[node.id] || 0
        const position = isCore ? corePositions.value[node.id] : null
        return {
          ...node,
          ...(position ? { x: position.x, y: position.y } : {}),
          name: node.name,
          nodeType: node.category,
          documentId: node.document_id,
          category: categoryIndex.value[node.category] ?? 0,
          value: degree,
          symbol: node.category === 'project' ? 'diamond' : 'circle',
          symbolSize: nodeSize(node),
          itemStyle: {
            color: typeColors[node.category] || '#8996a8',
            borderColor: '#ffffff',
            borderWidth: 1.6,
            shadowBlur: inside ? 18 : 7,
            shadowColor: 'rgba(17, 20, 24, 0.18)'
          },
          label: {
            show: shouldShowLabel(node),
            position: inside ? 'inside' : (position?.x > 170 ? 'left' : 'right'),
            distance: 7,
            color: inside ? '#ffffff' : '#344156',
            fontSize: inside ? 10 : 10.5,
            fontWeight: inside ? 600 : 500,
            backgroundColor: inside ? 'transparent' : 'rgba(255, 255, 255, 0.88)',
            padding: inside ? 0 : [3, 5],
            borderRadius: 5,
            formatter: () => shortName(node.name)
          }
        }
      }),
      links: visibleGraph.value.links.map((link) => {
        const source = nodeById.value[link.source]
        const target = nodeById.value[link.target]
        const departmentEdge = [source?.category, target?.category].includes('department')
        return {
          ...link,
          value: link.relation,
          lineStyle: {
            color: departmentEdge ? '#7b8b9e' : '#adb6c2',
            width: departmentEdge ? 1.05 : 0.65,
            opacity: departmentEdge ? 0.28 : 0.14,
            curveness: departmentEdge ? 0.06 : 0.03
          }
        }
      }),
      categories: graph.value.categories.map((item) => ({ name: typeLabels[item.name] || item.name })),
      top: compactViewport.value ? 104 : 74,
      bottom: 24,
      left: compactViewport.value ? 12 : 24,
      right: compactViewport.value ? 12 : 24,
      zoom: isCore ? (compactViewport.value ? 0.94 : 0.96) : (compactViewport.value ? 0.34 : 0.62),
      roam: true,
      draggable: true,
      scaleLimit: { min: 0.45, max: 3.2 },
      selectedMode: 'single',
      force: {
        repulsion: isCore ? 420 : 150,
        edgeLength: isCore ? [80, 125] : [40, 70],
        gravity: isCore ? 0.14 : 0.12,
        friction: 0.62,
        layoutAnimation: true
      },
      labelLayout: { hideOverlap: true, moveOverlap: 'shiftY' },
      lineStyle: { opacity: 0.16, width: 0.7, curveness: 0.04 },
      emphasis: {
        focus: 'adjacency',
        scale: true,
        itemStyle: { shadowBlur: 24, shadowColor: 'rgba(12, 122, 102, 0.3)' },
        lineStyle: { color: '#0c7a66', width: 1.8, opacity: 0.72 },
        label: { show: true }
      },
      blur: {
        itemStyle: { opacity: 0.16 },
        lineStyle: { opacity: 0.05 },
        label: { opacity: 0.12 }
      },
      select: {
        itemStyle: { borderColor: '#0c7a66', borderWidth: 2.5 },
        label: { show: true }
      },
      edgeSymbol: 'none'
    }]
  }
})

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
  selectedNode.value = raw || null
  if (raw?.document_id) router.push(`/documents/${raw.document_id}`)
}

function setView(mode) {
  viewMode.value = mode
  selectedNode.value = null
}

function toggleLabels() {
  showAllLabels.value = !showAllLabels.value
}

function resetView() {
  chartRef.value?.resetView()
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

function syncCompactViewport(event) {
  compactViewport.value = event.matches
}

function handleKeydown(event) {
  if (event.key === 'Escape' && manageOpen.value) manageOpen.value = false
}

onMounted(() => {
  compactMedia = window.matchMedia('(max-width: 760px)')
  compactViewport.value = compactMedia.matches
  compactMedia.addEventListener('change', syncCompactViewport)
  window.addEventListener('keydown', handleKeydown)
  load()
})

onBeforeUnmount(() => {
  compactMedia?.removeEventListener('change', syncCompactViewport)
  window.removeEventListener('keydown', handleKeydown)
})
</script>

<template>
  <div class="view graph-view">
    <PageHeader
      eyebrow="Graph"
      title="知识关系图"
      :description="compactViewport
        ? '默认展示高关联核心结构；轻点节点查看关联，双指缩放画布，点击文档节点进入详情。'
        : '默认展示高关联核心结构，低关联标签可切换查看；悬停聚焦邻接关系，点击文档节点进入详情。'"
    >
      <template #actions>
        <button class="button button--ghost" :disabled="loading" @click="load"><AppIcon name="refresh" :size="16" /> 刷新图谱</button>
        <button v-if="session.store.user?.is_admin" class="button button--primary" @click="openManage"><AppIcon name="plus" :size="16" /> 维护图谱</button>
      </template>
    </PageHeader>

    <div v-if="error" class="inline-alert inline-alert--error"><AppIcon name="warning" />{{ error }}</div>

    <div class="graph-layout">
      <section class="panel graph-canvas-panel">
        <div v-if="!loading && graph.nodes.length" class="graph-canvas-toolbar">
          <div class="graph-view-switch" role="group" aria-label="图谱视图">
            <button :class="{ 'is-active': viewMode === 'core' }" @click="setView('core')">
              核心视图 <span>{{ coreNodeCount }}</span>
            </button>
            <button :class="{ 'is-active': viewMode === 'full' }" @click="setView('full')">
              完整图谱 <span>{{ graph.nodes.length }}</span>
            </button>
          </div>
          <div class="graph-toolbar-actions">
            <button
              class="graph-tool-button"
              :class="{ 'is-active': showAllLabels }"
              :aria-pressed="showAllLabels"
              title="显示或隐藏节点名称"
              @click="toggleLabels"
            >
              <AppIcon name="eye" :size="15" /> 名称
            </button>
            <button class="graph-tool-button" title="重新布局并适配画布" @click="resetView">
              <AppIcon name="refresh" :size="15" /> 适配
            </button>
          </div>
        </div>

        <div v-if="loading" class="skeleton skeleton--graph" />
        <BaseChart
          v-else-if="graph.nodes.length"
          ref="chartRef"
          :option="graphOption"
          :height="compactViewport ? '560px' : '650px'"
          @chart-click="handleNodeClick"
        />
        <div v-else class="empty-mini">当前权限范围内暂无可视图谱。</div>

        <div v-if="!loading && graph.nodes.length" class="graph-canvas-hint">
          <span><i /> {{ compactViewport ? '轻点节点查看邻接关系' : '悬停节点查看邻接关系' }}</span>
          <span>{{ visibleGraph.nodes.length }} / {{ graph.nodes.length }} 节点</span>
        </div>
      </section>

      <aside class="graph-aside">
        <section class="panel graph-stats">
          <p class="eyebrow">GRAPH OVERVIEW</p>
          <h3>图谱概览</h3>
          <div class="graph-stats__hero">
            <div><strong>{{ visibleGraph.nodes.length }}</strong><span>当前节点</span></div>
            <i />
            <div><strong>{{ visibleGraph.links.length }}</strong><span>当前关系</span></div>
          </div>
          <p class="graph-stats__note">
            {{ viewMode === 'core' ? '已隐藏低关联关键词节点' : '完整图谱包含全部知识标签' }}
            · 全量 {{ graph.nodes.length }} 节点 / {{ graph.links.length }} 关系
          </p>
          <div class="graph-legend">
            <div v-for="(label, type) in typeLabels" :key="type" class="graph-legend__item">
              <span :style="{ background: typeColors[type] }" />
              <p>{{ label }}</p>
              <b>{{ summary[type] || 0 }}</b>
            </div>
          </div>
        </section>

        <Transition name="soft-panel">
          <section v-if="selectedInfo" class="panel graph-selected">
            <p class="eyebrow">FOCUSED NODE</p>
            <div class="graph-selected__head">
              <span :style="{ background: typeColors[selectedInfo.category] || '#8996a8' }" />
              <div>
                <h3>{{ selectedInfo.name.replace(/^文档:/, '') }}</h3>
                <p>{{ selectedInfo.typeLabel }} · {{ selectedInfo.degree }} 度关联</p>
              </div>
            </div>
            <button v-if="selectedInfo.document_id" class="text-link" @click="router.push(`/documents/${selectedInfo.document_id}`)">
              打开文档 <AppIcon name="arrow" :size="14" />
            </button>
          </section>
        </Transition>

        <section class="panel">
          <p class="eyebrow">INTERACTION</p>
          <h3>操作说明</h3>
          <ul class="instruction-list">
            <li><span>切换</span>核心结构或完整标签图谱</li>
            <li><span>名称</span>显示全部节点标签</li>
            <template v-if="compactViewport">
              <li><span>单指</span>平移或拖动节点</li>
              <li><span>双指</span>缩放画布</li>
              <li><span>轻点</span>聚焦关联；文档节点打开详情</li>
            </template>
            <template v-else>
              <li><span>拖动</span>平移画布或拖动节点</li>
              <li><span>悬停</span>聚焦相邻节点与关系</li>
              <li><span>点击</span>文档节点打开详情</li>
            </template>
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
      <section class="modal modal--wide" role="dialog" aria-modal="true" aria-labelledby="graph-manage-title">
        <button class="icon-button modal__close" aria-label="关闭" @click="manageOpen = false"><AppIcon name="close" :size="18" /></button>
        <p class="eyebrow">ADMIN ONLY</p>
        <h2 id="graph-manage-title">维护知识图谱</h2>
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
