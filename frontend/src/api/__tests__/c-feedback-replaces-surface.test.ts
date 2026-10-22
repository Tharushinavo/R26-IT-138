// While `answer-feedback-panel.tsx` is showing, `c-session-screen.tsx` must render it INSTEAD OF
// the archetype surface -- never alongside it. That is a correctness requirement, not a layout
// choice: an archetype surface calls `onSubmit` on the child's own action, and a second live
// surface means a second chance to submit against a task instance that may already have written
// its one allowed terminal event (a CORRECT answer does; `task_service.py`'s
// `has_terminal_for_instance` guard). Resubmitting a terminal instance is refused with HTTP 409
// (`task_already_terminal`), which `classifySessionFailure` routes to the technical-block screen --
// a child would experience that as the app breaking, immediately after being told "Nice work!".
//
// WHAT THIS FILE CANNOT DO, STATED PLAINLY, matching this project's standing admission across
// every source-scan test of this shape: it does not mount a component tree and does not observe
// that only one of the two elements is ever actually on screen at once. What is proven below is
// structural -- that the two are written as mutually exclusive branches of one conditional, never
// as two independently-rendered elements -- which is what makes "both mounted at once" impossible
// by construction rather than by convention.

import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, resolve } from 'node:path';

const here = dirname(fileURLToPath(import.meta.url));
const screenPath = resolve(here, '..', '..', 'features', 'c-session', 'c-session-screen.tsx');

