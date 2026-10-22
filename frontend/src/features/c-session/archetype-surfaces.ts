// The archetype -> surface lookup. 10.0b-ii shipped no archetype surface -- the eight identifiers
// registry.ts resolves name components that belong to 10a...10h -- so this module returned `null`
// for every archetype id. 10a populates the first entry.
//
// It exists so the task loop (c-session-screen.tsx) can be built once: a later sub-phase populates
// one entry here and the loop does not change, because the loop already treats "resolved
// archetype, no surface registered" as a first-class case distinct from "unresolvable template"
// (c-session-logic.ts's `planTask` returns `{kind:'archetype'}` vs `{kind:'fail-closed'}` for
// exactly that reason).

import type { ComponentType } from 'react';

import type { CNextTaskResponse } from '@/src/api/generated/openapi-types';
import type { ArchetypeId } from '@/src/features/c-session/archetypes/registry';
import { LinePositionSurface } from '@/src/features/c-session/archetypes/line-position-surface';
import { LineTraversalSurface } from '@/src/features/c-session/archetypes/line-traversal-surface';
import { NamedIntegerFieldsSurface } from '@/src/features/c-session/archetypes/named-integer-fields-surface';
import { ObjectSetActionSurface } from '@/src/features/c-session/archetypes/object-set-action-surface';
import { PartitionAllocationSurface } from '@/src/features/c-session/archetypes/partition-allocation-surface';
import { OptionSelectSurface } from '@/src/features/c-session/archetypes/option-select-surface';
import { OrderedValueSequenceSurface } from '@/src/features/c-session/archetypes/ordered-value-sequence-surface';
import { ValueReportSurface } from '@/src/features/c-session/archetypes/value-report-surface';

export type ArchetypeSurfaceProps = {
  task: CNextTaskResponse;
  onSubmit: (payload: Record<string, unknown>) => void | Promise<void>;
};

const SURFACE_TABLE: Partial<Record<ArchetypeId, ComponentType<ArchetypeSurfaceProps>>> = {
  'ordered-value-sequence': OrderedValueSequenceSurface,
  'value-report': ValueReportSurface,
  'line-traversal': LineTraversalSurface,
  // Registered by archetype id, not template id: this one entry also lights up C-CC-03/C-CC-04
  // (C-GF-01, already routed here by registry.ts before this batch existed) alongside this batch's
  // own C-MCL-02/C-MCL-03 (C-GF-03) -- see option-select-logic.ts's header for why C-MCL-01/C-CC-03
  // structurally refuse rather than mount a partial or answer-leaking surface, and 10d's own
  // build-log entry for the finding this was raised against before this line was added.
  'option-select': OptionSelectSurface,
  // Registered by archetype id: this one entry lights up both C-CC-01 and C-CC-02 (C-GF-01),
  // registry.ts's own pre-existing mapping -- see object-set-action-logic.ts's header for how one
  // resolver covers both templates' different declared-key shapes.
  'object-set-action': ObjectSetActionSurface,
  // C-MCL-04 alone (C-GF-03). Completes the family this batch's own option-select entry already
  // partially lit up -- see line-position-logic.ts's header for why this is a separate archetype
  // from line-traversal, and unit-stepper.tsx's own coarse-step addition for the interaction-cost
  // fix this template needed before it could ship (master work order §2.2).
  'line-position': LinePositionSurface,
  // C-BT-01..04 (C-GF-04) alongside C-EG-02 (C-GF-07, registry.ts's own pre-existing mapping) --
  // one resolver, no template branch. C-EG-02's `rows`/`cols` are consumed structurally as an
  // `ArrayGrid`'s dimensions rather than rendered as payload numerals (they double as
  // `valid_action_space` keys, so printing them would leak 2 of 3 answers) -- see
  // named-integer-fields-logic.ts's own header, "C-EG-02 IS SUPPORTED HERE".
  'named-integer-fields': NamedIntegerFieldsSurface,
  // C-EG-01 (C-GF-07) alongside C-SF-01 (C-GF-08, registry.ts's own pre-existing mapping) -- one
  // resolver, no template branch, see partition-allocation-logic.ts's header. C-SF-02 also resolves
  // to this archetype id but structurally fails closed on its extra `integer-field` action key.
  // That refusal is PERMANENT as of 10h's ruling (2026-08-26), not the pending-a-later-batch kind
  // named-integer-fields-logic.ts's C-EG-02 refusal turned out to be: C-SF-02 declares no bin-count
  // payload key at all, so its bin count IS its answer, and no fixed-slot scene can render it
  // without leaking that answer. C-18's "configuration, not a new screen" claim is falsified by this
  // one template -- full finding, and the configuration points a future variable-bin-count scene
  // would need, in backend/buildLog2.md's 10h entry.
  'partition-allocation': PartitionAllocationSurface,
};

/**
 * Resolve the rendering surface for one archetype id, or `null` if none is registered yet.
 * `null` here is what makes the task loop fall back to `FailClosedFrame` -- never a guessed or
 * partial rendering. Own-property lookup against a fixed, closed union of eight ids: `archetypeId`
 * is a value this codebase produces (ArchetypeId), never a wire string, but the same discipline is
 * kept here rather than relying on that.
 */
export function resolveArchetypeSurface(
  archetypeId: ArchetypeId,
): ComponentType<ArchetypeSurfaceProps> | null {
  if (!Object.prototype.hasOwnProperty.call(SURFACE_TABLE, archetypeId)) return null;
  return SURFACE_TABLE[archetypeId] ?? null;
}
