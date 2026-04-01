import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { VitePWA } from 'vite-plugin-pwa'
import path from 'path'

export default defineConfig({
  plugins: [
    react(),
    VitePWA({
      registerType: 'autoUpdate',
      includeAssets: ['favicon-industrial.ico'],
      manifest: {
        name: 'Gandiva Pro',
        short_name: 'Gandiva',
        description: 'AI-Designed Professional Industrial Dashboard',
        theme_color: '#0A0F1A',
        background_color: '#0A0F1A',
        display: 'standalone',
        icons: [
          {
            src: 'favicon-industrial.ico',
            sizes: '192x192',
            type: 'image/x-icon'
          }
        ]
      }
    })
  ],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    port: 3000,
    proxy: {
      '/api/v2/ws/realtime': {
        target: 'ws://localhost:8000',
        ws: true,
        changeOrigin: true,
      },
      '/ws': {
        target: 'ws://localhost:8000',
        ws: true,
        changeOrigin: true,
      },
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
})

