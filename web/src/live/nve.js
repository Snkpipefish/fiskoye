/** Leser data/live/nve.json (skrevet av GitHub Actions). Returnerer beste stasjon for området, eller null. */
export function stationFor(nve, slug) {
  const st = nve?.areas?.[slug]?.stations || [];
  return st.find((s) => s.q_day?.length) || st[0] || null;
}

const lastBefore = (series, t) => {
  if (!series?.length) return null;
  let best = null;
  for (const [ts, v] of series) { const d = new Date(ts); if (d <= t) best = { t: d, v }; else break; }
  return best || { t: new Date(series[0][0]), v: series[0][1] };
};

/** Vannføring ved t: {Q, Qmed, a=ln(Q/Qmed), dlnQ24, tw, level, station}. Q fra timeserie hvis den dekker t, ellers døgn. */
export function flowAt(station, t, fallbackMedian) {
  if (!station) return null;
  const h = lastBefore(station.q_hour, t);
  const d = lastBefore(station.q_day, t);
  const cur = (h && Math.abs(t - h.t) < 3 * 36e5) ? h : d;
  if (!cur) return null;
  const prev = lastBefore(station.q_day, new Date(t.getTime() - 24 * 36e5));
  const month = t.getMonth();
  const Qmed = station.q_median_month?.[month] ?? fallbackMedian?.[month] ?? null;
  const a = Qmed && cur.v > 0 ? Math.log(cur.v / Qmed) : null;
  const dlnQ24 = prev && prev.v > 0 && cur.v > 0 ? Math.log(cur.v / prev.v) : 0;
  const tw = lastBefore(station.tw_day, t);
  const lvl = lastBefore(station.level_day, t);
  return { Q: cur.v, Qt: cur.t, Qmed, a, dlnQ24, tw: tw?.v ?? null, level: lvl?.v ?? null, station };
}
