import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// In dev, `npm run dev` serves the UI on :5173 and forwards /api to the FastAPI panel.
const API = process.env.PANEL_API || 'http://127.0.0.1:8000';

export default defineConfig({
  plugins: [react()],
  server: { port: 5173, proxy: { '/api': API } },
  build: { outDir: 'dist', emptyOutDir: true },
});
