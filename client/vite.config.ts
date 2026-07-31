import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': 'http://localhost:8080',
    },
  },
  build: {
    // Spring Boot가 서빙하는 정적 리소스 디렉터리로 직접 빌드한다.
    outDir: '../server/src/main/resources/static',
    emptyOutDir: true,
  },
})
