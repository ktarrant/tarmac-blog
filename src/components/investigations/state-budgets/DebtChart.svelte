<script lang="ts">
  import EChart from "../../charts/EChart.svelte";
  import { categorical, chrome } from "../../../lib/charts/palette";

  let {
    years,
    debt,
    population = [],
  }: {
    years: number[];
    debt: Record<string, number[]>;
    population?: number[];
  } = $props();

  // The stock of debt, not the flows — issuance and repayment are shown against
  // capital spending in the chart above, and repeating them here said the same
  // thing twice without adding the one number this answers: what is still owed.
  const outstanding = $derived(debt.outstanding_end ?? []);
  const perCapita = $derived(
    years.map((_, i) => (population[i] ? (outstanding[i] ?? 0) / population[i] : 0))
  );

  const option = $derived({
    grid: { left: 68, right: 20, top: 44, bottom: 30 },
    legend: { top: 8 },
    tooltip: {
      trigger: "axis",
      formatter: (params: any[]) => {
        const index = params[0].dataIndex;
        return `<strong>FY${years[index]}</strong><br/>Outstanding: <strong>$${(
          (outstanding[index] ?? 0) / 1e9
        ).toFixed(1)}B</strong><br/>Per resident: <strong>$${Math.round(
          perCapita[index]
        ).toLocaleString()}</strong>`;
      },
    },
    xAxis: { type: "category", data: years.map(String) },
    yAxis: {
      type: "value",
      axisLabel: { formatter: (value: number) => `$${(value / 1e9).toFixed(0)}B` },
    },
    series: [
      {
        name: "Long-term debt outstanding",
        type: "line",
        data: outstanding,
        lineStyle: { width: 2 },
        itemStyle: { color: categorical[7] },
        areaStyle: { opacity: 0.1 },
        symbol: "circle",
        symbolSize: 8,
      },
    ],
  });
</script>

<EChart {option} height="300px" />
<p class="note">
  Debt per resident:
  {#if perCapita.length}
    ${Math.round(perCapita[0]).toLocaleString()} in FY{years[0]} →
    <strong style={`color:${chrome.ink}`}
      >${Math.round(perCapita[perCapita.length - 1]).toLocaleString()}</strong
    >
    in FY{years[years.length - 1]}.
  {/if}
  This is money owed on bonds, not an annual cost — what it costs each year is
  the interest, counted in the operating budget.
</p>

<style>
  .note {
    margin: 0.5rem 0 0;
    font-size: 0.8rem;
    color: var(--color-text-muted);
  }
</style>
