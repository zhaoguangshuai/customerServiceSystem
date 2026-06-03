import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('../views/login/LoginView.vue'),
    meta: { public: true },
  },
  {
    path: '/',
    component: () => import('../components/AdminLayout.vue'),
    redirect: '/dashboard',
    children: [
      {
        path: 'dashboard',
        name: 'Dashboard',
        component: () => import('../views/dashboard/DashboardView.vue'),
        meta: { title: '工作台' },
      },
      {
        path: 'tenants',
        name: 'Tenants',
        component: () => import('../views/tenant/TenantView.vue'),
        meta: { title: '租户管理' },
      },
      {
        path: 'knowledge',
        name: 'Knowledge',
        component: () => import('../views/knowledge/KnowledgeView.vue'),
        meta: { title: '知识库管理' },
      },
      {
        path: 'prompts',
        name: 'Prompts',
        component: () => import('../views/prompt/PromptView.vue'),
        meta: { title: '提示词配置' },
      },
      {
        path: 'chat',
        name: 'Chat',
        component: () => import('../views/chat/ChatView.vue'),
        meta: { title: '对话测试' },
      },
      {
        path: 'chatlogs',
        name: 'ChatLogs',
        component: () => import('../views/chatlog/ChatLogView.vue'),
        meta: { title: '对话日志' },
      },
      {
        path: 'faqs',
        name: 'FAQs',
        component: () => import('../views/faq/FaqView.vue'),
        meta: { title: 'FAQ管理' },
      },
      {
        path: 'reviews',
        name: 'Reviews',
        component: () => import('../views/review/QualityReviewView.vue'),
        meta: { title: '质检中心' },
      },
    ],
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach((to, from, next) => {
  const token = localStorage.getItem('token')
  if (!to.meta.public && !token) {
    next('/login')
  } else {
    next()
  }
})

export default router
