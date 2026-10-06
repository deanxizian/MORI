import { defineConfig } from 'vitest/config'
export default defineConfig({ test: { include: ['apps/console/tests/*.test.ts'], environment: 'node' } })
