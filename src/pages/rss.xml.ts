import rss from "@astrojs/rss";
import { getCollection } from "astro:content";
import type { APIContext } from "astro";
import { withBase } from "../lib/withBase";

export async function GET(context: APIContext) {
  const entries = await getCollection("investigations", ({ data }) => !data.draft);
  return rss({
    title: "tarmac",
    description: "Data investigations and visualizations",
    site: context.site!,
    items: entries.map((entry) => ({
      title: entry.data.title,
      description: entry.data.summary,
      pubDate: entry.data.date,
      link: withBase(`/investigations/${entry.id}/`),
    })),
  });
}
