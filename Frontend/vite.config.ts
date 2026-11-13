import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import path from 'node:path'

// Vite config: https://vitejs.dev/config/
// The Figma-only preview helpers from the original export were removed.
// The design, styling and components are untouched.
export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    // The backend only accepts requests from http://localhost:3000 (see CORS_ORIGINS in backend/.env).
    host: 'localhost',
    port: 3000,
    strictPort: true,
  },
  preview: {
    host: 'localhost',
    port: 3000,
    strictPort: true,
  },
})
