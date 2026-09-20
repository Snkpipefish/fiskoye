import { FORMULA, LABELS } from '../model/bite.js';
import { dynamicWhy, fredning, staticWhy } from '../model/why.js';

const fmt = (v, d = 2) => (v == null || Number.isNaN(v)) ? '—' : Number(v).toFixed(d);
const SF = { dybde: 'trapes(dybde_est; d0..d3)', strom: 'tabell(strømklasse)', vegetasjon: 'lin(veg; v0→v1)', struktur: '1 − Π(1 − w·x) over os, sving, innsnevring, bukt, dropoff, bru, dam, sand', skygge: 'lin(skygge; s0→s1)' };

export class SpotPanel {
  constructor(el) { this.el = el; this.el.addEventListener('click', (e) => { if (e.target.classList.contains('close')) this.hide(); }); this.onSpecies = () => {}; }
  hide() { this.el.classList.add('hidden'); this.current = null; }
  get visible() { return !this.el.classList.contains('hidden'); }

  show(f, sid, sp, r, base, t, areaSpecies, speciesAll) {
    this.current = { f, kind: 'spot' };
    const p = f.properties; const [lon, lat] = f.geometry.coordinates;
    const rules = areaSpecies?.[sid]?.regler; const fr = fredning(rules, t);
    const why = [...staticWhy(p.komponenter), ...dynamicWhy(sp, r, { fredet: fr?.inside ? fr.text : null })];
    const kl = p.klasse?.[sid], rank = p.rank?.[sid];
    const arts = Object.entries(p.H).sort((a, b) => b[1] - a[1]).map(([id, H]) => `<span class="${id === sid ? 'on' : ''}" data-id="${id}">${speciesAll[id]?.navn || id} ${Math.round(H)}</span>`).join('');
    const fx = p.f?.[sid] || {};
    const rows = [
      ['B bittindeks nå', fmt(r.B, 0), FORMULA.B], ['H habitat (statisk)', fmt(r.H, 0), 'H = 100·geomean(f_k^w_k)/P99'],
      ['A aktivitet (område)', fmt(r.A), FORMULA.A], ['L lokal modifikator', fmt(r.L), FORMULA.L],
      ...Object.entries(fx).map(([k, v]) => [`f_${k}`, fmt(v), SF[k]]),
      ...Object.keys(LABELS).filter((k) => r.comps[k] != null).map((k) => [`f_${LABELS[k]}`, fmt(r.comps[k]), FORMULA[k]]),
      ['dybde (estimat)', `${fmt(p.dybde_est, 1)} m`, 'h_Manning · e^(0,35·z_S2)'], ['bredde / dybde / fart', `${fmt(p.w, 0)} m / ${fmt(p.h, 1)} m / ${fmt(p.v, 2)} m/s`, 'Manning: Q = (1/n)·w·h·R^(2/3)·S^(1/2)'],
      ['strøm', p.klasse_strom, '<0,15 stille · <0,4 svak · <0,8 moderat · stryk'], ['vegetasjon', fmt(p.veg), 'andel NDVI>0,25 innen 30 m fra bredden'],
      ['skygge', fmt(p.skygge), '0,6·trekroner + 0,4·(1−hillshade SV)'], ['bredd', `${p.side_navn || ''} · ${p.banktype || ''}`, ''],
      ...Object.entries(p.struct || {}).filter(([, v]) => v > 0.05).map(([k, v]) => [`struktur: ${k}`, fmt(v), '']),
    ];
    this.el.innerHTML = `
      <span class="close">✕</span>
      <h2>${kl ? `<span class="badge ${kl}">${rank}${kl}</span>` : ''}${p.id}. ${p.navn}</h2>
      <div class="sub">${lat.toFixed(5)} N, ${lon.toFixed(5)} Ø · ${p.elv} km ${fmt(p.km, 1)} · ${p.side_navn}</div>
      <div class="bar"><i style="width:${Math.max(2, r.B)}%"></i></div>
      <div class="arts">${arts}</div>
      <div class="why">${why.join(' ')}</div>
      ${p.adkomst?.adkomst ? `<div class="why access">🚗 ${p.adkomst.adkomst}</div>` : ''}
      <table>${rows.map((x) => `<tr><td>${x[0]}${x[2] ? `<div class="formula">${x[2]}</div>` : ''}</td><td>${x[1]}</td></tr>`).join('')}</table>
      ${p.satsjekk ? `<img src="${base}${p.satsjekk}" alt="Satellittutsnitt" loading="lazy" onerror="this.remove()" />` : ''}
      <div class="dl" style="margin-top:8px"><a href="https://www.norgeskart.no/#!?project=norgeskart&layers=1002&zoom=15&lat=${lat}&lon=${lon}&markerLat=${lat}&markerLon=${lon}" target="_blank" rel="noopener">Norgeskart ↗</a>
      <a href="https://www.google.com/maps?q=${lat},${lon}" target="_blank" rel="noopener">Google Maps ↗</a></div>`;
    this.el.querySelectorAll('.arts span').forEach((s) => { s.onclick = () => this.onSpecies(s.dataset.id); });
    this.el.classList.remove('hidden');
  }

