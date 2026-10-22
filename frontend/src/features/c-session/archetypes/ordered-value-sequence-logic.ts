// Pure resolution logic for the `ordered-value-sequence` archetype (10a). No React/React Native
// import in this file -- the surface (ordered-value-sequence-surface.tsx) is a thin layer over
// this, mirroring c-session-logic.ts's own split from c-session-screen.tsx.
//
// Scene detection reads the single `list[int]`-typed key's NAME in `valid_action_space`:
// `entered_values` -> entry scene (continue a sequence), `arranged_values` -> arrangement scene
// (order a set of cards). Both names are fixed in the Phase 10 Sub-Phase Sequence's own parameter
// table -- hardcoding these two literals is reading the wire's vocabulary, not building a second
// template-id catalogue (the two-layer rule forbids the latter, not the former).
//
// Per the two-layer rule, this function does not assume `valid_action_space` declares exactly one
// key: it iterates the full declared key set, classifies the one `list[int]` key that carries the
// scene, and renders any OTHER declared key generically via the existing field-kind layer. No NP
// template declares an extra key today; this is "build as if they might not" (10a work order),
// not speculative engineering -- the loop already has to exist to find the scene key, and handling
// an extra key inside it costs nothing this batch doesn't already pay for.
//
// All `prompt_payload` / `valid_action_space` access goes through
// `Object.prototype.hasOwnProperty.call(...)`, never bare property access: both objects originate
// on the wire, and a key named `constructor`, `toString` or `__proto__` resolves to an inherited
// `Object.prototype` member under bare access.

import type { CNextTaskResponse } from '@/src/api/generated/openapi-types';
import { bindFieldKind, type FieldKindBinding } from '@/src/features/c-session/archetypes/field-kinds';

// Layout robustness bound, not a catalogue constraint: the generator's real maximum across every
// difficulty level of all four NP templates is 7 (`shown_length` 5 + `blanks` 2, NP-01/02/03) or 5
// (NP-04, `count_a_by_level` tops out at 5). 20 is comfortably above any real generator output
// while still catching a materially corrupted payload before it reaches a token row.
const MAX_SEQUENCE_LENGTH = 20;

// Same rationale, applied to `blanks`: the real maximum is 2 (difficulty 3-5). 10 is a robustness
// ceiling, not an observed value.
const MAX_BLANKS = 10;

export type ExtraField = {
  key: string;
  binding: FieldKindBinding;
};

export type OrderedValueSequenceEntrySpec = {
  scene: 'entry';
  promptText: string;
  shownSequence: readonly number[];
  // Present only for C-NP-03. Carried for completeness (the generic-key path this file already
  // needs); not separately rendered -- `promptText` already communicates the pattern to the child.
  step: number | null;
  blanks: number;
  entryKey: 'entered_values';
  extraFields: readonly ExtraField[];
  interactiveAssets: Record<string, unknown>;
};

export type OrderedValueSequenceArrangeSpec = {
  scene: 'arrange';
  promptText: string;
  values: readonly number[];
  // Relayed, never interpreted. `promptText` is where the direction already reached the child
  // (backend-resolved by variant) -- this field exists so nothing is silently dropped from the
  // wire, not so the surface can render a visual ordering cue from it.
  direction: string;
  arrangeKey: 'arranged_values';
  extraFields: readonly ExtraField[];
  interactiveAssets: Record<string, unknown>;
};

export type OrderedValueSequenceSpec = OrderedValueSequenceEntrySpec | OrderedValueSequenceArrangeSpec;

function isBoundedIntegerArray(value: unknown): value is number[] {
  if (!Array.isArray(value)) return false;
  if (value.length === 0) return false;
  if (value.length > MAX_SEQUENCE_LENGTH) return false;
  return value.every((element) => typeof element === 'number' && Number.isInteger(element));
}

/**
 * Resolve one task's `ordered-value-sequence` rendering spec, or `null` if resolution cannot
 * proceed. `null` here is what drives `FailClosedFrame` in the surface -- never a guessed
 * rendering, never a partial one.
 *
 * Fails closed for: `prompt_text` absent or empty; `valid_action_space` declaring no key, an
 * unbound declared type, more than one `list[int]` key, a `list[int]` key under a name this
 * archetype does not recognise, a second collection-shaped key (`list[int]` or `list[str]`) beyond
 * the scene key; a required `prompt_payload` key absent, non-array, empty, over the layout bound,
 * or containing a non-integer element; `step` present but not an integer; `blanks` violating its
 * bound for the scene (not a positive integer <= 10 for the entry scene; not exactly `null` for the
 * arrangement scene).
 */
export function resolveOrderedValueSequenceSpec(task: CNextTaskResponse): OrderedValueSequenceSpec | null {
  if (typeof task.prompt_text !== 'string' || task.prompt_text.length === 0) return null;

  const validActionSpace = task.valid_action_space;
  const keys = Object.keys(validActionSpace);
  if (keys.length === 0) return null;

  let sceneKey: 'entered_values' | 'arranged_values' | null = null;
  const extraFields: ExtraField[] = [];

  for (const key of keys) {
    const declaredType = validActionSpace[key];
    const binding = bindFieldKind(declaredType);
    if (binding === null) return null;

    if (binding.kind === 'ordered-integer-collection') {
      if (key !== 'entered_values' && key !== 'arranged_values') return null;
      if (sceneKey !== null) return null;
      sceneKey = key;
      continue;
    }

    if (binding.kind === 'id-set-collection') return null;

    extraFields.push({ key, binding });
  }

  if (sceneKey === null) return null;

  const promptPayload = task.prompt_payload;
  const interactiveAssets = task.interactive_assets;

  if (sceneKey === 'entered_values') {
    if (!Object.prototype.hasOwnProperty.call(promptPayload, 'shown_sequence')) return null;
    const shownSequence = promptPayload.shown_sequence;
    if (!isBoundedIntegerArray(shownSequence)) return null;

    let step: number | null = null;
    if (Object.prototype.hasOwnProperty.call(promptPayload, 'step')) {
      const rawStep = promptPayload.step;
      if (typeof rawStep !== 'number' || !Number.isInteger(rawStep)) return null;
      step = rawStep;
    }

    const { blanks } = task;
    if (!Number.isInteger(blanks) || (blanks as number) <= 0 || (blanks as number) > MAX_BLANKS) return null;

    return {
      scene: 'entry',
      promptText: task.prompt_text,
      shownSequence,
      step,
      blanks: blanks as number,
      entryKey: sceneKey,
      extraFields,
      interactiveAssets,
    };
  }

  // sceneKey === 'arranged_values'
  if (!Object.prototype.hasOwnProperty.call(promptPayload, 'values')) return null;
  const values = promptPayload.values;
  if (!isBoundedIntegerArray(values)) return null;

  if (!Object.prototype.hasOwnProperty.call(promptPayload, 'direction')) return null;
  const direction = promptPayload.direction;
  if (typeof direction !== 'string' || direction.length === 0) return null;

  if (task.blanks !== null) return null;

  return {
    scene: 'arrange',
    promptText: task.prompt_text,
    values,
    direction,
    arrangeKey: sceneKey,
    extraFields,
    interactiveAssets,
  };
}
