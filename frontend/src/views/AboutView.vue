<script setup>
import { onMounted, ref } from 'vue'
import AppIcon from '../components/AppIcon.vue'
import PageHeader from '../components/PageHeader.vue'
import { api } from '../api/client'

const data = ref(null)
const loading = ref(true)

const featureIcons = ['shield', 'document', 'spark', 'graph', 'audit']

async function load() {
  try {
    data.value = await api.get('/about')
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<template>
  <div class="view about-view">
    <PageHeader
      eyebrow="ABOUT THE PROJECT"
      title="关于系统"
      description="智慧企业知识财富库是软件工程课程大作业，采用前后端分离架构，覆盖需求、设计、开发、测试与项目管理全过程。"
    />

    <div v-if="loading" class="skeleton skeleton--detail" />

    <template v-else-if="data">
      <section class="about-hero">
        <div>
          <p class="eyebrow eyebrow--light">ENTERPRISE KNOWLEDGE WEALTH BASE</p>
          <h2>{{ data.app.name }}</h2>
          <p>{{ data.app.tagline }}。系统以权限可控的文档库为底座，叠加检索增强问答、知识关系图与审计治理。</p>
          <div class="about-hero__badges">
            <span>Version {{ data.app.version }}</span>
            <span>课程大作业</span>
            <span>前后端分离</span>
          </div>
        </div>
        <div class="about-hero__mark"><AppIcon name="book" :size="64" :stroke-width="1.2" /></div>
      </section>

      <div class="about-stats">
        <div><strong>{{ data.stats.documents }}</strong><span>可见文档</span></div>
        <div><strong>{{ data.stats.chunks }}</strong><span>知识片段</span></div>
        <div><strong>{{ data.stats.nodes }}</strong><span>图谱节点</span></div>
        <div><strong>{{ data.stats.edges }}</strong><span>图谱关系</span></div>
        <div><strong>{{ data.stats.qa }}</strong><span>我的问答</span></div>
      </div>
      <p class="scope-note"><AppIcon name="info" :size="14" /> 文档与知识片段统计口径：{{ data.scope }}</p>

      <section class="panel">
        <div class="section-heading">
          <div><p class="eyebrow">CORE CAPABILITIES</p><h3>核心能力</h3></div>
        </div>
        <div class="feature-grid">
          <article v-for="(feature, index) in data.app.features" :key="feature" class="feature-card">
            <span class="feature-card__icon"><AppIcon :name="featureIcons[index] || 'check'" :size="21" /></span>
            <div><b>0{{ index + 1 }}</b><h4>{{ feature }}</h4></div>
          </article>
        </div>
      </section>

      <div class="about-grid">
        <section class="panel">
          <p class="eyebrow">TECHNOLOGY STACK</p>
          <h3>技术架构</h3>
          <p class="about-tech">{{ data.app.tech_stack }}</p>
          <div class="architecture-flow">
            <div><AppIcon name="book" :size="20" /><strong>Vue 3 SPA</strong><span>页面与交互</span></div>
            <AppIcon name="arrow" :size="18" />
            <div><AppIcon name="key" :size="20" /><strong>REST API</strong><span>JSON 接口</span></div>
            <AppIcon name="arrow" :size="18" />
            <div><AppIcon name="database" :size="20" /><strong>Flask</strong><span>权限与业务</span></div>
            <AppIcon name="arrow" :size="18" />
            <div><AppIcon name="database" :size="20" /><strong>SQLite</strong><span>持久化</span></div>
          </div>
        </section>

        <section class="panel">
          <p class="eyebrow">USE CASES</p>
          <h3>典型使用场景</h3>
          <div class="scenario-list">
            <div v-for="(scenario, index) in data.app.scenarios" :key="scenario">
              <span>{{ index + 1 }}</span><p>{{ scenario }}</p>
            </div>
          </div>
        </section>
      </div>

      <section class="project-footer-card">
        <div>
          <p class="eyebrow">COURSE DELIVERABLE</p>
          <h3>单人独立完成的完整软件工程作业</h3>
          <p>项目包含需求规格、设计规格、开发计划、测试计划、测试用例、个人小结、UML 图与可运行源代码。</p>
        </div>
        <div class="project-footer-card__meta">
          <span><AppIcon name="check" :size="15" /> 136 条自动化测试</span>
          <span><AppIcon name="check" :size="15" /> 5 项个人考核材料</span>
          <span><AppIcon name="check" :size="15" /> 10 张 UML 图</span>
        </div>
      </section>
    </template>
  </div>
</template>
