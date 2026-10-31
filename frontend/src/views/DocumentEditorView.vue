<script setup>
import { computed, onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import { onBeforeRouteLeave, useRoute, useRouter } from 'vue-router'
import AppIcon from '../components/AppIcon.vue'
import PageHeader from '../components/PageHeader.vue'
import { api } from '../api/client'
import { toast } from '../stores/toast'

const route = useRoute()
const router = useRouter()
const isEdit = computed(() => Boolean(route.params.id))
const categories = ref([])
const loading = ref(Boolean(route.params.id))
const saving = ref(false)
const error = ref('')
const showPreview = ref(false)
const snapshotReady = ref(false)
const savedSnapshot = ref('')
const leavingAfterSave = ref(false)
const form = reactive({
  title: '',
  content: '',
  summary: '',
  category_id: '',
  department: '',
  visibility: 'internal',
  status: 'published',
  version: '1.0',
  tags: ''
})

function formSnapshot() {
  return JSON.stringify(form)
}

const dirty = computed(() => snapshotReady.value && savedSnapshot.value !== formSnapshot())

async function load() {
  try {
    categories.value = (await api.get('/categories')).items
    if (isEdit.value) {
      const result = await api.get(`/documents/${route.params.id}`)
      if (!result.can_edit) {
        toast.error('无权编辑该文档')
        router.replace(`/documents/${route.params.id}`)
        return
      }
      const doc = result.document
      Object.assign(form, {
        title: doc.title,
        content: doc.content,
        summary: doc.summary,
        category_id: doc.category_id ? String(doc.category_id) : '',
        department: doc.department,
        visibility: doc.visibility,
        status: doc.status,
        version: doc.version,
        tags: doc.tags.join(', ')
      })
    }
  } catch (err) {
    error.value = err.message
  } finally {
    loading.value = false
    savedSnapshot.value = formSnapshot()
    snapshotReady.value = true
  }
}

async function submit() {
  error.value = ''
  if (!form.title.trim() || !form.content.trim()) {
    error.value = '标题与正文不能为空'
    return
  }
  saving.value = true
  try {
    const payload = {
      ...form,
      category_id: form.category_id ? Number(form.category_id) : null,
      tags: form.tags.split(/[,，]/).map((tag) => tag.trim()).filter(Boolean)
    }
    const result = isEdit.value
      ? await api.put(`/documents/${route.params.id}`, payload)
      : await api.post('/documents', payload)
    toast.success(result.message)
    leavingAfterSave.value = true
    savedSnapshot.value = formSnapshot()
    router.push(`/documents/${result.document.id}`)
  } catch (err) {
    error.value = err.message
    toast.error(err.message)
  } finally {
    saving.value = false
  }
}

function handleBeforeUnload(event) {
  if (!dirty.value || leavingAfterSave.value) return
  event.preventDefault()
  event.returnValue = ''
}

function handleSaveShortcut(event) {
  if ((event.ctrlKey || event.metaKey) && event.key.toLocaleLowerCase() === 's') {
    event.preventDefault()
    if (!loading.value && !saving.value) submit()
  }
}

onBeforeRouteLeave(() => {
  if (!dirty.value || leavingAfterSave.value) return true
  return window.confirm('当前修改尚未保存，确定离开吗？')
})

onMounted(() => {
  load()
  window.addEventListener('beforeunload', handleBeforeUnload)
  window.addEventListener('keydown', handleSaveShortcut)
})
onBeforeUnmount(() => {
  window.removeEventListener('beforeunload', handleBeforeUnload)
  window.removeEventListener('keydown', handleSaveShortcut)
})
</script>

<template>
  <div class="view editor-view">
    <PageHeader
      eyebrow="DOCUMENT WORKSPACE"
      :title="isEdit ? '编辑知识文档' : '新建知识文档'"
      description="保存后系统会自动切分知识片段、提取关键词并同步知识关系图。"
    >
      <template #actions>
        <span v-if="dirty" class="unsaved-indicator" role="status"><i /> 有未保存修改</span>
        <button class="button button--ghost" @click="showPreview = !showPreview">
          <AppIcon name="eye" :size="16" /> {{ showPreview ? '关闭预览' : '预览正文' }}
        </button>
        <button class="button button--primary" :disabled="saving || loading" title="保存文档 (Ctrl+S)" @click="submit">
          <span v-if="saving" class="spinner spinner--light" />
          <AppIcon v-else name="check" :size="17" />
          {{ saving ? '保存中…' : '保存文档' }}
        </button>
      </template>
    </PageHeader>

    <div v-if="error" class="inline-alert inline-alert--error"><AppIcon name="warning" />{{ error }}</div>

    <div v-if="loading" class="skeleton skeleton--detail" />

    <form v-else class="editor-layout" @submit.prevent="submit">
      <section class="panel editor-main">
        <label class="field">
          <span>文档标题 <b>*</b></span>
          <input v-model="form.title" class="input-large" maxlength="200" required placeholder="例如：员工年休假管理办法" />
        </label>

        <label class="field">
          <span>摘要</span>
          <textarea v-model="form.summary" rows="3" maxlength="500" placeholder="留空时自动截取正文首段，最多 500 字。" />
          <small>{{ form.summary.length }} / 500</small>
        </label>

        <div class="editor-content-head">
          <div>
            <label class="field-label">正文 <b>*</b></label>
            <p>建议用空行分隔段落，系统会按段落进行知识切分。</p>
          </div>
          <span>{{ form.content.length }} 字</span>
        </div>
        <textarea v-model="form.content" class="content-editor" rows="16" required aria-label="文档正文" placeholder="请输入制度、手册或业务知识正文…" />

        <div v-if="showPreview" class="content-preview">
          <div class="section-heading section-heading--compact">
            <div><h3>正文预览</h3><p>与详情页展示效果一致</p></div>
          </div>
          <div class="document-content">{{ form.content || '暂无正文' }}</div>
        </div>
      </section>

      <aside class="editor-aside">
        <section class="panel">
          <p class="eyebrow">METADATA</p>
          <h3>文档属性</h3>

          <label class="field">
            <span>分类</span>
            <select v-model="form.category_id">
              <option value="">未分类</option>
              <option v-for="cat in categories" :key="cat.id" :value="String(cat.id)">{{ cat.name }}</option>
            </select>
          </label>
          <label class="field">
            <span>所属部门</span>
            <select v-model="form.department">
              <option value="">使用当前账号部门</option>
              <option value="综合部">综合部</option>
              <option value="人事部">人事部</option>
              <option value="财务部">财务部</option>
              <option value="信息部">信息部</option>
              <option value="产品部">产品部</option>
              <option value="运营部">运营部</option>
              <option value="市场部">市场部</option>
              <option value="法务部">法务部</option>
              <option value="技术部">技术部</option>
            </select>
          </label>
          <label class="field">
            <span>访问密级</span>
            <select v-model="form.visibility">
              <option value="public">公开 · 所有登录用户</option>
              <option value="internal">内部 · 所有登录用户</option>
              <option value="secret">机密 · 仅同部门或作者</option>
            </select>
          </label>
          <label class="field">
            <span>发布状态</span>
            <select v-model="form.status">
              <option value="published">已发布</option>
              <option value="draft">草稿</option>
              <option value="archived">已归档</option>
            </select>
          </label>
          <label class="field">
            <span>版本号</span>
            <input v-model="form.version" placeholder="1.0" />
          </label>
          <label class="field">
            <span>标签</span>
            <input v-model="form.tags" placeholder="年假, 人事, 制度" />
            <small>使用逗号分隔；保存后参与图谱与检索。</small>
          </label>
        </section>

        <section class="panel tips-panel">
          <p class="eyebrow">QUALITY CHECK</p>
          <h3>提交前检查</h3>
          <ul>
            <li><AppIcon name="check" :size="15" /> 标题能准确概括正文主题</li>
            <li><AppIcon name="check" :size="15" /> 正文分段清晰，避免整段黏连</li>
            <li><AppIcon name="check" :size="15" /> 密级与所属部门一致</li>
            <li><AppIcon name="check" :size="15" /> 标签覆盖主要业务关键词</li>
          </ul>
        </section>
      </aside>
    </form>
  </div>
</template>
