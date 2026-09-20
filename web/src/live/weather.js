/** Open-Meteo: én forespørsel med 45 døgn historikk + 7 døgn varsel, timesoppløsning, epoch-tid. */
const API = 'https://api.open-meteo.com/v1/forecast';
const VARS = 'temperature_2m,precipitation,pressure_msl,wind_speed_10m,wind_direction_10m,cloud_cover,shortwave_radiation';

export async function fetchWeather(lat, lon) {
  const key = `fiskoye:wx:${lat.toFixed(2)},${lon.toFixed(2)}`;
  try {
    const c = JSON.parse(localStorage.getItem(key));
    if (c && Date.now() - c.at < 3600e3) return hydrate(c.d);
  } catch { /* ignorer */ }
  const url = `${API}?latitude=${lat}&longitude=${lon}&hourly=${VARS}&past_days=45&forecast_days=7&timezone=Europe%2FOslo&wind_speed_unit=ms&timeformat=unixtime`;
  const r = await fetch(url);
  if (!r.ok) throw new Error(`Open-Meteo HTTP ${r.status}`);
  const d = await r.json();
  try { localStorage.setItem(key, JSON.stringify({ at: Date.now(), d })); } catch { /* full */ }
  return hydrate(d);
}

function hydrate(d) {
  const h = d.hourly;
  return { time: h.time, temp: h.temperature_2m, precip: h.precipitation, pressure: h.pressure_msl, wind: h.wind_speed_10m,
    winddir: h.wind_direction_10m, cloud: h.cloud_cover, rad: h.shortwave_radiation, elevation: d.elevation, fetched: new Date() };
}

export function idx(w, t) {
  const i = Math.round((t.getTime() / 1000 - w.time[0]) / 3600);
  return Math.min(Math.max(i, 0), w.time.length - 1);
}
export const at = (w, key, t) => w[key][idx(w, t)];
export function sum(w, key, t, hoursBack) {
  const i1 = idx(w, t); const i0 = Math.max(0, i1 - hoursBack);
  let s = 0; for (let i = i0; i <= i1; i++) s += w[key][i] ?? 0;
  return s;
}
export function inRange(w, t) { const s = t.getTime() / 1000; return s >= w.time[0] && s <= w.time[w.time.length - 1] + 3600; }
export const range = (w) => [new Date(w.time[0] * 1000), new Date(w.time[w.time.length - 1] * 1000)];
