<script lang="ts">
  import EChart from "../../charts/EChart.svelte";
  import { categorical, chrome } from "../../../lib/charts/palette";

  let {
    years,
    name,
    burden,
    median,
  }: {
    years: number[];
    name: string;
    burden: { interest_share: number[]; debt_share: number[] };
    median: { interest_share: number[]; debt_share: number[] };
  } = $props();

  // Interest is the burden. Debt outstanding is a stock that costs nothing by
  // itself; what a budget actually feels is the interest coming due each year.
  // Principal repaid is deliberately excluded — much of it is refinancing, and
  // counting it puts states that rolled over debt at 37% of revenue, which
  // describes their treasury operations rather than any strain on them.
  const option = $derived({
    grid: { left: 58, right: 20, top: 48, bottom: 30 },
    legend: { top: 8, textStyle: { fontSize: 11 } },
    tooltip: {
      trigger: "axis",
      formatter: (params: any[]) => {
        const i = params[0].dataIndex;
        const months = burden.debt_share[i] * 12;
        const medianMonths = median.debt_share[i] * 12;
        return `<strong>FY${years[i]}</strong><br/>
          ${name}: <strong>${(burden.interest_share[i] * 100).toFixed(2)}%</strong> of revenue goes to interest<br/>
          <span style="color:${chrome.inkMuted}">Median state: ${(
            median.interest_share[i] * 100
          ).toFixed(2)}%</span><br/>
          <br/>Debt outstanding equals <strong>${months.toFixed(1)} months</strong> of revenue<br/>
          <span style="color:${chrome.inkMuted}">Median state: ${medianMonths.toFixed(
            1
          )} months</span>`;
      },
    },
    xAxis: { type: "category", data: years.map(String), boundaryGap: false },
    yAxis: {
      type: "value",
      axisLabel: { formatter: (value: number) => `${(value * 100).toFixed(1)}%` },
    },
    series: [
      {
        name,
        type: "line",
        data: burden.interest_share,
        lineStyle: { width: 2 },
        itemStyle: { color: categorical[1] },
        areaStyle: { color: categorical[1], opacity: 0.16 },
        symbol: "circle",
        symbolSize: 8,
        z: 3,
      },
      {
        name: "Median state",
        type: "line",
        data: median.interest_share,
        lineStyle: { width: 2, type: "dashed" },
        itemStyle: { color: chrome.inkMuted },
        symbol: "none",
        z: 2,
      },
    ],
  });
</script>

<EChart {option} height="360px" />

<p class="note">
  Interest only. Principal repaid is left out because much of it refinances
  existing bonds rather than retiring them, which would put states that simply
  rolled debt over at a third of their revenue and describe their treasury
  operations rather than any strain on them.
</p>

<style>
  .note {
    margin: 0.5rem 0 0;
    font-size: 0.8rem;
    color: var(--color-text-muted);
    max-width: 70ch;
  }
</style>
