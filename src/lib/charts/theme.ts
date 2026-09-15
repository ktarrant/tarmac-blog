import * as echarts from "echarts/core";
import { categorical, chrome } from "./palette";

/**
 * The "tarmac" ECharts theme: dark asphalt surface, fixed-order categorical
 * palette, recessive hairline gridlines, 2px lines. Register once, then pass
 * `theme: "tarmac"` to `echarts.init`.
 */
export const tarmacTheme = {
  color: categorical,
  backgroundColor: "transparent",
  textStyle: {
    fontFamily: "Inter, system-ui, sans-serif",
    color: chrome.inkSecondary,
  },
  title: {
    textStyle: { color: chrome.ink, fontFamily: "Space Grotesk, system-ui, sans-serif" },
  },
  line: {
    lineStyle: { width: 2 },
    symbol: "circle",
    symbolSize: 8,
    smooth: false,
  },
  bar: {
    itemStyle: { borderRadius: [4, 4, 0, 0] },
  },
  categoryAxis: {
    axisLine: { lineStyle: { color: chrome.baseline } },
    axisTick: { show: false },
    axisLabel: { color: chrome.inkMuted },
    splitLine: { show: false },
  },
  valueAxis: {
    axisLine: { show: false },
    axisTick: { show: false },
    axisLabel: { color: chrome.inkMuted },
    splitLine: { lineStyle: { color: chrome.gridline, width: 1, type: "solid" } },
  },
  legend: {
    textStyle: { color: chrome.inkSecondary },
    inactiveColor: chrome.inkMuted,
  },
  tooltip: {
    backgroundColor: chrome.surface,
    borderColor: chrome.gridline,
    borderWidth: 1,
    textStyle: { color: chrome.ink },
  },
  visualMap: {
    textStyle: { color: chrome.inkSecondary },
  },
};

let registered = false;

/** Registers the "tarmac" theme with the shared ECharts core, once. */
export function registerTarmacTheme() {
  if (registered) return;
  echarts.registerTheme("tarmac", tarmacTheme);
  registered = true;
}
