// Pure resolution logic for the `value-report` archetype (10b). No React/React Native import in
// this file -- the surface (value-report-surface.tsx) is a thin layer over this, mirroring
// `ordered-value-sequence-logic.ts`'s own split.
//
// `value-report`'s scene is the simplest of the eight archetypes: exactly one `int`-typed key in
// `valid_action_space` is the answer field (`submitted_remainder`, `submitted_difference`,
// `submitted_total`, `submitted_sum`, `submitted_product`, `submitted_quotient` across the real
// registry -- six distinct names, one scene). Per the two-layer rule, this resolver never compares
// against any of those literal names: it classifies by declared TYPE (`integer-field`, via
// field-kinds.ts), not by key name, so a seventh int key name would resolve identically without a
// code change. Any other declared key beyond the one scene key is collected as a generic extra
// field the same way `ordered-value-sequence-logic.ts` does -- in this batch's real data that is
// always `exchange_performed: bool` (C-TC-04, C-JB-04) or nothing.
//
// `prompt_payload`'s numeric values ARE rendered -- a correction to this archetype's first draft,
// which assumed none of these eight `prompt_text` strings were deictic and left `prompt_payload`
// uninspected. They all are: "Take away the amount shown", "Add the two numbers", "Subtract the
// second number from the first", "Find the total for the equal groups shown", "Split the number in
// half" all point at a quantity the text itself never states, and `interactive_assets` is `{}` for
// every real exemplar across all eight templates -- there is no picture standing in for it either.
// Without rendering `prompt_payload`, the child has no way to know what number to work with at all.
//
// The rendering is generic, per the two-layer rule: every `prompt_payload` value is required to be
// a finite number (never a per-template key-name table -- `initial_count`/`removed_count`,
// `minuend`/`subtrahend`, `count_a`/`count_b`, `addend_a`/`addend_b`, `operand_a`/`operand_b`,
// `multiplicand`/`multiplier`, `dividend` all satisfy this with zero special-casing), and every key
// found is carried through, in the wire's own key order, for the surface to render as read-only
// tokens. A non-numeric `prompt_payload` value (e.g. a boolean discriminator) fails resolution
// closed rather than being silently dropped or coerced -- this archetype has no way to render
// anything other than a number.
//
// Bare numbers alone were tried first and found insufficient by hand-testing: two unlabeled tokens
// give no indication which is which or in what order to use them ("is it 4-2 or 2-4?"). Each
// `PayloadValue` therefore also carries a child-facing `label`, resolved per key by
// `payload-value-labels.ts` -- a lookup keyed by `prompt_payload` key name, not template id,
// kept in its own module so this file stays about resolving the SPEC, not about content wording.
//
// All `valid_action_space` access goes through `Object.prototype.hasOwnProperty.call(...)` /
// `Object.entries(...)`, never bare property access: the object originates on the wire, and a key
// named `constructor`, `toString` or `__proto__` resolves to an inherited `Object.prototype` member
// under bare access.

import type { CNextTaskResponse } from '@/src/api/generated/openapi-types';
import { bindFieldKind, type FieldKindBinding } from '@/src/features/c-session/archetypes/field-kinds';
import { labelForPayloadKey } from '@/src/features/c-session/archetypes/payload-value-labels';

export type ValueReportExtraField = {
  key: string;
  binding: FieldKindBinding;
};

export type PayloadValue = {
  key: string;
  label: string;
  value: number;
};

export type ValueReportSpec = {
  promptText: string;
  payloadValues: readonly PayloadValue[];
  scoreKey: string;
  extraFields: readonly ValueReportExtraField[];
  interactiveAssets: Record<string, unknown>;
};

/**
 * Resolve one task's `value-report` rendering spec, or `null` if resolution cannot proceed. `null`
 * here is what drives `FailClosedFrame` in the surface -- never a guessed rendering, never a
 * partial one.
 *
 * Fails closed for: `game_task_template_id === 'C-TC-02'` (an explicit, temporary refusal -- see
 * the check itself for the full reason); `prompt_text` absent or empty; `prompt_payload` absent,
 * not an object, empty, or containing any value that is not a finite number; `valid_action_space`
 * declaring no key; a declared type this codebase does not bind (field-kinds.ts); a declared-type
 * count of `integer-field` keys other than exactly one (zero, or two-or-more, both mean this is
 * not a single-answer `value-report` scene); any extra declared key whose bound kind is not
 * `boolean-control` (this batch's real data never produces one, but the resolver does not assume
 * that); `task.blanks` not exactly `null`.
 */
export function resolveValueReportSpec(task: CNextTaskResponse): ValueReportSpec | null {
  // C-TC-02 is excluded here, not merely absent from real data: registry.ts's ARCHETYPE_TABLE
  // already routed 'C-TC-02' -> 'value-report' before this batch existed, and this resolver is
  // otherwise purely type-based (never branches on template id) -- so without this explicit
  // refusal, C-TC-02 would silently resolve to a live, mounted surface despite never having been
  // built for. Its `directed` payload flag may require a signed answer at difficulty 5;
  // DigitKeypad has no minus key (10b-10h-master-work-order.md §2.1). Remove this line, and only
  // this line, the moment that question is answered -- it is a refusal, not a rule about
  // C-TC-02's shape, and every other check in this function stays template-id-blind.
  if (task.game_task_template_id === 'C-TC-02') return null;

  if (typeof task.prompt_text !== 'string' || task.prompt_text.length === 0) return null;

  const promptPayload = task.prompt_payload;
  if (typeof promptPayload !== 'object' || promptPayload === null) return null;

  const payloadKeys = Object.keys(promptPayload);
  if (payloadKeys.length === 0) return null;
  const payloadValues: PayloadValue[] = [];
  for (const key of payloadKeys) {
    const value = (promptPayload as Record<string, unknown>)[key];
    if (typeof value !== 'number' || !Number.isFinite(value)) return null;
    payloadValues.push({ key, label: labelForPayloadKey(key), value });
  }

  const validActionSpace = task.valid_action_space;
  const keys = Object.keys(validActionSpace);
  if (keys.length === 0) return null;

  let scoreKey: string | null = null;
  const extraFields: ValueReportExtraField[] = [];

  for (const key of keys) {
    const declaredType = validActionSpace[key];
    const binding = bindFieldKind(declaredType);
    if (binding === null) return null;

    if (binding.kind === 'integer-field') {
      if (scoreKey !== null) return null;
      scoreKey = key;
      continue;
    }

    if (binding.kind !== 'boolean-control') return null;
    extraFields.push({ key, binding });
  }

  if (scoreKey === null) return null;
  if (task.blanks !== null) return null;

  return {
    promptText: task.prompt_text,
    payloadValues,
    scoreKey,
    extraFields,
    interactiveAssets: task.interactive_assets,
  };
}
