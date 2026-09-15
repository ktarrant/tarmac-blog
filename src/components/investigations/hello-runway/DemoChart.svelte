<script lang="ts">
  import EChart from "../../charts/EChart.svelte";
  import { hoveredState } from "../../../lib/stores";

  const days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];
  const departures = [412, 438, 455, 470, 510, 305, 268];

  const option = {
    grid: { left: 48, right: 16, top: 16, bottom: 28 },
    xAxis: { type: "category", data: days },
    yAxis: { type: "value" },
    tooltip: { trigger: "axis" },
    series: [{ type: "bar", data: departures, barMaxWidth: 24 }],
  };

  function handleHover(name: string) {
    hoveredState.set(name);
  }
</script>

<EChart {option} height="320px" onhover={handleHover} />
<p class="hover-readout">Hovered: {$hoveredState ?? "—"}</p>

<style>
  .hover-readout {
    margin: 0.5rem 0 0;
    font-size: 0.8rem;
    color: var(--color-text-muted);
  }
</style>
