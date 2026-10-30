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
      <div class="login-hero__glow login-hero__glow--one" />
      <div class="login-hero__glow login-hero__glow--two" />
      <div class="login-brand">
        <div class="brand__mark brand__mark--large"><AppIcon name="book" :size="27" /></div>
        <div>
          <strong>智慧企业知识财富库</strong>
          <span>Enterprise Knowledge Wealth Base</span>
        </div>
      </div>

      <div class="login-hero__copy">
        <p class="eyebrow eyebrow--light">KNOWLEDGE · PERMISSION · ANSWERS</p>
        <h1>让企业知识<br /><span>可查、可问、可治理</span></h1>
        <p>
          面向企业制度与业务资料的统一知识平台。按部门与密级控制访问，
          用检索增强问答定位答案，并以关系图呈现文档、部门与关键词之间的连接。
        </p>
      </div>

      <div class="login-features">
        <span><AppIcon name="document" :size="17" /> 分级文档库</span>
        <span><AppIcon name="spark" :size="17" /> 可溯源问答</span>
        <span><AppIcon name="graph" :size="17" /> 知识关系图</span>
        <span><AppIcon name="audit" :size="17" /> 全链路审计</span>
      </div>
    </section>

    <section class="login-panel">
      <div class="login-panel__inner">
        <div class="login-panel__head">
          <p class="eyebrow">COURSE PROJECT · V{{ session.store.meta?.version || '2.0' }}</p>
          <h2>登录知识工作台</h2>
          <p>使用演示账号体验不同部门与角色的权限边界。</p>
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
              <p>点击即可填入，体验不同权限。</p>
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
          所有演示数据均为课程作业虚构内容，不包含真实企业资料。
        </p>
      </div>
    </section>
  </main>
</template>
