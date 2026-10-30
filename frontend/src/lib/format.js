// Locale-aware formatting. Amounts are shown without a currency symbol because
// the currency is a business setting, not something the API stores per amount.

export const money = (v) =>
  Number(v ?? 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });

export const number = (v, digits = 0) =>
  Number(v ?? 0).toLocaleString(undefined, { maximumFractionDigits: digits });

export const dateTime = (v) => (v ? new Date(v).toLocaleString() : "—");

export const date = (v) => (v ? new Date(v).toLocaleDateString() : "—");

/** Viewer's UTC offset in minutes (e.g. 330 for IST), as the delivery analytics API expects. */
export const tzOffsetMinutes = () => -new Date().getTimezoneOffset();
