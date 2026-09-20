import SunCalc from 'suncalc';

const valid = (d) => (d instanceof Date && !Number.isNaN(d.getTime())) ? d : null;
export const hourOf = (d) => d.getHours() + d.getMinutes() / 60;
export const startOfDay = (d) => { const x = new Date(d); x.setHours(0, 0, 0, 0); return x; };
export const dayOfYear = (d) => Math.floor((startOfDay(d) - new Date(d.getFullYear(), 0, 1)) / 864e5) + 1;

export function sunTimes(date, lat, lon) {
  const s = SunCalc.getTimes(date, lat, lon);
  const sunrise = valid(s.sunrise), sunset = valid(s.sunset);
  const noonAlt = SunCalc.getPosition(valid(s.solarNoon) || date, lat, lon).altitude;
  return { sunrise, sunset, polarDay: !sunrise && noonAlt > 0, polarNight: !sunrise && noonAlt <= 0,
    sunriseH: sunrise ? hourOf(sunrise) : (noonAlt > 0 ? 0 : 12), sunsetH: sunset ? hourOf(sunset) : (noonAlt > 0 ? 24 : 12) };
}
export const sunAlt = (t, lat, lon) => SunCalc.getPosition(t, lat, lon).altitude * 180 / Math.PI;

const PHASES = ['nymåne', 'voksende', 'første kvarter', 'voksende', 'fullmåne', 'minkende', 'siste kvarter', 'minkende'];
export function moonInfo(date, lat, lon) {
  const ill = SunCalc.getMoonIllumination(date);
  const mt = SunCalc.getMoonTimes(startOfDay(date), lat, lon);
  const d0 = startOfDay(date);
  const alts = [];
  for (let m = -6; m <= 24 * 6 + 6; m++) { const t = new Date(d0.getTime() + m * 600e3); alts.push({ t, a: SunCalc.getMoonPosition(t, lat, lon).altitude }); }
  const majors = [];
  for (let i = 1; i < alts.length - 1; i++) {
    const p = alts[i - 1].a, c = alts[i].a, n = alts[i + 1].a;
    if ((c > p && c >= n) || (c < p && c <= n)) majors.push(alts[i].t);
  }
  const minors = [valid(mt.rise), valid(mt.set)].filter(Boolean);
  const ph = ill.phase;
  const nearNewFull = ph < 0.07 || ph > 0.93 || Math.abs(ph - 0.5) < 0.07;
  return { phase: ph, fraction: ill.fraction, majors, minors, nearNewFull, name: PHASES[Math.round(ph * 8) % 8] };
}

const G = (dtH, s) => Math.exp(-(dtH * dtH) / (2 * s * s));
/** Solunar-styrke 0..1 ved tidspunkt t. Major = månetransitt/anti-transitt (σ 1 t), minor = måne opp/ned (σ 0,5 t). */
export function solunar(t, moon) {
  let s = 0;
  for (const m of moon.majors) s = Math.max(s, G((t - m) / 36e5, 1.0));
  for (const m of moon.minors) s = Math.max(s, 0.5 * G((t - m) / 36e5, 0.5));
  return s * (moon.nearNewFull ? 1.0 : 0.8);
}
