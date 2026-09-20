import { defineConfig } from 'vite';

export default defineConfig({
  base: process.env.BASE_PATH ?? '/',
  build: {
    chunkSizeWarningLimit: 2000,
    rollupOptions: { input: { main: 'index.html', metode: 'metode.html' } },
  },
  server: { port: 5173 },
});
