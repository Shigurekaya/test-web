<script setup>
import { computed, onMounted, ref } from 'vue'
import AppIcon from '../components/AppIcon.vue'
import PageHeader from '../components/PageHeader.vue'
import { api } from '../api/client'

const data = ref(null)
const loading = ref(true)
const query = ref('')

const filtered = computed(() => {
  const items = data.value?.items || []
  const q = query.value.trim().toLowerCase()
  if (!q) return items
  return items.filter((item) => [item.username, item.display_name, item.department, item.role_label].join(' ').toLowerCase().includes(q))
})

async function load() {
  loading.value = true
  try {
    data.value = await api.get('/admin/users')
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<template>
  <div class="view users-view">
    <PageHeader
      eyebrow="IDENTITY & ACCESS"
      title="用户管理"
      description="查看系统账号、角色、部门和文档贡献情况。当前版本用于课程演示，账号由种子数据维护。"
    >
      <template #actions>
        <button class="button button--ghost" @click="load"><AppIcon name="refresh" :size="16" /> 刷新</button>
      </template>
    </PageHeader>

    <div v-if="data" class="mini-stats">
      <div><strong>{{ data.summary.total }}</strong><span>全部账号</span></div>
      <div><strong>{{ data.summary.admins }}</strong><span>管理员</span></div>
      <div><strong>{{ data.summary.employees }}</strong><span>普通员工</span></div>
      <div><strong>{{ data.items.reduce((sum, item) => sum + item.document_count, 0) }}</strong><span>累计文档贡献</span></div>
    </div>

    <section class="panel">
      <div class="toolbar">
        <div class="section-heading section-heading--compact">
          <div><p class="eyebrow">ACCOUNT DIRECTORY</p><h3>账号目录</h3></div>
        </div>
        <div class="input-shell toolbar__search">
          <AppIcon name="search" :size="17" />
          <input v-model="query" placeholder="搜索姓名、账号或部门" />
        </div>
      </div>

      <div v-if="loading" class="skeleton skeleton--table" />
      <div v-else class="table-wrap">
        <table class="data-table">
          <thead>
            <tr><th>用户</th><th>账号</th><th>角色</th><th>部门</th><th>文档数</th><th>创建时间</th></tr>
          </thead>
          <tbody>
            <tr v-for="user in filtered" :key="user.id">
              <td>
                <div class="person-cell">
                  <span class="avatar avatar--small">{{ user.display_name.slice(0, 1) }}</span>
                  <div><strong>{{ user.display_name }}</strong><small>#{{ user.id }}</small></div>
                </div>
              </td>
              <td><code>{{ user.username }}</code></td>
              <td><span class="status-pill" :class="user.is_admin ? 'status-pill--secret' : 'status-pill--neutral'">{{ user.role_label }}</span></td>
              <td>{{ user.department }}</td>
              <td><strong>{{ user.document_count }}</strong></td>
              <td class="muted">{{ user.created_at }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>
  </div>
</template>
