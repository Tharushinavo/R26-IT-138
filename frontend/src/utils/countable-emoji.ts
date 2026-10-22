// The emoji a child counts, shared by Component B's prompt visuals and Component C's object
// primitives so the two can never drift apart.
//
// OWNER REQUEST, 2026-10-18: real emoji characters, and no disc behind them -- the emoji IS the
// object. Adding a fruit later is one entry in the list below and both components pick it up.
//
// ONE EMOJI PER QUESTION, IDENTICAL WITHIN A SET (owner decision, 2026-10-18). The emoji varies
// between questions -- bananas on one, stars on the next -- but every object inside a single set is
// the same. That is not a styling preference, it protects what the item measures:
// `prompt-visuals/object-set.tsx` states the rule it has always followed, "A plain wrapped row of
// identical shapes is the point, not a shortcut". Counting seven identical things and counting two
// bananas, three apples and two stars are different cognitive tasks -- a mixed set is harder for a
// 7-9 year old to enumerate and invites sorting before counting. These visuals back real catalogue
// items (B-CNT02, B-CNT03, B-NS02, B-NS03, B-SUB01) in a screening instrument, so "which objects"
// is a measurement question. Varying ACROSS questions costs none of that.
//
// DETERMINISTIC, NEVER `Math.random()` IN RENDER. A random pick in the render path is re-rolled on
// every re-render, so the fruit would visibly change while a child is mid-count -- and in Component
// C, on every single tap, since selection re-renders the pool. Each caller passes a seed that is
// stable for the question (`itemOpportunityId` in B, the object ids in C) and the same seed always
// yields the same emoji.
//
// A NOTE ON RENDERING, because this codebase has been bitten before. `c-session/primitives/
// unit-stepper.tsx` records that an earlier emoji glyph "did not render consistently and showed as
// a placeholder box", which is why these objects were icon-font glyphs until now. Emoji are drawn
// from the platform's own font: web and iOS are reliable, ANDROID IS THE RISK. If a box appears on
// a device, the fix is a bundled emoji font or a return to icon glyphs -- not a different emoji.

/**
 * The pool, in no meaningful order. Extend freely: nothing keys off the index, and the picker
 * handles any length.
 *
 * Deliberately all simple, single-codepoint-ish, widely-supported characters. Avoid anything using
 * ZWJ sequences, skin-tone modifiers or regional indicators -- those are exactly the emoji that
 * degrade into boxes or split into two glyphs on older Android builds.
 */
export const COUNTABLE_EMOJI = ['🍌', '🍎', '🍊', '⭐'] as const;

export type CountableEmoji = (typeof COUNTABLE_EMOJI)[number];

/** Spoken name per emoji, for screen readers. Never a count -- see `pickCountableEmoji`. */
const EMOJI_LABELS: Record<string, string> = {
  '⭐': 'Star',
  '🍊': 'Orange',
  '🍌': 'Banana',
  '🍎': 'Apple',
};

/**
 * FNV-1a, 32-bit. A tiny, stable string hash -- the point is only that the same seed maps to the
 * same bucket on every platform and every render, not cryptographic quality.
 */
function hashSeed(seed: string): number {
  let hash = 0x811c9dc5;
  for (let index = 0; index < seed.length; index += 1) {
    hash ^= seed.charCodeAt(index);
    hash = Math.imul(hash, 0x01000193);
  }
  return hash >>> 0;
}

/**
 * The emoji for one question's whole set.
 *
 * Pass something stable for the question and unique between questions -- Component B uses
 * `plan.itemOpportunityId`, Component C the object ids. An empty or missing seed still returns a
 * valid emoji rather than throwing, because a missing id must never blank out the thing a child is
 * supposed to count.
 */
export function pickCountableEmoji(seed: string): CountableEmoji {
  return COUNTABLE_EMOJI[hashSeed(seed) % COUNTABLE_EMOJI.length];
}

/**
 * What a screen reader says for ONE object.
 *
 * Never includes a count, and the callers never label the group with one either: on a "how many
 * objects are there?" item that would read the answer aloud. The existing visuals have that rule
 * written into them and it is unchanged here -- a screen-reader user counts by traversing the
 * objects, exactly as a sighted child counts by looking.
 */
export function labelForCountableEmoji(emoji: string): string {
  return EMOJI_LABELS[emoji] ?? 'Object';
}
