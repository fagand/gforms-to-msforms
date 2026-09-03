import { defineConfig } from 'vite';

export default defineConfig({
  base: '/work/forms/',
  build: {
    outDir: 'app/static',
    emptyOutDir: true,
  },
  test: {
    environment: 'jsdom',
    exclude: ['**/node_modules/**', '**/app/static/**'],
  },
});
