# FISKEØYE – fiskeplasser, bittindeks og utstyrsråd fra satellitt

Statisk webapp (Vite + Leaflet) med en Python-pipeline som regner ut habitat-egnethet for fiskearter langs en elvestrekning, og en nettleser-modell som kombinerer den med live vær, sol/måne og vannføring til en bittindeks time for time. Første område: **Glomma ved Skarnes**. Nye områder legges til i `pipeline/config/areas.yaml`.

Inspirert av søsterprosjektene *soppkart* og *gulløye*, og av UI-et i Fishing Planet.

## Kjøre

```bash
# pipeline (bruk et venv med requirements.txt)
cd pipeline
python -m fiskpipe run --area skarnes          # --skip-sentinel --skip-images --skip-gbif for rask kjøring
python -m pytest                               # tester + genererer fixtures/bite_ref.json

# web
cd web
npm install
npm run dev                                    # http://localhost:5173
npm test                                       # paritetstest Python <-> JS (krever species.json + fixture)
BASE_PATH=/fiskoye/ npm run build                 # GitHub Pages
```

Live vannføring fra NVE hentes i GitHub Actions (`.github/workflows/pages.yml`, cron hver 6. time) med repo-secret `NVE_HYDAPI_KEY` (gratis nøkkel fra hydapi.nve.no). Uten nøkkel fungerer alt, men vannføringsfaktoren er 1.

## Struktur

- `pipeline/config/areas.yaml` – områder (bbox, elver, NVE-hint, regler, rekorder)
- `pipeline/config/species.yaml` – global artskatalog (habitatkurver, sesong, døgn, vær, utstyr, regler, tekst)
- `pipeline/fiskpipe/` – fetch (OSM, Kartverket DTM, Sentinel-2, GBIF, Open-Meteo, NVE) → `channel` (bredde/bukter) → `remote` (S2-indekser) → `features` → `scoring` (H) → `spots` → `export`
- `web/public/data/` – alt pipelinen skriver: `index.json`, `species.json`, `areas/<slug>/{area.json, segments.geojson, spots.geojson, s2_rgb.png, satcheck_N.jpg, points.gpx}`
- `web/src/model/` – `bite.js` (A, L, B, døgnkurve, ukesprognose), `water.js` (vanntemp), `tackle.js` (utstyr), `why.js` (prosa), `curves.js` (speil av `suitability.py`)
- `web/metode.html` – alle formler

## Formler i korte trekk

`B = H · A · L`. `H` = habitat 0–100 (geometrisk middel av dybde, strøm, vegetasjon, struktur, skygge). `A` = vektet geometrisk middel av sesong, døgn, vanntemp, trykktrend, vind, lys, vannføring, sikt, solunar. `L` = lokal justering for skygge, pålandsvind og flom. Se `web/metode.html`.

## Forbehold

Modellen er en beregning fra erfaringsregler, ikke fangstdata. Sjekk alltid gjeldende fiskekort, fredningstider og minstemål.
