export const clamp = (x, lo = 0, hi = 1) => Math.max(lo, Math.min(hi, x));
export const logistic = x => 1 / (1 + Math.exp(-x));
export const mean = a => a.length ? a.reduce((s, x) => s + x, 0) / a.length : 0;
export function quantile(a, q) {
  if (!a.length) return 0;
  const b = [...a].sort((x, y) => x - y);
  const pos = (b.length - 1) * q; const lo = Math.floor(pos), hi = Math.ceil(pos);
  return lo === hi ? b[lo] : b[lo] + (b[hi] - b[lo]) * (pos - lo);
}
export function summarize(a) {
  return { mean: mean(a), p10: quantile(a, .1), p50: quantile(a, .5), p90: quantile(a, .9), p95: quantile(a, .95), min: Math.min(...a), max: Math.max(...a) };
}
export function fmtSeconds(s) {
  s = Math.max(0, Math.round(s));
  const m = Math.floor(s / 60), sec = s % 60;
  return `${m}:${String(sec).padStart(2, '0')}`;
}
