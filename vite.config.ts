import react from '@vitejs/plugin-react'
import { fileURLToPath, URL } from 'node:url'
import { defineConfig } from 'vite'

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      // The shared harness lives outside apps/web on purpose -- it is owned by
      // neither the frontend nor the backend, because both must run the exact
      // same file. Imported with ?raw, so it's bundled at build time and cannot
      // drift from the copy the sandbox image uses.
      '@harness': fileURLToPath(new URL('../../packages/harness', import.meta.url)),
    },
  },
  server: {
    // 5273, not the default 5173. Deliberately outside the range every other
    // Vite project on a machine competes for.
    port: 5273,
    // Fail loudly if 5273 is taken rather than silently walking to the next free
    // port. Drifting is worse than failing: you end up on a port some other
    // project used, a stale browser tab reloads against this server, and you get
    // "outside of Vite serving allow list" errors naming a project you aren't
    // working on. Bookmarks and the API's CORS config also stop matching.
    strictPort: true,
    fs: {
      // Vite refuses to serve files outside the project root by default.
      // packages/harness is outside apps/web, so it has to be allowed.
      allow: ['..', '../../packages'],
    },
  },
  optimizeDeps: {
    // Pyodide ships its own WASM loader and breaks if Vite pre-bundles it.
    exclude: ['pyodide'],
  },
  worker: { format: 'es' },
})
