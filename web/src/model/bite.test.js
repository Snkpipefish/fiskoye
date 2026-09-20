// node --test src/model/  – paritet mot pipeline/tests/fixtures/bite_ref.json (generert av pytest)
import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';
import { fSesong, fDiel, fTemp, fTrykk, fVind, fLys, fFlow, fKlar, W } from './bite.js';
import { wgeomean } from './curves.js';

const here = dirname(fileURLToPath(import.meta.url));
const fix = JSON.parse(readFileSync(join(here, '../../../pipeline/tests/fixtures/bite_ref.json'), 'utf8'));
const species = JSON.parse(readFileSync(join(here, '../../public/data/species.json'), 'utf8')).species;

test('bittindeks-komponenter er identiske i Python og JS', () => {
  assert.deepEqual(W, fix.W);
  for (const c of fix.cases) {
    const sp = species[c.art]; const x = c.ctx;
    const comps = {
      sesong: fSesong(sp.sesong.maaned, x.doy, sp.sesong.gyting),
      diel: fDiel(x.hour, x.sunrise, x.sunset, x.sun_alt, sp.diel),
      temp: fTemp(x.tw, sp.habitat.temp_c),
      trykk: fTrykk(x.dp3, sp.vaer.trykk),
      vind: fVind(x.wind, sp.vaer.vind.opt_ms, sp.vaer.vind.max_ms),
      lys: fLys(x.sun_alt, x.cloud, sp.vaer.lys),
      flow: fFlow(x.a, sp.vaer.vannforing.a_opt, sp.vaer.vannforing.sigma),
      klar: fKlar(x.turb, sp.vaer.klarhet.folsomhet),
    };
    for (const k of Object.keys(comps)) assert.ok(Math.abs(comps[k] - c.comps[k]) < 1e-9, `${c.navn}.${k}: ${comps[k]} vs ${c.comps[k]}`);
    const keys = Object.keys(W);
    const A = wgeomean(keys.map((k) => comps[k]), keys.map((k) => W[k]));
    assert.ok(Math.abs(A - c.A) < 1e-9, `${c.navn}.A`);
  }
});
