import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, resolve } from 'node:path';

import { applyDemoPrepBarOverrides } from '@/src/features/home/demo-prep-bar-overrides';
import { PREP_CARD_SKILL_ORDER, skillBarFills } from '@/src/features/home/skill-bar-fill';
import { isLearnerSkillStatesResponse } from '@/src/api/runtime-validation';

const here = dirname(fileURLToPath(import.meta.url));
const frontendRoot = resolve(here, '..', '..', '..');

// The 2026-09-21 product-owner ruling: the child sees mastery as bar LENGTH only. These pin the
// three consequences that make that honest -- a prior is not evidence, absence is empty, and the
// number itself never reaches the UI in any other form.

const state = (skill_id: string, p_l: number, observation_count: number) => ({ skill_id, p_l, observation_count });

test('every skill renders, in the fixed order, even when the server sent nothing', () => {
  const fills = skillBarFills(null);
  assert.deepEqual(Object.keys(fills), [...PREP_CARD_SKILL_ORDER]);
  assert.deepEqual(Object.values(fills), [0, 0, 0, 0, 0, 0, 0]);
  assert.deepEqual(skillBarFills([]), fills);
  assert.deepEqual(skillBarFills(undefined), fills);
});

test('p_l becomes a 0..100 width for any row the server sent, observations or not', () => {
  // OWNER RULING, 2026-10-10. This used to assert the opposite -- that a row with
  // `observation_count` 0 drew EMPTY, because its `p_l` is the bundle's P(L0) prior rather than
  // anything learned about this child. The owner decided the prior should be shown, with the
  // trade-off on the table: the prior is a constant, so a one-fifth bar distinguishes nothing,
  // and at Grade 2 (no multiplication/division templates) those bars can never move.
  const fills = skillBarFills([
    state('counting', 0.73, 12),
    state('addition', 0.415, 3),
    state('division', 0.2, 0),
    state('multiplication', 0.95, 0),
  ]);
  assert.equal(fills.counting, 73);
  assert.equal(fills.addition, 42);
  assert.equal(fills.division, 20, 'the P(L0) prior now draws as a bar');
  assert.equal(fills.multiplication, 95, 'and a zero-observation row is not special-cased');
  // Never sent at all -> still empty, and the others keep their slots. This is the line the ruling
  // did NOT move: with no row there is no server-sent value, and the client must not invent one.
  assert.equal(fills.number_sense, 0);
  assert.equal(fills.place_value, 0);
  assert.equal(fills.subtraction, 0);
});

test('a skill the server never sent stays empty, even though priors are now drawn', () => {
  // The boundary of the 2026-10-10 ruling. A learner who has never started a Component B session
  // has no rows at all, so every bar is empty -- the card must not fabricate P(L0) client-side.
  const fills = skillBarFills([state('counting', 0.2, 0)]);
  assert.equal(fills.counting, 20, 'a sent row draws, prior or not');
  for (const skill of ['number_sense', 'place_value', 'addition', 'subtraction', 'multiplication', 'division'] as const) {
    assert.equal(fills[skill], 0, `${skill} was never sent and must stay empty`);
  }
});

test('a bar can never overflow or underflow its track', () => {
  const fills = skillBarFills([
    state('counting', 1, 5),
    state('addition', 0, 5),
    // Defensive: the validator rejects these upstream, but the fill rule clamps on its own too.
    state('subtraction', 1.7, 5),
    state('place_value', -0.3, 5),
    state('number_sense', Number.NaN, 5),
  ]);
  assert.equal(fills.counting, 100);
  assert.equal(fills.addition, 0);
  assert.equal(fills.subtraction, 100);
  assert.equal(fills.place_value, 0);
  assert.equal(fills.number_sense, 0);
});

test('unknown skill ids are ignored rather than added', () => {
  const fills = skillBarFills([state('fractions', 0.9, 9), state('counting', 0.5, 1)]);
  assert.deepEqual(Object.keys(fills), [...PREP_CARD_SKILL_ORDER]);
  assert.equal(fills.counting, 50);
});

// --- runtime validation --------------------------------------------------------------------------

