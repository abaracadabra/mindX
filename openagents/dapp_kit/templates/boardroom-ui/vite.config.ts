import { defineConfig } from 'vite';

export default defineConfig({
  server: {
    port: 5173,
    proxy: {
      // During local dev, proxy /<svc>-svc paths to the Node services.
      '/boardroom-svc':  { target: 'http://127.0.0.1:8771', changeOrigin: true, ws: true,
                           rewrite: (p) => p.replace(/^\/boardroom-svc/, '') },
      '/dojo-svc':       { target: 'http://127.0.0.1:8772', changeOrigin: true, ws: true,
                           rewrite: (p) => p.replace(/^\/dojo-svc/, '') },
      '/warcouncil-svc': { target: 'http://127.0.0.1:8773', changeOrigin: true, ws: true,
                           rewrite: (p) => p.replace(/^\/warcouncil-svc/, '') },
    },
  },
  build: {
    target: 'es2022',
    sourcemap: true,
    outDir: 'dist',
  },
});
