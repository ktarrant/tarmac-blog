<script lang="ts">
  import EChart from "../../charts/EChart.svelte";
  import { categorical, chrome } from "../../../lib/charts/palette";
  import { label } from "../../../lib/stateBudgets";

  let {
    years,
    capitalByFunction,
  }: { years: number[]; capitalByFunction: Record<string, number[]> } = $props();

  const MAX_SERIES = 6;

  // Ranked by the biggest year rather than the period total, so a category
  // that only started mattering recently — school construction that begins
  // mid-series, say — is still named instead of vanishing into "Other".
  const ranked = $derived(
    Object.entries(capitalByFunction)
      .map(([key, values]) => ({
        key,
        values,
        total: values.reduce((a, b) => a + b, 0),
        peak: Math.max(...values),
      }))
      .filter((s) => s.total > 0)
      .sort((a, b) => b.peak - a.peak)
  );

  const series = $derived.by(() => {
    const leaders = ranked.slice(0, MAX_SERIES);
    const rest = ranked.slice(MAX_SERIES);
    const out = leaders.map((s, index) => ({
      name: label(s.key),
      type: "bar" as const,
      stack: "capital",
      data: s.values,
      itemStyle: { color: categorical[index % categorical.length] },
      barMaxWidth: 26,
    }));
    if (rest.length) {
      out.push({
        name: "Other",
        type: "bar",
        stack: "capital",
        data: years.map((_, i) => rest.reduce((sum, s) => sum + (s.values[i] ?? 0), 0)),
        itemStyle: { color: chrome.inkMuted },
        barMaxWidth: 26,
      });
    }
    return out;
  });

  // Share of the whole period, which is what the takeaway quotes.
  const shares = $derived.by(() => {
    const total = ranked.reduce((sum, s) => sum + s.total, 0);
    return [...ranked]
      .sort((a, b) => b.total - a.total)
      .slice(0, 3)
      .map((s) => ({ key: s.key, share: total ? s.total / total : 0 }));
  });

  const option = $derived({
    grid: { left: 64, right: 20, top: 56, bottom: 30 },
    legend: { top: 8, type: "scroll", textStyle: { fontSize: 11 } },
    tooltip: {
      trigger: "axis",
      axisPointer: { type: "shadow" },
      valueFormatter: (value: number) => `$${(value / 1e9).toFixed(2)}B`,
    },
    xAxis: { type: "category", data: years.map(String) },
    yAxis: {
      type: "value",
      axisLabel: { formatter: (value: number) => `$${(value / 1e9).toFixed(0)}B` },
    },
    series,
  });
</script>

<EChart {option} height="340px" />

<p class="note">
  Over the whole period,
  {#each shares as item, i}
    <strong>{label(item.key).toLowerCase()}</strong> took
    {Math.round(item.share * 100)}%{i < shares.length - 1 ? ", " : ""}
  {/each}
  of capital spending.
</p>

<style>
  .note {
    margin: 0.5rem 0 0;
    font-size: 0.8rem;
    color: var(--color-text-muted);
    max-width: 68ch;
  }
</style>
