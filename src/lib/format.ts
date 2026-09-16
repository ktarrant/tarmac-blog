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

// Dates in frontmatter and in the data are plain calendar days, which parse as
// UTC midnight. Formatting those in local time renders the day before west of
// Greenwich, so every date on the site is formatted in UTC.
const longDate = new Intl.DateTimeFormat("en-US", {
  year: "numeric",
  month: "long",
  day: "numeric",
  timeZone: "UTC",
});

const shortDate = new Intl.DateTimeFormat("en-US", {
  year: "numeric",
  month: "short",
  day: "numeric",
  timeZone: "UTC",
});

export const formatDate = (value: Date | string) =>
  longDate.format(typeof value === "string" ? new Date(value) : value);

export const formatDateShort = (value: Date | string) =>
  shortDate.format(typeof value === "string" ? new Date(value) : value);

export const formatCurrencyCompact = (value: number) => currencyCompact.format(value);
export const formatCurrency = (value: number) => currencyFull.format(value);
export const formatPercent = (value: number) => percent.format(value);
export const formatPerCapita = (value: number) => `${currencyFull.format(value)} per capita`;
