<script setup>
import { computed, nextTick, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import AppIcon from '../components/AppIcon.vue'
import PageHeader from '../components/PageHeader.vue'
import { api } from '../api/client'
import { toast } from '../stores/toast'

const route = useRoute()
const pageData = ref(null)
const loading = ref(true)
const asking = ref(false)
const question = ref(typeof route.query.q === 'string' ? route.query.q : '')
const conversation = ref([])
const error = ref('')
const composer = ref(null)
const selectedHistory = ref(null)

const suggestions = computed(() => pageData.value?.suggestions || [])
const history = computed(() => pageData.value?.history || [])
const canAsk = computed(() => question.value.trim().length > 0 && !asking.value)
const composerPlaceholder = computed(() => (
  suggestions.value[0] ? `输入你的问题，例如：${suggestions.value[0]}` : '输入你的问题'
))

async function load() {
  loading.value = true
  try {
    pageData.value = await api.get('/qa')
  } catch (err) {
    error.value = err.message
  } finally {
    loading.value = false
    focusComposer()
  }
}

function focusComposer() {
  nextTick(() => composer.value?.focus())
}

async function ask(text = question.value) {
  const value = text.trim()
  if (!value || asking.value) return
  question.value = value
  asking.value = true
  error.value = ''
  conversation.value.push({ id: `q-${Date.now()}`, type: 'question', text: value, time: new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' }) })
  try {
    const result = await api.post('/qa/ask', { question: value })
    conversation.value.push({
      id: `a-${result.history_id}`,
      type: 'answer',
      text: result.answer,
      mode: result.mode,
      modeLabel: result.mode_label,
      sources: result.sources || [],
      fragments: result.fragments || [],
      time: new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
    })
    question.value = ''
    const historyEntry = {
      id: result.history_id,
      question: value,
      answer: result.answer,
      mode_label: result.mode_label,
      created_at: new Date().toLocaleString('zh-CN')
    }
    const key = (text) => String(text || '').trim().replace(/\s+/g, ' ').replace(/[?？!！。.,，]+$/, '').toLocaleLowerCase()
    const duplicateIndex = pageData.value.history.findIndex((item) => key(item.question) === key(value))
    if (duplicateIndex >= 0) pageData.value.history.splice(duplicateIndex, 1)
    pageData.value.history.unshift(historyEntry)
    if (pageData.value.history.length > 20) pageData.value.history.pop()
    nextTick(() => window.scrollTo({ top: document.body.scrollHeight, behavior: 'smooth' }))
  } catch (err) {
    error.value = err.message
    conversation.value.push({ id: `e-${Date.now()}`, type: 'error', text: err.message })
  } finally {
    asking.value = false
    focusComposer()
  }
}

async function openHistory(item) {
  try {
    const result = await api.get(`/qa/history/${item.id}`)
    selectedHistory.value = result.item
  } catch (err) {
    toast.error(err.message)
  }
}

function useSuggestion(text) {
  question.value = text
  focusComposer()
}

function newConversation() {
  conversation.value = []
  question.value = ''
  selectedHistory.value = null
  focusComposer()
}

onMounted(load)
</script>

<template>
  <div class="view qa-view">
    <PageHeader
      eyebrow="Retrieval"
      title="智能问答"
      description="先按账号权限裁剪文档，再检索相关知识片段；每条回答附带可核对来源。"
    >
      <template #actions>
        <span class="capability-pill" :class="{ 'capability-pill--live': pageData?.llm_enabled }">
          <AppIcon name="spark" :size="15" />
          {{ pageData?.llm_enabled ? '大模型增强已启用' : '本地检索摘要模式' }}
        </span>
        <button class="button button--ghost" @click="newConversation">
          <AppIcon name="plus" :size="16" /> 新对话
        </button>
      </template>
    </PageHeader>

    <div class="qa-layout">
      <section class="panel qa-chat">
        <div v-if="!conversation.length" class="qa-welcome">
          <span class="qa-welcome__badge"><i /> 权限感知 · 来源可追溯</span>
          <div class="qa-welcome__mark"><AppIcon name="spark" :size="30" /></div>
          <h2>今天想了解什么？</h2>
          <p>我可以基于你有权访问的企业知识文档回答问题，并给出原文来源。</p>
          <div class="suggestion-grid">
            <button v-for="item in suggestions.slice(0, 6)" :key="item" class="suggestion-card" @click="ask(item)">
              <span>{{ item }}</span>
              <AppIcon name="arrow" :size="15" />
            </button>
          </div>
        </div>

        <div v-else class="conversation">
          <template v-for="message in conversation" :key="message.id">
            <div v-if="message.type === 'question'" class="message message--question">
              <div class="message__avatar">{{ '我' }}</div>
              <div class="message__bubble">
                <div class="message__meta"><span>我</span><small>{{ message.time }}</small></div>
                <p>{{ message.text }}</p>
              </div>
            </div>
            <div v-else-if="message.type === 'answer'" class="message message--answer">
              <div class="message__avatar message__avatar--bot"><AppIcon name="spark" :size="18" /></div>
              <div class="message__bubble">
                <div class="message__meta">
                  <span>知识助手</span>
                  <small>{{ message.modeLabel }} · {{ message.time }}</small>
                </div>
                <div class="answer-text">{{ message.text }}</div>
                <div v-if="message.sources.length" class="source-block">
                  <div class="source-block__title"><AppIcon name="book" :size="16" /> 检索依据（{{ message.sources.length }} 篇）</div>
                  <details v-for="source in message.sources" :key="source.document_id" class="source-card">
                    <summary>
                      <span class="source-card__index">{{ source.document_id }}</span>
                      <span>
                        <strong>{{ source.title }}</strong>
                        <small>{{ source.department }} · 最高相关度 {{ source.score }}</small>
                      </span>
                      <AppIcon name="chevron" :size="15" />
                    </summary>
                    <div class="source-fragments">
                      <p v-for="fragment in source.fragments" :key="fragment.chunk_id">{{ fragment.content }}</p>
                    </div>
                  </details>
                </div>
              </div>
            </div>
            <div v-else class="inline-alert inline-alert--error"><AppIcon name="warning" />{{ message.text }}</div>
          </template>
          <div v-if="asking" class="message message--answer">
            <div class="message__avatar message__avatar--bot"><AppIcon name="spark" :size="18" /></div>
            <div class="message__bubble typing-bubble">
              <span /><span /><span />
              <small>正在检索权限内知识片段…</small>
            </div>
          </div>
        </div>

        <form class="qa-composer" @submit.prevent="ask()">
          <textarea ref="composer" v-model="question" rows="2" :placeholder="composerPlaceholder" @keydown.enter.exact.prevent="ask()" />
          <div class="qa-composer__bottom">
            <span><AppIcon name="shield" :size="14" /> 仅检索你有权限查看的已发布文档</span>
            <button class="button button--primary" type="submit" :disabled="!canAsk">
              <span v-if="asking" class="spinner spinner--light" />
              <AppIcon v-else name="send" :size="16" />
              {{ asking ? '回答中' : '发送问题' }}
            </button>
          </div>
        </form>
      </section>

      <aside class="qa-aside">
        <section class="panel">
          <div class="section-heading section-heading--compact">
            <div><p class="eyebrow">HISTORY</p><h3>最近问答</h3></div>
            <span class="count-badge">{{ history.length }}</span>
          </div>
          <div v-if="history.length" class="history-list">
            <button v-for="item in history" :key="item.id" class="history-item" @click="openHistory(item)">
              <span class="history-item__icon"><AppIcon name="clock" :size="15" /></span>
              <span>
                <strong>{{ item.question }}</strong>
                <small>{{ item.mode_label }} · {{ item.created_at }}</small>
              </span>
            </button>
          </div>
          <div v-else class="empty-mini">还没有问答记录。</div>
        </section>

        <section class="panel qa-guide">
          <p class="eyebrow">HOW IT WORKS</p>
          <h3>回答是如何生成的</h3>
          <ol>
            <li><b>01</b><span>按部门与密级筛选可访问文档</span></li>
            <li><b>02</b><span>分词检索并计算片段相关度</span></li>
            <li><b>03</b><span>合并文档来源，生成带依据的回答</span></li>
          </ol>
          <p class="qa-guide__note">未配置大模型密钥时，系统使用可解释的本地检索摘要，不会伪装成 AI 生成。</p>
        </section>
      </aside>
    </div>

    <div v-if="selectedHistory" class="modal-backdrop" @click.self="selectedHistory = null">
      <section class="modal modal--wide">
        <button class="icon-button modal__close" aria-label="关闭" @click="selectedHistory = null"><AppIcon name="close" :size="18" /></button>
        <p class="eyebrow">SAVED ANSWER</p>
        <h2>{{ selectedHistory.question }}</h2>
        <p class="muted">{{ selectedHistory.mode_label }} · {{ selectedHistory.created_at }}</p>
        <div class="answer-text modal__answer">{{ selectedHistory.answer }}</div>
        <div v-if="selectedHistory.sources?.length" class="source-block">
          <div class="source-block__title"><AppIcon name="book" :size="16" /> 来源文档</div>
          <div v-for="source in selectedHistory.sources" :key="source.document_id" class="source-inline">
            <span>#{{ source.document_id }}</span>
            <strong>{{ source.title }}</strong>
            <small>相关度 {{ source.score }}</small>
          </div>
        </div>
      </section>
    </div>
  </div>
</template>
