import { trykkKlasse } from '../model/bite.js';
import { fmtTime } from './scrubber.js';

const DIR = ['N', 'NØ', 'Ø', 'SØ', 'S', 'SV', 'V', 'NV'];
const dir = (deg) => DIR[Math.round(deg / 45) % 8];
const ARROW = { fallende: '↘', stabil: '→', stigende: '↗', raskt: '⇅' };

export function renderWeather(el, whenEl, d, ctx, climate, t) {
  if (!d.ok) { el.innerHTML = '<div class="warn"><span>Ingen værdata for dette tidspunktet</span><span>—</span></div>'; return; }
  const tk = trykkKlasse(d.dp3);
  const f = d.flow;
  const m = t.getMonth();
  const norm = climate?.tw_month_mean?.[m];
  const rows = [
    ['Luft', `${d.ta?.toFixed(1)} °C`],
    ['Vann (est.)', `${d.tw.toFixed(1)} °C${norm != null ? ` <span class="dim">(norm ${norm})</span>` : ''}${ctx.twInfo?.observed ? ' ✓NVE' : ''}`],
    ['Vind', `${d.wind.toFixed(1)} m/s ${dir(d.winddir)}`],
    ['Trykk', `${Math.round(d.pressure)} hPa ${ARROW[tk]} ${tk}`],
    ['Skyer', `${Math.round(d.cloud)} %`],
    ['Nedbør 24 t', `${d.rain24.toFixed(1)} mm`],
    ['Sikt', d.turb > 0.4 ? 'grumsete' : d.turb > 0.15 ? 'middels' : 'klart', d.turb > 0.4],
    ['Sol', d.sun.polarDay ? 'midnattssol' : d.sun.polarNight ? 'mørketid' : `${fmtTime(d.sun.sunrise)}–${fmtTime(d.sun.sunset)}`],
    ['Måne', `${d.moon.name} ${Math.round(d.moon.fraction * 100)} %`],
    ['Vannføring', f ? `${f.Q.toFixed(0)} m³/s${f.Qmed ? ` (${(100 * f.Q / f.Qmed - 100).toFixed(0) > 0 ? '+' : ''}${(100 * f.Q / f.Qmed - 100).toFixed(0)} % vs median)` : ''}` : '<span class="dim">ukjent – modellert middel</span>', f && Math.abs(f.a ?? 0) > 0.5],
  ];
  el.innerHTML = rows.map(([k, v, warn]) => `<div class="${warn ? 'warn' : ''}"><span>${k}</span><span>${v}</span></div>`).join('');
  whenEl.textContent = `· ${d.ok ? (t < ctx.weather.fetched ? 'historikk' : 'varsel') : ''}`;
}
