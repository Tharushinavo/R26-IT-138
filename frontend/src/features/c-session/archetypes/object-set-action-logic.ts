// Pure resolution logic for the `object-set-action` archetype (10e, C-CC-01/C-CC-02). No React/
// React Native import in this file -- the surface (object-set-action-surface.tsx) is a thin layer
// over this, mirroring `value-report-logic.ts`'s / `line-traversal-logic.ts`'s / `option-select-
// logic.ts`'s own split.
//
// THE COMPOSITE PROOF THIS SUB-PHASE OWES (master work order §4 / §3): C-CC-01 declares BOTH an
// `id-set-collection` AND an `integer-field`; C-CC-02 declares ONLY the `id-set-collection`. One
// archetype covers both because the difference is a fact about which declared TYPES are present in
// `valid_action_space`, not a per-template branch -- classified here exactly as every other
// archetype in this codebase classifies, by declared type alone. `totalKey` on the resolved spec is
// `string | null`: non-null for C-CC-01, null for C-CC-02, and that presence/absence is what the
// surface switches on, never `task.game_task_template_id`.
//
// STRUCTURAL, NOT BY-NAME, ID-SET RESOLUTION. C-CC-01 carries its ids across TWO payload keys
// (`valid_object_ids`, `distractor_object_ids`); C-CC-02 carries them in ONE (`available_object_ids`).
// A name table keyed on three different names would be exactly the growing template-vocabulary
// catalogue the two-layer rule forbids. Instead: every `prompt_payload` key whose value is a
// `string[]` is concatenated, in wire key order, into one flat `objectIds` list -- structurally
// identical treatment regardless of how many such keys exist or what they are called. This is also
// why C-CC-01's `valid_object_ids` and `distractor_object_ids` are rendered as ONE undifferentiated
// pool: this resolver does not know, and must not know, which key a given id came from once
// concatenated -- see the surface's own header for why that lack of distinction is deliberate, not
// an oversight (master work order §3: "No client-side distinction between valid and distractor ids
// beyond rendering them").
//
// THE OWNER RULING THIS BATCH IMPLEMENTS (2026-08-26, this session): `submitted_total` (C-CC-01) is
// NEVER auto-derived from `objectIds.length` or from however many the child selected. Counting the
// selected set IS the assessed skill for this template, and unlike `line-traversal-logic.ts`'s
// derived `final_position` (where the landed-on number was already visible on the number line),
// nothing on this screen already shows the count -- auto-filling it would make the client perform
// the very act being measured, and would additionally guarantee
// `len(selected_object_ids) == submitted_total`, one of the server's own correctness conditions.
// This resolver exposes `totalKey` purely as a field to render a `DigitKeypad` against; it computes
// nothing from the selection.
//
// All `prompt_payload` / `valid_action_space` access goes through
// `Object.prototype.hasOwnProperty.call(...)` / `Object.keys(...)`, never bare property access:
// both objects originate on the wire, and a key named `constructor`, `toString` or `__proto__`
// resolves to an inherited `Object.prototype` member under bare access.
//
// No template id appears anywhere in this file's executable code -- only in comments, as before
// (c-object-set-action-no-template-branch.test.ts proves this by source scan).

import type { CNextTaskResponse } from '@/src/api/generated/openapi-types';
import { bindFieldKind } from '@/src/features/c-session/archetypes/field-kinds';
import { labelForPayloadKey } from '@/src/features/c-session/archetypes/payload-value-labels';

// A CORRUPTION-SAFETY CEILING on the pool, not a considered judgement about how many objects a
// child can select from -- literal, never derived from any payload value, mirroring `line-traversal
// -logic.ts`'s `MAX_LINE_FORWARD_STEPS` / `option-select-logic.ts`'s `MAX_QUANTITY` doctrine.
// Measured real maximum across both templates at difficulty 5 is C-CC-01's 18 valid ids (plus up to
// 4 distractors, 22 total) and C-CC-02's ~20 available ids; 60 sits comfortably above either without
// approaching a magnitude a future difficulty ramp could plausibly reach by accident.
const MAX_POOL_OBJECTS = 60;

// A CORRUPTION-SAFETY CEILING on the target quantity (C-CC-02's `target_n`), same doctrine as
// above. Measured real maximum at difficulty 5 is well under 20; 100 is the same numeric ceiling
// `option-select-logic.ts`'s own `MAX_QUANTITY` uses, for the same "never a considered answer about
// counting ability" reason stated there.
const MAX_TARGET_VALUE = 100;

