import type { PlaceName, PromptVisualSpec } from '@/src/features/session/prompt-visuals/types';

// The prompt-visual registry: decides whether a prompt payload can be drawn, and as what.
//
// RESOLUTION IS KEY-DRIVEN, NOT TEMPLATE-ID-DRIVEN, for two reasons.
//
// 1. A template-id list would be catalogue content restated in the client, free to drift from the
//    backend's own template set — the same argument that keeps `formatSkillLabel` from carrying a
//    curated id→name table.
// 2. `representation_type`, the field that *should* drive this, is unusable today: the fixture
//    catalogue flattens it to "numeral" for all 36 templates while the governed catalogue says
//    `pictorial_objects`, `dot_sets`, `concrete_simulated`. Branching on it would branch on a value
//    that is currently wrong on the wire. Nothing here reads it.
//
// Every value is validated before it can reach a component. Anything absent, malformed, negative,
// non-integer or out of range resolves to `null`, and `null` means "no visual for this payload" —
// the screen renders stem-only, exactly today's behaviour, never worse. Unknown keys are ignored
// silently, also exactly as today.

// A layout/robustness bound, NOT a catalogue constraint — the client must not restate the
// generator's ranges. For reference the live samplers produce object_count 1..20, set_a/set_b
// 1..20, and pool_size up to 28 (target 1..20 plus 3..8), so this sits comfortably above every
// real value while still refusing an absurd one that would hang the layout.
export const MAX_RENDERABLE_OBJECTS = 40;

function readCount(value: unknown): number | null {
  // `typeof value === 'number'` first: a numeric *string* is not accepted, because coercing one
  // would be the client repairing a payload shape rather than reading it.
  if (typeof value !== 'number') return null;
  if (!Number.isInteger(value)) return null;
  if (value < 0 || value > MAX_RENDERABLE_OBJECTS) return null;
  return value;
}

function readLayout(value: unknown): string | null {
  return typeof value === 'string' && value.trim().length > 0 ? value : null;
}

// Place-value visuals carry a number whose *digits* are drawn, not a count of objects, so the
// object bound does not apply. Three digits is the catalogue's ceiling (B-PV03/B-PV04 are 100..999).
const MAX_RENDERABLE_PLACE_VALUE = 999;

const PLACE_NAMES = ['hundreds', 'tens', 'ones'] as const;

function readPlaceValue(value: unknown): number | null {
  if (typeof value !== 'number' || !Number.isInteger(value)) return null;
  if (value < 0 || value > MAX_RENDERABLE_PLACE_VALUE) return null;
  return value;
}

function readPlaceName(value: unknown): PlaceName | null {
  return typeof value === 'string' && (PLACE_NAMES as readonly string[]).includes(value)
    ? (value as PlaceName)
    : null;
}

function readPlaceNames(value: unknown): readonly PlaceName[] | null {
  if (!Array.isArray(value) || value.length === 0) return null;
  const names: PlaceName[] = [];
  for (const entry of value) {
    const name = readPlaceName(entry);
    if (name === null) return null;
    names.push(name);
  }
  return names;
}

function readSignedDelta(value: unknown): number | null {
  if (typeof value !== 'number' || !Number.isInteger(value)) return null;
  // Symmetric bound around the object bound: an "after" panel is still a set of drawable objects.
  if (Math.abs(value) > MAX_RENDERABLE_OBJECTS) return null;
  return value;
}

function has(prompt: Record<string, unknown>, key: string): boolean {
  // Own-property check, never bare access: a payload key named "constructor" or "__proto__" would
  // otherwise resolve to an inherited Object.prototype member. Same discipline as FE-3a's renderer
  // registry.
  return Object.prototype.hasOwnProperty.call(prompt, key);
}

