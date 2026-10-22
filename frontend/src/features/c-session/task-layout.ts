// How far a Component C task's content sits from the task card's border.
//
// WHY THIS IS ONE NUMBER IN ONE PLACE. The inset is the SUM of two values that live in different
// files -- the task panel's own `padding` in c-session-screen.tsx, plus the `padding` repeated in
// nine `container` styles across eight archetype surfaces. Nothing recorded that those were meant
// to add up to a single designed gap, so changing it meant finding all nine and doing the
// arithmetic by hand, and any surface added later would quietly get whatever `spacing.lg` happened
// to be. Stating the total once and deriving both halves from it is what makes "every game type"
// true by construction rather than by nine numbers happening to agree.
//
// THE VALUE. 36 -> 18 (owner instruction, 2026-10-10: half of what it was). Both contributors were
// halved rather than taking it all out of one, so the panel keeps a margin of its own and the
// surfaces keep theirs:
//
//     panel  12 -> 6
//     surface 24 -> 12
//
// WHAT IT CONTROLS. Everything the child sees inside the card is a child of a surface container:
// the question card at the top and SUBMIT at the bottom are siblings there, so they share this
// inset by construction. That is why halving one number moves both together and keeps them equal.
//
// VERIFIED TO FIT, not assumed -- in the widening direction this is the binding constraint, so the
// check is recorded here for whoever raises it next. The narrowest case is a 360pt viewport, where
// the card is 324pt wide; at this inset that leaves 280pt of content. The digit keypad is the
// widest fixed element inside it and needs 3 x KEYPAD_KEY_SIZE (48) plus 2 x KEYPAD_KEY_SPACING
// (8) = 160pt. Comfortable here; it would start to bind again somewhere above a 65pt inset.

import { spacing } from '@/src/theme/tokens';

/**
 * The task panel's own padding, in c-session-screen.tsx.
 *
 * Does NOT affect the card's background artwork. That image is an absolutely-positioned child, and
 * an absolute child's containing block is the padding BOX -- which includes the padding area -- so
 * the image still fills the card edge to edge inside its border whatever this value is.
 */
export const TASK_PANEL_PADDING = spacing.smPlus / 2;

/** The designed distance from the card's inner border to the content. See the note above. */
export const TASK_CONTENT_INSET = 18;

/**
 * What each archetype surface's own outer container uses, so that panel padding plus this equals
 * `TASK_CONTENT_INSET` exactly. Never hardcode the gap in a surface -- use this, so a new game type
 * inherits the same inset as every existing one.
 */
export const TASK_SURFACE_PADDING = TASK_CONTENT_INSET - TASK_PANEL_PADDING;
