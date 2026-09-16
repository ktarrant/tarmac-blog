<script lang="ts">
  import EChart from "../../charts/EChart.svelte";
  import { categorical, chrome } from "../../../lib/charts/palette";

  let {
    years,
    capital,
    operating,
    revenue,
    debt,
    byPurpose = {},
    population = [],
  }: {
    years: number[];
    capital: number[];
    operating: number[];
    revenue: number[];
    debt: Record<string, number[]>;
    byPurpose?: Record<string, number[]>;
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

  // Two tracks, stacked to the published total. Conduit debt is borrowing the
  // state issues for private borrowers who repay it, so it inflates the total
  // without being a burden on taxpayers — which is why it was dropped in FY2022.
  const conduit = $derived(byPurpose.private_purpose ?? years.map(() => 0));
  const ownDebt = $derived(
    byPurpose.public_purpose ?? years.map((_, i) => outstanding[i] ?? 0)
  );

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
        // The split stops after FY2021, when Census dropped conduit debt.
        const split = conduit[i]
          ? `<br/><span style="color:${chrome.inkMuted}">of which ${billions(
              conduit[i]
            )} was conduit debt issued for private borrowers</span>`
          : "";
        return `<strong>FY${years[i]}</strong><br/>
          Owed at year end: <strong>${billions(outstanding[i] ?? 0)}</strong>${perPerson}${split}<br/>
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
        name: "The state's own debt",
        type: "line",
        stack: "owed",
        data: ownDebt,
        lineStyle: { width: 0 },
        // itemStyle drives the legend swatch; without it the legend shows a
        // default palette colour that doesn't match the fill.
        itemStyle: { color: categorical[6] },
        areaStyle: { color: categorical[6], opacity: 0.32 },
        symbol: "none",
        z: 2,
      },
      {
        name: "Conduit debt (issued for private borrowers)",
        type: "line",
        stack: "owed",
        data: conduit,
        lineStyle: { width: 0 },
        itemStyle: { color: chrome.inkMuted },
        areaStyle: { color: chrome.inkMuted, opacity: 0.22 },
        symbol: "none",
        z: 2,
      },
      {
        name: "Capital spending",
        type: "bar",
        data: capital,
        barMaxWidth: 16,
        itemStyle: { color: categorical[0], borderRadius: [4, 4, 0, 0] },
        z: 4,
      },
      {
        name: "Net new borrowing",
        type: "bar",
        data: net,
        barMaxWidth: 16,
        itemStyle: { color: categorical[3], borderRadius: [4, 4, 0, 0] },
        z: 4,
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

{#if conduit.some((v) => v > 0)}
  <p class="note">
    The grey band is conduit debt — bonds a state issues on behalf of private
    borrowers such as industrial developers, hospitals and colleges, who repay
    them. It counts against the state on paper without being a burden on its
    taxpayers. Accounting standards changed in FY2022 and Census stopped
    reporting it, which is why the total drops that year: nothing was repaid,
    it stopped being counted.
  </p>
{/if}

<style>
  .note {
    margin: 0.5rem 0 0;
    font-size: 0.8rem;
    color: var(--color-text-muted);
    max-width: 68ch;
  }
</style>
