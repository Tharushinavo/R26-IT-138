// The neutral screen rendered when `resolveArchetype` returns `null`, or when a resolved archetype
// has no surface registered yet (archetype-surfaces.ts) -- both are indistinguishable to the child
// by design. Never a text box, never a partial surface, never a guessed rendering. Component B's
// renderers/registry.ts documents why a fallback input is harmful: it lets a child enter something
// the item cannot accept and then be marked wrong for it, which is exactly the failure the
// authority boundary exists to prevent.
//
// Every task renders this frame in this batch, because 10.0b-ii ships no archetype surface -- the
// eight identifiers registry.ts resolves name components 10a...10h build. That is the batch
// working correctly, not failing.

import { NeutralMessageScreen } from '@/src/features/c-session/neutral-message-screen';

export type FailClosedFrameProps = {
  supportCode: string | null;
  onExit: () => void;
};

export function FailClosedFrame({ onExit, supportCode }: FailClosedFrameProps) {
  return (
    <NeutralMessageScreen
      detail="Let's head back and try again soon."
      onExit={onExit}
      supportCode={supportCode}
      title="This one isn't ready"
    />
  );
}
