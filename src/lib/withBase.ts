/** Prefixes an internal path with the site's base path (e.g. `/tarmac-blog`). */
export function withBase(path: string): string {
  const base = import.meta.env.BASE_URL.replace(/\/$/, "");
  return `${base}/${path.replace(/^\//, "")}`;
}
