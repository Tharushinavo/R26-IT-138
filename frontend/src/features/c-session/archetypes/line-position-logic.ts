// Pure resolution logic for the `line-position` archetype (10d, C-MCL-04 only). No React/React
// Native import in this file -- the surface (line-position-surface.tsx) is a thin layer over this,
// mirroring `line-traversal-logic.ts`'s own split (this file is written directly against that one's
// shape, since both are number-line scenes over the same `unit-stepper.tsx` primitive per master
// work order §5A: "Build the stepping primitive once; `line-position` and `line-traversal` are two
// thin compositions over it, not two separate designs").
//
// A DIFFERENT SCENE FROM `line-traversal`, DELIBERATELY (master work order §3, `line-position`'s own
// row: "A separate archetype from `line-traversal` -- do not merge them"). `line-traversal`
// accumulates jumps FROM a given origin toward an unknown sum; `line-position` locates a GIVEN
// target on a bounded, given-range line. The wire shapes differ accordingly:
//   - `prompt_payload`: `interval_max` (the line's own range, 0..interval_max) and `target_position`
//     (where the marker must land) -- both read BY NAME, the same precedent `line-traversal-logic.ts`
//     already sets for `start`: "hardcoding these two literals is reading the wire's vocabulary, not
//     building a second template-id catalogue".
//   - `valid_action_space`: exactly one `numeric-field` key (`number`, not `int` -- the only
//     `number`-typed action key across all thirty templates), classified by declared type alone,
//     never by name.
//
// `target_position` IS THE GIVEN, NOT THE ANSWER, AND MUST STILL NEVER BE RENDERED AS A NUMERAL.
// The prompt text ("Move the marker to the target spot on the line") is deictic and needs a visible
// target -- unlike `line-traversal`'s sum, there is no way to complete this task without showing
// WHERE the target is. The surface renders it as a marked TICK on the line itself (the same
// non-numeral treatment `line-traversal`'s own `start` origin gets), never as a bare digit token --
// showing "26" next to the prompt would let the child match a printed number instead of reading the
// line, which is not what a spatial-location task is meant to assess. `target_position` is therefore
// excluded from `payloadValues` here exactly as `start` is excluded in `line-traversal-logic.ts`,
// for the same reason: it is consumed structurally by the scene, not rendered generically.
//
// THE INTERACTION-COST FIX THIS ARCHETYPE OWES (10d work order §2.2, `unit-stepper.tsx`'s own
// header). Measured from the real exemplars: `interval_max` ramps 10 -> 200 across L1-L5 and
// `target_position` reaches up to 34 units from the origin at L5. Unit-only stepping (line-
// traversal's own shape) would cost up to 34 taps there against 2 at L1 -- a 17x spread that SPEC
// section 10 forbids, because unlike `line-traversal` (where each unit jump IS the counting-on act
// being scored) every one of those taps here is pure transit cost after the first, assessing
// nothing. `COARSE_STEP` (a fixed 10, chosen once, never derived from `interval_max` or
// `difficulty_level`) is what `unit-stepper.tsx`'s new `coarseStep` prop composes over: at L5 this
// reduces 34 taps to 7 (3 coarse + 4 fine). Still fully within ruling 6.3 -- still discrete integer
// stepping, still a constant per-step touch target, the line still scrolls rather than compresses.
//
// All `prompt_payload` / `valid_action_space` access goes through
// `Object.prototype.hasOwnProperty.call(...)` / `Object.keys(...)`, never bare property access:
// both objects originate on the wire, and a key named `constructor`, `toString` or `__proto__`
// resolves to an inherited `Object.prototype` member under bare access.

import type { CNextTaskResponse } from '@/src/api/generated/openapi-types';
import { bindFieldKind } from '@/src/features/c-session/archetypes/field-kinds';
import { labelForPayloadKey } from '@/src/features/c-session/archetypes/payload-value-labels';

/** The `prompt_payload` keys this scene consumes structurally. See the header. */
const INTERVAL_MAX_KEY = 'interval_max';
const TARGET_POSITION_KEY = 'target_position';

// A CORRUPTION-SAFETY CEILING on the line's own range, not a considered judgement about how far a
// child can track a line -- literal, never derived from anything, mirroring `unit-stepper.tsx`'s own
// `MAX_LINE_FORWARD_STEPS` doctrine. The real observed maximum is 200 (L5); 1000 is comfortably
// above that while still catching a materially corrupted `interval_max` before it asks
// `unit-stepper.tsx` to render an unbounded number of ticks.
const MAX_INTERVAL_MAX = 1000;

