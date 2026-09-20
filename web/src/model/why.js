/** «Hvorfor her»-prosa fra statiske komponenter (pipeline) + dynamiske (bittindeks). */
import { trykkKlasse } from './bite.js';

const STATIC = {
  bukt: 'Bakevje/bukt der strømmen dør ut – rovfisken står i le og venter.',
  dropoff: 'Brå dybdeøkning fra bredden (S2-fargeforskjell) – storfisk står på kanten.',
  veg_hoy: 'Tett sivbelte/vannvegetasjon i kanten – skjul for gjedde og småfisk.',
  veg: 'Litt vegetasjon langs bredden.',
  bru: 'Brukar gir skygge, strømskygge og hard bunn.',
  innsnevring: 'Innsnevring – strømmen samler næringen.',
  sving: 'Sving – dypt i yttersvingen, rolig i innersvingen.',
  sandbanke: 'Sandbanke – grunt og lyst, harr og abbor på kanten.',
  skygge: 'Skyggefull bredd (skog eller vestvendt) – bedre i sol.',
  oy: 'Øy/deling av løpet – strømkant på begge sider.',
};
const PREF = { 'os:': (n) => `${n} munner ut her – næring og agnfisk.`, 'dam:': (n) => `Like ved ${n} – oksygenrikt vann, ørret og harr nedstrøms.`, 'strom:': (n) => `Strøm: ${n}.` };

export function staticWhy(komponenter = []) {
  const out = [];
  for (const k of komponenter) {
    if (STATIC[k]) out.push(STATIC[k]);
    else for (const [p, fn] of Object.entries(PREF)) if (k.startsWith(p)) out.push(fn(k.slice(p.length)));
  }
  return out;
}

export function dynamicWhy(sp, r, rules) {
  const c = r.comps, d = r.d, out = [];
  if (c.diel > 0.85) out.push(d.sunAlt < 0 ? 'Skumring/daggry: beste døgnvindu.' : 'Godt døgnvindu.');
  else if (c.diel < 0.35) out.push('Dårlig tid på døgnet for arten.');
  const tk = trykkKlasse(d.dp3);
  if (tk === 'fallende' && sp.vaer.trykk.fallende >= 0.95) out.push('Fallende trykk – rovfisken jakter.');
  if (tk === 'raskt') out.push('Rask trykkendring – ofte dårlig bitt.');
  if (c.temp < 0.4) out.push(`Vanntemp ${d.tw.toFixed(0)} °C er langt fra optimum ${sp.habitat.temp_c.opt} °C.`);
  else if (c.temp > 0.9) out.push(`Vanntemp ${d.tw.toFixed(0)} °C nær optimum.`);
  if (d.turb > 0.5) out.push('Grumsete etter regn: velg vibrasjon og sterke farger.');
  if (c.flow < 0.5 && d.a != null) out.push(d.a > 0 ? 'Høy vannføring – fisken trekker ut av strømmen.' : 'Lav vannføring – fisken står dypere.');
  if (c.sesong < 0.4) out.push('Utenfor hovedsesongen.');
  if (r.L > 1.05) out.push('Pålandsvind/skygge gir denne bredden et lite pluss.');
  if (rules?.fredet) out.push(`FREDET ${rules.fredet} – ikke fisk etter arten nå.`);
  return out;
}

export function fredning(regler, t) {
  const f = regler?.fredning;
  if (!f) return null;
  const [[m1, d1], [m2, d2]] = f;
  const m = t.getMonth() + 1, d = t.getDate();
  const a = m1 * 100 + d1, b = m2 * 100 + d2, x = m * 100 + d;
  const inside = a <= b ? (x >= a && x <= b) : (x >= a || x <= b);
  return { inside, text: `${d1}.${m1}–${d2}.${m2}` };
}
