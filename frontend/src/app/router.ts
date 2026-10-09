import { createRouter, createWebHistory } from 'vue-router'

import AppLayout from '@/layouts/AppLayout.vue'

export const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      component: AppLayout,
      children: [
        {
          path: '',
          component: () => import('@/pages/RepositoryListPage.vue'),
          meta: { title: '仓库管理' },
        },
        {
          path: 'repo/:repoName',
          component: () => import('@/pages/RepositoryPage.vue'),
          meta: { title: '仓库浏览' },
        },
        {
          path: 'classify',
          component: () => import('@/pages/ClassifyPage.vue'),
          meta: { title: '图片分类' },
        },
        {
          path: 'sort',
          component: () => import('@/pages/SortPage.vue'),
          meta: { title: '图片排序' },
        },
        {
          path: 'convert',
          component: () => import('@/pages/ConvertPage.vue'),
          meta: { title: '格式转换' },
        },
        {
          path: 'search',
          component: () => import('@/pages/SearchPage.vue'),
          meta: { title: '相似搜索' },
        },
        {
          path: 'tasks',
          component: () => import('@/pages/TasksPage.vue'),
          meta: { title: '任务队列' },
        },
        {
          path: 'settings',
          component: () => import('@/pages/SettingsPage.vue'),
          meta: { title: '设置' },
        },
      ],
    },
    {
      path: '/:pathMatch(.*)*',
      component: () => import('@/pages/NotFoundPage.vue'),
      meta: { title: '页面不存在' },
    },
  ],
  scrollBehavior: () => ({ top: 0 }),
})

router.afterEach((route) => {
  const title = typeof route.meta.title === 'string' ? route.meta.title : 'Waifu Toolbox'
  document.title = `${title} · Waifu Toolbox`
})
