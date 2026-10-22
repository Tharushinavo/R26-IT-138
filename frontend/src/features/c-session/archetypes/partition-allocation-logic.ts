// Pure resolution logic for the `partition-allocation` archetype (10g, C-EG-01; also lights up
// C-SF-01 by declared shape). No React/React Native import in this file -- the surface
// (partition-allocation-surface.tsx) is a thin layer over this, mirroring every archetype since 10b.
//
// THE SCENE: a total distributed into a fixed number of bins, each an entry the child fills.
// Measured from the frozen exemplars:
//
//   | Template  | prompt_payload                    | valid_action_space          |
//   | --------- | ---------------------------------- | ---------------------------- |
//   | C-EG-01   | number_of_groups, group_size       | groups: list[int]            |
//   | C-SF-01   | total, recipient_count             | allocations: list[int]       |
//
// `ValueTokenRow`'s own header already commits to being reused UNMODIFIED here ("no
// partition-allocation-specific behaviour (bin labels, totals, etc.) lives here") -- master work
// order §5A. Its `display-with-entry` mode is positional and unlabeled, which is exactly what an
// unnamed set of bins is; this file supplies only the bin COUNT and the payload values around it.
//
// THE COLLECTION KEY IS READ BY NAME, THE SAME PRECEDENT `ordered-value-sequence-logic.ts` SETS FOR
// `entered_values`/`arranged_values`: reading the wire's vocabulary is not a template-id catalogue,
// because a name is not a template id -- a future fifth `list[int]`-bearing template that reuses
// `groups` or `allocations` resolves here with zero code change, and one that introduces a THIRD
// name would need a one-line addition to `COLLECTION_KEY_VOCABULARY`, not a new branch.
//
// THE FIXED/VARIABLE DISCRIMINANT IS TYPE-LEVEL, NEVER A TEMPLATE ID. `C-SF-02` also declares a
// `list[int]` collection (`groups`) but ADDITIONALLY declares `submitted_group_count: int` -- the
// child chooses the bin count there, which is a materially different scene this file does not
// build. The presence of any `integer-field` key alongside the collection is what routes to `null`
// here, following `value-report-logic.ts`'s own sanctioned `C-TC-02` refusal pattern.
//
// 10H RULED ON THIS (§2.3's falsification test, owner decision, 2026-08-26): THE REFUSAL STAYS.
// C-SF-02's `prompt_payload` is only `{group_size, total}` -- unlike `C-EG-01`/`C-SF-01`, it
// declares NO bin-count key in `BIN_COUNT_KEY_VOCABULARY` at all. The bin count is the answer
// (`total / group_size`, exact at every real difficulty level) and a declared `valid_action_space`
// key. Deriving it client-side would compute an answer key and render exactly that many slots --
// the same leak class `C-EG-02`'s `rows`/`cols` and `C-MCL-01`'s numeral-options path were built to
// avoid, not the "one extra field, scene unchanged" shape §2.3 tested for. The only non-leaking
// shape is a two-stage interaction (child enters the count, THEN fills that many bins), which
// `DisplayWithEntryRow` cannot do at all -- `blanks` is read once in a `useState` lazy initializer,
// never re-synced, with no add/remove affordance, and that primitive's own header commits to
// UNMODIFIED reuse. That is a new interaction, not configuration -- C-18's claim ("a new template
// within an existing archetype is configuration, not a new screen") is FALSIFIED by this one key,
// even though it HELD for `submitted_group_count` itself (a genuine one-field extension, no
// different from `C-JB-04`'s boolean in 10c). The full finding, with the specific configuration
// points a variable-bin-count scene would need, is written to `backend/buildLog2.md`'s 10h entry --
// this comment states the ruling, that entry states the reasoning. This guard is therefore
// permanent, not provisional: do NOT remove it without a fresh owner ruling superseding this one.
//
// THE BIN COUNT IS READ FROM THE PAYLOAD BY NAME -- `number_of_groups` or `recipient_count` -- the
// same by-name precedent `line-position-logic.ts` sets for `interval_max`/`target_position`.
// CONSUMED STRUCTURALLY, AND THEREFORE EXCLUDED FROM `payloadValues`, for the identical reason
// `target_position` is excluded there: the bin count is already visible ON SCREEN as the number of
// rendered slots, so printing it again as a redundant numeral would be noise, not information (and
// unlike a true given, it is never itself part of the answer here, so this exclusion is not an
// answer-leak guard the way `target_position`'s is -- it is purely a "don't render it twice" one).
//
// NO CLIENT-SIDE VALIDATION AT ALL (work order, `partition-allocation` section, verbatim: "No
// validation that groups are equal, that a partition is exhaustive, or that a product is right. The
// client submits; the server evaluates."). This file computes nothing about whether the bins the
// child fills are correct, equal, or sum to anything -- it only classifies the wire shape and
// supplies the bin count. `c-partition-allocation-no-client-validation.test.ts` holds that line.
//
// All `prompt_payload` / `valid_action_space` access goes through
// `Object.prototype.hasOwnProperty.call(...)` / `Object.keys(...)`, never bare property access:
// both objects originate on the wire, and a key named `constructor`, `toString` or `__proto__`
// resolves to an inherited `Object.prototype` member under bare access.

