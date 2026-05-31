import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    proxy: {
      '/api': 'http://localhost:8100',
      '/health': 'http://localhost:8100',
      '/uploads': 'http://localhost:8100',
    },
  },
})
