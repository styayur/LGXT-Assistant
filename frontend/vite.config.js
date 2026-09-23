import { defineConfig } from "vite";
import { readFileSync, writeFileSync } from "node:fs";
export default defineConfig({
  plugins: [
    {
      name: "desktop-entry",
      closeBundle() {
        const html = readFileSync("dist/index.html", "utf8");
        writeFileSync(
          "dist/desktop.html",
          html.replace("<html ", '<html data-desktop="true" '),
        );
      },
    },
  ],
  base: "./",
  build: { outDir: "dist", chunkSizeWarningLimit: 900 },
});
