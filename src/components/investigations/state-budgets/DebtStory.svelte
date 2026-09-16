<script lang="ts">
  import EChart from "../../charts/EChart.svelte";
  import { categorical, chrome } from "../../../lib/charts/palette";

  let {
    years,
    capital,
    operating,
    revenue,
    debt,
    population = [],
  }: {
    years: number[];
    capital: number[];
    operating: number[];
    revenue: number[];
    debt: Record<string, number[]>;
    population?: number[];
  } = $props();

  const issued = $derived(debt.issued ?? []);
  const retired = $derived(debt.retired ?? []);
  const outstanding = $derived(debt.outstanding_end ?? []);

  // Borrowing issued minus borrowing repaid. This is the flow that moves the
  // stock of debt; issuance alone overstates it, because a large share of most
  // years' issuance refinances bonds being retired the same year.
  const net = $derived(years.map((_, i) => (issued[i] ?? 0) - (retired[i] ?? 0)));
  const surplus = $derived(years.map((_, i) => (revenue[i] ?? 0) - (operating[i] ?? 0)));

  const billions = (value: number) => `$${(value / 1e9).toFixed(2)}B`;

  const option = $derived({
    grid: { left: 70, right: 20, top: 48, bottom: 30 },
    legend: { top: 8 },
    tooltip: {
      trigger: "axis",
      formatter: (params: any[]) => {
        const i = params[0].dataIndex;
        const perPerson = population[i]
          ? `<br/><span style="color:${chrome.inkMuted}">$${Math.round(
              (outstanding[i] ?? 0) / population[i]
            ).toLocaleString()} per resident</span>`
          : "";
        return `<strong>FY${years[i]}</strong><br/>
          Owed at year end: <strong>${billions(outstanding[i] ?? 0)}</strong>${perPerson}<br/>
          Net new borrowing: <strong>${billions(net[i])}</strong><br/>
          Capital spending: <strong>${billions(capital[i] ?? 0)}</strong><br/>
          <span style="color:${chrome.inkMuted}">Operating surplus that year: ${billions(
            surplus[i]
          )}</span>`;
      },
    },
    xAxis: { type: "category", data: years.map(String) },
    yAxis: {
      type: "value",
      axisLabel: { formatter: (value: number) => `$${(value / 1e9).toFixed(0)}B` },
    },
    series: [
      {
        name: "Total owed",
        type: "line",
        data: outstanding,
        lineStyle: { width: 2 },
        itemStyle: { color: chrome.ink },
        areaStyle: { color: chrome.ink, opacity: 0.06 },
        symbol: "circle",
        symbolSize: 8,
        z: 3,
      },
      {
        name: "Capital spending",
        type: "bar",
        data: capital,
        barMaxWidth: 16,
        itemStyle: { color: categorical[0], borderRadius: [4, 4, 0, 0] },
      },
      {
        name: "Net new borrowing",
        type: "bar",
        data: net,
        barMaxWidth: 16,
        itemStyle: { color: categorical[3], borderRadius: [4, 4, 0, 0] },
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

<EChart {option} height="380px" />

<style>
</style>
