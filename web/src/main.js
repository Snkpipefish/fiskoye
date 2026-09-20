import 'leaflet/dist/leaflet.css';
import { state, bus, setTime, setSpecies, setSpot, sp } from './state.js';
import { loadIndex, loadSpecies, loadArea, loadNve } from './data.js';
import { fetchWeather, range } from './live/weather.js';
import { stationFor } from './live/nve.js';
import { waterTempSeries } from './model/water.js';
import { derive, activity, bite, curve, bestWindow, week } from './model/bite.js';
import { MapView } from './map.js';
import { BASEMAPS } from './basemaps.js';
import { SpeciesList } from './hud/species.js';
import { renderAreas } from './hud/areas.js';
import { Scrubber, fmtDate, fmtTime } from './hud/scrubber.js';
import { renderWeather } from './hud/weather.js';
import { renderClock } from './hud/clock.js';
import { renderForecast } from './hud/forecast.js';
import { SpotPanel } from './hud/spot.js';
import { SetupPanel } from './hud/setup.js';
import { startOfDay } from './live/astro.js';

const $ = (id) => document.getElementById(id);
const status = (t) => { $('status').textContent = t; };

async function main() {
  status('STARTER KART…');
  const map = new MapView('map');
  const speciesList = new SpeciesList($('species-list'), (id) => setSpecies(id));
  const scrubber = new Scrubber($('scrub-panel'));
  const spotPanel = new SpotPanel($('target'));
  const setupPanel = new SetupPanel($('setup'));
  spotPanel.onSpecies = (id) => setSpecies(id);
  window.__f = { state, map, bite, curve, derive };

  // kartstabel
  const chipBox = $('basemap-chips');
  for (const b of BASEMAPS) { const el = document.createElement('div'); el.className = 'chip'; el.textContent = b.label; el.dataset.id = b.id; el.onclick = () => map.setBasemap(b.id); chipBox.appendChild(el); }
  map.onBasemap = (id) => { for (const el of chipBox.children) el.classList.toggle('on', el.dataset.id === id); };
  map.setBasemap('esri');
  const toggles = [['segments', 'ELVESEGMENTER (H·A)'], ['spots', 'FISKEPLASSER'], ['structures', 'BRUER · DAMMER · UTSETT'], ['s2', 'SENTINEL-2 SCENE']];
  for (const [id, label] of toggles) {
    const l = document.createElement('label'); const i = document.createElement('input'); i.type = 'checkbox'; i.checked = map.state[id];
    i.onchange = () => map.toggle(id, i.checked); l.append(i, document.createTextNode(label)); $('layer-toggles').appendChild(l);
  }

  // klokke og koordinater
  setInterval(() => { $('clock').textContent = new Date().toLocaleString('nb-NO', { hour12: false }); }, 1000);
  map.map.on('mousemove', (e) => { $('coords').textContent = `LAT ${e.latlng.lat.toFixed(4)}  LON ${e.latlng.lng.toFixed(4)}`; });
  setInterval(() => { if (state.live) setTime(new Date(), true); }, 60000);

  // data
  status('LASTER DATAINDEKS…');
  const [idx, spj, nve] = await Promise.all([loadIndex(), loadSpecies(), loadNve()]);
  state.index = idx; state.species = spj.species; state.nve = nve;

  function areaSpecies() { return Object.keys(state.area.species).filter((id) => state.species[id]); }

  async function gotoArea(slug) {
    status(`LASTER ${slug.toUpperCase()}…`);
    spotPanel.hide(); setupPanel.hide(); state.spot = null;
    const a = await loadArea(slug);
    Object.assign(state, { areaSlug: slug, area: a.area, segments: a.segments, spots: a.spots, s2: a.s2, climate: a.climate, base: a.base });
    $('area-name').textContent = a.area.name;
    $('gpx-link').href = `${a.base}points.gpx`;
    $('help-legal').textContent = a.area.disclaimer || '';
    renderAreas($('area-list'), idx.areas, slug, gotoArea);
    if (!state.area.species[state.speciesId]) state.speciesId = areaSpecies()[0];
    map.setArea(a);
    map.toggle('s2', false); $('layer-toggles').querySelectorAll('input')[3].checked = false;
    status('HENTER VÆR (OPEN-METEO)…');
    try {
      const weather = await fetchWeather(...a.area.weather_point);
      const station = stationFor(nve, slug);
      const tw = waterTempSeries(weather, station);
      state.ctx = { weather, tw: tw.tw, twInfo: tw, lat: a.area.weather_point[0], lon: a.area.weather_point[1], station, qMedianFallback: a.area.nve?.q_monthly_median };
      scrubber.setRange(...range(weather));
    } catch (e) {
      console.error(e); status('VÆR FEILET: ' + e.message); return;
    }
    location.hash = `${slug}/${state.speciesId}`;
    bus.emit('area');
    refresh();
    status(`${a.area.stats.segmenter} SEGMENTER · ${a.area.stats.spots} PLASSER · ${areaSpecies().length} ARTER`);
  }

  // --- hovedoppdatering ved endring av tid/art/plass
  let dayCurve = null, wk = null, best = null;
  function refresh() {
    if (!state.ctx) return;
    const t = state.t, sid = state.speciesId, S = sp();
    const d = derive(t, state.ctx); state.d = d;
    const A = activity(S, d).A;
    const spotP = state.spot?.properties || null;
    // artsliste (område eller valgt plass)
    const rows = areaSpecies().map((id) => {
      const r = bite(state.species[id], id, t, state.ctx, spotP, d);
      return { id, sp: state.species[id], B: spotP ? r.B : r.A * 100, regler: state.area.species[id].regler, presence: state.area.species[id].presence };
    });
    speciesList.render(rows, sid, t, import.meta.env.BASE_URL);
    // kart
    map.restyle(sid, A, (f) => bite(S, sid, t, state.ctx, f.properties, d).B);
    // klokke + prognose
    dayCurve = curve(S, sid, t, state.ctx, spotP);
    best = dayCurve.some((x) => x.ok) ? bestWindow(dayCurve, 2) : null;
    const now = bite(S, sid, t, state.ctx, spotP, d);
    const Bnow = spotP ? now.B : now.A * 100;
    renderClock($('clock-widget'), dayCurve, d, t, best, (h) => { const x = startOfDay(t); x.setMinutes(Math.round(h * 60)); setTime(x, false); }, Bnow);
    $('dock-title').textContent = `BITTINDEKS · ${S.navn.toUpperCase()}${spotP ? ` · ${spotP.navn.toUpperCase()}` : ' · OMRÅDET'}`;
    const comps = Object.entries(now.comps).map(([k, v]) => `<span>${k} <b>${v.toFixed(2)}</b></span>`).join('');
    $('bite-now').innerHTML = `<b>${Math.round(Bnow)}</b> <span class="dim">${spotP ? 'B = H·A·L' : 'A·100 (områdeaktivitet)'} · ${fmtDate(t)} ${fmtTime(t)}</span><div class="comps">${comps}</div>`;
    wk = week(S, sid, state.ctx, spotP, state.live ? new Date() : t);
    renderForecast($('forecast'), wk, t, (w) => setTime(w.best.start, false));
    renderWeather($('weather'), $('weather-when'), d, state.ctx, state.climate, t);
    scrubber.render();
    if (spotPanel.visible && spotPanel.current) {
      if (spotPanel.current.kind === 'spot') spotPanel.show(spotPanel.current.f, sid, S, bite(S, sid, t, state.ctx, spotPanel.current.f.properties, d), state.base, t, state.area.species, state.species);
      else spotPanel.showSegment(spotPanel.current.f, sid, A, state.species);
    }
    if (setupPanel.visible) setupPanel.render(S, d, spotP, best);
    location.hash = `${state.areaSlug}/${sid}`;
  }
  bus.on('time', refresh); bus.on('species', refresh); bus.on('spot', refresh);

  map.onSpot = (f) => { map.select(f.properties.id); setSpot(f); const r = bite(sp(), state.speciesId, state.t, state.ctx, f.properties); spotPanel.show(f, state.speciesId, sp(), r, state.base, state.t, state.area.species, state.species); };
  map.onSegment = (f) => { map.select(null); state.spot = null; spotPanel.showSegment(f, state.speciesId, activity(sp(), state.d).A, state.species); refresh(); };
  map.map.on('click', () => { if (state.spot) { map.select(null); setSpot(null); } });

  // --- taster
  let introDone = false;
  window.addEventListener('keydown', (e) => {
    if (['INPUT', 'TEXTAREA', 'SELECT'].includes(e.target.tagName)) return;
    const k = e.key;
    if (!introDone) { skipIntro(); return; }
    const shift = (h, dd) => { const x = new Date(state.t); x.setHours(x.getHours() + h); x.setDate(x.getDate() + dd); setTime(x, false); };
    if (k === 'm' || k === 'M') map.nextBasemap();
    else if (k === 'Escape') { spotPanel.hide(); setupPanel.hide(); $('help').classList.add('hidden'); if (state.spot) { map.select(null); setSpot(null); } }
    else if (k === 'h' || k === 'H') $('help').classList.toggle('hidden');
    else if (k === 'l' || k === 'L') $('layers-panel').classList.toggle('hidden');
    else if (k === 'u' || k === 'U') { setupPanel.toggle(); if (setupPanel.visible) setupPanel.render(sp(), state.d, state.spot?.properties || null, best); }
    else if (k === 't' || k === 'T') setTime(new Date(), true);
    else if (k === 'ArrowRight') { e.preventDefault(); shift(1, 0); }
    else if (k === 'ArrowLeft') { e.preventDefault(); shift(-1, 0); }
    else if (k === 'ArrowUp') { e.preventDefault(); shift(0, 1); }
    else if (k === 'ArrowDown') { e.preventDefault(); shift(0, -1); }
    else if (/^[1-9]$/.test(k)) { const id = areaSpecies()[Number(k) - 1]; if (id) setSpecies(id); }
    else if (/^[abcABC]$/.test(k)) {
      const kl = k.toUpperCase(); const sid = state.speciesId;
      const f = state.spots.features.filter((x) => x.properties.klasse?.[sid] === kl).sort((x, y) => x.properties.rank[sid] - y.properties.rank[sid])[0];
      if (f) { const [lon, lat] = f.geometry.coordinates; map.flyTo(lat, lon, 15.5); map.onSpot(f); }
    }
  });
  $('help-link').onclick = (e) => { e.preventDefault(); $('help').classList.toggle('hidden'); };
  $('help-close').onclick = () => $('help').classList.add('hidden');
  $('setup-btn').onclick = () => { setupPanel.toggle(); if (setupPanel.visible) setupPanel.render(sp(), state.d, state.spot?.properties || null, best); };

  // --- GPS
  $('gps-btn').onclick = () => {
    if (!navigator.geolocation) { status('INGEN GPS I NETTLESEREN'); return; }
    status('HENTER POSISJON…');
    navigator.geolocation.getCurrentPosition((pos) => {
      const { latitude: lat, longitude: lon, accuracy } = pos.coords;
      state.userPos = { lat, lon }; map.setUser(lat, lon);
      const sid = state.speciesId;
      const near = state.spots.features.map((f) => { const [x, y] = f.geometry.coordinates; return { f, d: haversine(lat, lon, y, x), b: bearing(lat, lon, y, x) }; }).sort((a, b) => a.d - b.d).slice(0, 6);
      spotPanel.showList('MIN POSISJON', `${lat.toFixed(5)} N, ${lon.toFixed(5)} Ø · ±${Math.round(accuracy)} m`,
        near.map((n) => [`${n.f.properties.id}. ${n.f.properties.navn} (${n.f.properties.side_navn})`, `${(n.d / 1000).toFixed(1)} km ${n.b} · B ${Math.round(bite(sp(), sid, state.t, state.ctx, n.f.properties).B)}`]));
      map.flyTo(lat, lon, 14);
      status('POSISJON LÅST');
    }, (err) => status('GPS FEILET: ' + err.message), { enableHighAccuracy: true, timeout: 15000 });
  };
  function haversine(a, b, c, d) { const R = 6371000, p1 = a * Math.PI / 180, p2 = c * Math.PI / 180, dp = (c - a) * Math.PI / 180, dl = (d - b) * Math.PI / 180; const x = Math.sin(dp / 2) ** 2 + Math.cos(p1) * Math.cos(p2) * Math.sin(dl / 2) ** 2; return 2 * R * Math.asin(Math.sqrt(x)); }
  function bearing(a, b, c, d) { const y = Math.sin((d - b) * Math.PI / 180) * Math.cos(c * Math.PI / 180); const x = Math.cos(a * Math.PI / 180) * Math.sin(c * Math.PI / 180) - Math.sin(a * Math.PI / 180) * Math.cos(c * Math.PI / 180) * Math.cos((d - b) * Math.PI / 180); const deg = (Math.atan2(y, x) * 180 / Math.PI + 360) % 360; return ['N', 'NØ', 'Ø', 'SØ', 'S', 'SV', 'V', 'NV'][Math.round(deg / 45) % 8]; }

  // --- intro
  const introEl = $('intro'); let typing = true;
  function skipIntro() { typing = false; introEl.classList.add('hidden'); introDone = true; }
  $('skip').onclick = skipIntro;
  const [hashArea, hashSp] = location.hash.replace('#', '').split('/');
  if (hashSp && spj.species[hashSp]) state.speciesId = hashSp;
  const first = idx.areas.find((a) => a.slug === hashArea) || idx.areas[0];
  const lines = ['FISKEØYE ONLINE', 'KOBLER TIL: OSM · KARTVERKET · COPERNICUS · OPEN-METEO · NVE', `MÅL: ${first.name.toUpperCase()}`];
  (async () => {
    const el = $('intro-text');
    for (const line of lines) { for (let i = 1; i <= line.length && typing; i++) { el.textContent = line.slice(0, i); await new Promise((r) => setTimeout(r, 18)); } await new Promise((r) => setTimeout(r, 350)); }
    skipIntro();
  })();
  await gotoArea(first.slug);
  skipIntro();
}

main().catch((e) => { console.error(e); status('FEIL: ' + e.message); });
