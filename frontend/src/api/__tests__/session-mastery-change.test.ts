// The results screen's per-skill bars (owner decision, 2026-10-20).
//
// This feature REVERSES a rule this codebase previously enforced — `resultsView`'s "no per-skill
// breakdown, no mastery figure, a child who got everything wrong and a child who got everything
// right see the identical screen". These tests pin the parts of that rule that still hold, and the
// two protections that make the reversal safe to show a seven-year-old:
//
//   * a bar never shrinks, so a session that lowered a probability is not rendered as a loss;
//   * no snapshot means no movement, rather than movement from zero.
//
// The copy guarantee is unchanged and still tested in session-results.test.ts.

import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';

import { PREP_CARD_SKILL_ORDER } from '@/src/features/home/skill-bar-fill';
import { hasAnyImprovement, skillBarChanges } from '@/src/features/session/session-mastery-change';

const state = (skill_id: string, p_l: number, observation_count = 5) =>
  ({ observation_count, p_l, skill_id }) as never;

test('every skill is returned, always, in the shared order', () => {
  // Seven rows whatever the server sent: a skill absent from the response is still a bar the child
  // expects to see, and the order must match the Play prep card's so the two screens agree.
  const changes = skillBarChanges(null, [state('counting', 0.5)]);
  assert.equal(changes.length, PREP_CARD_SKILL_ORDER.length);
  assert.deepEqual(
    changes.map((c) => c.skillId),
    [...PREP_CARD_SKILL_ORDER],
  );
});

test('a skill that grew is marked improved, with before below after', () => {
  const changes = skillBarChanges([state('counting', 0.2)], [state('counting', 0.8)]);
  const counting = changes.find((c) => c.skillId === 'counting');
  assert.ok(counting);
  assert.ok(counting.before < counting.after, 'the start must sit below the current value');
  assert.equal(counting.improved, true);
});

test('NO SNAPSHOT means no movement at all, not movement from zero', () => {
  // A reload mid-session, or a session started before this shipped, leaves nothing to compare.
  // Rendering `before: 0` would animate a full sweep and tell the child they went from nothing to
  // everything — inventing a result. Equal values assert nothing instead.
  const changes = skillBarChanges(null, [state('counting', 0.8), state('addition', 0.4)]);
  for (const change of changes) {
    assert.equal(change.before, change.after, `${change.skillId} must not appear to move`);
    assert.equal(change.improved, false);
  }
  assert.equal(hasAnyImprovement(changes), false);
});

test('A BAR NEVER SHRINKS — a lowered probability renders flat, never as a loss', () => {
  // BKT moves p_l DOWN on a wrong first attempt. A bar visibly shrinking at the end of a session
  // is precisely the "you did badly" message this screen must not deliver, so a fall is clamped to
  // flat. The underlying value is untouched; only the drawing is.
  const changes = skillBarChanges([state('counting', 0.9)], [state('counting', 0.3)]);
  const counting = changes.find((c) => c.skillId === 'counting');
  assert.ok(counting);
  assert.equal(counting.before, counting.after, 'a fall must draw flat');
  assert.equal(counting.improved, false, 'and must never be flagged as improvement');
});

test('an unchanged skill is not flagged as improved', () => {
  const changes = skillBarChanges([state('addition', 0.6)], [state('addition', 0.6)]);
  assert.equal(changes.find((c) => c.skillId === 'addition')?.improved, false);
});

test('hasAnyImprovement is true only when something actually grew', () => {
  assert.equal(hasAnyImprovement(skillBarChanges([state('counting', 0.2)], [state('counting', 0.7)])), true);
  assert.equal(hasAnyImprovement(skillBarChanges([state('counting', 0.7)], [state('counting', 0.7)])), false);
});

// --- structural guards -------------------------------------------------------------------------

test('the bars print no number, and announce none', () => {
  // The length IS the message. Printing "62%" would reintroduce the mastery FIGURE, which the
  // owner decision did not license — it licensed the bars.
  const source = readFileSync('src/features/session/session-mastery-bars.tsx', 'utf8');
  assert.doesNotMatch(source, /accessibilityValue/, 'no spoken numeric value');
  assert.doesNotMatch(source, /\{`\$\{[a-zA-Z]+\}%`\}/, 'no percentage rendered as text');
  assert.doesNotMatch(source, /toFixed|Math\.round\([a-z]/i, 'no number formatted for display');
});

test('the width rule is shared with the prep card, not re-derived', () => {
  // Two screens showing the same learner at two different bar widths would be worse than showing
  // nothing, so there is exactly one probability-to-width conversion.
  const source = readFileSync('src/features/session/session-mastery-change.ts', 'utf8');
  assert.match(source, /skillBarFills/);
  assert.doesNotMatch(source, /p_l\s*\*|observation_count\s*[<>]/, 'must not compute its own fill');
});

test('the snapshot is in memory only and never persisted', () => {
  // A shared classroom device must never show one child's starting mastery against another's, and
  // the results screen is documented as not surviving a reload.
  const source = readFileSync('src/features/session/session-mastery-snapshot.ts', 'utf8');
  assert.doesNotMatch(source, /AsyncStorage|SecureStore|localStorage|sessionStorage/);
  assert.match(source, /snapshots\.has\(sessionId\)/, 'first write must win');
});

// --- improvement is decided on the BKT value, not the drawn width --------------------------------

test('a rise too small for the bar to show is STILL improvement', () => {
  // The case that made this rule necessary. Under TEST_FIXTURE_ONLY parameters p_l saturates
  // toward 1.0, so a learner with a few sessions behind them moves 0.996 -> 0.998. Both round to a
  // 100%-wide bar, so a width comparison reports "nothing happened" for a session that did move
  // the model. The skill must light up, even though it cannot visibly travel.
  const changes = skillBarChanges([state('counting', 0.996)], [state('counting', 0.998)]);
  const counting = changes.find((c) => c.skillId === 'counting');
  assert.ok(counting);
  assert.equal(counting.improved, true, 'a real rise must count as improvement');
  assert.equal(counting.before, counting.after, 'and the bar still cannot show it');
});

test('a fall too small for the bar to show is NOT improvement', () => {
  const changes = skillBarChanges([state('counting', 0.998)], [state('counting', 0.996)]);
  assert.equal(changes.find((c) => c.skillId === 'counting')?.improved, false);
});

test('a saturated skill that did not move stays dull', () => {
  // Identical probabilities, not merely identical widths: nothing happened, and the screen must
  // say so rather than animate something.
  const changes = skillBarChanges([state('counting', 1)], [state('counting', 1)]);
  assert.equal(changes.find((c) => c.skillId === 'counting')?.improved, false);
  assert.equal(hasAnyImprovement(changes), false);
});

test('the shimmer marks ONLY the skills that moved, and is clipped to the bar', () => {
  // The cue has to stay tied to `improved`. A highlight travelling along every bar would say
  // "everything changed", which is the opposite of what this screen is for; and an unclipped one
  // would paint across the empty part of the track, implying length the skill has not earned.
  const source = readFileSync('src/features/session/session-mastery-bars.tsx', 'utf8');
  assert.match(source, /\{improved \? \(/, 'the highlight must be gated on improved');
  assert.match(source, /trackFill: \{[^}]*overflow: 'hidden'/, 'the fill must clip the highlight');
});
