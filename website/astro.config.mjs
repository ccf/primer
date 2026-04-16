import { defineConfig } from "astro/config";
import mdx from "@astrojs/mdx";
import react from "@astrojs/react";
import sitemap from "@astrojs/sitemap";
import inline from "@playform/inline";
import tailwindcss from "@tailwindcss/vite";

export default defineConfig({
  site: "https://useprimer.dev",
  base: "/",
  integrations: [
    mdx(),
    react(),
    sitemap({
      changefreq: "weekly",
      priority: 0.7,
      lastmod: new Date(),
      filter: (page) => !page.includes("/blog"),
    }),
    inline({
      Critters: {
        // "swap" converts deferred links to preloads that swap to
        // rel="stylesheet" once loaded — preserving inline critical CSS
        // so pages don't render unstyled while waiting for the full
        // stylesheet. The default "media" strategy was causing some
        // pages (docs/server) to render with zero CSS.
        preload: "swap",
      },
    }),
  ],
  markdown: {
    shikiConfig: {
      themes: { light: "github-light", dark: "github-dark-dimmed" },
    },
  },
  vite: {
    plugins: [tailwindcss()],
  },
});
