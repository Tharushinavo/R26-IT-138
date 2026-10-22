// Pure resolution logic for the `line-traversal` archetype (10c). No React/React Native import in
// this file -- the surface (line-traversal-surface.tsx) is a thin layer over this, mirroring
// `value-report-logic.ts`'s and `ordered-value-sequence-logic.ts`'s own split.
//
// `line-traversal` is the archetype for C-JB-02 alone ("Count On from an Addend"). Its scene is a
// bounded number line: the child starts at a given position and makes successive UNIT jumps
// forward, and the client records each jump made. Two declared keys, classified by declared TYPE
// (field-kinds.ts) and never by key name:
//   - the one `integer-field` key  -> where the child says they landed (`final_position` today)
//   - the one `ordered-integer-collection` key -> the jumps actually made (`jumps` today)
// A different template declaring the same two kinds under different names would resolve here
// unchanged; that is the two-layer rule (sequence doc §3.0) working.
//
// WHY `jumps` IS ACCUMULATED, NOT ENTERED. Sequence doc §3.2 binds `list[int]` to two different
// primitives -- `value-token-row` (entered) and `jump-accumulator` (accumulated) -- and states the
// ARCHETYPE chooses which, "because the scene decides whether a list is entered or accumulated.
// That is the one place the scene layer reaches into the field layer, and it is why
// `line-traversal` is separate from `ordered-value-sequence`". This archetype accumulates: one
// entry appended per jump the child actually makes. `ValueTokenRow` is deliberately NOT reused.
//
// WHY `start` IS READ BY NAME. This archetype's scene needs an origin for its line, and `start` is
// that origin's name in the wire's own vocabulary for this scene. `ordered-value-sequence-logic.ts`
// sets the precedent for exactly this and states the rule: "hardcoding these two literals is
// reading the wire's vocabulary, not building a second template-id catalogue (the two-layer rule
// forbids the latter, not the former)". `start` is also EXCLUDED from `payloadValues` so the
// surface does not render it twice -- the generator sets `start = max(addend_a, addend_b)`, so
// rendering all three payload keys as tokens would show the larger addend's value in two places at
// once (difficulty 5: addend_a=3, addend_b=9, start=9). The line shows it; the token row does not.
//
// WHAT THIS FILE MUST NEVER DO. It never adds the addends together. `addend_a + addend_b` is the
// task's ANSWER (the server's `correct_answer_payload.sum`), so deriving anything from that sum --
// the line's extent above all -- would put the answer on screen. The line's length is a fixed
// layout constant owned by the stepper primitive, never a function of this payload.
// c-line-traversal-no-answer-derivation.test.ts guards this.
//
// All `prompt_payload` / `valid_action_space` access goes through
// `Object.prototype.hasOwnProperty.call(...)` / `Object.keys(...)`, never bare property access:
// both objects originate on the wire, and a key named `constructor`, `toString` or `__proto__`
// resolves to an inherited `Object.prototype` member under bare access.

import type { CNextTaskResponse } from '@/src/api/generated/openapi-types';
import { bindFieldKind } from '@/src/features/c-session/archetypes/field-kinds';
import { labelForPayloadKey } from '@/src/features/c-session/archetypes/payload-value-labels';

/** The `prompt_payload` key this archetype's scene consumes as its line origin. See the header. */
const LINE_ORIGIN_KEY = 'start';

export type LineTraversalPayloadValue = {
  key: string;
  label: string;
  value: number;
};

export type LineTraversalSpec = {
  promptText: string;
  /** Where the line begins. Rendered by the line itself, never as a token -- see the header. */
  startValue: number;
  /** Every other declared `prompt_payload` key, in the wire's own key order. */
  payloadValues: readonly LineTraversalPayloadValue[];
  /** The one `integer-field` key -- where the child reports landing. */
  positionKey: string;
  /** The one `ordered-integer-collection` key -- the jumps actually made. */
  jumpsKey: string;
  interactiveAssets: Record<string, unknown>;
};

/**
 * Resolve one task's `line-traversal` rendering spec, or `null` if resolution cannot proceed.
 * `null` here is what drives `FailClosedFrame` in the surface -- never a guessed rendering, never
 * a partial one.
 *
 * Fails closed for: `prompt_text` absent or empty; `prompt_payload` absent, not an object, or
 * containing any value that is not a finite number; the line-origin key (`start`) absent or not a
 * finite integer; `valid_action_space` declaring no key; a declared type this codebase does not
 * bind (field-kinds.ts); a count of `integer-field` keys other than exactly one; a count of
 * `ordered-integer-collection` keys other than exactly one; any declared key bound to any other
 * kind at all (this archetype's scene has nowhere to put one, and rendering a partial scene is
 * exactly what failing closed exists to prevent); `task.blanks` not exactly `null`.
 *
 * Note what is NOT checked, deliberately: the number of jumps, whether the reported position is
 * consistent with them, and whether either is correct. The client relays what the child did; the
 * server evaluates it (sequence doc §4, 10c: "Any jump-count validation; the client relays the
 * jumps the child made").
 */
export function resolveLineTraversalSpec(task: CNextTaskResponse): LineTraversalSpec | null {
  if (typeof task.prompt_text !== 'string' || task.prompt_text.length === 0) return null;

  const promptPayload = task.prompt_payload;
  if (typeof promptPayload !== 'object' || promptPayload === null) return null;

  const payloadKeys = Object.keys(promptPayload);
  if (payloadKeys.length === 0) return null;

  if (!Object.prototype.hasOwnProperty.call(promptPayload, LINE_ORIGIN_KEY)) return null;

  let startValue: number | null = null;
  const payloadValues: LineTraversalPayloadValue[] = [];

  for (const key of payloadKeys) {
    const value = (promptPayload as Record<string, unknown>)[key];
    if (typeof value !== 'number' || !Number.isFinite(value)) return null;

    if (key === LINE_ORIGIN_KEY) {
      // The origin indexes discrete tick positions on a line, so a fractional origin has no
      // meaning here -- unlike the other payload values, which only have to be displayable.
      if (!Number.isInteger(value)) return null;
      startValue = value;
      continue;
    }

    payloadValues.push({ key, label: labelForPayloadKey(key), value });
  }

  if (startValue === null) return null;

  const validActionSpace = task.valid_action_space;
  const actionKeys = Object.keys(validActionSpace);
  if (actionKeys.length === 0) return null;

  let positionKey: string | null = null;
  let jumpsKey: string | null = null;

  for (const key of actionKeys) {
    const binding = bindFieldKind(validActionSpace[key]);
    if (binding === null) return null;

    if (binding.kind === 'integer-field') {
      if (positionKey !== null) return null;
      positionKey = key;
      continue;
    }

    if (binding.kind === 'ordered-integer-collection') {
      if (jumpsKey !== null) return null;
      jumpsKey = key;
      continue;
    }

    return null;
  }

  if (positionKey === null || jumpsKey === null) return null;
  if (task.blanks !== null) return null;

  return {
    promptText: task.prompt_text,
    startValue,
    payloadValues,
    positionKey,
    jumpsKey,
    interactiveAssets: task.interactive_assets,
  };
}
