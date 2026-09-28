import path from "node:path";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: [
      { find: "@", replacement: path.resolve(import.meta.dirname, "src") },
      {
        find: /^react$/,
        replacement: path.resolve(import.meta.dirname, "node_modules/react"),
      },
      {
        find: /^react\/(.*)$/,
        replacement: path.resolve(import.meta.dirname, "node_modules/react/$1"),
      },
      {
        find: /^react-dom$/,
        replacement: path.resolve(
          import.meta.dirname,
          "node_modules/react-dom",
        ),
      },
      {
        find: /^react-dom\/(.*)$/,
        replacement: path.resolve(
          import.meta.dirname,
          "node_modules/react-dom/$1",
        ),
      },
    ],
  },
  test: {
    environment: "jsdom",
    setupFiles: ["./src/test/setup.ts"],
    restoreMocks: true,
    // Playwright specs live in `e2e/` and must not be collected by Vitest.
    include: ["src/**/*.test.{ts,tsx}"],
  },
});
