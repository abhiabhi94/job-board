import { defineConfig } from 'vitest/config';

export default defineConfig({
  test: {
    environment: 'happy-dom',
    include: ['tests/js/**/*.test.js'],
    setupFiles: ['tests/js/setup.js'],
    globals: true,
    watch: false,  // Disable watch mode to avoid file watcher issues
    coverage: {
      provider: 'istanbul',  // Switch from v8 to istanbul for better performance
      include: ['job_board/static/js/main.mjs'],
      exclude: ['node_modules/**', 'tests/**', 'venv/**', '*.config.*'],
      reporter: ['text', 'lcov'],  // Add lcov for CI/Codecov
      all: false,
      allowExternal: false,  // Don't analyze external files
      skipFull: true,
      thresholds: {
        statements: 99,
        branches: 70,
        functions: 99,
        lines: 99
      }
    }
  }
});
