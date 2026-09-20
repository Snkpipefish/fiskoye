/** Vanntemperatur: EWMA(τ = 7 døgn) av lufttemp -> Mohseni-logistikk. Bias-korrigeres mot NVE-målt vanntemp om den finnes. */
export const mohseni = (ta, mu = 0.5, alpha = 24, beta = 12, gamma = 0.18) => mu + (alpha - mu) / (1 + Math.exp(gamma * (beta - ta)));

export function waterTempSeries(w, station) {
  const a = 1 - Math.exp(-1 / (7 * 24));
  let s = null; const tw = new Array(w.time.length); const taS = new Array(w.time.length);
  for (let i = 0; i < w.time.length; i++) {
    const ta = w.temp[i];
    if (ta == null) { tw[i] = tw[i - 1] ?? null; taS[i] = s; continue; }
    s = s == null ? ta : s + a * (ta - s);
    taS[i] = s; tw[i] = mohseni(s);
  }
  let bias = 0, nb = 0;
  for (const [ts, v] of station?.tw_day || []) {
    const t = new Date(ts).getTime() / 1000;
    const i = Math.round((t + 12 * 3600 - w.time[0]) / 3600);
    if (i >= 0 && i < tw.length && tw[i] != null && t > w.time[w.time.length - 1] - 20 * 86400) { bias += v - tw[i]; nb++; }
  }
  bias = nb ? bias / nb : 0;
  if (nb) for (let i = 0; i < tw.length; i++) if (tw[i] != null) tw[i] += bias;
  return { tw, taS, bias, observed: nb > 0 };
}
