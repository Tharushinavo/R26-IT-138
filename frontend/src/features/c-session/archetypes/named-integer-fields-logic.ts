// Pure resolution logic for the `named-integer-fields` archetype (10f, C-BT-01..04). No React /
// React Native import in this file -- the surface (named-integer-fields-surface.tsx) is a thin
// layer over this, mirroring every archetype since 10b.
//
// THE SCENE: two or more integer answers, entered simultaneously, each labelled by its own
// `valid_action_space` key. Measured from the frozen exemplars:
//
//   | Template  | prompt_payload            | valid_action_space                    |
//   | --------- | ------------------------- | ------------------------------------- |
//   | C-BT-01   | target_number             | tens, ones                            |
//   | C-BT-02   | target_number             | hundreds, tens, ones                  |
//   | C-BT-03   | pre_tens, pre_ones        | post_tens, post_ones                  |
//   | C-BT-04   | pre_tens, pre_ones        | post_tens, post_ones                  |
//
// THE DISCRIMINATOR AGAINST `value-report` IS THE FIELD COUNT, AND IT IS TYPE-DERIVED, NOT DECLARED.
// `value-report-logic.ts` requires exactly ONE `integer-field`; this requires TWO OR MORE. Neither
// resolver reads a template id to decide, and neither carries a per-template key table -- the two
// scenes are distinguished purely by how many `integer-field` keys the wire declares. Two keys
// (BT-01/03/04) and three (BT-02) both resolve here with zero code difference between them, which
// is the two-layer rule's strongest demonstration in this codebase: the field COUNT, the field
// ORDER and the field LABELS are all read off `valid_action_space` at runtime.
//
// FIELD LABELS COME FROM THE KEYS THEMSELVES, NEVER FROM A TABLE (master work order §3,
// `named-integer-fields`' own row: "Field labels come from `valid_action_space` keys, not a client
// table"). `humanizeActionKey` below is a mechanical transformation of the key string and consults
// nothing -- `tens` -> "Tens", `post_ones` -> "Post Ones". It is deliberately NOT
// `labelForPayloadKey` from payload-value-labels.ts, and is defined locally rather than imported,
// even though the two are similar: that module's whole purpose is a fixed lookup TABLE, which is
// exactly what an action key must never be routed through. Keeping the action-key path in a
// separate function, in this file, with no table in scope, means a future edit cannot quietly add
// `post_tens: 'Tens now'` to a table and have it apply here. `prompt_payload` keys are a different
// matter and DO go through that table -- a payload key is content the child reads, not a field the
// child fills, and the table has always been allowed there.
//
// NO AUTO-CARRY, NO AUTO-BORROW, NO PRE-FILL (master work order §10f row, verbatim). Performing the
// trade IS the assessed skill in BT-03/04, and decomposing the number IS the assessed skill in
// BT-01/02. So this resolver deliberately does NOT expose any derived quantity: it does not compute
// what `tens`/`ones` should be from `target_number`, does not compute the post-trade state from
// `pre_tens`/`pre_ones`, and does not report whether the fields currently sum to anything. The
// surface has nothing to pre-fill from and nothing to auto-complete with, because none of it is
// resolved here. `c-named-integer-fields-no-client-arithmetic.test.ts` holds that line.
//
// C-EG-02 IS SUPPORTED HERE, AS A NAMED, NARROW EXTENSION TO THE OTHERWISE-GENERIC PAYLOAD GUARD
// (10g). `registry.ts` maps `C-EG-02` -> `named-integer-fields` (per the work order's own sequence
// table: "10g ... Reuses `named-integer-fields` (EG-02)"). Its `prompt_payload` carries `rows` and
// `cols` -- also the names of TWO of its THREE `valid_action_space` keys -- and `direction`, a
// STRING (`"read"` at difficulty 1-4, `"build"` at difficulty 5; both prompts are deictic about
// "the array", and `interactive_assets` is `{}` on every real exemplar, so the client owes a
// visual). Two consequences, both handled explicitly rather than by relaxing the general guard:
//
//   1. `rows`/`cols` are consumed STRUCTURALLY, as grid dimensions for `ArrayGrid`
//      (primitives/array-grid.tsx), and excluded from `payloadValues` -- the identical treatment
//      `line-position-logic.ts` gives `target_position` and `partition-allocation-logic.ts` gives
//      its bin-count key. Rendering them as payload numeral tokens (what this file did for BT-01..04
//      before this batch) would print 2 of the 3 answers on screen, since they are simultaneously
//      GIVEN and part of the answer here -- unlike BT-01..04's payload, which never overlaps its own
//      action space.
//   2. `direction` is admitted as a STRING through a narrow, NAMED vocabulary exception (just this
//      one key), carried in the spec, and rendered nowhere and branched on nowhere -- 10a's own
//      standing ruling for `C-NP-04.direction` ("the direction reaches the child through
//      `prompt_text`"), applied unchanged. EVERY OTHER payload value still fails closed if it is
//      not a finite number: this is not a relaxation of the guard, only a single recognised name
//      admitted alongside it. `c-named-integer-fields-array-grid.test.ts` and
//      `c-named-integer-fields-eg02-fails-closed.test.ts` (renamed from its own prior, now-inverted
//      assertion -- see that file's own header) hold this line.
//
// C-BT-01..04 declare neither `rows`, `cols` nor `direction`, so `grid`/`direction` are `null` for
// them and their behaviour is byte-for-byte unchanged from 10f.
//
// All `prompt_payload` / `valid_action_space` access goes through
// `Object.prototype.hasOwnProperty.call(...)` / `Object.keys(...)`, never bare property access:
// both objects originate on the wire, and a key named `constructor`, `toString` or `__proto__`
// resolves to an inherited `Object.prototype` member under bare access.

