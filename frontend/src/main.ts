import '@/styles.css'

import { VueQueryPlugin } from '@tanstack/vue-query'
import { createPinia } from 'pinia'
import { createApp } from 'vue'

import App from '@/App.vue'
import { favicon } from '@/app/branding'
import { queryClient } from '@/app/query'
import { router } from '@/app/router'

const icon = document.querySelector<HTMLLinkElement>('link[rel="icon"]')
if (icon) icon.href = favicon

createApp(App).use(createPinia()).use(VueQueryPlugin, { queryClient }).use(router).mount('#app')
