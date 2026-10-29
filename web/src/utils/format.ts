// Shared number formatting. Each formatter returns null for a missing value, so the caller can
// show "—" with the reason (never 0 or a blank).

/** Counts with thousands separators: 43591 -> "43,591". */
export const fmtCount = (n: number | null | undefined): string | null =>
  n == null ? null : n.toLocaleString('en-US');

/** Run rates, economy and averages to two decimals: 12 -> "12.00". */
export const fmtRate = (n: number | null | undefined): string | null =>
  n == null ? null : n.toFixed(2);

/** Percentages the API already rounded to one decimal: 60 -> "60.0%". */
export const fmtPct = (n: number | null | undefined): string | null =>
  n == null ? null : `${n.toFixed(1)}%`;

/** Seasons compressed into ranges: [2011, 2022, 2023, 2024] -> "2011, 2022–2024". */
export const fmtSeasons = (seasons: number[]): string => {
  const sorted = [...seasons].sort((a, b) => a - b);
  const parts: string[] = [];
  sorted.forEach((s, i) => {
    if (i > 0 && s === sorted[i - 1] + 1) return;
    let end = s;
    while (sorted.includes(end + 1)) end += 1;
    parts.push(end === s ? `${s}` : `${s}–${end}`);
  });
  return parts.join(', ');
};

/** part / whole as a one-decimal percentage, halves rounded up; null when whole is 0. */
export const fmtShare = (part: number, whole: number): string | null =>
  whole > 0 ? fmtPct(Math.round((part * 1000) / whole) / 10) : null;
