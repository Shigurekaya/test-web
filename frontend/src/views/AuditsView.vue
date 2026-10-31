<script setup>
import { onMounted, reactive, ref } from 'vue'
import AppIcon from '../components/AppIcon.vue'
import PageHeader from '../components/PageHeader.vue'
import { api } from '../api/client'
import { toast } from '../stores/toast'

const data = ref(null)
const loading = ref(true)
const filters = reactive({ action: '', user: '', detail: '', page: 1 })

async function load() {
  loading.value = true
  try {
    const params = new URLSearchParams()
    if (filters.action) params.set('action', filters.action)
    if (filters.user) params.set('user', filters.user)
    if (filters.detail) params.set('detail', filters.detail)
    params.set('page', String(filters.page))
    data.value = await api.get(`/admin/audits?${params}`)
  } catch (err) {
    toast.error(err.message)
  } finally {
    loading.value = false
  }
}

function apply() {
  filters.page = 1
  load()
}

function reset() {
  filters.action = ''
  filters.user = ''
  filters.detail = ''
  filters.page = 1
  load()
}

async function goPage(page) {
  filters.page = page
  await load()
  document.querySelector('.audits-view .panel--flush')?.scrollIntoView({ behavior: 'smooth', block: 'start' })
}

onMounted(load)
</script>

<template>
  <div class="view audits-view">
    <PageHeader
      eyebrow="AUDIT & COMPLIANCE"
      title="审计日志"
      description="记录登录、文档查看与编辑、问答等关键操作。日志支持服务端筛选与分页，便于追溯权限使用。"
    >
      <template #actions>
        <button class="button button--ghost" :disabled="loading" @click="load"><AppIcon name="refresh" :size="16" /> 刷新</button>
      </template>
    </PageHeader>

    <div v-if="data" class="audit-actions" role="group" aria-label="按操作类型快速筛选">
      <button
        v-for="item in data.actions"
        :key="item.value"
        class="audit-action-chip"
        :class="{ 'audit-action-chip--active': filters.action === item.value }"
        :aria-pressed="filters.action === item.value"
        @click="filters.action = filters.action === item.value ? '' : item.value; apply()"
      >
        <span>{{ item.label }}</span>
        <b>{{ data.action_stats[item.value] || 0 }}</b>
      </button>
    </div>

    <section class="panel">
      <form class="filter-grid filter-grid--audit" @submit.prevent="apply">
        <label class="field">
          <span>操作类型</span>
          <select v-model="filters.action">
            <option value="">全部操作</option>
            <option v-for="item in data?.actions || []" :key="item.value" :value="item.value">{{ item.label }}</option>
          </select>
        </label>
        <label class="field"><span>用户账号</span><input v-model="filters.user" placeholder="如 admin" /></label>
        <label class="field filter-grid__search"><span>明细关键词</span><input v-model="filters.detail" placeholder="如 年假、#12" /></label>
        <div class="filter-actions">
          <button class="button button--primary"><AppIcon name="filter" :size="16" /> 查询</button>
          <button type="button" class="button button--ghost" @click="reset">重置</button>
        </div>
      </form>
    </section>

    <section class="panel panel--flush">
      <div class="section-heading section-heading--padded">
        <div><p class="eyebrow">LOG ENTRIES</p><h3>日志明细</h3></div>
        <span v-if="data" class="count-badge">{{ data.pagination.total }} 条</span>
      </div>

      <div v-if="loading" class="skeleton skeleton--table" />
      <div v-else class="table-wrap">
        <table class="data-table">
          <thead><tr><th>时间</th><th>用户</th><th>操作</th><th>明细</th><th>编号</th></tr></thead>
          <tbody>
            <tr v-for="log in data?.items || []" :key="log.id">
              <td data-label="时间" class="muted nowrap">{{ log.created_at }}</td>
              <td data-label="用户"><span class="person-inline">{{ log.username }}</span></td>
              <td data-label="操作"><span class="status-pill" :class="log.action.includes('failed') ? 'status-pill--secret' : 'status-pill--neutral'">{{ log.action_label }}</span></td>
              <td data-label="明细">{{ log.detail }}</td>
              <td data-label="编号" class="muted">#{{ log.id }}</td>
            </tr>
          </tbody>
        </table>
        <div v-if="!data?.items.length" class="empty-mini">没有匹配的审计日志。</div>
      </div>

      <nav v-if="data?.pagination.pages > 1" class="pagination pagination--padded">
        <button class="button button--ghost button--small" :disabled="filters.page <= 1" @click="goPage(filters.page - 1)">上一页</button>
        <span>第 {{ data.pagination.page }} / {{ data.pagination.pages }} 页</span>
        <button class="button button--ghost button--small" :disabled="filters.page >= data.pagination.pages" @click="goPage(filters.page + 1)">下一页</button>
      </nav>
    </section>
  </div>
</template>
