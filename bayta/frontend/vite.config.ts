import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import { viteSingleFile } from "vite-plugin-singlefile";

// mode "demo": fixture-backed build inlined into ONE html file, publishable
// anywhere static (the hosted demo artifact). Normal builds are untouched.
export default defineConfig(({ mode }) => ({
  plugins: [react(), tailwindcss(), ...(mode === "demo" ? [viteSingleFile()] : [])],
  build:
    mode === "demo"
      ? { outDir: "dist-demo", assetsInlineLimit: 100_000_000, target: "es2022" }
      : { target: "es2022" },
  server: {
    proxy: {
      "/api": "http://localhost:8000",
      "/media": "http://localhost:8000",
    },
  },
}));
