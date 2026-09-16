<script lang="ts">
  import EChart from "../../charts/EChart.svelte";
  import { categorical, chrome } from "../../../lib/charts/palette";

  let {
    years,
    capital,
    operating,
    revenue,
    debt,
    byGuarantee = {},
    population = [],
  }: {
    years: number[];
    capital: number[];
    operating: number[];
    revenue: number[];
    debt: Record<string, number[]>;
    byGuarantee?: Record<string, number[]>;
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
        const go = byGuarantee.full_faith_and_credit?.[i] ?? 0;
        const rev = byGuarantee.nonguaranteed?.[i] ?? 0;
        // The split stops after FY2021, when Census dropped conduit debt.
        const split = go
          ? `<br/><span style="color:${chrome.inkMuted}">of which ${billions(
              go
            )} general obligation, ${billions(rev)} revenue-backed</span>`
          : "";
        return `<strong>FY${years[i]}</strong><br/>
          Owed at year end: <strong>${billions(outstanding[i] ?? 0)}</strong>${perPerson}<br/>
          Net new borrowing: <strong>${billions(net[i])}</strong><br/>
          Capital spending: <strong>${billions(capital[i] ?? 0)}</strong><br/>
          <span style="color:${chrome.inkMuted}">Operating surplus that year: ${billions(
            surplus[i]
          )}</span>${split}`;
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

{#if byGuarantee.full_faith_and_credit?.some((v) => v > 0)}
  <p class="note">
    Total owed steps down in FY2022 because Census stopped counting conduit debt
    — borrowing a state issues on another body's behalf without guaranteeing it —
    after a change in accounting standards. That is a change in what is measured,
    not a repayment. The split between general-obligation and revenue-backed debt
    stops at the same point.
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
