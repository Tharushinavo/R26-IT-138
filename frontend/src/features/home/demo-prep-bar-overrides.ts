/**
 * DEMO VALUES for two of the Play prep card's mastery bars.
 *
 * Multiplication and Division are drawn at fixed lengths instead of their model value. Owner
 * decision, 2026-10-10: these are shown in a live demo and explained verbally there.
 *
 * These numbers are invented -- they are not BKT output and do not describe any learner. Every
 * other bar on the card is still a real `p_l` the server sent. Kept in its own file so the
 * governed rule in `skill-bar-fill.ts` stays untouched and this can be deleted in one step when
 * the demo is over: remove this file and the `applyDemoPrepBarOverrides` call in
 * play-prep-card.tsx.
 */

import type { PrepCardSkillId } from '@/src/features/home/skill-bar-fill';

/** Invented bar lengths, 0..100. Not model output. */
const DEMO_PREP_BAR_OVERRIDES: Partial<Record<PrepCardSkillId, number>> = {
  division: 37,
  multiplication: 45,
};

/** Replaces the named skills' fills with the demo lengths; every other skill is untouched. */
export function applyDemoPrepBarOverrides(
  fills: Record<PrepCardSkillId, number>,
): Record<PrepCardSkillId, number> {
  return { ...fills, ...DEMO_PREP_BAR_OVERRIDES };
}
