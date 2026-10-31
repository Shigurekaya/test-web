<script setup>
import { computed, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import AppIcon from '../components/AppIcon.vue'
import { session } from '../stores/session'
import { toast } from '../stores/toast'

const route = useRoute()
const router = useRouter()
const form = reactive({ username: 'admin', password: 'admin123' })
const loading = ref(false)
const error = ref('')
const showPassword = ref(false)

const accounts = computed(() => session.store.meta?.demo_accounts || [])

function useAccount(account) {
  form.username = account.username
  form.password = account.password
  error.value = ''
}

async function submit() {
  if (!form.username.trim() || !form.password) {
    error.value = '请输入用户名和密码'
    return
  }
  loading.value = true
  error.value = ''
  try {
    const result = await session.login(form.username.trim(), form.password)
    toast.success(`欢迎回来，${result.user.display_name}`)
    const redirect = typeof route.query.redirect === 'string' ? route.query.redirect : '/dashboard'
    router.replace(redirect.startsWith('/') ? redirect : '/dashboard')
  } catch (err) {
    error.value = err.message || '登录失败，请稍后重试'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <main class="login-page">
    <section class="login-hero">
      <div class="login-brand">
        <div class="brand__mark brand__mark--large"><AppIcon name="book" :size="26" /></div>
        <div>
          <strong>智慧企业知识财富库</strong>
          <span>Enterprise Knowledge Archive</span>
        </div>
      </div>

      <div class="login-hero__copy">
        <p class="eyebrow eyebrow--light">Permission · Retrieval · Trace</p>
        <h1>企业知识<br /><span>收纳、检索、可问</span></h1>
        <p>
          把制度、手册与经验沉淀成可治理的知识资产：部门密级控权，
          检索问答带来源，关系图呈现文档之间的结构。
        </p>
      </div>

      <div class="login-features">
        <span><AppIcon name="document" :size="16" /> 分级文档库</span>
        <span><AppIcon name="spark" :size="16" /> 可溯源问答</span>
        <span><AppIcon name="graph" :size="16" /> 知识关系图</span>
        <span><AppIcon name="audit" :size="16" /> 全链路审计</span>
      </div>
    </section>

    <section class="login-panel">
      <div class="login-panel__inner">
        <div class="login-panel__head">
          <p class="eyebrow">Course Project · V{{ session.store.meta?.version || '2.0' }}</p>
          <h2>进入知识工作台</h2>
          <p>选择演示账号，体验不同部门与角色的权限边界。</p>
        </div>

        <form class="login-form" @submit.prevent="submit">
          <label class="field">
            <span>用户名</span>
            <div class="input-shell">
              <AppIcon name="users" :size="18" />
              <input v-model="form.username" autocomplete="username" placeholder="请输入用户名" />
            </div>
          </label>
          <label class="field">
            <span>密码</span>
            <div class="input-shell">
              <AppIcon name="key" :size="18" />
              <input
                v-model="form.password"
                :type="showPassword ? 'text' : 'password'"
                autocomplete="current-password"
                placeholder="请输入密码"
              />
              <button type="button" class="text-button" @click="showPassword = !showPassword">
                {{ showPassword ? '隐藏' : '显示' }}
              </button>
            </div>
          </label>

          <div v-if="error" class="inline-alert inline-alert--error">
            <AppIcon name="warning" :size="18" />
            <span>{{ error }}</span>
          </div>

          <button class="button button--primary button--wide button--large" type="submit" :disabled="loading">
            <span v-if="loading" class="spinner spinner--light" />
            <AppIcon v-else name="arrow" :size="18" />
            {{ loading ? '正在登录…' : '进入工作台' }}
          </button>
        </form>

        <div class="demo-accounts">
          <div class="section-heading section-heading--compact">
            <div>
              <h3>演示账号</h3>
              <p>点击填入，切换权限视角。</p>
            </div>
          </div>
          <div class="demo-accounts__grid">
            <button
              v-for="account in accounts"
              :key="account.username"
              class="demo-account"
              :class="{ 'demo-account--active': form.username === account.username }"
              type="button"
              @click="useAccount(account)"
            >
              <span class="demo-account__avatar">{{ account.username.slice(0, 1).toUpperCase() }}</span>
              <span>
                <strong>{{ account.username }}</strong>
                <small>{{ account.label }} · {{ account.hint }}</small>
              </span>
            </button>
          </div>
        </div>

        <p class="login-note">
          <AppIcon name="info" :size="15" />
          演示数据均为课程作业虚构内容，不包含真实企业资料。
        </p>
      </div>
    </section>
  </main>
</template>
