const currencyCompact = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
  notation: "compact",
  maximumFractionDigits: 1,
});

const currencyFull = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
  maximumFractionDigits: 0,
});

const percent = new Intl.NumberFormat("en-US", {
  style: "percent",
  maximumFractionDigits: 1,
});

export const formatCurrencyCompact = (value: number) => currencyCompact.format(value);
export const formatCurrency = (value: number) => currencyFull.format(value);
export const formatPercent = (value: number) => percent.format(value);
export const formatPerCapita = (value: number) => `${currencyFull.format(value)} per capita`;
