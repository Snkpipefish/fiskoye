/** Egnethetskurver – speiler pipeline/fiskpipe/suitability.py nøyaktig. */
export const clip = (x, lo = 0, hi = 1) => (x < lo ? lo : x > hi ? hi : x);

export function trapezoid(x, d0, d1, d2, d3) {
  if (x <= d0 || x >= d3) return 0;
  if (x < d1) return (x - d0) / Math.max(d1 - d0, 1e-9);
  if (x <= d2) return 1;
  return (d3 - x) / Math.max(d3 - d2, 1e-9);
}
export function linear(x, v0, v1) { if (v0 === v1) return 1; return clip((x - v0) / (v1 - v0)); }
export const categorical = (cls, table, def = 0.3) => (table[cls] ?? def);
export function gaussAsym(x, opt, sLo, sHi, lo = null, hi = null, floor = 0.05) {
  if (lo !== null && x < lo) return floor;
  if (hi !== null && x > hi) return floor;
  const s = x < opt ? sLo : sHi;
  return Math.exp(-0.5 * ((x - opt) / Math.max(s, 1e-6)) ** 2);
}
export function wgeomean(values, weights, floor = 0.02) {
  const tot = weights.reduce((a, b) => a + b, 0);
  if (tot <= 0) return 0;
  let s = 0;
  for (let i = 0; i < values.length; i++) s += weights[i] * Math.log(Math.max(values[i], floor));
  return Math.exp(s / tot);
}
export function noisyOr(pairs) { let p = 1; for (const [w, x] of pairs) p *= 1 - clip(w * x); return 1 - p; }
