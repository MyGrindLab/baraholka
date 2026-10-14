import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    host: true,
    port: 3000,
    strictPort: true,
    proxy: {
      '/api': {
        target: process.env.VITE_PROXY_TARGET ?? 'http://baraholka-app:8080',
        changeOrigin: true,
      },
    },
    // Bind-mounted sources on macOS/Windows don't emit inotify events
    watch: process.env.VITE_USE_POLLING === '1' ? { usePolling: true } : undefined,
  },
  test: {
    environment: 'jsdom',
    setupFiles: ['./src/test/setup.js'],
    include: ['src/**/*.test.{js,jsx}'],
  },
})
