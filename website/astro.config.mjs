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
      // @playform/inline wraps the `beasties` library, so the config
      // key is "Beasties" (not "Critters"). An unrecognized key is
      // silently ignored — which is how the initial fix missed its
      // target and docs pages kept rendering unstyled with the
      // default "media" preload strategy.
      Beasties: {
        // "swap" converts deferred links to preloads that swap to
        // rel="stylesheet" once loaded, while still inlining critical
        // CSS so the page renders styled on first paint.
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
