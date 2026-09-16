<script lang="ts">
  import EChart from "../../charts/EChart.svelte";
  import { categorical, chrome } from "../../../lib/charts/palette";

  let {
    years,
    debt,
  }: { years: number[]; debt: Record<string, number[]> } = $props();

  const outstanding = $derived(debt.outstanding_end ?? []);
  const issued = $derived(debt.issued ?? []);
  const retired = $derived(debt.retired ?? []);

  const option = $derived({
    grid: { left: 64, right: 64, top: 44, bottom: 30 },
    legend: { top: 8 },
    tooltip: {
      trigger: "axis",
      valueFormatter: (value: number) => `$${(value / 1e9).toFixed(1)}B`,
    },
    xAxis: { type: "category", data: years.map(String) },
    yAxis: {
      type: "value",
      axisLabel: { formatter: (value: number) => `$${(value / 1e9).toFixed(0)}B` },
    },
    series: [
      {
        name: "Issued",
        type: "bar",
        data: issued,
        barMaxWidth: 18,
        itemStyle: { color: categorical[3], borderRadius: [4, 4, 0, 0] },
      },
      {
        name: "Retired",
        type: "bar",
        data: retired.map((v) => -v),
        barMaxWidth: 18,
        itemStyle: { color: categorical[2], borderRadius: [0, 0, 4, 4] },
        tooltip: { valueFormatter: (v: number) => `$${(Math.abs(v) / 1e9).toFixed(1)}B` },
      },
      {
        name: "Outstanding",
        type: "line",
        data: outstanding,
        lineStyle: { width: 2 },
        itemStyle: { color: chrome.ink },
        symbol: "circle",
        symbolSize: 8,
      },
    ],
  });
</script>

<EChart {option} height="340px" />
<p class="note">
  Bars show debt issued and retired each year; the line is total long-term debt
  outstanding. Issuance is lumpy by nature — a state borrows when it borrows.
</p>

<style>
  .note {
    margin: 0.5rem 0 0;
    font-size: 0.8rem;
    color: var(--color-text-muted);
  }
</style>
