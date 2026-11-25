import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Local development only: the Vite dev server forwards /api to the backend
// running on http://localhost:8002, so no CORS setup is needed locally.
// In Docker / on Render the built app calls the backend URL directly
// (API_URL env var -> window.__ENV__.API_URL, or VITE_API_URL at build time)
// and the backend must allow the frontend origin via CORS_ORIGINS.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': 'http://localhost:8002',
    },
  },
})
