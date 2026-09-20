export function renderAreas(el, areas, current, onPick) {
  el.innerHTML = '';
  for (const a of areas) {
    const row = document.createElement('div');
    row.className = 'row' + (a.slug === current ? ' on' : '');
    row.innerHTML = `<span>${a.name.toUpperCase()}</span><span class="n">${a.n_spots} PLASSER</span>`;
    row.onclick = () => onPick(a.slug);
    el.appendChild(row);
  }
}
