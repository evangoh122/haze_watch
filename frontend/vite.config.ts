import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, ".", "");
  // Path prefix the app is served under. "/" for local dev and root hosting;
  // "/haze-watch/" when routed at evangoh.com/haze-watch (docs/deployment.md).
  // loadEnv with an empty prefix also picks up VITE_BASE_PATH from the shell /
  // Docker ENV, which is how the container build sets it.
  const base = env.VITE_BASE_PATH || "/";
  return {
    base,
    plugins: [react()],
    server: {
      port: 5173,
      proxy: {
        "/api": {
          target: env.VITE_API_BASE_URL ?? "http://localhost:8000",
          changeOrigin: true,
        },
      },
    },
  };
});
