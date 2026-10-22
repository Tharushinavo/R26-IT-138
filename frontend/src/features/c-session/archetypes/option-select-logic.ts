// Pure resolution logic for the `option-select` archetype (10d, extended 10e-0). No React/React
// Native import in this file -- the surface (option-select-surface.tsx) is a thin layer over this,
// mirroring `value-report-logic.ts`'s and `line-traversal-logic.ts`'s own split.
//
// `option-select`'s real registry rows split into two genuinely different option sources:
//   - a pipe-string `valid_action_space` value (`exact-choice-control`, field-kinds.ts) whose own
//     parsed alternatives ARE the options -- e.g. `left|right|equal`, `<|>|=` (10d, unchanged here);
//   - an `int`-typed key (`integer-field`) whose options are a `prompt_payload`-borne numeral array
//     (`numeral_options`), and whose submitted value is one of those numbers (10e-0, this batch).
//
// 10d refused the second path outright: the payload number it would have needed to display (the
// task's own quantity) IS one of the numbers in `numeral_options`, i.e. the correct answer, and the
// only rendering this resolver knew how to produce for a payload number was a numeral token --
// which would have put the answer on screen. 10e-0 unblocks this by resolving the quantity into its
// own field (`quantity`, on the `'numeral-options'` variant below) and NEVER placing it anywhere a
// numeral-rendering-based type (`OptionSelectPayloadValue`) could carry it. This is a stronger
// guarantee than a runtime check: the two variants below are structurally incapable of confusing a
// quantity for a payload token, because only the `'choice'` variant HAS a `payloadValues` field at
// all.
//
// STILL UNRESOLVED, ESCALATED, NOT DECIDED HERE (10e-0 build-log entry has the full finding): (1)
// whether a flat, ungrouped, wrapped display of a large quantity (up to 66 for one real template)
// honestly represents that quantity at all -- distinct from, but related to, (2) whether it should
// be grouped (base-ten, subitizing blocks, or similar) at all, which is a representation choice this
// codebase has repeatedly ruled is scientific, not a builder's or a layout question. Both templates
// on this path ship this batch regardless, per an explicit ruling that a magnitude-only structural
// bound cannot cleanly separate them anyway (their real quantity ranges overlap: one template's low
// levels sit inside the other's full range) -- see MAX_QUANTITY's own comment for why the bound
// below is corruption-safety only, never a considered answer to either open question.
//
// STRUCTURAL, NOT BY-NAME, QUANTITY RESOLUTION. `numeral_options` is still read BY NAME -- that was
// already sanctioned in 10d, for the same reason `line-traversal-logic.ts` reads `start` by name:
// it is the wire's own vocabulary for this scene's option source, not a template-id catalogue. The
// QUANTITY key is different: the two real templates on this path name it differently
// (`target_representation_value`, `set_size`), and a two-name lookup table would be exactly the
// growing template-vocabulary catalogue the two-layer rule forbids -- closer to that forbidden
// shape than `start` ever was, since `start` only ever needed one name. So the quantity is resolved
// STRUCTURALLY instead: `prompt_payload` on this path is required to carry EXACTLY two keys, and
// the quantity is whichever one is not `numeral_options`. A third real template naming its quantity
// key anything at all resolves here unchanged.
//
// All `prompt_payload` / `valid_action_space` access goes through
// `Object.prototype.hasOwnProperty.call(...)` / `Object.keys(...)`, never bare property access:
// both objects originate on the wire, and a key named `constructor`, `toString` or `__proto__`
// resolves to an inherited `Object.prototype` member under bare access.
//
// No template id appears anywhere in this file's executable code -- only in comments, as before.

import type { CNextTaskResponse } from '@/src/api/generated/openapi-types';
import { bindFieldKind, type FieldKindBinding } from '@/src/features/c-session/archetypes/field-kinds';
import { labelForPayloadKey } from '@/src/features/c-session/archetypes/payload-value-labels';