// The fixed coarse step `unit-stepper.tsx`'s own `coarseStep` prop is given. See the header's
// "THE INTERACTION-COST FIX" paragraph for why this is a constant, never a function of the wire.
export const LINE_POSITION_COARSE_STEP = 10;

// THE DISCOVERABILITY HINT (2026-08-26, owner decision, found by the user testing at difficulty 5).
// The stepper only auto-scrolls to keep the MARKER in view (unit-stepper.tsx's own doctrine, shared
// with line-traversal); the marker starts at 0, so a target far down a long line (up to 200 units)
// is entirely off-screen with nothing telling the child which direction, or how far, to go. A
// bucketed RANGE -- never the exact value -- solves that without reopening the leak this archetype
// otherwise avoids: `targetRangeStart`/`targetRangeEnd` narrow the search to a fixed-width window
// rather than the full `intervalMax`, the same trade-off a paper number line's own printed
// gridlines make (a labelled "30" gridline narrows a search without pinpointing 34 on its own).
// `TARGET_HINT_BUCKET_SIZE` is a constant, never derived from `intervalMax` or `difficulty_level` --
// the bucket is the same width regardless of how long the line is.
//
// TENS, not fives (owner instruction, 2026-09-28). Boundaries now land on 0, 10, 20, 30 -- the
// numbers a child counts in and the ones a number line is conventionally labelled with, so the
// hint names a landmark they already recognise rather than an arbitrary half-step.
//
// The trade-off, stated rather than hidden: on the SHORTEST line (L1, `intervalMax` 10) a ten-wide
// bucket is the whole line, so the hint stops narrowing anything there. That is acceptable because
// it is not where the hint is needed -- a 10-unit line is fully visible without scrolling, and this
// hint exists for the 200-unit line at L5 where the target starts off-screen. On that line a
// ten-wide window is still a twentieth of the search.
const TARGET_HINT_BUCKET_SIZE = 10;

export type LinePositionPayloadValue = {
  key: string;
  label: string;
  value: number;
};

export type LinePositionSpec = {
  promptText: string;
  /** The line's own range: ticks render from 0 to this value. See the header. */
  intervalMax: number;
  /** Where the marker must land. Rendered as a marked TICK on the line, never as a numeral -- see
   *  the header's own "IS THE GIVEN, NOT THE ANSWER" paragraph. */
  targetPosition: number;
  /** A `TARGET_HINT_BUCKET_SIZE`-wide window containing `targetPosition` -- see "THE
   *  DISCOVERABILITY HINT" above. Boundaries fall on multiples of `TARGET_HINT_BUCKET_SIZE`
   *  ("0-10, 10-20, 20-30", not "0-9, 10-19, 20-29"): normally `targetRangeStart` is the multiple at
   *  or below `targetPosition` and `targetRangeEnd` the next one up, but at the line's far end the
   *  window SLIDES DOWN to stay full width rather than shrinking against `intervalMax`. Always
   *  satisfies `targetRangeStart <= targetPosition <= targetRangeEnd`, and the width is always
   *  `TARGET_HINT_BUCKET_SIZE` unless the whole line is shorter than one bucket -- NEVER zero,
   *  which would state the answer outright. */
  targetRangeStart: number;
  targetRangeEnd: number;
  /** Every other declared `prompt_payload` key, in the wire's own key order (empty on every real
   *  exemplar today; carried for the same reason `line-traversal-logic.ts` carries its own). */
  payloadValues: readonly LinePositionPayloadValue[];
  /** The one `numeric-field` key -- where the child reports the marker landed. */
  positionKey: string;
  interactiveAssets: Record<string, unknown>;
};

/**
 * Resolve one task's `line-position` rendering spec, or `null` if resolution cannot proceed. `null`
 * here is what drives `FailClosedFrame` in the surface -- never a guessed rendering, never a partial
 * one.
 *
 * Fails closed for: `prompt_text` absent or empty; `prompt_payload` absent, not an object, or
 * containing any value that is not a finite number; `interval_max` absent, not a finite integer,
 * non-positive, or exceeding `MAX_INTERVAL_MAX`; `target_position` absent, not a finite integer, or
 * outside `[0, intervalMax]`; `valid_action_space` declaring no key; a declared type this codebase
 * does not bind (field-kinds.ts); a count of `numeric-field` keys other than exactly one; any
 * declared key bound to any other kind at all (this archetype's scene has nowhere to put one);
 * `task.blanks` not exactly `null`.
 *
 * Note what is NOT checked, deliberately: whether the reported `marker_position` is within
 * `tolerance` of `target_position`. `tolerance` lives in `correct_answer_payload` and never reaches
 * the client (10d work order §2.2) -- the client relays what the child submitted; the server grades
 * it.
 */
