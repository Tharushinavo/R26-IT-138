// The template -> archetype table (Component C Phase 10 Sub-Phase Sequence v1.1 §3.1), and
// `resolveArchetype`, the client-side resolver for it.
//
// This module maps template ids to archetype IDENTIFIERS only. The components those identifiers
// name are 10a...10h's work and do not exist yet -- `resolveArchetype` returning an identifier
// with no surface behind it is the correct end state of this batch, not a gap.
//
// Per the two-layer rule (sequence doc §3.0): an archetype declares a SCENE; the FIELDS are
// derived, one per key, from `valid_action_space`, by declared type (field-kinds.ts). No
// archetype here hardcodes a key count, a key name, or a field set -- the eight rows below are a
// scene classification, not a per-template shape table. The sequence doc's own §3.1 states this
// explicitly: "No archetype declares its own key set... It is documentation, not a constraint the
// code carries." Consequently `resolveArchetype` cannot check "does this archetype's expected
// shape match" against `valid_action_space`, because there is no fixed shape to check against by
// design. The one thing it CAN and does check against `valid_action_space` is that every declared
// type in it is bound by the field-kind layer -- an unbound type fails the whole resolution
// closed, per §5.3.
//
// There is no family notion in this table, derived or otherwise. `game_family_id` on the wire is
// catalogue-sourced (`C-GF-01`..`C-GF-08`); the template-id prefix (`CC`, `NP`, `MCL`, ...) joins
// with nothing, per the backend supervisor's explicit finding (agent1.md §2.3). Do not add one.

import { bindFieldKind } from '@/src/features/c-session/archetypes/field-kinds';

export type ArchetypeId =
  | 'value-report'
  | 'option-select'
  | 'object-set-action'
  | 'ordered-value-sequence'
  | 'named-integer-fields'
  | 'partition-allocation'
  | 'line-position'
  | 'line-traversal';

// 9 + 5 + 2 + 4 + 5 + 3 + 1 + 1 = 30, verified against c-template-registry.json's 30 entries by
// the table-coverage test (c-archetype-resolution.test.ts).
const ARCHETYPE_TABLE: Record<string, ArchetypeId> = {
  'C-JB-01': 'value-report',
  'C-JB-03': 'value-report',
  'C-JB-04': 'value-report',
  'C-TC-01': 'value-report',
  'C-TC-02': 'value-report',
  'C-TC-03': 'value-report',
  'C-TC-04': 'value-report',
  'C-EG-03': 'value-report',
  'C-SF-03': 'value-report',
  'C-CC-03': 'option-select',
  'C-CC-04': 'option-select',
  'C-MCL-01': 'option-select',
  'C-MCL-02': 'option-select',
  'C-MCL-03': 'option-select',
  'C-CC-01': 'object-set-action',
  'C-CC-02': 'object-set-action',
  'C-NP-01': 'ordered-value-sequence',
  'C-NP-02': 'ordered-value-sequence',
  'C-NP-03': 'ordered-value-sequence',
  'C-NP-04': 'ordered-value-sequence',
  'C-BT-01': 'named-integer-fields',
  'C-BT-02': 'named-integer-fields',
  'C-BT-03': 'named-integer-fields',
  'C-BT-04': 'named-integer-fields',
  'C-EG-02': 'named-integer-fields',
  'C-EG-01': 'partition-allocation',
  'C-SF-01': 'partition-allocation',
  'C-SF-02': 'partition-allocation',
  'C-MCL-04': 'line-position',
  'C-JB-02': 'line-traversal',
};

/**
 * Resolve one template id's archetype, or `null` if resolution cannot proceed.
 *
 * Returns `null` for:
 *   1. a `templateId` not present in the table -- own-property lookup, never bare access, so a
 *      drifted or hostile id like "constructor", "toString" or "__proto__" cannot resolve to an
 *      inherited `Object.prototype` member;
 *   2. a `validActionSpace` carrying any declared type the field-kind layer does not bind.
 *
 * There is no fallback surface for either case. `null` here is what drives `fail-closed-frame`
 * (10.0b-ii) -- never a guessed rendering, never a partial one.
 */
export function resolveArchetype(
  templateId: string,
  validActionSpace: Record<string, string>,
): ArchetypeId | null {
  if (!Object.prototype.hasOwnProperty.call(ARCHETYPE_TABLE, templateId)) return null;

  for (const declaredType of Object.values(validActionSpace)) {
    if (bindFieldKind(declaredType) === null) return null;
  }

  return ARCHETYPE_TABLE[templateId];
}

/** The archetype table's own template-id set, for the coverage test's set-equality assertion. */
export function archetypeTableTemplateIds(): readonly string[] {
  return Object.keys(ARCHETYPE_TABLE);
}
