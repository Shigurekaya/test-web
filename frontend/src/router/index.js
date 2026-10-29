import { createRouter, createWebHistory } from 'vue-router'
import { session } from '../stores/session'

const routes = [
  { path: '/login', name: 'login', component: () => import('../views/LoginView.vue'), meta: { public: true, title: '登录' } },
  {
    path: '/',
    component: () => import('../components/AppShell.vue'),
    children: [
      { path: '', redirect: '/dashboard' },
      { path: 'dashboard', name: 'dashboard', component: () => import('../views/DashboardView.vue'), meta: { title: '工作台' } },
      { path: 'documents', name: 'documents', component: () => import('../views/DocumentsView.vue'), meta: { title: '知识文档' } },
      { path: 'documents/new', name: 'document-new', component: () => import('../views/DocumentEditorView.vue'), meta: { title: '新建文档' } },
      { path: 'documents/:id', name: 'document-detail', component: () => import('../views/DocumentDetailView.vue'), meta: { title: '文档详情' } },
      { path: 'documents/:id/edit', name: 'document-edit', component: () => import('../views/DocumentEditorView.vue'), meta: { title: '编辑文档' } },
      { path: 'qa', name: 'qa', component: () => import('../views/QaView.vue'), meta: { title: '智能问答' } },
      { path: 'graph', name: 'graph', component: () => import('../views/GraphView.vue'), meta: { title: '知识关系图' } },
      { path: 'admin/users', name: 'users', component: () => import('../views/UsersView.vue'), meta: { title: '用户管理', admin: true } },
      { path: 'admin/audits', name: 'audits', component: () => import('../views/AuditsView.vue'), meta: { title: '审计日志', admin: true } },
      { path: 'about', name: 'about', component: () => import('../views/AboutView.vue'), meta: { title: '关于系统' } }
    ]
  },
  { path: '/:pathMatch(.*)*', name: 'not-found', component: () => import('../views/NotFoundView.vue'), meta: { public: true, title: '页面不存在' } }
]

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes,
  scrollBehavior() {
    return { top: 0 }
  }
})

router.beforeEach(async (to) => {
  await session.bootstrap()
  const user = session.store.user
  if (!to.meta.public && !user) {
    return { name: 'login', query: { redirect: to.fullPath } }
  }
  if (to.name === 'login' && user) {
    return { name: 'dashboard' }
  }
  if (to.meta.admin && user && !user.is_admin) {
    return { name: 'dashboard' }
  }
  return true
})

router.afterEach((to) => {
  document.title = `${to.meta.title || '智慧企业知识财富库'} | 智慧企业知识财富库`
})

export default router
