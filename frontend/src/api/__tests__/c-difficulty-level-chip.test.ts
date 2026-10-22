// The Component C card's top-right level chip (owner instruction, 2026-10-10).
//
// It used to show `scaffold_state` -- the SUPPORT level, how much help the engine is giving --
// rendered as "Lv 1".."Lv 5" from `C0`..`C4`. On the card that reads as the game's level, which it
// is not. It now shows `CNextTaskResponse.difficulty_level`, the integer the adaptation engine
// actually moves per task.
//
// AND IT PRINTS NO DENOMINATOR. The approved bundle defines no maximum difficulty: it carries
// `familiarization_difficulty_level: 1`, `fallback_difficulty_level: 1` and caps of 2, while no
// catalogue template carries a difficulty field at all. "Lv 2 of 3" would be the client asserting
// a ceiling the governed configuration does not define.

import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';

const SCREEN = 'src/features/c-session/c-session-screen.tsx';
const source = readFileSync(SCREEN, 'utf8');

test('the chip is sourced from difficulty_level, not scaffold_state', () => {
  assert.match(source, /function difficultyLevelLabel\(difficultyLevel: number\)/);
  assert.match(source, /difficultyLevelLabel\(task\.difficulty_level\)/);
  assert.doesNotMatch(
    source,
    /scaffoldLevelLabel/,
    'the support level must no longer masquerade as the game level',
  );
});

test('the chip prints no denominator', () => {
  const fn = source.slice(
    source.indexOf('function difficultyLevelLabel('),
    source.indexOf('function softTint('),
  );
  assert.match(fn, /return `Lv \$\{difficultyLevel\}`;/, 'just the server value');
  assert.doesNotMatch(fn, /of 3|\/ ?3|\bmax\b/i, 'no ceiling the bundle does not define');
});

test('a non-integer or out-of-range level renders nothing rather than leaking a raw value', () => {
  // Same tolerance the scaffold label it replaces had: fail to a missing chip, never a crash and
  // never a raw value on screen.
  const fn = source.slice(
    source.indexOf('function difficultyLevelLabel('),
    source.indexOf('function softTint('),
  );
  assert.match(fn, /if \(!Number\.isInteger\(difficultyLevel\) \|\| difficultyLevel < 1\) return null;/);
  assert.match(source, /difficultyLevelLabel\(task\.difficulty_level\) !== null \?/);
});

test('scaffold level is still shown where it belongs — the wrong-answer feedback panel', () => {
  // Replacing the chip must not lose the support level entirely: it is still relayed to
  // AnswerFeedbackPanel, which shows it only when the answer was not matched.
  assert.match(source, /scaffoldLevel=\{feedback\.scaffoldLevel\}/);
  assert.match(source, /scaffoldLevel: result\.scaffold_level/);
});
