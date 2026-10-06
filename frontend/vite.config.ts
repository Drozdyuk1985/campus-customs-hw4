import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// The FastAPI backend (backend/main.py) runs on :8000 by default; Vite forwards
// API calls and product images to it so the browser only talks to one origin.
// Override with BACKEND_URL=http://127.0.0.1:<port> npm run dev
const BACKEND = process.env.BACKEND_URL ?? 'http://127.0.0.1:8000'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5174,
    strictPort: true,
    proxy: {
      '/api': BACKEND,
      '/media': BACKEND,
    },
  },
})
