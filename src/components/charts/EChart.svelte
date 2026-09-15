<script lang="ts">
  import { onMount, onDestroy } from "svelte";
  import type { EChartsCoreOption, ECharts } from "echarts/core";
  import { echarts, setupEcharts } from "../../lib/charts/setup";

  let {
    option,
    height = "360px",
    onhover,
    onclick,
  }: {
    option: EChartsCoreOption;
    height?: string;
    onhover?: (name: string) => void;
    onclick?: (name: string) => void;
  } = $props();

  let el: HTMLDivElement;
  let chart: ECharts | null = null;
  let ro: ResizeObserver | null = null;

  onMount(() => {
    setupEcharts();
    const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    chart = echarts.init(el, "tarmac", { renderer: "svg" });
    chart.setOption({ ...option, animation: !reduceMotion });
    chart.on("mouseover", (params: any) => onhover?.(String(params.name)));
    chart.on("click", (params: any) => onclick?.(String(params.name)));

    ro = new ResizeObserver(() => chart?.resize());
    ro.observe(el);
  });

  onDestroy(() => {
    ro?.disconnect();
    chart?.dispose();
  });

  $effect(() => {
    chart?.setOption(option);
  });
</script>

<div class="echart" bind:this={el} style:height></div>

<style>
  .echart {
    width: 100%;
  }
</style>
