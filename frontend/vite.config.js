import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// The page asks for /api/... on its own address; in development Vite forwards those requests to the backend.
// Point it somewhere else with VITE_API_PROXY (default: a backend on this machine, port 8000).
const backend = process.env.VITE_API_PROXY || 'http://localhost:8000'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': { target: backend, changeOrigin: true },
      '/vault': { target: backend, changeOrigin: true },
    },
  },
})
