import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  base: '/painel/',
  server: {
    port: 3000,
    proxy: {
      '/api': 'http://localhost:5050',
      '/auth': 'http://localhost:5050',
      '/admin': 'http://localhost:5050',
    }
  },
  build: {
    outDir: 'dist',
    emptyOutDir: true,
  }
})
