export const DATA = `${import.meta.env.BASE_URL}data/`;

export async function getJSON(url, { optional = false } = {}) {
  const r = await fetch(url, { cache: 'no-cache' });
  if (!r.ok) { if (optional) return null; throw new Error(`${url}: HTTP ${r.status}`); }
  return r.json();
}

export const loadIndex = () => getJSON(`${DATA}index.json`);
export const loadSpecies = () => getJSON(`${DATA}species.json`);
export const loadNve = () => getJSON(`${DATA}live/nve.json`, { optional: true }).catch(() => null);

export async function loadArea(slug) {
  const base = `${DATA}areas/${slug}/`;
  const [area, segments, spots, s2, climate] = await Promise.all([
    getJSON(`${base}area.json`), getJSON(`${base}segments.geojson`), getJSON(`${base}spots.geojson`),
    getJSON(`${base}s2_rgb.json`, { optional: true }), getJSON(`${base}climate.json`, { optional: true }),
  ]);
  return { area, segments, spots, s2, climate, base };
}
