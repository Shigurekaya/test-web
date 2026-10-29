<script setup>
import { onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import AppIcon from '../components/AppIcon.vue'
import { api } from '../api/client'
import { toast } from '../stores/toast'

const route = useRoute()
const router = useRouter()
const documentData = ref(null)
const loading = ref(true)
const error = ref('')
const busy = ref(false)

async function load() {
  loading.value = true
  error.value = ''
  try {
    documentData.value = await api.get(`/documents/${route.params.id}`)
  } catch (err) {
    error.value = err.message
  } finally {
    loading.value = false
  }
}

async function toggleFavorite() {
  busy.value = true
  try {
    const result = await api.post(`/documents/${route.params.id}/favorite`)
    documentData.value.document.is_favorite = result.is_favorite
    toast.success(result.message)
  } catch (err) {
    toast.error(err.message)
  } finally {
    busy.value = false
  }
}

async function removeDocument() {
  if (!window.confirm('确定删除这篇文档吗？删除后不可恢复。')) return
  busy.value = true
  try {
    await api.delete(`/documents/${route.params.id}`)
    toast.success('文档已删除')
    router.replace('/documents')
  } catch (err) {
    toast.error(err.message)
  } finally {
    busy.value = false
  }
}

async function copyContent() {
  try {
    await navigator.clipboard.writeText(documentData.value.document.content)
    toast.success('正文已复制')
  } catch {
    toast.error('复制失败，请手动选择正文')
  }
}

onMounted(load)
</script>

<template>
  <div class="view document-detail-view">
    <div v-if="loading" class="detail-layout">
      <div class="skeleton skeleton--detail" />
      <div class="skeleton skeleton--aside" />
    </div>

    <div v-else-if="error" class="panel">
      <div class="inline-alert inline-alert--error"><AppIcon name="warning" />{{ error }}</div>
      <RouterLink to="/documents" class="button button--ghost"><AppIcon name="arrow" :size="16" /> 返回文档列表</RouterLink>
    </div>

    <template v-else-if="documentData">
      <div class="detail-breadcrumb">
        <RouterLink to="/documents">知识文档</RouterLink>
        <AppIcon name="chevron" :size="14" />
        <span>{{ documentData.document.category }}</span>
      </div>

      <div class="detail-layout">
        <article class="panel document-article">
          <header class="document-article__header">
            <div class="document-article__badges">
              <span class="status-pill" :class="`status-pill--${documentData.document.visibility}`">{{ documentData.document.visibility_label }}</span>
              <span class="status-pill status-pill--neutral">{{ documentData.document.status_label }}</span>
              <span class="status-pill status-pill--neutral">v{{ documentData.document.version }}</span>
            </div>
            <h1>{{ documentData.document.title }}</h1>
            <p class="document-article__summary">{{ documentData.document.summary }}</p>
            <div class="document-article__meta">
              <span><AppIcon name="folder" :size="15" /> {{ documentData.document.category }}</span>
              <span><AppIcon name="users" :size="15" /> {{ documentData.document.department }}</span>
              <span><AppIcon name="clock" :size="15" /> {{ documentData.document.updated_at }}</span>
              <span><AppIcon name="database" :size="15" /> {{ documentData.document.chunk_count }} 个知识片段</span>
            </div>
            <div class="tag-row">
              <span v-for="tag in documentData.document.tags" :key="tag" class="tag"># {{ tag }}</span>
            </div>
          </header>

          <div class="document-article__toolbar">
            <span>作者：{{ documentData.document.author }}</span>
            <div>
              <button class="button button--ghost button--small" @click="copyContent"><AppIcon name="copy" :size="15" /> 复制正文</button>
              <button class="button button--ghost button--small" :disabled="busy" @click="toggleFavorite">
                <AppIcon name="favorite" :size="15" /> {{ documentData.document.is_favorite ? '取消收藏' : '收藏' }}
              </button>
            </div>
          </div>

          <div class="document-content">{{ documentData.document.content }}</div>
        </article>

        <aside class="detail-aside">
          <section class="panel action-panel">
            <p class="eyebrow">DOCUMENT ACTIONS</p>
            <h3>文档操作</h3>
            <RouterLink v-if="documentData.can_edit" :to="`/documents/${documentData.document.id}/edit`" class="button button--primary button--wide">
              <AppIcon name="edit" :size="16" /> 编辑文档
            </RouterLink>
            <button v-if="documentData.can_edit" class="button button--danger-ghost button--wide" :disabled="busy" @click="removeDocument">
              <AppIcon name="trash" :size="16" /> 删除文档
            </button>
            <RouterLink to="/qa" class="button button--ghost button--wide"><AppIcon name="spark" :size="16" /> 围绕此主题提问</RouterLink>
          </section>

          <section class="panel document-info-panel">
            <p class="eyebrow">DOCUMENT INFO</p>
            <h3>文档信息</h3>
            <dl>
              <div><dt>文档编号</dt><dd>#{{ documentData.document.id }}</dd></div>
              <div><dt>所属部门</dt><dd>{{ documentData.document.department }}</dd></div>
              <div><dt>密级</dt><dd>{{ documentData.document.visibility_label }}</dd></div>
              <div><dt>正文字数</dt><dd>{{ documentData.document.char_count }}</dd></div>
              <div><dt>创建时间</dt><dd>{{ documentData.document.created_at }}</dd></div>
              <div><dt>更新时间</dt><dd>{{ documentData.document.updated_at }}</dd></div>
            </dl>
          </section>

          <section v-if="documentData.related.length" class="panel">
            <p class="eyebrow">RELATED READING</p>
            <h3>相关文档</h3>
            <RouterLink v-for="doc in documentData.related" :key="doc.id" :to="`/documents/${doc.id}`" class="related-doc">
              <span class="related-doc__icon"><AppIcon name="document" :size="16" /></span>
              <span>
                <strong>{{ doc.title }}</strong>
                <small>{{ doc.department }} · {{ doc.category }}</small>
              </span>
              <AppIcon name="chevron" :size="15" />
            </RouterLink>
          </section>
        </aside>
      </div>
    </template>
  </div>
</template>