export function resolveLinePositionSpec(task: CNextTaskResponse): LinePositionSpec | null {
  if (typeof task.prompt_text !== 'string' || task.prompt_text.length === 0) return null;
  if (task.blanks !== null) return null;

  const promptPayload = task.prompt_payload;
  if (typeof promptPayload !== 'object' || promptPayload === null) return null;

  const payloadKeys = Object.keys(promptPayload);
  if (payloadKeys.length === 0) return null;

  if (!Object.prototype.hasOwnProperty.call(promptPayload, INTERVAL_MAX_KEY)) return null;
  if (!Object.prototype.hasOwnProperty.call(promptPayload, TARGET_POSITION_KEY)) return null;

  let intervalMax: number | null = null;
  let targetPosition: number | null = null;
  const payloadValues: LinePositionPayloadValue[] = [];

  for (const key of payloadKeys) {
    const value = (promptPayload as Record<string, unknown>)[key];
    if (typeof value !== 'number' || !Number.isFinite(value)) return null;

    if (key === INTERVAL_MAX_KEY) {
      if (!Number.isInteger(value) || value <= 0 || value > MAX_INTERVAL_MAX) return null;
      intervalMax = value;
      continue;
    }

    if (key === TARGET_POSITION_KEY) {
      // Validated fully below, once intervalMax is known -- target_position must fall within
      // [0, intervalMax], and intervalMax may appear after it in wire key order.
      if (!Number.isInteger(value)) return null;
      targetPosition = value;
      continue;
    }

    payloadValues.push({ key, label: labelForPayloadKey(key), value });
  }

  if (intervalMax === null || targetPosition === null) return null;
  if (targetPosition < 0 || targetPosition > intervalMax) return null;

  const validActionSpace = task.valid_action_space;
  const actionKeys = Object.keys(validActionSpace);
  if (actionKeys.length === 0) return null;

  let positionKey: string | null = null;

  for (const key of actionKeys) {
    const binding = bindFieldKind(validActionSpace[key]);
    if (binding === null) return null;

    if (binding.kind === 'numeric-field') {
      if (positionKey !== null) return null;
      positionKey = key;
      continue;
    }

    return null;
  }

  if (positionKey === null) return null;

  // Bucket boundaries at multiples of TARGET_HINT_BUCKET_SIZE (2026-08-26 correction: "0-10,
  // 10-20, 20-30" -- each bucket's end is the NEXT multiple, not one short of it, matching how a
  // number line's own gridlines are conventionally labelled). Target 34 -> bucket [30, 40],
  // displayed "30 and 40".
  //
  // AT THE LINE'S FAR END THE WINDOW SLIDES DOWN; IT DOES NOT SHRINK (2026-09-28). This used to
  // clamp the END to `intervalMax`, which COLLAPSED the window to zero width whenever the target
  // sat exactly on the last bucket boundary: target 10 on a 10-unit line produced start 10, end
  // min(10, 15) = 10, and the hint read "Target is between 10 and 10" -- the exact answer, stated
  // as a numeral, which is the one thing this archetype's whole design refuses to do (see the
  // header's "IS THE GIVEN, NOT THE ANSWER"). Sliding the start back instead keeps the window its
  // full width and keeps the target inside it: the same [5, 10] a paper number line's gridlines
  // would give. A line SHORTER than one bucket is the only case that still yields a narrower
  // window -- there, [0, intervalMax] is the whole line and there is nothing narrower to leak.
  const bucketStart = Math.floor(targetPosition / TARGET_HINT_BUCKET_SIZE) * TARGET_HINT_BUCKET_SIZE;
  const targetRangeStart = Math.max(0, Math.min(bucketStart, intervalMax - TARGET_HINT_BUCKET_SIZE));
  const targetRangeEnd = Math.min(intervalMax, targetRangeStart + TARGET_HINT_BUCKET_SIZE);

  return {
    promptText: task.prompt_text,
    intervalMax,
    targetPosition,
    targetRangeStart,
    targetRangeEnd,
    payloadValues,
    positionKey,
    interactiveAssets: task.interactive_assets,
  };
}