import type { CNextTaskResponse } from '@/src/api/generated/openapi-types';
import { bindFieldKind } from '@/src/features/c-session/archetypes/field-kinds';
import { labelForPayloadKey } from '@/src/features/c-session/archetypes/payload-value-labels';

/** The `list[int]`-bound `valid_action_space` key names this scene recognises. See the header's
 *  "THE COLLECTION KEY IS READ BY NAME" paragraph. */
const COLLECTION_KEY_VOCABULARY = ['groups', 'allocations'] as const;

/** The `prompt_payload` key names that carry the bin count. See the header's "THE BIN COUNT IS READ
 *  FROM THE PAYLOAD BY NAME" paragraph. */
const BIN_COUNT_KEY_VOCABULARY = ['number_of_groups', 'recipient_count'] as const;

// A CORRUPTION-SAFETY CEILING on how many bins will be rendered, not a considered judgement about
// how many a child can handle -- literal, never derived from anything, mirroring `MAX_FIELDS` /
// `MAX_POOL_OBJECTS` / `MAX_INTERVAL_MAX` doctrine. The real observed maximum is 5 (C-EG-01 L5,
// C-SF-01 L5); 12 is comfortably above that while still catching a materially corrupted payload
// before it asks `ValueTokenRow` to render an unbounded row of slots.
const MAX_BINS = 12;

export type PartitionAllocationPayloadValue = {
  key: string;
  label: string;
  value: number;
};

export type PartitionAllocationSpec = {
  promptText: string;
  /** The `list[int]` action key -- where the child's filled bins are submitted. */
  binsKey: string;
  /** The number of entry slots to render. Always a positive integer, at most `MAX_BINS`. */
  binCount: number;
  /** Every `prompt_payload` key EXCEPT the bin-count key, in the wire's own key order, labelled for
   *  display. See the header's "CONSUMED STRUCTURALLY" paragraph for why the bin-count key itself is
   *  excluded. */
  payloadValues: readonly PartitionAllocationPayloadValue[];
  interactiveAssets: Record<string, unknown>;
};

/**
 * Resolve one task's `partition-allocation` rendering spec, or `null` if resolution cannot proceed.
 * `null` here is what drives `FailClosedFrame` in the surface -- never a guessed rendering, never a
 * partial one.
 *
 * Fails closed for: `prompt_text` absent or empty; `prompt_payload` absent, not an object, empty, or
 * containing any value that is not a finite number; no `BIN_COUNT_KEY_VOCABULARY` key present, or
 * more than one; the bin-count value not a positive integer, or exceeding `MAX_BINS`;
 * `valid_action_space` declaring no key; a declared type this codebase does not bind
 * (field-kinds.ts); a count of `ordered-integer-collection` keys other than exactly one; that key's
 * name outside `COLLECTION_KEY_VOCABULARY` (see the header); any `integer-field` key present
 * alongside it (the variable-bin-count shape -- see the header's "FIXED/VARIABLE DISCRIMINANT"
 * paragraph); any other declared kind at all (this scene has nowhere to put one);
 * `task.blanks` not exactly `null`.
 */
export function resolvePartitionAllocationSpec(task: CNextTaskResponse): PartitionAllocationSpec | null {
  if (typeof task.prompt_text !== 'string' || task.prompt_text.length === 0) return null;
  if (task.blanks !== null) return null;

  const promptPayload = task.prompt_payload;
  if (typeof promptPayload !== 'object' || promptPayload === null) return null;

  const payloadKeys = Object.keys(promptPayload);
  if (payloadKeys.length === 0) return null;

  let binCountKey: string | null = null;
  let binCount: number | null = null;
  const payloadValues: PartitionAllocationPayloadValue[] = [];

  for (const key of payloadKeys) {
    const value = (promptPayload as Record<string, unknown>)[key];
    if (typeof value !== 'number' || !Number.isFinite(value)) return null;

    if ((BIN_COUNT_KEY_VOCABULARY as readonly string[]).includes(key)) {
      if (binCountKey !== null) return null;
      if (!Number.isInteger(value) || value <= 0 || value > MAX_BINS) return null;
      binCountKey = key;
      binCount = value;
      continue;
    }

    payloadValues.push({ key, label: labelForPayloadKey(key), value });
  }

  if (binCountKey === null || binCount === null) return null;

  const validActionSpace = task.valid_action_space;
  const actionKeys = Object.keys(validActionSpace);
  if (actionKeys.length === 0) return null;

  let binsKey: string | null = null;

  for (const key of actionKeys) {
    const binding = bindFieldKind(validActionSpace[key]);
    if (binding === null) return null;

    if (binding.kind === 'ordered-integer-collection') {
      if (!(COLLECTION_KEY_VOCABULARY as readonly string[]).includes(key)) return null;
      if (binsKey !== null) return null;
      binsKey = key;
      continue;
    }

    // Any other bound kind -- including `integer-field`, the variable-bin-count shape (C-SF-02) --
    // refuses the whole resolution. See the header's "FIXED/VARIABLE DISCRIMINANT" paragraph.
    return null;
  }

  if (binsKey === null) return null;

  return {
    promptText: task.prompt_text,
    binsKey,
    binCount,
    payloadValues,
    interactiveAssets: task.interactive_assets,
  };
}
