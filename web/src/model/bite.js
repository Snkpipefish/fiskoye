/** Dynamisk bittindeks B = H · A(t) · L(t, spot). Formlene speiles i pipeline/tests/bite_ref.py (paritetstest). */
import { clip, gaussAsym, wgeomean } from './curves.js';
import { idx, sum, inRange } from '../live/weather.js';
import { dayOfYear, hourOf, moonInfo, solunar, startOfDay, sunAlt, sunTimes } from '../live/astro.js';
import { flowAt } from '../live/nve.js';

export const W = { sesong: 0.2, diel: 0.25, temp: 0.2, trykk: 0.1, vind: 0.05, lys: 0.05, flow: 0.1, klar: 0.05 };
export const LABELS = { sesong: 'sesong', diel: 'døgn', temp: 'vanntemp', trykk: 'trykk', vind: 'vind', lys: 'lys', flow: 'vannføring', klar: 'sikt', solunar: 'solunar' };
export const FORMULA = {
  sesong: 'f = interp(måned, doy) · gyting', diel: 'f = max(base, daggry·G(t−soloppgang−½t), skumring·G(t−solnedgang+½t)), σ=1,5 t',
  temp: 'f = exp(−(Tw−opt)²/2σ²), σ_lo/σ_hi', trykk: 'f = tabell(ΔP 3 t: fallende/stabil/stigende/raskt)',
  vind: 'f = 1 (v≤opt) → 0,4 (v=maks) → 0,3', lys: 'f = sol·(1−sky) + overskyet·sky, bare når solhøyde > 10°',
  flow: 'f = exp(−(a−a_opt)²/2σ²), a = ln(Q/Q_median)', klar: 'f = 1 − følsomhet·turb, turb = 0,03·regn72 + 3·max(0, ΔlnQ24)',
  solunar: 'f = 1 − k + k·S, S = major(σ 1 t) / ½ minor(σ ½ t) · fase', A: 'A = exp(Σ w·ln f / Σ w)  (vektet geometrisk middel)',
  L: 'L = clip(1 + 0,15·skygge·sol + 0,10·pålandsvind − 0,25·flom·strøm, 0,6, 1,15)', B: 'B = H · A · L',
};

const DOY0 = [0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334];
const doyOf = (m, d) => DOY0[m - 1] + d;
const cdiff = (a, b) => { const d = ((a - b) % 24 + 24) % 24; return d > 12 ? d - 24 : d; };

export function fSesong(maaned, doy, gyting) {
  const t = (((doy - 15.2) / 30.44) % 12 + 12) % 12;
  const i0 = Math.floor(t) % 12, i1 = (i0 + 1) % 12, fr = t - Math.floor(t);
  let v = maaned[i0] * (1 - fr) + maaned[i1] * fr;
  if (gyting) {
    const a = doyOf(...gyting.fra), b = doyOf(...gyting.til);
    const inside = a <= b ? (doy >= a && doy <= b) : (doy >= a || doy <= b);
    if (inside) v *= gyting.effekt;
  }
  return v;
}
export function fDiel(h, sr, ss, alt, diel) {
  const base = alt > -6 ? diel.dag : diel.natt;
  const s = diel.sigma_h; const g = (dx) => Math.exp(-dx * dx / (2 * s * s));
  return Math.max(base, diel.daggry * g(cdiff(h, sr + 0.5)), diel.skumring * g(cdiff(h, ss - 0.5)));
}
export const fTemp = (tw, t) => gaussAsym(tw, t.opt, t.sigma_lo, t.sigma_hi, t.min, t.max);
export function trykkKlasse(dp3) { if (Math.abs(dp3) >= 4) return 'raskt'; if (dp3 > -4 && dp3 <= -1) return 'fallende'; if (dp3 >= 1 && dp3 < 4) return 'stigende'; return 'stabil'; }
export const fTrykk = (dp3, tab) => tab[trykkKlasse(dp3)];
export function fVind(v, opt, mx) { if (v <= opt) return 1; if (v <= mx) return 1 - 0.6 * (v - opt) / (mx - opt); return 0.3; }
export function fLys(alt, cloud, lys) { if (alt <= 10) return 1; const c = cloud / 100; return lys.sol * (1 - c) + lys.overskyet * c; }
export const fFlow = (a, aOpt, sigma) => (a == null ? 1 : Math.exp(-((a - aOpt) ** 2) / (2 * sigma * sigma)));
export const fKlar = (turb, fols) => 1 - fols * turb;

