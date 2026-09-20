import { biteColor } from '../map.js';
import { fmtTime } from './scrubber.js';

const DAYS = ['sø', 'ma', 'ti', 'on', 'to', 'fr', 'lø'];
export function renderForecast(el, wk, t, onPick) {
  const sameDay = (a, b) => a.getFullYear() === b.getFullYear() && a.getMonth() === b.getMonth() && a.getDate() === b.getDate();
  el.innerHTML = wk.map((w) => `<div class="day${sameDay(w.date, t) ? ' on' : ''}" title="Beste vindu ${fmtTime(w.best.start)}–${fmtTime(w.best.end)}">
    <div>${DAYS[w.date.getDay()]} ${w.date.getDate()}</div>
    <div class="b"><i style="height:${Math.max(6, 34 * w.max / 100)}px;background:${biteColor(w.max)}"></i></div>
    <div class="v">${Math.round(w.max)}</div><div>${String(w.best.start.getHours()).padStart(2, '0')}–${String(w.best.end.getHours() || 24).padStart(2, '0')}</div></div>`).join('');
  [...el.children].forEach((c, i) => { c.onclick = () => onPick(wk[i]); });
}
