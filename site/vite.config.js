import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  base: "/fde-backend-service/",
  plugins: [react()],
});
