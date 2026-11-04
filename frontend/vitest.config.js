import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  test: {
    environment: "jsdom",
    globals: true,
    include: ["src/**/*.test.{js,jsx}"],
    coverage: {
      provider: "v8",
      reporter: ["text-summary", "lcov"],
      // The embed script lives outside frontend/. Collect it when a test imports it.
      allowExternal: true,
    },
  },
});