export type ObjectSetActionTargetValue = {
  key: string;
  label: string;
  value: number;
};

/**
 * `totalKey` is `string | null` -- present for C-CC-01 (a companion `integer-field` alongside the
 * id-set), absent for C-CC-02 (the id-set is the only declared key). This is the type-level fact
 * that makes "does this template also need a typed total" a property the surface can switch on,
 * never a runtime guess and never a per-template branch.
 */
export type ObjectSetActionSpec = {
  promptText: string;
  objectIds: readonly string[];
  idSetKey: string;
  totalKey: string | null;
  targetValue: ObjectSetActionTargetValue | null;
  interactiveAssets: Record<string, unknown>;
};

/**
 * Resolve one task's `object-set-action` rendering spec, or `null` if resolution cannot proceed.
 * `null` here is what drives `FailClosedFrame` in the surface -- never a guessed rendering, never a
 * partial one.
 *
 * Fail-closed guards, each independently necessary (c-object-set-action-fail-closed.test.ts proves
 * every one with a negative control against an otherwise-valid baseline):
 *   - `prompt_text` absent or empty string;
 *   - `task.blanks` not exactly `null`;
 *   - `prompt_payload` absent, not an object, or `null`;
 *   - zero `string[]`-valued `prompt_payload` keys (no id source at all);
 *   - any id-array element that is not a non-empty string;
 *   - a duplicate id across the concatenated pool (would collide as both a React key and a
 *     selection-set member);
 *   - the concatenated pool exceeding `MAX_POOL_OBJECTS`;
 *   - more than one non-array `prompt_payload` key (a second, unclassified scalar this resolver has
 *     no scene for);
 *   - the one allowed non-array key present but not a finite, non-negative integer, or exceeding
 *     `MAX_TARGET_VALUE`;
 *   - `valid_action_space` declaring no key, or any key whose declared type this codebase does not
 *     bind (field-kinds.ts);
 *   - a declared-type count of `id-set-collection` other than exactly one;
 *   - a declared-type count of `integer-field` other than zero or exactly one.
 */
export function resolveObjectSetActionSpec(task: CNextTaskResponse): ObjectSetActionSpec | null {
  if (typeof task.prompt_text !== 'string' || task.prompt_text.length === 0) return null;
  if (task.blanks !== null) return null;

  const validActionSpace = task.valid_action_space;
  const actionKeys = Object.keys(validActionSpace);
  if (actionKeys.length === 0) return null;

  let idSetKey: string | null = null;
  let totalKey: string | null = null;

  for (const key of actionKeys) {
    const declaredType = validActionSpace[key];
    const binding = bindFieldKind(declaredType);
    if (binding === null) return null;

    if (binding.kind === 'id-set-collection') {
      if (idSetKey !== null) return null;
      idSetKey = key;
      continue;
    }

    if (binding.kind === 'integer-field') {
      if (totalKey !== null) return null;
      totalKey = key;
      continue;
    }

    return null;
  }

  if (idSetKey === null) return null;

  const promptPayload = task.prompt_payload;
  if (typeof promptPayload !== 'object' || promptPayload === null) return null;
  const payloadKeys = Object.keys(promptPayload);

  const objectIds: string[] = [];
  const seenIds = new Set<string>();
  let nonArrayKey: string | null = null;

  for (const key of payloadKeys) {
    const value = (promptPayload as Record<string, unknown>)[key];

    if (Array.isArray(value)) {
      for (const element of value) {
        if (typeof element !== 'string' || element.length === 0) return null;
        if (seenIds.has(element)) return null;
        seenIds.add(element);
        objectIds.push(element);
      }
      continue;
    }

    if (nonArrayKey !== null) return null;
    nonArrayKey = key;
  }

  if (objectIds.length === 0) return null;
  if (objectIds.length > MAX_POOL_OBJECTS) return null;

  let targetValue: ObjectSetActionTargetValue | null = null;
  if (nonArrayKey !== null) {
    const raw = (promptPayload as Record<string, unknown>)[nonArrayKey];
    if (typeof raw !== 'number' || !Number.isFinite(raw)) return null;
    if (!Number.isInteger(raw)) return null;
    if (raw < 0 || raw > MAX_TARGET_VALUE) return null;
    targetValue = { key: nonArrayKey, label: labelForPayloadKey(nonArrayKey), value: raw };
  }

  return {
    promptText: task.prompt_text,
    objectIds,
    idSetKey,
    totalKey,
    targetValue,
    interactiveAssets: task.interactive_assets,
  };
}