/** The `prompt_payload` key this scene's option array is read by name from. See the header. */
const NUMERAL_OPTIONS_KEY = 'numeral_options';

// A LAYOUT bound on how many entries `numeral_options` may declare, not a catalogue constraint --
// carried over from 10d's own (never-applied, since the path was refused) reasoning: the real
// observed maximum is 5 (one real template, its hardest difficulty level), and 10 is double that,
// comfortably wide enough to never fire against real data while still catching a materially
// corrupted or hostile array before it is ever handed to a rendering primitive.
const MAX_NUMERAL_OPTIONS = 10;

// A CORRUPTION-SAFETY CEILING on the quantity itself, not a considered judgement about how many
// objects a child can count -- deliberately set (100) above every real quantity either template on
// this path produces (66, one real template's hardest difficulty level) so that it never fires
// against real data at any difficulty level of either template. A future reader must not mistake
// this for an answer to the open question this batch escalates (whether a flat display of dozens of
// objects is a valid instrument at all) -- it is not one, and was chosen without reference to it.
// Numerically mirrored, independently, by `object-quantity-display.tsx`'s own `RENDER_CAP` -- see
// that file's header for why that is a second, defense-in-depth line, not the same check reused.
const MAX_QUANTITY = 100;

export type OptionSelectExtraField = {
  key: string;
  binding: FieldKindBinding;
};

export type OptionSelectPayloadValue = {
  key: string;
  label: string;
  value: number;
};

/**
 * The pipe-string option source (10d, unchanged): the options are the declared type's own parsed
 * alternatives, and every `prompt_payload` value is a given operand, rendered as a read-only
 * numeral token -- safe here because none of these payload values are ever the answer themselves
 * (unlike the `'numeral-options'` variant below).
 */
export type OptionSelectChoiceSpec = {
  kind: 'choice';
  promptText: string;
  payloadValues: readonly OptionSelectPayloadValue[];
  scoreKey: string;
  alternatives: readonly string[];
  extraFields: readonly OptionSelectExtraField[];
  interactiveAssets: Record<string, unknown>;
};

/**
 * The numeral-options source (10e-0): the options are a payload-borne numeral array, and the
 * quantity is carried in its OWN field, deliberately never a `PayloadValue` -- there is no
 * `payloadValues` field on this variant at all, which is what makes "the quantity can never be
 * rendered as a numeral token" a fact about the TYPE, not merely about what the surface currently
 * chooses to do with it.
 */
export type OptionSelectNumeralOptionsSpec = {
  kind: 'numeral-options';
  promptText: string;
  scoreKey: string;
  numeralOptions: readonly number[];
  /** The quantity to render as a count of objects -- never as a numeral, anywhere. */
  quantity: number;
  extraFields: readonly OptionSelectExtraField[];
  interactiveAssets: Record<string, unknown>;
};

export type OptionSelectSpec = OptionSelectChoiceSpec | OptionSelectNumeralOptionsSpec;

/**
 * Resolve one task's `option-select` rendering spec, or `null` if resolution cannot proceed. `null`
 * here is what drives `FailClosedFrame` in the surface -- never a guessed rendering, never a
 * partial one.
 *
 * Shared, path-independent guards: `prompt_text` absent or empty; `task.blanks` not exactly `null`;
 * `valid_action_space` declaring no key; a declared type this codebase does not bind
 * (field-kinds.ts); a declared-type count of (`exact-choice-control` + `integer-field`) keys other
 * than exactly one (this is the scene's single answer key, whichever kind it turns out to be); any
 * other declared key whose bound kind is not `boolean-control`; `prompt_payload` absent, not an
 * object, or empty.
 *
 * Pipe-string-path-only guards (10d, unchanged): any payload value that is not a finite number.
 *
 * Numeral-options-path-only guards (10e-0): `prompt_payload` declaring a key count other than
 * exactly 2; no `numeral_options` key present; `numeral_options` not an array; `numeral_options`
 * with fewer than 2 or more than `MAX_NUMERAL_OPTIONS` entries; any `numeral_options` element that
 * is not a finite number; the remaining (quantity) key's value not a finite number, not an integer,
 * negative, or above `MAX_QUANTITY`.
 */
