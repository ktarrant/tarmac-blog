import * as echarts from "echarts/core";
import { LineChart, BarChart } from "echarts/charts";
import {
  GridComponent,
  TooltipComponent,
  LegendComponent,
  TitleComponent,
  DatasetComponent,
} from "echarts/components";
import { SVGRenderer } from "echarts/renderers";
import { registerTarmacTheme } from "./theme";

let initialized = false;

/**
 * Registers the chart types/components used so far and the tarmac theme,
 * once. Add more `echarts/charts` (map, treemap, sunburst, sankey…) here as
 * later investigations need them — keeps the bundle tree-shaken.
 */
export function setupEcharts() {
  if (initialized) return;
  echarts.use([
    LineChart,
    BarChart,
    GridComponent,
    TooltipComponent,
    LegendComponent,
    TitleComponent,
    DatasetComponent,
    SVGRenderer,
  ]);
  registerTarmacTheme();
  initialized = true;
}

export { echarts };