import type { CNextTaskResponse } from '@/src/api/generated/openapi-types';
import { bindFieldKind } from '@/src/features/c-session/archetypes/field-kinds';
import { labelForPayloadKey } from '@/src/features/c-session/archetypes/payload-value-labels';

// The minimum field count that makes this scene this scene rather than `value-report`'s. See the
// header's "THE DISCRIMINATOR" paragraph.
const MIN_FIELDS = 2;

// A CORRUPTION-SAFETY CEILING on how many entry fields will be rendered, not a considered judgement
// about how many a child can handle -- literal, never derived from anything, mirroring
// `MAX_INTERVAL_MAX` / `MAX_POOL_OBJECTS` / `MAX_LINE_FORWARD_STEPS` doctrine. The real observed
// maximum across all five templates that route here is 3 (C-BT-02, C-EG-02); 6 is comfortably above
// that while still catching a materially corrupted `valid_action_space` before it asks the surface
// to render an unbounded number of keypad-backed fields.
const MAX_FIELDS = 6;

// A CORRUPTION-SAFETY CEILING on the array grid's own dimensions, not a considered judgement about
// how large a grid a child can handle -- literal, never derived from anything, mirroring
// `MAX_FIELDS`'s own doctrine. The real observed maximum is 5x5 (C-EG-02 L5); 10 is comfortably
// above that while still catching a materially corrupted `rows`/`cols` pair before it asks
// `ArrayGrid` to render an unbounded number of cells.
const MAX_GRID_DIMENSION = 10;

export type NamedIntegerFieldsPayloadValue = {
  key: string;
  label: string;
  value: number;
};

export type NamedIntegerFieldsGrid = {
  rows: number;
  cols: number;
};

export type NamedIntegerFieldsField = {
  /** The `valid_action_space` key this field submits under. */
  key: string;
  /** Mechanically derived from `key` -- see the header. Never a table lookup. */
  label: string;
};

export type NamedIntegerFieldsSpec = {
  promptText: string;
  /** Every `prompt_payload` key, in the wire's own key order, labelled for display. */
  payloadValues: readonly NamedIntegerFieldsPayloadValue[];
  /** The `integer-field` keys, in the wire's own key order. Always at least `MIN_FIELDS` long. */
  fields: readonly NamedIntegerFieldsField[];
  /** Present only for C-EG-02: `rows`/`cols` consumed structurally as grid dimensions, `null` for
   *  every other template. See the header's "C-EG-02 IS SUPPORTED HERE" paragraph. */
  grid: NamedIntegerFieldsGrid | null;
  /** Present only for C-EG-02: relayed verbatim, rendered nowhere, branched on nowhere -- `null`
   *  for every other template. See the header. */
  direction: string | null;
  interactiveAssets: Record<string, unknown>;
};

