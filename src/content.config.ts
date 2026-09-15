import { defineCollection, z } from "astro:content";
import { glob } from "astro/loaders";

const investigations = defineCollection({
  loader: glob({ pattern: "**/index.mdx", base: "./src/content/investigations" }),
  schema: z.object({
    title: z.string(),
    summary: z.string(),
    date: z.coerce.date(),
    updated: z.coerce.date().optional(),
    tags: z.array(z.string()).default([]),
    cover: z.string().optional(),
    featured: z.boolean().default(false),
    draft: z.boolean().default(false),
  }),
});

export const collections = { investigations };
