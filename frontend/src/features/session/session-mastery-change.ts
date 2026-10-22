import type { LearnerSkillStateItem } from '@/src/api/generated/openapi-types';
import {
  PREP_CARD_SKILL_ORDER,
  skillBarFills,
  type PrepCardSkillId,
} from '@/src/features/home/skill-bar-fill';

// Turns a before/after pair of skill states into what the results screen draws (owner decision,
// 2026-10-20). Pure: no React, no fetching, no animation -- so the rule is testable on its own.
//
// IT REUSES `skillBarFills` RATHER THAN RE-DERIVING. The probability-to-width rule lives in
// skill-bar-fill.ts and is shared with the Play prep card. Two screens showing the same learner's
// mastery at different widths would be worse than showing nothing, so there is exactly one
// conversion and both screens call it.
//
// NOTHING HERE IS A SCORE. `before`/`after` are bar widths, never printed, never summed, never
// turned into a percentage or a count of improved skills. The screen draws two lengths; it does
// not tell a child how well they did in words or numbers.

export type SkillBarChange = {
  skillId: PrepCardSkillId;
  /** Bar width 0..100 as the session STARTED. Equals `after` when no snapshot was captured. */
  before: number;
  /** Bar width 0..100 now. */
  after: number;
  /** True when the skill's BKT probability rose this session -- even if by less than the bar can
   * show. Drives the sweep and the full-colour treatment; a false row is drawn dulled and still. */
  improved: boolean;
};

/**
 * One entry per skill, always all seven, always in `PREP_CARD_SKILL_ORDER`.
 *
 * A NULL SNAPSHOT MEANS "NOTHING TO COMPARE", and is returned as `before === after` for every
 * skill -- so the screen draws current mastery with no movement and no dim marker. That is the
 * honest rendering of "we do not know where you started": it asserts nothing, rather than
 * implying the child made no progress, which a zeroed `before` would do.
 *
 * `before` is also clamped to never exceed `after`. BKT can move a probability DOWN -- a wrong
 * first attempt lowers `p_l` -- and a bar visibly shrinking at the end of a session is exactly the
 * "you did badly" message this screen must not deliver. A skill that fell is shown as flat, not as
 * a loss; `improved` stays false, so it simply does not animate.
 */
export function skillBarChanges(
  before: readonly LearnerSkillStateItem[] | null,
  after: readonly LearnerSkillStateItem[] | null,
): readonly SkillBarChange[] {
  const afterFills = skillBarFills(after);
  const beforeFills = before === null ? afterFills : skillBarFills(before);
  // The RAW probabilities, used only to answer "did this skill move?". Widths still come from
  // skillBarFills above -- see the note on `improved` below for why the two must be asked
  // separately.
  const afterProbabilities = probabilityBySkill(after);
  const beforeProbabilities = before === null ? afterProbabilities : probabilityBySkill(before);

  return PREP_CARD_SKILL_ORDER.map((skillId) => {
    const now = afterFills[skillId];
    const start = Math.min(beforeFills[skillId], now);
    const probabilityNow = afterProbabilities.get(skillId);
    const probabilityStart = beforeProbabilities.get(skillId);
    // IMPROVEMENT IS DECIDED ON THE BKT VALUES, NOT ON THE BAR WIDTHS.
    //
    // `skillBarFills` rounds `p_l` to a whole percent, because a bar is drawn in pixels. Asking
    // the rounded width whether a skill moved throws away every change smaller than one percent --
    // and under the current TEST_FIXTURE_ONLY parameters `p_l` saturates toward 1.0, so a learner
    // with a few sessions behind them sits at 0.996 and climbs to 0.998. That IS progress the
    // model recorded; rounding both ends to 100 reports it as nothing happening.
    //
    // So the two questions are asked of two different sources: "how long is the bar" of the
    // rounded fill, and "did it move" of the probability itself. A skill can therefore come back
    // `improved` with `before === after` -- it genuinely moved, but by less than the bar can show.
    // That is the honest rendering: it is lit rather than dulled, and it barely travels.
    const improved =
      probabilityNow !== undefined && probabilityStart !== undefined
        ? probabilityNow > probabilityStart
        : now > start;
    return { after: now, before: start, improved, skillId };
  });
}

/**
 * Raw `p_l` per skill, for the did-it-move comparison only. A skill the server sent no row for is
 * absent rather than zero: "no row" is not a probability, and inventing one would manufacture a
 * change the first time a row appears.
 */
function probabilityBySkill(
  states: readonly LearnerSkillStateItem[] | null,
): ReadonlyMap<string, number> {
  const probabilities = new Map<string, number>();
  for (const state of states ?? []) {
    if (Number.isFinite(state.p_l)) probabilities.set(state.skill_id, state.p_l);
  }
  return probabilities;
}

/** True when at least one bar grew. The screen uses it to decide whether to animate at all. */
export function hasAnyImprovement(changes: readonly SkillBarChange[]): boolean {
  return changes.some((change) => change.improved);
}
