import { fredning } from '../model/why.js';

export class SpeciesList {
  constructor(el, onPick) { this.el = el; this.onPick = onPick; }
  /** rows: [{id, sp, B, regler, presence}] */
  render(rows, selectedId, t, base) {
    this.el.innerHTML = '';
    rows.forEach((r, i) => {
      const fr = fredning(r.regler, t);
      const row = document.createElement('div');
      row.className = 'row' + (r.id === selectedId ? ' on' : '');
      row.dataset.id = r.id;
      const badges = [];
      if (fr?.inside) badges.push(`<span class="badge fredet">FREDET ${fr.text}</span>`);
      else if (r.regler?.minstemal_cm) badges.push(`<span class="badge min">min ${r.regler.minstemal_cm} cm</span>`);
      if (r.presence === 'mulig') badges.push('<span class="badge mulig">USIKKER</span>');
      row.innerHTML = `<span class="n">${i < 9 ? i + 1 : '·'}</span><span class="sil" style="--sil:url('${base}${r.sp.silhouette}')"></span>
        <span class="nm"><b>${r.sp.navn.toUpperCase()} ${badges.join('')}</b><span class="bar"><i style="width:${Math.max(2, r.B)}%"></i></span></span>
        <span class="val">${Math.round(r.B)}</span>`;
      row.onclick = () => this.onPick(r.id);
      this.el.appendChild(row);
    });
  }
}
