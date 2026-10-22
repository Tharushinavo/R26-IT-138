// The declared-type -> field-kind binding (Component C Phase 10 Sub-Phase Sequence v1.1 §3.0,
// §3.2). This is the second half of the two-layer rule: an archetype declares a scene, and the
// fields within it are derived one-per-key from `valid_action_space`, by declared type alone.
// This module owns that second layer and nothing else -- it has no notion of archetypes, scenes,
// or template ids.
//
// Total over the vocabulary `action_payload_validation.py` recognises:
//
//   | Declared type | Field kind                 |
//   | -------------- | --------------------------- |
//   | int             | integer-field                |
//   | number          | numeric-field                 |
//   | bool            | boolean-control                |
//   | list[int]       | ordered-integer-collection      |
//   | list[str]       | id-set-collection                |
//   | pipe-string     | exact-choice-control (parsed)      |
//
// An unbound declared type -- anything not in this table and not a valid pipe-string -- fails
// closed: `bindFieldKind` returns `null` and there is no default fallthrough. Per the backend
// supervisor's standing ruling (agent1.md §2.2), a type string outside this vocabulary is a
// STOP, not something this module silently learns to render.

export type FieldKindBinding =
  | { kind: 'integer-field' }
  | { kind: 'numeric-field' }
  | { kind: 'boolean-control' }
  | { kind: 'ordered-integer-collection' }
  | { kind: 'id-set-collection' }
  | { kind: 'exact-choice-control'; alternatives: readonly string[] };

const FIXED_TYPE_TABLE: Record<string, FieldKindBinding> = {
  int: { kind: 'integer-field' },
  number: { kind: 'numeric-field' },
  bool: { kind: 'boolean-control' },
  'list[int]': { kind: 'ordered-integer-collection' },
  'list[str]': { kind: 'id-set-collection' },
};

// A pipe-string requires at least two non-empty, pipe-free alternatives -- "|" alone, a leading
// or trailing empty alternative, or a single value with no "|" at all is not a valid choice set.
// This parser is intentionally separate from (and stricter in spirit than) the classifier regex
// in c-template-registry-freeze.test.ts's `PIPE_STRING`, which 10.0a's own build-log entry flags
// as latent-but-not-live: that regex would still accept a hybrid shape like "list[int]|foo". This
// parser is what actually acts on the alternatives (building the exact-choice set an encoded
// value is checked against), so it is held to the standard that matters for encoding, not just
// classification. None of the 30 real templates produce a hybrid shape either way.
function parsePipeStringAlternatives(declaredType: string): readonly string[] | null {
  if (declaredType.length === 0) return null;
  const parts = declaredType.split('|');
  if (parts.length < 2) return null;
  if (parts.some((part) => part.length === 0)) return null;
  return parts;
}

/**
 * Bind one declared type string (as it appears in a `valid_action_space` value) to the field kind
 * that renders and validates it. Returns `null` for any type string outside the recognised
 * vocabulary -- never a default kind.
 *
 * Own-property lookup against the fixed table: `declaredType` originates on the wire, and a
 * drifted or hostile value like "constructor" or "toString" must not resolve to an inherited
 * `Object.prototype` member.
 */
export function bindFieldKind(declaredType: string): FieldKindBinding | null {
  if (Object.prototype.hasOwnProperty.call(FIXED_TYPE_TABLE, declaredType)) {
    return FIXED_TYPE_TABLE[declaredType];
  }
  const alternatives = parsePipeStringAlternatives(declaredType);
  if (alternatives !== null) {
    return { kind: 'exact-choice-control', alternatives };
  }
  return null;
}

/**
 * Does `value` satisfy the field kind `binding` describes? Used by `encodeActionPayload` to
 * reject a submission value before it is ever assembled into a payload.
 *
 * The boolean trap named in the work order: never coerce with `Number(value)` before checking --
 * `Number(true) === 1` and `Number.isInteger(1)` is `true`, so a check built on a coerced value
 * would silently admit a boolean where `int` or `number` is declared. Every numeric branch below
 * checks `typeof value === 'number'` on the raw value first, which is already `false` for a
 * boolean, so no coercion step exists anywhere in this function.
 */
export function isValidForKind(binding: FieldKindBinding, value: unknown): boolean {
  switch (binding.kind) {
    case 'integer-field':
      return typeof value === 'number' && Number.isInteger(value);
    case 'numeric-field':
      return typeof value === 'number' && Number.isFinite(value);
    case 'boolean-control':
      return typeof value === 'boolean';
    case 'ordered-integer-collection':
      return Array.isArray(value) && value.every((element) => typeof element === 'number' && Number.isInteger(element));
    case 'id-set-collection':
      return Array.isArray(value) && value.every((element) => typeof element === 'string');
    case 'exact-choice-control':
      return typeof value === 'string' && binding.alternatives.includes(value);
    default: {
      const exhaustive: never = binding;
      return exhaustive;
    }
  }
}