  showSegment(f, sid, A, speciesAll) {
    this.current = { f, kind: 'segment' };
    const p = f.properties;
    const rows = [['H (valgt art)', fmt(p.H?.[sid], 0)], ['B = H·A', fmt((p.H?.[sid] ?? 0) * A, 0)], ['bredde', `${fmt(p.w, 0)} m (v ${fmt(p.w_v, 0)} / h ${fmt(p.w_h, 0)})`], ['dybde / fart', `${fmt(p.h, 1)} m / ${fmt(p.v, 2)} m/s · ${p.klasse_strom}`],
      ['fall', `${fmt(p.S * 1000, 2)} ‰`], ['vegetasjon v/h', `${fmt(p.veg_v)} / ${fmt(p.veg_h)}`], ['dropoff v/h', `${fmt(p.dropoff_v)} / ${fmt(p.dropoff_h)}`], ['bukt v/h', `${fmt(p.bukt_v)} / ${fmt(p.bukt_h)}`],
      ['innsnevring / sving', `${fmt(p.innsnevring)} / ${fmt(p.sving)}`], ['os / bru / dam', `${fmt(p.os)} / ${fmt(p.bru)} / ${fmt(p.dam)}`], ['skygge v/h', `${fmt(p.skygge_v)} / ${fmt(p.skygge_h)}`]];
    const arts = Object.entries(p.H || {}).sort((a, b) => b[1] - a[1]).map(([id, H]) => `<span class="${id === sid ? 'on' : ''}" data-id="${id}">${speciesAll[id]?.navn || id} ${Math.round(H)}</span>`).join('');
    this.el.innerHTML = `<span class="close">✕</span><h2>SEGMENT · ${p.elv} km ${fmt(p.km, 1)}</h2>
      <div class="sub">${p.side_navn_v} = venstre (v), ${p.side_navn_h} = høyre (h), sett nedstrøms</div>
      <div class="arts">${arts}</div>
      <table>${rows.map((x) => `<tr><td>${x[0]}</td><td>${x[1]}</td></tr>`).join('')}</table>
      <div class="sub" style="margin-top:8px">Klikk på en nummerert plass for full begrunnelse, satellittsjekk og utstyr.</div>`;
    this.el.querySelectorAll('.arts span').forEach((s) => { s.onclick = () => this.onSpecies(s.dataset.id); });
    this.el.classList.remove('hidden');
  }

  showList(title, sub, items) {
    this.current = null;
    this.el.innerHTML = `<span class="close">✕</span><h2>${title}</h2><div class="sub">${sub}</div><table>${items.map((i) => `<tr><td>${i[0]}</td><td>${i[1]}</td></tr>`).join('')}</table>`;
    this.el.classList.remove('hidden');
  }
}
