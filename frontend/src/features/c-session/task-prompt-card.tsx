// The card that holds a Component C task's question and the things it refers to.
//
// OWNER INSTRUCTION, 2026-09-28: Component C used to draw ONE big card around the entire task --
// exit control, family pill, level chip, question, manipulatives, answer controls and SUBMIT all
// inside a single accent-bordered panel filling the screen. That panel is gone. What replaces it
// is this: a small card around the QUESTION AND ITS ITEMS only, with the answer controls and
// SUBMIT sitting on the warm ground below it, exactly as Component B has always done.
//
// The shape is Component B's `promptCard` reproduced value-for-value (live-session-screen.tsx):
// `surface1` ground, `radius.lg`, a 2px `border` with a 3px `borderStrong` bottom edge, and
// `spacing.md` of padding. Reproduced rather than imported because that style is private to
// Component B's screen and the two components deliberately keep their own stylesheets -- but the
// numbers are copied, not re-chosen, so the two read as one product.
//
// WHAT GOES INSIDE, and what does not. Inside: the question, and whatever the child LOOKS AT to
// answer it -- the object set, the payload tokens, the number line, the array. Outside: anything
// the child ACTS ON to give their answer -- option rows, keypads, steppers, toggles -- and SUBMIT.
// That line is what makes the card mean "here is the question" rather than "here is the task", and
// it is the same line Component B draws.

import type { ReactNode } from 'react';
import { StyleSheet, View } from 'react-native';

import { colors, radius, spacing } from '@/src/theme/tokens';

export function TaskPromptCard({ children }: { children: ReactNode }) {
  return <View style={styles.card}>{children}</View>;
}

/** The same card as a bare style, for the surfaces that ALREADY have a wrapper View around their
 * question and its items (`promptBlock`). Restyling that existing element is safer than threading
 * a component through JSX whose closing tag is ambiguous -- and it is the same card either way,
 * defined once here. */
/**
 * The question card's ground: `colors.surface1` (#ffffff) at 60% opacity, not solid white.
 *
 * WHY (owner instruction, 2026-10-10). The task panel behind this card now carries a pastel
 * pattern (`artwork.cTaskBackground`). A fully opaque card blanked it out over the card's whole
 * footprint, which is most of the panel -- so the pattern read as a border decoration rather than
 * the card's ground. Letting it through makes the two layers read as one surface. Tuned on the
 * day: 60%, then 30%, settling at 55%.
 *
 * 0.55 x 255 = 140.25, rounded to 140 = 0x8C (54.9%), written as an 8-digit hex rather than rgba()
 * to match how the rest of this codebase expresses alpha (see `withAlpha`/`GRADIENT_WASH_ALPHA` in
 * rotating-gradient-background.tsx).
 *
 * LEGIBILITY IS THE CONSTRAINT, not aesthetics: the question text and the numbers the child reads
 * sit on this ground, and in a dyscalculia screening tool a misread digit is a measurement error,
 * not a cosmetic one. 55% clears WCAG AA comfortably here, but ONLY because the pattern
 * behind it is itself near-white (a very light lavender with pale outlined doodles) -- compositing
 * 55% white over it lands around #f7f2fa, which against the dark prompt text is still well above
 * 12:1. That headroom belongs to the ARTWORK, not to this number: swap in a darker or more
 * saturated background and this alpha stops being safe. Re-measure if the image changes.
 */
const TASK_PROMPT_CARD_BACKGROUND = `${colors.surface1}8C`;

export const taskPromptCardStyle = {
  backgroundColor: TASK_PROMPT_CARD_BACKGROUND,
  borderBottomColor: colors.borderStrong,
  borderBottomWidth: 3,
  borderColor: colors.border,
  borderRadius: radius.lg,
  borderWidth: 2,
  padding: spacing.md,
} as const;

const styles = StyleSheet.create({
  card: { ...taskPromptCardStyle, gap: spacing.smPlus, width: '100%' },
});
