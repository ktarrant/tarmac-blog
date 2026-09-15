/**
 * Fixed-order categorical palette, validated against --color-bg (#0e1116)
 * with the dataviz skill's validator (all checks pass; worst adjacent CVD
 * ΔE 8.4). Assign by slot order — never cycle or reassign by rank.
 */
export const categorical = [
  "#3987e5", // 1 blue
  "#d95926", // 2 orange
  "#199e70", // 3 aqua
  "#c98500", // 4 yellow
  "#d55181", // 5 magenta
  "#008300", // 6 green
  "#9085e9", // 7 violet
  "#e66767", // 8 red
];

export const party = {
  dem: "#3987e5",
  gop: "#e66767",
};

export const status = {
  good: "#0ca30c",
  warning: "#fab219",
  serious: "#ec835a",
  critical: "#d03b3b",
};

export const sequentialBlue = [
  "#cde2fb",
  "#9ec5f4",
  "#6da7ec",
  "#3987e5",
  "#256abf",
  "#184f95",
  "#0d366b",
];

export const chrome = {
  surface: "#161b22",
  page: "#0e1116",
  ink: "#eef1f5",
  inkSecondary: "#a8b0bb",
  inkMuted: "#6b7280",
  gridline: "#232933",
  baseline: "#383a40",
};
