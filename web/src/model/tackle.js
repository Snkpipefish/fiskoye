/** Utstyrsmotor: velger metode, sluk/agn, farge, størrelse, snøre ut fra art, forhold og plass. */
const mid = (r) => (r[0] + r[1]) / 2;
const central = (x, r) => { if (x == null) return 0.5; const h = (r[1] - r[0]) / 2; if (h <= 0) return x === r[0] ? 1 : 0; const c = 1 - Math.abs(x - mid(r)) / h; return c < 0 ? 0 : 0.5 + 0.5 * c; };
const inMonth = (m, r) => (r[0] <= r[1] ? m >= r[0] && m <= r[1] : m >= r[0] || m <= r[1]);

export function lightClass(d) { return d.sunAlt < 5 ? 'skumring' : d.cloud > 70 ? 'overskyet' : 'sol'; }
export function waterClass(d) { const l = lightClass(d); return d.turb > 0.4 ? 'grumsete' : l === 'sol' ? 'klart_sol' : 'klart_skygge'; }

export function scoreMethod(m, d, spot) {
  const b = m.betingelser || {};
  let s = 1;
  if (b.temp_c) s *= central(d.tw, b.temp_c);
  if (b.dybde_m) s *= central(spot?.dybde_est ?? 2, b.dybde_m);
  if (b.vind_ms) s *= central(d.wind, b.vind_ms);
  if (b.strom) s *= b.strom.includes(spot?.klasse_strom || 'svak') ? 1 : 0;
  if (b.maaned) s *= inMonth(new Date().getMonth() + 1, b.maaned) ? 1 : 0;
  return s;
}

export function recommend(sp, d, spot, best) {
  const water = waterClass(d), light = lightClass(d);
  const kaldt = d.tw < 10;
  const strom = spot?.klasse_strom || 'svak';
  const dyb = spot?.dybde_est ?? 2;
  let scored = sp.utstyr.metoder.map((m) => ({ m, s: scoreMethod(m, d, spot) })).sort((a, b) => b.s - a.s);
  if (!scored.some((x) => x.s > 0)) scored = sp.utstyr.metoder.map((m) => ({ m, s: 0.01 }));
  const usable = scored.filter((x) => x.s > 0);
  const top = usable[0].m, alts = usable.slice(1, 3).map((x) => x.m);
  const detail = (m) => {
    const o = { navn: m.navn, type: m.type, farge: m.farge?.[water], innsveiv: m.innsveiv?.[kaldt ? 'kaldt' : 'varmt'], agn: m.agn, tips: m.tips };
    if (m.storrelse_cm) { const [lo, hi] = m.storrelse_cm; const md = Math.round(mid(m.storrelse_cm)); o.storrelse = (d.turb > 0.4 || d.tw > 15) ? `${md}–${hi} cm` : `${lo}–${md} cm`; }
    if (m.vekt_g) { const [lo, hi] = m.vekt_g; o.vekt = strom === 'stryk' ? `${Math.round(mid(m.vekt_g))}–${hi} g` : strom === 'stille' ? `${lo}–${Math.round(mid(m.vekt_g))} g` : `${Math.round(mid(m.vekt_g))} g`; }
    if (o.farge === '–') o.farge = null;
    return o;
  };
  const begrunnelse = [];
  begrunnelse.push(`Vann ≈ ${d.tw.toFixed(1)} °C → ${kaldt ? 'sakte presentasjon, lange pauser' : 'aktivt fiske, raskere innsveiv'}.`);
  begrunnelse.push(d.turb > 0.4 ? `Grumsete (regn ${d.rain72.toFixed(0)} mm/72 t${d.flow?.dlnQ24 > 0.1 ? ', stigende vannføring' : ''}) → vibrasjon og sterke farger.` : `Sikt ${d.turb < 0.15 ? 'god' : 'middels'} → ${light === 'sol' ? 'naturlige farger i sol' : 'lysere/kontrast i svakt lys'}.`);
  begrunnelse.push(`Lys: ${light}${d.sunAlt > 10 ? ` (sky ${Math.round(d.cloud)} %)` : ''}.`);
  if (strom === 'stryk' || strom === 'moderat') begrunnelse.push(`Strøm ${strom} → tyngre sluk, kast skrått oppstrøms.`);
  if (spot) begrunnelse.push(`Plassen er ${dyb.toFixed(1)} m dyp (estimat) → fisk ${Math.max(0.5, dyb * 0.4).toFixed(1)}–${dyb.toFixed(1)} m.`);
  if (best) begrunnelse.push(`Beste vindu i dag: ${hhmm(best.start)}–${hhmm(best.end)}.`);
  return { anbefalt: detail(top), alternativer: alts.map(detail), snore: sp.utstyr.snore, stang: sp.utstyr.stang, water, light, kaldt, begrunnelse,
    dybde: spot ? `${Math.max(0.5, dyb * 0.4).toFixed(1)}–${dyb.toFixed(1)} m` : null };
}
export const hhmm = (t) => `${String(t.getHours()).padStart(2, '0')}:${String(t.getMinutes()).padStart(2, '0')}`;
