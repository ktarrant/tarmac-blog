<script lang="ts">
  import EChart from "../../charts/EChart.svelte";
  import { categorical, chrome } from "../../../lib/charts/palette";

  let {
    years,
    capital,
    debt,
  }: {
    years: number[];
    capital: number[];
    debt: Record<string, number[]>;
  } = $props();

  const issued = $derived(debt.issued ?? []);
  const retired = $derived(debt.retired ?? []);

  // Net borrowing is what actually changes what a state owes. Issuance alone
  // overstates it, because much of each year's issuance refinances debt being
  // retired in the same year.
  const net = $derived(years.map((_, i) => (issued[i] ?? 0) - (retired[i] ?? 0)));

  const option = $derived({
    grid: { left: 68, right: 20, top: 44, bottom: 30 },
    legend: { top: 8 },
    tooltip: {
      trigger: "axis",
      valueFormatter: (value: number) => `$${(value / 1e9).toFixed(2)}B`,
    },
    xAxis: { type: "category", data: years.map(String) },
    yAxis: {
      type: "value",
      axisLabel: { formatter: (value: number) => `$${(value / 1e9).toFixed(0)}B` },
    },
    series: [
      {
        name: "Capital spending",
        type: "bar",
        data: capital,
        barMaxWidth: 22,
        itemStyle: { color: categorical[0], borderRadius: [4, 4, 0, 0] },
      },
      {
        name: "Net new borrowing",
        type: "line",
        data: net,
        lineStyle: { width: 2 },
        itemStyle: { color: categorical[3] },
        symbol: "circle",
        symbolSize: 8,
        markLine: {
          silent: true,
          symbol: "none",
          lineStyle: { color: chrome.baseline, width: 1 },
          label: { show: false },
          data: [{ yAxis: 0 }],
        },
      },
    ],
  });
</script>

<EChart {option} height="320px" />
<p class="note">
  Bars are what the state spent building things; the line is borrowing issued
  minus borrowing repaid. Where the line sits below zero the state paid down
  more than it took on.
</p>

<style>
  .note {
    margin: 0.5rem 0 0;
    font-size: 0.8rem;
    color: var(--color-text-muted);
  }
</style>
