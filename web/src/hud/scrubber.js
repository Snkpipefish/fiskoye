import { setTime, state } from '../state.js';
import { startOfDay } from '../live/astro.js';

const DAYS = ['søn', 'man', 'tir', 'ons', 'tor', 'fre', 'lør'];
export const fmtDate = (t) => `${DAYS[t.getDay()]} ${t.getDate()}.${t.getMonth() + 1}.`;
export const fmtTime = (t) => `${String(t.getHours()).padStart(2, '0')}:${String(t.getMinutes()).padStart(2, '0')}`;
const isoDate = (t) => `${t.getFullYear()}-${String(t.getMonth() + 1).padStart(2, '0')}-${String(t.getDate()).padStart(2, '0')}`;

export class Scrubber {
  constructor(panel) {
    this.panel = panel;
    this.date = panel.querySelector('#scrub-date'); this.hour = panel.querySelector('#scrub-hour'); this.label = panel.querySelector('#scrub-label');
    panel.querySelector('#scrub-now').onclick = () => setTime(new Date(), true);
    this.date.onchange = () => this.apply();
    this.hour.oninput = () => this.apply();
  }
  apply() {
    const [y, m, d] = this.date.value.split('-').map(Number);
    if (!y) return;
    const t = new Date(y, m - 1, d, 0, 0);
    t.setMinutes(Number(this.hour.value) * 30);
    setTime(t, false);
  }
  setRange(min, max) { this.date.min = isoDate(min); this.date.max = isoDate(max); }
  render() {
    const t = state.t;
    this.date.value = isoDate(t);
    this.hour.value = Math.round((t - startOfDay(t)) / 18e5);
    this.label.textContent = `${state.live ? 'NÅ · ' : ''}${fmtDate(t)} ${fmtTime(t)}`;
    this.panel.classList.toggle('live', state.live);
  }
}
