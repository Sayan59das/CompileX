import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  build: {
    rollupOptions: {
      output: {
        // The big libraries get their own files: the browser downloads them in parallel and keeps them cached across
        // deploys of our own code. Three.js and the charts are only fetched by the pages that use them.
        manualChunks(id) {
          if (!id.includes('node_modules')) return undefined
          if (/node_modules\/three\//.test(id)) return 'three'
          if (/node_modules\/(recharts|d3-[^/]+|victory-vendor|internmap|decimal\.js-light)\//.test(id)) return 'charts'
          if (/node_modules\/katex\//.test(id)) return 'katex'
          if (/node_modules\/(react|react-dom|react-router|react-router-dom|scheduler|@remix-run)\//.test(id)) return 'react'
          return undefined
        },
      },
    },
  },
  server: {
    port: 5173,
    host: '0.0.0.0',
    strictPort: true,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
        secure: false,
      },
      '/socket.io': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
        ws: true,
        secure: false,
      },
    },
  },
})
