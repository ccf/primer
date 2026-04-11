import { defineConfig } from "astro/config";
import mdx from "@astrojs/mdx";
import react from "@astrojs/react";
import sitemap from "@astrojs/sitemap";
import critters from "astro-critters";
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
    }),
    critters(),
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
