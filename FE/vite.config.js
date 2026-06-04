import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { fileURLToPath, URL } from 'node:url'

export default defineConfig({
  plugins: [
    vue({
      template: {
        compilerOptions: {
          isCustomElement: (tag) => tag === 'iconify-icon'
        }
      }
    })
  ],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url))
    }
  },
  server: {
    port: 5173,
    host: true,
    open: true,
    proxy: {
      // 开发时把 /api/ 转发到 FastAPI 后端,规避跨域
      // 用 ^/api/ 正则锚点:只匹配 /api/ 开头的请求,
      // 避免误吞 /apitest 等以 api 开头的前端路由
      '^/api/': {
        target: 'http://localhost:8000',
        changeOrigin: true
      }
    }
  }
})
