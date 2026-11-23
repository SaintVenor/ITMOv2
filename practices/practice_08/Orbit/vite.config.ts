import { defineConfig } from 'vite';

export default defineConfig({
  root: 'frontend',
  server: {
    proxy: {
      '/api': 'http://127.0.0.1:' + (process.env.ORBIT_API_PORT ?? '8000'),
    },
  },
});
