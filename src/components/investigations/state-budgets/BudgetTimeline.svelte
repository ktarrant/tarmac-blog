<script lang="ts">
  import EChart from "../../charts/EChart.svelte";
  import { party as partyColors, chrome, categorical } from "../../../lib/charts/palette";
  import {
    anomalyLabel,
    governorForYear,
    PARTY_NAMES,
    type Anomaly,
    type GovernorTerm,
  } from "../../../lib/stateBudgets";

  let {
    years,
    spending,
    revenue,
    governors,
    anomalies = [],
    fiscalStartMonth = 7,
    perCapita = false,
    population = [],
    spendingLabel = "Operating spending",
  }: {
    years: number[];
    spending: number[];
    revenue: number[];
    governors: GovernorTerm[];
    anomalies?: Anomaly[];
    fiscalStartMonth?: number;
    perCapita?: boolean;
    population?: number[];
    spendingLabel?: string;
  } = $props();

  const scale = (values: number[]) =>
    perCapita ? values.map((v, i) => (population[i] ? v / population[i] : 0)) : values;

  const money = (value: number) =>
    perCapita
      ? `$${Math.round(value).toLocaleString()} per person`
      : `$${(value / 1e9).toFixed(1)}B`;

  // One band per governor, held as axis indices rather than year labels. A
  // band runs from half a step before its first fiscal year to half a step
  // after its last, so consecutive terms meet exactly at the midpoint between
  // two ticks instead of leaving an unshaded gap — which is also the honest
  // place for the boundary, since governors take office mid-fiscal-year.
  const bands = $derived.by(() => {
    const seen: { term: GovernorTerm; from: number; to: number }[] = [];
    years.forEach((year, index) => {
      const term = governorForYear(governors, year, fiscalStartMonth);
      if (!term) return;
      const last = seen.at(-1);
      if (last && last.term.name === term.name) last.to = index;
      else seen.push({ term, from: index, to: index });
    });
    return seen;
  });

  const bandColor = (party: string | null) => {
    if (party === "D") return partyColors.dem;
    if (party === "R") return partyColors.gop;
    return chrome.inkMuted;
  };

  // Only events worth a marker: real ones, ranked, not data artifacts.
  const marked = $derived(
    anomalies
      .filter((a) => a.kind === "spike" || a.kind === "level_shift")
      .slice(0, 4)
  );

  const option = $derived({
    grid: { left: 64, right: 20, top: 44, bottom: 30 },
    legend: { top: 8, data: [spendingLabel, "Revenue"] },
    tooltip: {
      trigger: "axis",
      formatter: (params: any[]) => {
        const year = params[0].axisValue;
        const term = governorForYear(governors, Number(year), fiscalStartMonth);
        const lines = params.map(
          (p) => `${p.marker} ${p.seriesName}: <strong>${money(p.value)}</strong>`
        );
        const who = term
          ? `<div style="color:${bandColor(term.party)};margin-top:4px">${term.name} (${
              PARTY_NAMES[term.party ?? ""] ?? "—"
            })</div>`
          : "";
        const events = marked.filter((a) => a.year === Number(year));
        const eventLines = events.map(
          (a) =>
            `<div style="color:${chrome.inkSecondary};margin-top:4px">${anomalyLabel(
              a.metric
            )} ${a.change > 0 ? "+" : ""}${Math.round(a.change * 100)}%</div>`
        );
        return `<strong>FY${year}</strong><br/>${lines.join("<br/>")}${who}${eventLines.join("")}`;
      },
    },
    xAxis: { type: "category", data: years.map(String), boundaryGap: false },
    yAxis: {
      type: "value",
      axisLabel: {
        formatter: (value: number) =>
          perCapita ? `$${(value / 1000).toFixed(0)}k` : `$${(value / 1e9).toFixed(0)}B`,
      },
    },
    series: [
      {
        name: spendingLabel,
        type: "line",
        data: scale(spending),
        lineStyle: { width: 2 },
        itemStyle: { color: categorical[1] },
        symbol: "circle",
        symbolSize: 8,
        z: 3,
        markArea: {
          silent: true,
          data: bands.map((band, index) => [
            {
              xAxis: band.from - 0.5,
              // Alternating weight keeps consecutive same-party governors
              // visually separable; colour alone can't, since both are red.
              itemStyle: {
                color: bandColor(band.term.party),
                opacity: index % 2 === 0 ? 0.14 : 0.07,
                borderColor: bandColor(band.term.party),
                borderWidth: 1,
                borderType: "dashed",
              },
              name: band.term.name,
              label: {
                show: band.to - band.from >= 1,
                position: "insideTopLeft",
                color: chrome.inkSecondary,
                fontSize: 11,
                padding: [4, 6, 0, 6],
                formatter: () => band.term.name,
              },
            },
            { xAxis: band.to + 0.5 },
          ]),
        },
        markLine: {
          silent: true,
          symbol: "none",
          lineStyle: { color: chrome.inkMuted, type: "dashed", width: 1 },
          label: { show: false },
          data: marked.map((a) => ({ xAxis: String(a.year) })),
        },
      },
      {
        name: "Revenue",
        type: "line",
        data: scale(revenue),
        lineStyle: { width: 2 },
        itemStyle: { color: categorical[2] },
        symbol: "circle",
        symbolSize: 8,
        z: 3,
      },
    ],
  });
</script>

<EChart {option} height="380px" />

<ul class="governors">
  {#each bands as band}
    <li>
      <span class="swatch" style={`background:${bandColor(band.term.party)}`}></span>
      <span class="who">{band.term.name}</span>
      <span class="when">
        FY{years[band.from]}{band.from === band.to ? "" : `–FY${years[band.to]}`}
        · {PARTY_NAMES[band.term.party ?? ""] ?? "—"}
      </span>
    </li>
  {/each}
</ul>

<style>
  .governors {
    display: flex;
    flex-wrap: wrap;
    gap: 0.35rem 1.25rem;
    list-style: none;
    margin: 0.75rem 0 0;
    padding: 0;
    font-size: 0.8rem;
  }

  .governors li {
    display: flex;
    align-items: center;
    gap: 0.4rem;
  }

  .swatch {
    width: 10px;
    height: 10px;
    border-radius: 2px;
    flex: none;
  }

  .who {
    color: var(--color-text);
  }

  .when {
    color: var(--color-text-muted);
  }
</style>
