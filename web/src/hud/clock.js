import { biteColor } from '../map.js';
import { fmtTime } from './scrubber.js';

const C = 85, R = 70, r = 50;
const pol = (a, rad) => [C + rad * Math.sin(a), C - rad * Math.cos(a)];
const ang = (h) => (h / 24) * 2 * Math.PI;
const arc = (h0, h1, ro, ri) => {
  const [ax, ay] = pol(ang(h0), ro), [bx, by] = pol(ang(h1), ro), [cx, cy] = pol(ang(h1), ri), [dx, dy] = pol(ang(h0), ri);
  const big = (h1 - h0) > 12 ? 1 : 0;
  return `M${ax},${ay} A${ro},${ro} 0 ${big} 1 ${bx},${by} L${cx},${cy} A${ri},${ri} 0 ${big} 0 ${dx},${dy} Z`;
};

/** cv: kurve (30-min-steg) for dagen, d: avledede forhold nå, t: tidspunkt, best: {start,end}, onPick(hour) */
export function renderClock(el, cv, d, t, best, onPick, Bnow) {
  const step = 24 / cv.length;
  const segs = cv.map((p, i) => `<path class="seg" data-h="${(i * step).toFixed(2)}" d="${arc(i * step, (i + 1) * step + 0.02, R, r)}" fill="${biteColor(p.B)}" opacity="${0.35 + 0.65 * (p.B / 100)}"/>`).join('');
  const sun = d.sun.polarNight ? '' : `<path d="${arc(d.sunriseH, d.sunsetH, R + 6, R + 3)}" fill="var(--amber)" opacity=".8"/>`;
  const bw = best ? `<path d="${arc(best.start.getHours() + best.start.getMinutes() / 60, best.end.getHours() + best.end.getMinutes() / 60 || 24, r - 2, r - 6)}" fill="#fff" opacity=".9"/>` : '';
  const h = t.getHours() + t.getMinutes() / 60;
  const [nx, ny] = pol(ang(h), R + 1), [mx, my] = pol(ang(h), r - 8);
  const labels = [0, 6, 12, 18].map((k) => { const [x, y] = pol(ang(k), R + 14); return `<text x="${x}" y="${y + 3}" text-anchor="middle">${k}</text>`; }).join('');
  el.innerHTML = `<svg viewBox="0 0 170 170" role="img" aria-label="Bittindeks gjennom døgnet">
    <circle cx="${C}" cy="${C}" r="${R + 1}" fill="none" stroke="rgba(255,255,255,.08)"/>
    ${segs}${sun}${bw}
    <line x1="${mx}" y1="${my}" x2="${nx}" y2="${ny}" stroke="#fff" stroke-width="2"/>
    ${labels}
    <text x="${C}" y="${C - 4}" text-anchor="middle" style="font-size:22px;fill:#fff">${Math.round(Bnow)}</text>
    <text x="${C}" y="${C + 12}" text-anchor="middle">${fmtTime(t)}</text>
    ${best ? `<text x="${C}" y="${C + 24}" text-anchor="middle" style="fill:var(--amber)">${fmtTime(best.start)}–${fmtTime(best.end)}</text>` : ''}
  </svg>`;
  el.querySelectorAll('.seg').forEach((s) => { s.onclick = () => onPick(Number(s.dataset.h)); });
}
