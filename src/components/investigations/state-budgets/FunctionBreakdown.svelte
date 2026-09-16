<script lang="ts">
  import EChart from "../../charts/EChart.svelte";
  import { categorical, chrome } from "../../../lib/charts/palette";
  import { label } from "../../../lib/stateBudgets";

  let {
    years,
    byFunction,
  }: { years: number[]; byFunction: Record<string, number[]> } = $props();

  // Rank by the most recent year and keep the leaders; the long tail of small
  // functions folds into "Other" rather than cycling colours past the palette.
  const MAX_SERIES = 7;

  const ranked = $derived(
    Object.entries(byFunction)
      .map(([key, values]) => ({ key, values, latest: values.at(-1) ?? 0 }))
      .sort((a, b) => b.latest - a.latest)
  );

  const series = $derived.by(() => {
    const leaders = ranked.slice(0, MAX_SERIES).filter((s) => s.latest > 0);
    const rest = ranked.slice(MAX_SERIES);
    const folded = years.map((_, i) =>
      rest.reduce((sum, s) => sum + (s.values[i] ?? 0), 0)
    );
    const out = leaders.map((s, index) => ({
      name: label(s.key),
      type: "line" as const,
      stack: "total",
      areaStyle: { opacity: 0.85 },
      lineStyle: { width: 0 },
      symbol: "none",
      emphasis: { focus: "series" as const },
      itemStyle: { color: categorical[index % categorical.length] },
      data: s.values,
    }));
    if (folded.some((v) => v > 0)) {
      out.push({
        name: "Other",
        type: "line",
        stack: "total",
        areaStyle: { opacity: 0.85 },
        lineStyle: { width: 0 },
        symbol: "none",
        emphasis: { focus: "series" },
        itemStyle: { color: chrome.inkMuted },
        data: folded,
      });
    }
    return out;
  });

  const option = $derived({
    grid: { left: 64, right: 20, top: 56, bottom: 30 },
    legend: { top: 8, type: "scroll", textStyle: { fontSize: 11 } },
    tooltip: {
      trigger: "axis",
      valueFormatter: (value: number) => `$${(value / 1e9).toFixed(1)}B`,
    },
    xAxis: { type: "category", data: years.map(String), boundaryGap: false },
    yAxis: {
      type: "value",
      axisLabel: { formatter: (value: number) => `$${(value / 1e9).toFixed(0)}B` },
    },
    series,
  });
</script>

<EChart {option} height="360px" />