function strippedSource(text: string): string {
  return text.replace(/\/\*[\s\S]*?\*\//g, '').replace(/^\s*\/\/.*$/gm, '');
}

/**
 * From `source[openParenIndex]` (which must be `(`), the index one past the matching close paren,
 * or `null` if the parens are unbalanced. Depth-counted so a `:` or `?` inside a nested expression
 * -- including a template literal's own `${...}:${...}` (exactly the shape this file's real `key`
 * expression has) -- can never be mistaken for the ternary's own separators.
 */
function matchingParenEnd(source: string, openParenIndex: number): number | null {
  let depth = 0;
  for (let i = openParenIndex; i < source.length; i += 1) {
    if (source[i] === '(') depth += 1;
    else if (source[i] === ')') {
      depth -= 1;
      if (depth === 0) return i + 1;
    }
  }
  return null;
}

/**
 * Whether the source renders `<Surface` and `<AnswerFeedbackPanel` as the two `(` `)`-wrapped
 * branches of one ternary keyed on a `feedback === null` / `== null` / `!== null` / `!= null`
 * comparison, in EITHER order -- the one shape that makes them mutually exclusive by construction.
 * Returns `false` for two elements written as siblings, two independent `{cond && <X />}` blocks
 * (NOT mutually exclusive with each other unless the conditions are already proven complementary,
 * which this scan does not attempt to verify), or either element missing entirely.
 *
 * Anchors on the exact `feedback <comparison> null` text, not the bare substring "feedback" --
 * which also appears in this file's own import path for answer-feedback-panel.tsx and would
 * otherwise anchor the scan on the wrong occurrence entirely.
 */
export function surfaceAndFeedbackAreMutuallyExclusive(source: string): boolean {
  const stripped = strippedSource(source);
  const hasSurface = /<Surface\b/.test(stripped);
  const hasFeedbackPanel = /<AnswerFeedbackPanel\b/.test(stripped);
  if (!hasSurface || !hasFeedbackPanel) return false;

  const condition = stripped.match(/feedback\s*(?:===?|!==?)\s*null/);
  if (!condition || condition.index === undefined) return false;

  // From the condition, find `?`, then the balanced `(...)` true-branch immediately after it
  // (skipping whitespace), then `:`, then the balanced `(...)` false-branch the same way. Any step
  // failing to line up returns false rather than falling back to a looser scan.
  const afterCondition = stripped.slice(condition.index + condition[0].length);
  const questionMatch = afterCondition.match(/^[^?]*\?\s*\(/);
  if (!questionMatch) return false;

  const trueBranchOpenParen = condition.index + condition[0].length + questionMatch[0].length - 1;
  const trueBranchEnd = matchingParenEnd(stripped, trueBranchOpenParen);
  if (trueBranchEnd === null) return false;
  const trueBranch = stripped.slice(trueBranchOpenParen, trueBranchEnd);

  const afterTrueBranch = stripped.slice(trueBranchEnd);
  const colonMatch = afterTrueBranch.match(/^\s*:\s*\(/);
  if (!colonMatch) return false;

  const falseBranchOpenParen = trueBranchEnd + colonMatch[0].length - 1;
  const falseBranchEnd = matchingParenEnd(stripped, falseBranchOpenParen);
  if (falseBranchEnd === null) return false;
  const falseBranch = stripped.slice(falseBranchOpenParen, falseBranchEnd);

  const combined = trueBranch + falseBranch;
  return combined.includes('<Surface') && combined.includes('<AnswerFeedbackPanel');
}

test('the real screen renders Surface and AnswerFeedbackPanel as mutually-exclusive branches', () => {
  const source = readFileSync(screenPath, 'utf8');
  assert.ok(
    surfaceAndFeedbackAreMutuallyExclusive(source),
    'c-session-screen.tsx does not render Surface / AnswerFeedbackPanel as one exclusive branch',
  );
});

// ---------------------------------------------------------------------------
// Negative controls -- the guard must go RED on each shape below, or it proves nothing about the
// real file.
// ---------------------------------------------------------------------------

test('the guard fires when the two elements are rendered as unconditional siblings', () => {
  const siblings = `
    <View>
      <Surface onSubmit={s} task={task} />
      <AnswerFeedbackPanel matched={true} scaffoldLevel="C0" onNext={n} onTryAgain={t} />
    </View>
  `;
  assert.equal(surfaceAndFeedbackAreMutuallyExclusive(siblings), false);
});

test('the guard fires when only the surface exists, with no feedback panel anywhere', () => {
  const surfaceOnly = '<Surface onSubmit={s} task={task} />';
  assert.equal(surfaceAndFeedbackAreMutuallyExclusive(surfaceOnly), false);
});

test('the guard fires when only the feedback panel exists, with no surface anywhere', () => {
  const feedbackOnly = '<AnswerFeedbackPanel matched={true} scaffoldLevel="C0" onNext={n} onTryAgain={t} />';
  assert.equal(surfaceAndFeedbackAreMutuallyExclusive(feedbackOnly), false);
});

test('the guard fires when the two live in independent, non-complementary conditionals', () => {
  const independentBlocks = `
    {showSurface && <Surface onSubmit={s} task={task} />}
    {showFeedback && <AnswerFeedbackPanel matched={true} scaffoldLevel="C0" onNext={n} onTryAgain={t} />}
  `;
  assert.equal(surfaceAndFeedbackAreMutuallyExclusive(independentBlocks), false);
});

test('the guard fires when a comment merely discusses the exclusivity but no such branch exists', () => {
  const commentOnly = [
    '// feedback === null ? <Surface ... /> : <AnswerFeedbackPanel ... />',
    '<Surface onSubmit={s} task={task} />',
  ].join('\n');
  assert.equal(surfaceAndFeedbackAreMutuallyExclusive(commentOnly), false);
});

// The positive control: the predicate must RECOGNISE the correct shape, in both branch orders,
// so the negative controls above are not passing merely because the guard is vacuously false.
test('the guard recognises the correct shape -- feedback-null branch first', () => {
  const correct = `
    {feedback === null ? (
      <Surface onSubmit={s} task={task} />
    ) : (
      <AnswerFeedbackPanel matched={feedback.matched} scaffoldLevel={feedback.scaffoldLevel} onNext={n} onTryAgain={t} />
    )}
  `;
  assert.ok(surfaceAndFeedbackAreMutuallyExclusive(correct));
});
