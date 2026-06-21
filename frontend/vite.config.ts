import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    port: 5173,
    proxy: {
      '/api': 'http://localhost:12301',
      '/v1': 'http://localhost:12301',
      '/agnesapi': 'http://localhost:12301',
      '/video-proxy': 'http://localhost:12301',
      '/outputs': 'http://localhost:12301',
    },
  },
})
