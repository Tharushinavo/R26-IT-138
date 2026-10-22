import { BaseTenBlocks } from '@/src/features/session/prompt-visuals/base-ten-blocks';
import { BeforeAfter } from '@/src/features/session/prompt-visuals/before-after';
import { ObjectSet } from '@/src/features/session/prompt-visuals/object-set';
import { PlaceValueChart } from '@/src/features/session/prompt-visuals/place-value-chart';
import { TakeAway } from '@/src/features/session/prompt-visuals/take-away';
import { TwoSets } from '@/src/features/session/prompt-visuals/two-sets';
import type { PromptVisualSpec } from '@/src/features/session/prompt-visuals/types';

// Dispatcher for the *passive* prompt visuals — the ones that illustrate the question without being
// part of answering it.
//
// `selectable-pool` is deliberately absent: it is an answer surface, not an illustration, and is
// rendered by `renderers/count-selection.tsx` so that the count the child submits comes from the
// objects they actually selected. Returning null for it here keeps it from being drawn twice.
//
// `seed` identifies the QUESTION, not the visual. It decides which emoji the countable objects are
// drawn as, so the choice is stable for as long as a question is on screen and differs between
// questions. The caller passes `plan.itemOpportunityId`; see utils/countable-emoji.ts for why this
// is seeded rather than random. The two chart visuals ignore it -- they draw places and blocks,
// not countable objects.
export function PromptVisual({ seed, spec }: { seed: string; spec: PromptVisualSpec }) {
  if (spec.kind === 'object-set') return <ObjectSet seed={seed} visual={spec} />;
  if (spec.kind === 'two-sets') return <TwoSets seed={seed} visual={spec} />;
  if (spec.kind === 'place-value-chart') return <PlaceValueChart visual={spec} />;
  if (spec.kind === 'base-ten-blocks') return <BaseTenBlocks visual={spec} />;
  if (spec.kind === 'take-away') return <TakeAway seed={seed} visual={spec} />;
  if (spec.kind === 'before-after') return <BeforeAfter seed={seed} visual={spec} />;
  return null;
}
