import L from 'leaflet';

export const BASEMAPS = [
  { id: 'esri', label: 'ESRI SAT', make: () => L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', { maxZoom: 19, maxNativeZoom: 18 }) },
  { id: 'eox', label: 'S2 CLOUDLESS', make: () => L.tileLayer('https://tiles.maps.eox.at/wmts/1.0.0/s2cloudless-2023_3857/default/g/{z}/{y}/{x}.jpg', { maxZoom: 19, maxNativeZoom: 16 }) },
  { id: 'topo', label: 'TOPO', make: () => L.tileLayer('https://cache.kartverket.no/v1/wmts/1.0.0/topo/default/webmercator/{z}/{y}/{x}.png', { maxZoom: 19, maxNativeZoom: 18 }) },
  { id: 'graa', label: 'TOPO GRÅ', make: () => L.tileLayer('https://cache.kartverket.no/v1/wmts/1.0.0/topograatone/default/webmercator/{z}/{y}/{x}.png', { maxZoom: 19, maxNativeZoom: 18 }) },
];