export function resolveOptionSelectSpec(task: CNextTaskResponse): OptionSelectSpec | null {
  if (typeof task.prompt_text !== 'string' || task.prompt_text.length === 0) return null;
  if (task.blanks !== null) return null;

  const validActionSpace = task.valid_action_space;
  const keys = Object.keys(validActionSpace);
  if (keys.length === 0) return null;

  let scoreKey: string | null = null;
  let scoreBindingKind: 'exact-choice-control' | 'integer-field' | null = null;
  let alternatives: readonly string[] | null = null;
  const extraFields: OptionSelectExtraField[] = [];

  for (const key of keys) {
    const declaredType = validActionSpace[key];
    const binding = bindFieldKind(declaredType);
    if (binding === null) return null;

    if (binding.kind === 'exact-choice-control' || binding.kind === 'integer-field') {
      if (scoreKey !== null) return null;
      scoreKey = key;
      scoreBindingKind = binding.kind;
      if (binding.kind === 'exact-choice-control') alternatives = binding.alternatives;
      continue;
    }

    if (binding.kind !== 'boolean-control') return null;
    extraFields.push({ key, binding });
  }

  if (scoreKey === null || scoreBindingKind === null) return null;

  const promptPayload = task.prompt_payload;
  if (typeof promptPayload !== 'object' || promptPayload === null) return null;
  const payloadKeys = Object.keys(promptPayload);
  if (payloadKeys.length === 0) return null;

  if (scoreBindingKind === 'exact-choice-control') {
    const payloadValues: OptionSelectPayloadValue[] = [];
    for (const key of payloadKeys) {
      const value = (promptPayload as Record<string, unknown>)[key];
      if (typeof value !== 'number' || !Number.isFinite(value)) return null;
      payloadValues.push({ key, label: labelForPayloadKey(key), value });
    }

    return {
      kind: 'choice',
      promptText: task.prompt_text,
      payloadValues,
      scoreKey,
      alternatives: alternatives!,
      extraFields,
      interactiveAssets: task.interactive_assets,
    };
  }

  // The numeral-options path (10e-0). Exactly two payload keys: numeral_options, and the quantity,
  // resolved structurally as "whichever key that is not" (see header).
  if (payloadKeys.length !== 2) return null;
  if (!Object.prototype.hasOwnProperty.call(promptPayload, NUMERAL_OPTIONS_KEY)) return null;

  const numeralOptionsRaw = (promptPayload as Record<string, unknown>)[NUMERAL_OPTIONS_KEY];
  if (!Array.isArray(numeralOptionsRaw)) return null;
  if (numeralOptionsRaw.length < 2 || numeralOptionsRaw.length > MAX_NUMERAL_OPTIONS) return null;

  const numeralOptions: number[] = [];
  for (const element of numeralOptionsRaw) {
    if (typeof element !== 'number' || !Number.isFinite(element)) return null;
    numeralOptions.push(element);
  }

  const quantityKey = payloadKeys.find((key) => key !== NUMERAL_OPTIONS_KEY)!;
  const quantityRaw = (promptPayload as Record<string, unknown>)[quantityKey];
  if (typeof quantityRaw !== 'number' || !Number.isFinite(quantityRaw)) return null;
  if (!Number.isInteger(quantityRaw)) return null;
  if (quantityRaw < 0 || quantityRaw > MAX_QUANTITY) return null;

  return {
    kind: 'numeral-options',
    promptText: task.prompt_text,
    scoreKey,
    numeralOptions,
    quantity: quantityRaw,
    extraFields,
    interactiveAssets: task.interactive_assets,
  };
}
