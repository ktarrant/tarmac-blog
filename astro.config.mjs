// @ts-check
import { defineConfig } from 'astro/config';

import mdx from '@astrojs/mdx';
import svelte from '@astrojs/svelte';
import sitemap from '@astrojs/sitemap';

// https://astro.build/config
export default defineConfig({
  site: 'https://ktarrant.github.io',
  base: '/tarmac-blog',
  integrations: [mdx(), svelte(), sitemap()]
});