/** Avledede forhold ved tidspunkt t (deles av alle arter). ctx = {weather, tw[], lat, lon, station, qMedianFallback}. */
export function derive(t, ctx) {
  const w = ctx.weather; const i = idx(w, t);
  const ok = inRange(w, t);
  const st = sunTimes(t, ctx.lat, ctx.lon);
  const dayKey = startOfDay(t).getTime();
  ctx._moon ||= {};
  const moon = ctx._moon[dayKey] ||= moonInfo(t, ctx.lat, ctx.lon);
  const flow = flowAt(ctx.station, t, ctx.qMedianFallback);
  const rain72 = sum(w, 'precip', t, 72);
  const turb = clip(0.03 * rain72 + 3 * Math.max(0, flow?.dlnQ24 ?? 0));
  const dp3 = (w.pressure[i] ?? 0) - (w.pressure[Math.max(0, i - 3)] ?? 0);
  return {
    ok, doy: dayOfYear(t), hour: hourOf(t), sunriseH: st.sunriseH, sunsetH: st.sunsetH, sun: st, sunAlt: sunAlt(t, ctx.lat, ctx.lon),
    tw: ctx.tw[i] ?? 10, ta: w.temp[i], dp3, pressure: w.pressure[i], wind: w.wind[i] ?? 0, winddir: w.winddir[i] ?? 0, cloud: w.cloud[i] ?? 50,
    precip: w.precip[i] ?? 0, rain72, rain24: sum(w, 'precip', t, 24), a: flow?.a ?? null, flow, turb, moon, S: solunar(t, moon),
  };
}

export function activity(sp, d) {
  const k = sp.vaer.solunar ?? 0;
  const comps = {
    sesong: fSesong(sp.sesong.maaned, d.doy, sp.sesong.gyting),
    diel: fDiel(d.hour, d.sunriseH, d.sunsetH, d.sunAlt, sp.diel),
    temp: fTemp(d.tw, sp.habitat.temp_c),
    trykk: fTrykk(d.dp3, sp.vaer.trykk),
    vind: fVind(d.wind, sp.vaer.vind.opt_ms, sp.vaer.vind.max_ms),
    lys: fLys(d.sunAlt, d.cloud, sp.vaer.lys),
    flow: fFlow(d.a, sp.vaer.vannforing.a_opt, sp.vaer.vannforing.sigma),
    klar: fKlar(d.turb, sp.vaer.klarhet.folsomhet),
    solunar: 1 - k + k * d.S,
  };
  const keys = Object.keys(W); const vals = keys.map((x) => comps[x]); const wts = keys.map((x) => W[x]);
  if (k > 0) { vals.push(comps.solunar); wts.push(k); }
  return { A: wgeomean(vals, wts), comps };
}

const COMPASS = { N: 0, 'NØ': 45, 'Ø': 90, 'SØ': 135, S: 180, SV: 225, V: 270, NV: 315 };
/** Lokal modifikator for en plass (spot.properties). */
export function local(sp, d, p) {
  if (!p) return 1;
  const shade = (p.skygge ?? 0) * (d.sunAlt > 25 ? 1 : 0) * (1 - d.cloud / 100);
  let wind = 0;
  const out = COMPASS[(p.side_navn || '').split('-')[0]];
  if (out != null && (sp.gruppe === 'rovfisk') && d.wind >= 3) {
    const to = (d.winddir + 180) * Math.PI / 180, o = out * Math.PI / 180;
    wind = Math.cos(to - o) > 0.5 ? 1 : 0;
  }
  const flowTerm = Math.max(0, d.a ?? 0) * (['moderat', 'stryk'].includes(p.klasse_strom) ? 1 : 0);
  return clip(1 + 0.15 * shade + 0.10 * wind - 0.25 * flowTerm, 0.6, 1.15);
}

export function bite(sp, sid, t, ctx, p = null, dPre = null) {
  const d = dPre || derive(t, ctx);
  const { A, comps } = activity(sp, d);
  const L = local(sp, d, p);
  const H = p ? (p.H?.[sid] ?? 0) : 100;
  return { B: H * A * L, A, L, H, comps, d };
}

export function curve(sp, sid, date, ctx, p = null, stepMin = 30) {
  const d0 = startOfDay(date); const out = [];
  for (let m = 0; m < 24 * 60; m += stepMin) {
    const t = new Date(d0.getTime() + m * 60e3);
    const r = bite(sp, sid, t, ctx, p);
    out.push({ t, B: r.B, A: r.A, sunAlt: r.d.sunAlt, ok: r.d.ok });
  }
  return out;
}

export function bestWindow(cv, hours = 2) {
  const n = Math.max(1, Math.round(hours * 60 / ((cv[1].t - cv[0].t) / 60e3)));
  let best = { i: 0, mean: -1 };
  for (let i = 0; i + n <= cv.length; i++) {
    let s = 0; for (let j = i; j < i + n; j++) s += cv[j].B;
    if (s / n > best.mean) best = { i, mean: s / n };
  }
  return { start: cv[best.i].t, end: new Date(cv[best.i].t.getTime() + n * (cv[1].t - cv[0].t)), mean: best.mean };
}

export function week(sp, sid, ctx, p = null, from = new Date()) {
  const out = [];
  for (let k = 0; k < 7; k++) {
    const date = new Date(startOfDay(from).getTime() + k * 864e5);
    const cv = curve(sp, sid, date, ctx, p, 60);
    if (!cv.some((x) => x.ok)) break;
    const max = Math.max(...cv.map((x) => x.B));
    out.push({ date, max, best: bestWindow(cv, 2), cv });
  }
  return out;
}

export function topSpots(sp, sid, t, ctx, spots, n = 5) {
  const d = derive(t, ctx);
  return spots.features.map((f) => ({ f, r: bite(sp, sid, t, ctx, f.properties, d) })).sort((x, y) => y.r.B - x.r.B).slice(0, n);
}