test('the response validator accepts the frozen shape and rejects out-of-range p_l', () => {
  const ok = { request_id: 'r-1', skill_states: [state('counting', 0.5, 2), state('division', 0, 0)] };
  assert.equal(isLearnerSkillStatesResponse(ok), true);
  assert.equal(isLearnerSkillStatesResponse({ request_id: 'r-1', skill_states: [] }), true);

  assert.equal(isLearnerSkillStatesResponse({ request_id: 'r-1', skill_states: [state('counting', 1.01, 2)] }), false);
  assert.equal(isLearnerSkillStatesResponse({ request_id: 'r-1', skill_states: [state('counting', -0.01, 2)] }), false);
  assert.equal(isLearnerSkillStatesResponse({ request_id: 'r-1', skill_states: [state('counting', 0.5, -1)] }), false);
  assert.equal(isLearnerSkillStatesResponse({ request_id: 'r-1', skill_states: [state('counting', 0.5, 1.5)] }), false);
  assert.equal(isLearnerSkillStatesResponse({ request_id: 'r-1', skill_states: [state('', 0.5, 1)] }), false);
  assert.equal(isLearnerSkillStatesResponse({ request_id: '', skill_states: [] }), false);
  assert.equal(isLearnerSkillStatesResponse({ skill_states: [] }), false);
  assert.equal(isLearnerSkillStatesResponse(null), false);
});

// --- the number never reaches the UI --------------------------------------------------------------

test('the prep card renders no numeric mastery: no percent text, no accessibilityValue, and the track is decorative', () => {
  const source = readFileSync(resolve(frontendRoot, 'src/features/home/play-prep-card.tsx'), 'utf8');
  // The only consumer of a fill is the animated width interpolation.
  //
  // FE-003 (2026-10-09) briefly changed this to an animated `scaleX`, to get the sweep off the JS
  // thread. REVERTED 2026-10-10: the bars drew at full length regardless of the learner's real
  // mastery -- five skills whose true fills were 17, 17, 56, 17 and 17 all rendered complete.
  // Under the ruling this test enforces, that is the worst possible failure: the bar IS the
  // statement about the child's progress, so a bar that always reads "full" is a false one.
  // The assertion is back on the width interpolation, and the guard below pins the revert.
  const fillUses = source.match(/fills\[skill\.key\]/g) ?? [];
  assert.equal(fillUses.length, 1, 'fills must feed exactly one place: the bar width');
  assert.match(source, /outputRange: \['0%', `\$\{fills\[skill\.key\]\}%`\]/);
  // A fill must reach the bar as a width, not as a transform scale: `scaleX` was observed to
  // render every non-zero bar full. Do not reintroduce it without first establishing why.
  assert.doesNotMatch(
    source,
    /scaleX: rowProgress/,
    'the bar length must not be driven by scaleX -- see the JSX comment on the bar',
  );
  // Nothing may announce or print it.
  assert.doesNotMatch(source, /accessibilityValue=/);
  assert.doesNotMatch(source, /accessibilityRole="progressbar"/);
  assert.doesNotMatch(source, /\{fills\[skill\.key\]\}%?\s*<\/AppText>/);
  assert.match(source, /accessible=\{false\}[^>]*style=\{styles\.track\}/s);
  // The staged targets are gone for good.
  assert.doesNotMatch(source, /target: \d+/);
});

// --- the demo override ------------------------------------------------------------------------

test('the demo override replaces only Multiplication and Division', () => {
  // Owner decision, 2026-10-10: fixed demo lengths for these two, explained verbally in the demo.
  // Invented numbers, so this pins the blast radius -- every other skill must keep its real p_l.
  const fills = skillBarFills([
    state('counting', 0.73, 12),
    state('multiplication', 0.95, 0),
    state('division', 0.2, 0),
  ]);
  const after = applyDemoPrepBarOverrides(fills);

  assert.equal(after.multiplication, 45);
  assert.equal(after.division, 37);
  assert.equal(after.counting, 73, 'a real value must not be touched');
  assert.equal(after.addition, 0, 'a skill the server never sent stays empty');
});

test('skill-bar-fill.ts itself stays free of the demo values', () => {
  // The governed module keeps implementing the real rule; the override is applied after it, so
  // deleting the demo file restores honest behaviour with no further edits.
  const source = readFileSync(resolve(frontendRoot, 'src/features/home/skill-bar-fill.ts'), 'utf8');
  assert.doesNotMatch(source, /applyDemoPrepBarOverrides/);
});
