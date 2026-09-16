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
  }: {
    years: number[];
    spending: number[];
    revenue: number[];
    governors: GovernorTerm[];
    anomalies?: Anomaly[];
    fiscalStartMonth?: number;
    perCapita?: boolean;
    population?: number[];
  } = $props();

  const scale = (values: number[]) =>
    perCapita ? values.map((v, i) => (population[i] ? v / population[i] : 0)) : values;

  const money = (value: number) =>
    perCapita
      ? `$${Math.round(value).toLocaleString()} per person`
      : `$${(value / 1e9).toFixed(1)}B`;

  // One band per governor, clipped to the years on the chart. Bands are drawn
  // behind the lines so the party context reads without competing with the data.
  const bands = $derived.by(() => {
    const seen: { term: GovernorTerm; from: number; to: number }[] = [];
    for (const year of years) {
      const term = governorForYear(governors, year, fiscalStartMonth);
      if (!term) continue;
      const last = seen.at(-1);
      if (last && last.term.name === term.name) last.to = year;
      else seen.push({ term, from: year, to: year });
    }
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
    legend: { top: 8, data: ["Spending", "Revenue"] },
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
        name: "Spending",
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
              xAxis: String(band.from),
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
                show: band.to - band.from >= 2,
                position: "insideTopLeft",
                color: chrome.inkSecondary,
                fontSize: 11,
                padding: [4, 6, 0, 6],
                formatter: () => band.term.name,
              },
            },
            { xAxis: String(band.to) },
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
