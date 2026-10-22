// `encodeActionPayload` -- the single most load-bearing piece of Phase 10 (10.0-work-order.md
// §3.1). All thirty templates submit through this function, and the server rejects any payload
// whose key set is not exactly equal to `valid_action_space`'s
// (action_payload_validation.py:88). A defect here is rejected for every task, not some of them.
//
// Driven by the wire's `valid_action_space` and by nothing else -- never a per-template key table
// in the client, which would be a second copy of the catalogue, free to drift from the first.

import { bindFieldKind, isValidForKind } from '@/src/features/c-session/archetypes/field-kinds';

/**
 * Encode one submission. Iterates `validActionSpace`'s own declared keys, in order, and for each:
 *   1. binds its declared type to a field kind (an unbound type fails the whole encode, closed);
 *   2. requires `values` to own that key (own-property check -- `values` may originate from
 *      caller-controlled state, and a key of "constructor" must not resolve to
 *      `Object.prototype.constructor`);
 *   3. requires the value to satisfy the bound kind (rejects a boolean where `int` or `number` is
 *      declared, rejects a wrongly-typed list element, rejects a value outside a pipe-string's
 *      parsed alternatives).
 *
 * On ANY failure, returns `null` -- never a partially built payload. The returned object's key
 * set is exactly `Object.keys(validActionSpace)` by construction: this function never reads or
 * emits a key `validActionSpace` does not declare, so it can neither under- nor over-submit.
 */
export function encodeActionPayload(
  validActionSpace: Record<string, string>,
  values: Record<string, unknown>,
): Record<string, unknown> | null {
  const result: Record<string, unknown> = {};

  for (const [key, declaredType] of Object.entries(validActionSpace)) {
    const binding = bindFieldKind(declaredType);
    if (binding === null) return null;

    if (!Object.prototype.hasOwnProperty.call(values, key)) return null;
    const value = values[key];

    if (!isValidForKind(binding, value)) return null;

    result[key] = value;
  }

  return result;
}

/**
 * Does `payload`'s key set exactly equal `validActionSpace`'s? Used by the table-coverage test's
 * negative controls: take a correctly encoded payload, mutate it (add an extra key, delete a
 * required one) in memory, and assert this predicate now rejects it -- proving the exact-key-set
 * property is actually checked rather than merely assumed from `encodeActionPayload`'s
 * construction.
 */
export function keySetEquals(
  payload: Record<string, unknown>,
  validActionSpace: Record<string, string>,
): boolean {
  const payloadKeys = Object.keys(payload).sort();
  const spaceKeys = Object.keys(validActionSpace).sort();
  if (payloadKeys.length !== spaceKeys.length) return false;
  return payloadKeys.every((key, index) => key === spaceKeys[index]);
}
