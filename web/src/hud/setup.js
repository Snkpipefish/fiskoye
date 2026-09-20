import { recommend } from '../model/tackle.js';

export class SetupPanel {
  constructor(el) { this.el = el; this.el.addEventListener('click', (e) => { if (e.target.classList.contains('close')) this.hide(); }); }
  hide() { this.el.classList.add('hidden'); }
  get visible() { return !this.el.classList.contains('hidden'); }
  toggle() { this.el.classList.toggle('hidden'); }

  render(sp, d, spot, best) {
    const r = recommend(sp, d, spot, best);
    const m = r.anbefalt;
    const line = (ic, lb, v) => (v ? `<div class="ic">${ic}</div><div><div class="lb">${lb}</div>${v}</div>` : '');
    const alt = (a) => `<div class="alt"><span class="tag">ALTERNATIV</span> <b>${a.navn}</b>${a.farge ? ` · ${a.farge}` : ''}${a.storrelse ? ` · ${a.storrelse}` : ''}${a.agn ? ` · ${a.agn}` : ''}</div>`;
    this.el.innerHTML = `<span class="close">✕</span>
      <h2>🎣 UTSTYR · ${sp.navn.toUpperCase()}</h2>
      <div class="sub">${spot ? `${spot.navn} (${spot.side_navn})` : 'hele området'} · ${r.water.replace('_', ' ')} · ${r.light}</div>
      <div class="rec"><span class="tag">ANBEFALT · ${m.type?.toUpperCase() || ''}</span>
        <div class="card">
          ${line(m.type === 'agn' ? '🪱' : m.type === 'flue' ? '🪶' : '🐟', m.type === 'agn' ? 'AGN' : m.type === 'flue' ? 'FLUE' : 'SLUK', `<b>${m.navn}</b>${m.agn ? `<br>${m.agn}` : ''}`)}
          ${line('🎨', 'FARGE', m.farge)}
          ${line('📏', 'STØRRELSE / VEKT', [m.storrelse, m.vekt].filter(Boolean).join(' · '))}
          ${line('🔄', 'INNSVEIV', m.innsveiv)}
          ${line('🌊', 'FISKEDYBDE', r.dybde)}
          ${line('💡', 'TIPS', m.tips)}
        </div></div>
      ${r.alternativer.map(alt).join('')}
      <div class="card">
        ${line('🎣', 'STANG', `${sp.utstyr.stang.lengde_cm[0]}–${sp.utstyr.stang.lengde_cm[1]} cm, ${sp.utstyr.stang.kastevekt_g[0]}–${sp.utstyr.stang.kastevekt_g[1]} g, ${sp.utstyr.stang.aksjon}`)}
        ${line('🧵', 'HOVEDSNØRE', sp.utstyr.snore.hoved)}
        ${line('🔗', 'FORTOM', sp.utstyr.snore.fortom)}
        ${line('🪝', 'KROK', sp.utstyr.snore.krok)}
      </div>
      <div class="lb" style="margin-top:6px">BEGRUNNELSE</div><ul>${r.begrunnelse.map((b) => `<li>${b}</li>`).join('')}</ul>`;
    this.el.classList.remove('hidden');
  }
}
