import L from 'leaflet';
import { BASEMAPS } from './basemaps.js';

export function biteColor(B, alpha = 1) {
  const t = Math.max(0, Math.min(1, B / 100));
  return `hsl(${195 - 170 * t} ${70 + 25 * t}% ${45 + 12 * t}% / ${alpha})`;
}

const STRUCT_ICON = { dam: '🏗', weir: '🏗', bru: '🌉', jernbanebru: '🚆', slipway: '🛶', pier: '⚓', fishing: '🎣', marina: '⚓' };

export class MapView {
  constructor(id) {
    this.map = L.map(id, { zoomControl: false, attributionControl: false, zoomSnap: 0.25, zoomDelta: 0.5 });
    this.map.createPane('s2').style.zIndex = 250;
    this.map.createPane('segs').style.zIndex = 400;
    this.base = null; this.baseId = null;
    this.layers = { segments: L.layerGroup().addTo(this.map), spots: L.layerGroup().addTo(this.map), structures: L.layerGroup().addTo(this.map), s2: L.layerGroup() };
    this.state = { segments: true, spots: true, structures: true, s2: false };
    this.onSpot = () => {}; this.onSegment = () => {}; this.onBasemap = () => {};
    this.spotMarkers = new Map();
    this.selected = null;
    this.userMarker = null;
  }
  setBasemap(id) {
    const def = BASEMAPS.find((b) => b.id === id) || BASEMAPS[0];
    if (this.base) this.map.removeLayer(this.base);
    this.base = def.make().addTo(this.map);
    this.baseId = def.id; this.onBasemap(def.id);
  }
  nextBasemap() { const i = BASEMAPS.findIndex((b) => b.id === this.baseId); this.setBasemap(BASEMAPS[(i + 1) % BASEMAPS.length].id); }
  toggle(id, on) {
    this.state[id] = on;
    const l = this.layers[id];
    if (on) l.addTo(this.map); else this.map.removeLayer(l);
  }
  fit(view) { this.map.fitBounds(view, { padding: [40, 40] }); }

  setArea(ctx) {
    const { area, segments, spots, s2, base } = ctx;
    this.segments = segments; this.spots = spots; this.area = area;
    for (const l of Object.values(this.layers)) l.clearLayers();
    this.spotMarkers.clear();
    if (s2) {
      L.imageOverlay(`${base}s2_rgb.png`, s2.bounds, { pane: 's2', opacity: 0.95 }).addTo(this.layers.s2);
    }
    this.segLayer = L.geoJSON(segments, {
      pane: 'segs',
      style: () => ({ color: '#37d3d8', weight: 3, opacity: 0.6 }),
      onEachFeature: (f, l) => { l.on('click', (e) => { L.DomEvent.stopPropagation(e); this.onSegment(f); }); },
    }).addTo(this.layers.segments);
    for (const s of area.structures || []) {
      const ic = STRUCT_ICON[s.kind] || '📍';
      L.marker([s.lat, s.lon], { icon: L.divIcon({ className: 'structmark', html: ic, iconSize: [18, 18], iconAnchor: [9, 9] }), interactive: true })
        .bindTooltip(`${s.name || s.kind}`, { direction: 'top' }).addTo(this.layers.structures);
    }
    for (const f of spots.features) {
      const [lon, lat] = f.geometry.coordinates;
      const m = L.marker([lat, lon], { icon: L.divIcon({ className: '', html: '<div class="dotmark"></div>', iconSize: [8, 8], iconAnchor: [4, 4] }), zIndexOffset: 100 });
      m.on('click', (e) => { L.DomEvent.stopPropagation(e); this.onSpot(f); });
      m.addTo(this.layers.spots);
      this.spotMarkers.set(f.properties.id, { m, f });
    }
    this.fit(area.view);
  }

  /** Farger segmenter etter B = H·A og oppdaterer plassmarkører for valgt art. biteSpot(f) -> B. */
  restyle(sid, A, biteSpot) {
    if (!this.segLayer) return;
    this.segLayer.eachLayer((l) => {
      const H = l.feature.properties.H?.[sid] ?? 0; const B = H * A;
      l.setStyle({ color: biteColor(B), weight: 2 + 5 * (B / 100), opacity: 0.35 + 0.6 * (B / 100) });
    });
    for (const { m, f } of this.spotMarkers.values()) {
      const p = f.properties; const rank = p.rank?.[sid]; const kl = p.klasse?.[sid];
      const sel = this.selected === p.id ? ' sel' : '';
      if (rank) {
        const B = biteSpot(f);
        m.setIcon(L.divIcon({ className: '', html: `<div class="box ${kl}${sel}"><i></i><b>${rank}${kl} · ${Math.round(B)}</b></div>`, iconSize: [34, 34], iconAnchor: [17, 17] }));
        m.setZIndexOffset(1000 - rank);
      } else {
        m.setIcon(L.divIcon({ className: '', html: `<div class="dotmark${sel}"></div>`, iconSize: [8, 8], iconAnchor: [4, 4] }));
        m.setZIndexOffset(100);
      }
    }
  }
  select(id) { this.selected = id; }
  flyTo(lat, lon, z = 16) { this.map.flyTo([lat, lon], Math.max(this.map.getZoom(), z), { duration: 0.8 }); }
  setUser(lat, lon) {
    if (this.userMarker) this.map.removeLayer(this.userMarker);
    this.userMarker = L.marker([lat, lon], { icon: L.divIcon({ className: '', html: '<div class="mepos"></div>', iconSize: [14, 14], iconAnchor: [7, 7] }), zIndexOffset: 2000 }).addTo(this.map);
  }
}
