<script lang="ts">
  import EChart from "../../charts/EChart.svelte";
  import { categorical, chrome } from "../../../lib/charts/palette";

  let {
    years,
    debt,
    byPurpose = {},
    holdings = {},
    gdp = [],
    population = [],
  }: {
    years: number[];
    debt: Record<string, number[]>;
    byPurpose?: Record<string, number[]>;
    holdings?: Record<string, number[]>;
    gdp?: number[];
    population?: number[];
  } = $props();

  const outstanding = $derived(debt.outstanding_end ?? []);
  const conduitDollars = $derived(byPurpose.private_purpose ?? years.map(() => 0));
  const ownDollars = $derived(
    byPurpose.public_purpose ?? years.map((_, i) => outstanding[i] ?? 0)
  );
  const holdingsDollars = $derived(
    years.map((_, i) => Object.values(holdings).reduce((sum, v) => sum + (v[i] ?? 0), 0))
  );

  // A dollar figure says nothing about whether a state owes a lot: $26B is
  // crushing for Vermont and trivial for California. Against the size of the
  // state's economy it becomes both interpretable and comparable.
  const share = (values: number[]) =>
    years.map((_, i) => (gdp[i] ? (values[i] ?? 0) / gdp[i] : null));

  const own = $derived(share(ownDollars));
  const conduit = $derived(share(conduitDollars));
  // Census stopped publishing holdings after FY2021, so the line ends rather
  // than dropping to zero, which would read as a state spending its reserves.
  const held = $derived(
    years.map((_, i) => (holdingsDollars[i] > 0 && gdp[i] ? holdingsDollars[i] / gdp[i] : null))
  );

  const pct = (value: number | null) => (value === null ? "—" : `${(value * 100).toFixed(1)}%`);
  const billions = (value: number) => `$${(value / 1e9).toFixed(1)}B`;

  const option = $derived({
    grid: { left: 58, right: 20, top: 48, bottom: 30 },
    legend: { top: 8, textStyle: { fontSize: 11 } },
    tooltip: {
      trigger: "axis",
      formatter: (params: any[]) => {
        const i = params[0].dataIndex;
        const perPerson = population[i]
          ? ` · $${Math.round((outstanding[i] ?? 0) / population[i]).toLocaleString()} per resident`
          : "";
        const conduitLine = conduitDollars[i]
          ? `<br/><span style="color:${chrome.inkMuted}">of which ${billions(
              conduitDollars[i]
            )} conduit debt for private borrowers</span>`
          : "";
        const heldLine = holdingsDollars[i]
          ? `<br/>Cash and securities held: <strong>${billions(holdingsDollars[i])}</strong> (${pct(
              held[i]
            )})`
          : `<br/><span style="color:${chrome.inkMuted}">Holdings no longer published</span>`;
        return `<strong>FY${years[i]}</strong><br/>
          Owed: <strong>${billions(outstanding[i] ?? 0)}</strong> (${pct(
            gdp[i] ? (outstanding[i] ?? 0) / gdp[i] : null
          )} of GDP)${perPerson}${conduitLine}${heldLine}<br/>
          <span style="color:${chrome.inkMuted}">State economy: ${billions(gdp[i] ?? 0)}</span>`;
      },
    },
    xAxis: { type: "category", data: years.map(String), boundaryGap: false },
    yAxis: {
      type: "value",
      axisLabel: { formatter: (value: number) => `${(value * 100).toFixed(0)}%` },
    },
    series: [
      {
        name: "The state's own debt",
        type: "line",
        stack: "owed",
        data: own,
        lineStyle: { width: 0 },
        itemStyle: { color: categorical[6] },
        areaStyle: { color: categorical[6], opacity: 0.4 },
        symbol: "none",
      },
      {
        name: "Conduit debt (for private borrowers)",
        type: "line",
        stack: "owed",
        data: conduit,
        lineStyle: { width: 0 },
        itemStyle: { color: chrome.inkMuted },
        areaStyle: { color: chrome.inkMuted, opacity: 0.25 },
        symbol: "none",
      },
      {
        name: "Cash and securities held",
        type: "line",
        data: held,
        lineStyle: { width: 2, type: "dashed" },
        itemStyle: { color: categorical[3] },
        symbol: "circle",
        symbolSize: 7,
        connectNulls: false,
        z: 4,
      },
    ],
  });
</script>

<EChart {option} height="380px" />

<p class="note">
  Measured against the size of the state's economy, so it can be compared with
  other states and with itself over time.
  {#if holdingsDollars.some((v) => v > 0)}
    The dashed line is cash and securities the state holds outside its pension
    funds — sinking funds set aside for debt service, unspent bond proceeds and
    general balances. Census stopped publishing it after FY2021, so the line
    ends there rather than falling to zero.
  {/if}
</p>

<style>
  .note {
    margin: 0.5rem 0 0;
    font-size: 0.8rem;
    color: var(--color-text-muted);
    max-width: 70ch;
  }
</style>
