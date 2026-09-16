<script lang="ts">
  import { onMount } from "svelte";
  import EChart from "../../charts/EChart.svelte";
  import { categorical, chrome } from "../../../lib/charts/palette";
  import { withBase } from "../../../lib/withBase";

  let { metric = "perCapita" }: { metric?: "perCapita" | "total" } = $props();

  interface Row {
    abbr: string;
    name: string;
    total: number;
    perCapita: number;
  }

  let rows = $state<Row[]>([]);
  let failed = $state(false);

  onMount(async () => {
    try {
      const response = await fetch(withBase("/data/state-budgets/national.json"));
      const data = await response.json();
      const last = data.years.length - 1;
      const functions: Record<string, number[][]> = data.expenditure_by_function;

      rows = data.states
        .map((abbr: string, index: number) => {
          const total = Object.values(functions).reduce(
            (sum, grid) => sum + (grid[index]?.[last] ?? 0),
            0
          );
          const population = data.population[index]?.[last] ?? 0;
          return {
            abbr,
            name: data.names[abbr] ?? abbr,
            total,
            perCapita: population ? total / population : 0,
          };
        })
        .sort((a: Row, b: Row) => b[metric] - a[metric]);
    } catch {
      failed = true;
    }
  });

  const option = $derived({
    grid: { left: 96, right: 60, top: 8, bottom: 8 },
    tooltip: {
      trigger: "item",
      formatter: (p: any) => {
        const row = rows[rows.length - 1 - p.dataIndex];
        return `<strong>${row.name}</strong><br/>$${Math.round(
          row.perCapita
        ).toLocaleString()} per resident<br/>$${(row.total / 1e9).toFixed(
          1
        )}B total<br/><span style="color:${chrome.inkMuted}">Click to open</span>`;
      },
    },
    xAxis: {
      type: "value",
      axisLabel: {
        formatter: (v: number) =>
          metric === "perCapita" ? `$${(v / 1000).toFixed(0)}k` : `$${(v / 1e9).toFixed(0)}B`,
      },
    },
    // Reversed so the largest sits at the top of a horizontal bar chart.
    yAxis: {
      type: "category",
      data: [...rows].reverse().map((r) => r.abbr),
      axisLabel: { fontSize: 10, color: chrome.inkSecondary },
    },
    series: [
      {
        type: "bar",
        data: [...rows].reverse().map((r) => r[metric]),
        barMaxWidth: 10,
        itemStyle: { color: categorical[0], borderRadius: [0, 4, 4, 0] },
      },
    ],
  });

  function open(abbr: string) {
    if (!rows.some((row) => row.abbr === abbr)) return;
    window.location.href = withBase(
      `/investigations/state-budgets/states/${abbr.toLowerCase()}/`
    );
  }
</script>

{#if failed}
  <p class="fallback">Couldn't load the ranking data.</p>
{:else if rows.length === 0}
  <p class="fallback">Loading…</p>
{:else}
  <EChart {option} height="760px" onclick={open} />
  <p class="hint">Click any state to open its page.</p>
{/if}

<style>
  .fallback,
  .hint {
    margin: 0.5rem 0 0;
    font-size: 0.8rem;
    color: var(--color-text-muted);
  }
</style>