/**
 * Mechanically humanise one `valid_action_space` key for display. Consults nothing -- see the
 * header's "FIELD LABELS COME FROM THE KEYS THEMSELVES" paragraph for why this is deliberately not
 * `labelForPayloadKey`, and why it lives here rather than beside it.
 */
export function humanizeActionKey(key: string): string {
  return key
    .split('_')
    .filter((part) => part.length > 0)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ');
}

/**
 * Resolve one task's `named-integer-fields` rendering spec, or `null` if resolution cannot proceed.
 * `null` here is what drives `FailClosedFrame` in the surface -- never a guessed rendering, never a
 * partial one.
 *
 * Fails closed for: `prompt_text` absent or empty; `prompt_payload` absent, not an object, empty, or
 * containing any value that is neither a finite number nor the single named `direction` string
 * exception (see the header); `rows`/`cols` present but not both, not a positive integer, or
 * exceeding `MAX_GRID_DIMENSION`; `direction` present but empty; `valid_action_space` declaring no
 * key; a declared type this codebase does not bind (field-kinds.ts); any declared key whose bound
 * kind is not `integer-field` (this scene has nowhere to put one); fewer than `MIN_FIELDS` or more
 * than `MAX_FIELDS` integer fields; `task.blanks` not exactly `null`.
 *
 * Note what is NOT checked, deliberately: whether the fields the child will enter decompose
 * `target_number`, correctly effect the trade from `pre_tens`/`pre_ones`, or match the grid's own
 * `rows`/`cols`/product. That is the server's judgement, and computing it here would be the
 * auto-carry the work order forbids.
 */
export function resolveNamedIntegerFieldsSpec(task: CNextTaskResponse): NamedIntegerFieldsSpec | null {
  if (typeof task.prompt_text !== 'string' || task.prompt_text.length === 0) return null;
  if (task.blanks !== null) return null;

  const promptPayload = task.prompt_payload;
  if (typeof promptPayload !== 'object' || promptPayload === null) return null;

  const payloadKeys = Object.keys(promptPayload);
  if (payloadKeys.length === 0) return null;

  const payloadValues: NamedIntegerFieldsPayloadValue[] = [];
  let gridRows: number | null = null;
  let gridCols: number | null = null;
  let direction: string | null = null;

  for (const key of payloadKeys) {
    const value = (promptPayload as Record<string, unknown>)[key];

    // The single named string exception -- see the header's "C-EG-02 IS SUPPORTED HERE" paragraph.
    // No other key may ever be a string; this branch is keyed on the name `direction` alone.
    if (key === 'direction') {
      if (typeof value !== 'string' || value.length === 0) return null;
      direction = value;
      continue;
    }

    // The numbers-only guard, unchanged for every other key.
    if (typeof value !== 'number' || !Number.isFinite(value)) return null;

    if (key === 'rows' || key === 'cols') {
      if (!Number.isInteger(value) || value <= 0 || value > MAX_GRID_DIMENSION) return null;
      if (key === 'rows') gridRows = value;
      else gridCols = value;
      continue;
    }

    payloadValues.push({ key, label: labelForPayloadKey(key), value });
  }

  // Both or neither -- a lone `rows` or `cols` is a malformed grid, not a partial one to render.
  if ((gridRows === null) !== (gridCols === null)) return null;
  const grid: NamedIntegerFieldsGrid | null = gridRows !== null && gridCols !== null ? { rows: gridRows, cols: gridCols } : null;

  const validActionSpace = task.valid_action_space;
  const actionKeys = Object.keys(validActionSpace);
  if (actionKeys.length === 0) return null;

  const fields: NamedIntegerFieldsField[] = [];
  for (const key of actionKeys) {
    const binding = bindFieldKind(validActionSpace[key]);
    if (binding === null) return null;
    if (binding.kind !== 'integer-field') return null;
    fields.push({ key, label: humanizeActionKey(key) });
  }

  if (fields.length < MIN_FIELDS) return null;
  if (fields.length > MAX_FIELDS) return null;

  return {
    promptText: task.prompt_text,
    payloadValues,
    fields,
    grid,
    direction,
    interactiveAssets: task.interactive_assets,
  };
}
