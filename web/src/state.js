export const state = {
  index: null, species: {}, speciesId: 'gjedde',
  areaSlug: null, area: null, segments: null, spots: null, s2: null, climate: null, base: '',
  t: new Date(), live: true,
  spot: null, weather: null, nve: null, ctx: null, userPos: null,
};

const subs = {};
export const bus = {
  on(ev, fn) { (subs[ev] ||= []).push(fn); },
  emit(ev, ...a) { for (const fn of subs[ev] || []) fn(...a); },
};

export function setTime(t, live = false) { state.t = t; state.live = live; bus.emit('time'); }
export function setSpecies(id) { if (!state.species[id]) return; state.speciesId = id; bus.emit('species'); }
export function setSpot(spot) { state.spot = spot; bus.emit('spot'); }
export const sp = () => state.species[state.speciesId];