/**
 * Resolve the visual for one prompt payload, or `null` for stem-only.
 *
 * PRECEDENCE is explicit and fixed, most-specific first, so the result is deterministic even if a
 * future payload carries several of these keys at once:
 *
 *   1. `initial_count` + `transformation` + `delta` → before-after
 *   2. `n` + `places`   (PLURAL) → base-ten-blocks
 *   3. `n` + `place`    (SINGULAR) → place-value-chart
 *   4. `total` + `removed` → take-away
 *   5. `set_a` + `set_b`   → two-sets
 *   6. `pool_size`         → selectable-pool
 *   7. `object_count`      → object-set
 *
 * TWO HAZARDS THIS ORDER AND THESE KEY SETS EXIST TO AVOID:
 *
 * - `place` (singular, a string) means a place-value CHART; `places` (plural, an array) means
 *   BASE-TEN BLOCKS. One character apart and completely different visuals. Both are matched by exact
 *   own-key presence, so a payload carrying one can never satisfy the other, and blocks are checked
 *   first so the more specific plural form wins even if some future payload carried both.
 *
 * - `total` is NOT distinctive. B-SUB01 sends `total` + `removed`, but B-DIV01 sends `total` +
 *   `recipients` and B-DIV02 sends `total` + `group_size`. The full pair is therefore required:
 *   `total` alone must never resolve, or both division templates would draw a take-away visual that
 *   misrepresents the question entirely.
 */
export function resolvePromptVisual(prompt: Record<string, unknown>): PromptVisualSpec | null {
  if (has(prompt, 'initial_count') && has(prompt, 'transformation') && has(prompt, 'delta')) {
    const before = readCount(prompt.initial_count);
    const delta = readSignedDelta(prompt.delta);
    if (before === null || delta === null) return null;
    const after = before + delta;
    // A negative or unrenderable "after" is drift, not a question: fail closed to stem-only rather
    // than draw a set that cannot exist.
    if (after < 0 || after > MAX_RENDERABLE_OBJECTS) return null;
    return { kind: 'before-after', before, after };
  }

  // PLURAL first — see the hazard note above.
  if (has(prompt, 'n') && has(prompt, 'places')) {
    const value = readPlaceValue(prompt.n);
    const places = readPlaceNames(prompt.places);
    if (value === null || places === null) return null;
    return { kind: 'base-ten-blocks', value, places };
  }

  if (has(prompt, 'n') && has(prompt, 'place')) {
    const value = readPlaceValue(prompt.n);
    const askedPlace = readPlaceName(prompt.place);
    if (value === null || askedPlace === null) return null;
    // The chart shows every place the number occupies, which is a property of the number itself and
    // not of which place the stem asks about.
    const places = value >= 100 ? PLACE_NAMES : (['tens', 'ones'] as const);
    return { kind: 'place-value-chart', value, places, askedPlace };
  }

  // Both keys required. `total` on its own belongs to two division templates whose questions this
  // visual would misrepresent.
  if (has(prompt, 'total') && has(prompt, 'removed')) {
    const total = readCount(prompt.total);
    const removed = readCount(prompt.removed);
    if (total === null || removed === null) return null;
    if (removed > total) return null;
    return { kind: 'take-away', total, removed };
  }

  if (has(prompt, 'set_a') && has(prompt, 'set_b')) {
    const setA = readCount(prompt.set_a);
    const setB = readCount(prompt.set_b);
    if (setA === null || setB === null) return null;
    return { kind: 'two-sets', setA, setB };
  }

  if (has(prompt, 'pool_size')) {
    const poolSize = readCount(prompt.pool_size);
    // A pool of nothing is not a selectable surface; fall through to stem-only rather than render an
    // empty tray the child cannot act on.
    if (poolSize === null || poolSize < 1) return null;
    return { kind: 'selectable-pool', poolSize };
  }

  if (has(prompt, 'object_count')) {
    const count = readCount(prompt.object_count);
    if (count === null) return null;
    return { kind: 'object-set', count, layout: readLayout(prompt.layout) };
  }

  return null;
}
