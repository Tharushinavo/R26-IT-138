// The Play prep card's seven skill bars, sized from the learner's real Component B BKT state
// (GET /api/v1/b/learner/skill-states) -- 2026-09-21 product-owner ruling.
//
// THE RULING, in full: the child may see their mastery as the LENGTH OF A BAR and nothing else.
// No percentage, no number, no word for it, nothing read aloud by a screen reader. `p_l` comes
// in here as a probability and leaves as a width; every other use is out of bounds. This module
// is the only place that conversion happens, so the rule has one home.
//
// WHAT AN EMPTY BAR MEANS -- owner ruling, 2026-10-10 (supersedes the stricter rule below).
//
// A skill whose row has `observation_count` 0 NOW DRAWS ITS `p_l`, which for such a row is the
// bundle's P(L0) prior (0.2 under the current config, so a one-fifth bar). The owner's decision,
// made with the trade-off below on the table.
//
// The rule this replaced treated a prior as "no evidence" and drew it empty, on the grounds that
// a filled bar claims knowledge the model does not have. That objection has not gone away and is
// recorded here so the choice stays visible rather than looking like an oversight:
//
//   - The prior is a CONSTANT. It is identical for every learner and every skill, so a 20% bar
//     says nothing about this child. Two children who have never touched Multiplication show the
//     same bar as each other, and as a child who answered a question and got it wrong.
//   - At Grade 2 there are ZERO multiplication and division templates (verified against the
//     catalogue's activation gate), so those two skills can never earn an observation. Their bars
//     will sit at exactly one fifth forever, no matter what the child does.
//
// The one thing that is NOT shown is a skill with NO ROW AT ALL -- the learner has never started a
// Component B session, so the server has sent nothing. That still draws empty, and must: the
// client does not hold P(L0) and would have to invent a number to fill it. Showing a value the
// server never sent is a different and worse thing than showing one it did.
//
// Unchanged by this ruling: the child still sees LENGTH only. No percentage, no number, no word
// for it, nothing read by a screen reader.

import type { LearnerSkillStateItem } from '@/src/api/generated/openapi-types';

/** The seven skills, in the order the card draws them. Frozen to Component B's own skill ids
 * (`b_learner_skill_states.skill_id`) -- the card looks each row up by this id, so a skill the
 * server has never sent simply renders empty rather than shifting the others. */
export const PREP_CARD_SKILL_ORDER = [
  'counting',
  'number_sense',
  'place_value',
  'addition',
  'subtraction',
  'multiplication',
  'division',
] as const;

export type PrepCardSkillId = (typeof PREP_CARD_SKILL_ORDER)[number];

/** Bar fill per skill, 0..100, in `PREP_CARD_SKILL_ORDER`. Never a value the UI should print. */
export function skillBarFills(
  states: readonly LearnerSkillStateItem[] | null | undefined,
): Record<PrepCardSkillId, number> {
  const bySkill = new Map<string, LearnerSkillStateItem>();
  for (const state of states ?? []) bySkill.set(state.skill_id, state);

  const fills = {} as Record<PrepCardSkillId, number>;
  for (const skillId of PREP_CARD_SKILL_ORDER) {
    fills[skillId] = fillFor(bySkill.get(skillId));
  }
  return fills;
}

function fillFor(state: LearnerSkillStateItem | undefined): number {
  // No row from the server -> nothing to draw. The client holds no P(L0) of its own and must not
  // invent one; see the header.
  if (!state) return 0;
  // `observation_count` is deliberately NOT a gate any more (owner ruling, 2026-10-10). A row with
  // zero observations carries the P(L0) prior, and the owner's decision is to show it.
  if (!Number.isFinite(state.p_l)) return 0;
  // Clamp defensively even though both the server and the runtime validator bound `p_l` to
  // [0, 1]: a bar must never overflow its track.
  const clamped = Math.min(1, Math.max(0, state.p_l));
  return Math.round(clamped * 100);
}
