// AC 1: proves `option-select`'s registration for the C-GF-03 family without ever importing
// `archetype-surfaces.ts` as a runtime VALUE -- that module imports every real archetype surface
// component, including react-native itself transitively, which `node --import tsx --test` cannot
// transform (`react-native/index.js` has genuine Flow syntax esbuild's transform rejects; the same
// class of defect `ffe543d`'s own commit message describes for the theme barrel, just with no leaf
// available here to switch to, since there is no RN-free version of a real surface component).
// c-plan-task-surface.test.ts already proves the `planTaskSurface` machinery generically with a
// FAKE resolver; this file instead source-scans `archetype-surfaces.ts` for the one line that
// matters, and cross-checks it against `resolveArchetype` (registry.ts, RN-free, safe to import as
// a value) for what each C-GF-03 template resolves to.

import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, resolve } from 'node:path';

import { EXEMPLAR_ENTRIES } from '@/src/api/generated/c-prompt-exemplars';
import { resolveArchetype } from '@/src/features/c-session/archetypes/registry';

const here = dirname(fileURLToPath(import.meta.url));
const surfacesFile = resolve(here, '..', '..', 'features', 'c-session', 'archetype-surfaces.ts');

function stripComments(source: string): string {
  return source.replace(/\/\*[\s\S]*?\*\//g, '').replace(/\/\/.*$/gm, '');
}

function entryFor(templateId: string) {
  return EXEMPLAR_ENTRIES.find((candidate) => candidate.game_task_template_id === templateId)!;
}

test("archetype-surfaces.ts's SURFACE_TABLE now has an 'option-select' entry (source-scan, comments stripped)", () => {
  const source = stripComments(readFileSync(surfacesFile, 'utf-8'));
  assert.match(source, /'option-select':\s*OptionSelectSurface/);
});

test("archetype-surfaces.ts's SURFACE_TABLE now has a 'line-position' entry (source-scan, comments stripped -- 2026-08-26: the §2.2 interaction-cost blocker is resolved via unit-stepper.tsx's new coarse-step, see line-position-logic.ts's own header)", () => {
  const source = stripComments(readFileSync(surfacesFile, 'utf-8'));
  assert.match(source, /'line-position':\s*LinePositionSurface/);
});

test('negative control: the source-scan pattern would NOT match an absent registration (proves the scan is not vacuous)', () => {
  const fabricated = "const SURFACE_TABLE = { 'value-report': ValueReportSurface };";
  assert.doesNotMatch(fabricated, /'line-position':\s*LinePositionSurface/);
});

for (const templateId of ['C-MCL-02', 'C-MCL-03']) {
  test(`${templateId}: resolveArchetype still yields 'option-select' (the id now registered)`, () => {
    assert.equal(resolveArchetype(templateId, entryFor(templateId).valid_action_space), 'option-select');
  });
}

test("C-MCL-04: resolveArchetype yields 'line-position' -- now a REGISTERED surface (2026-08-26), no longer the no-surface-registered fail-closed case this test previously described", () => {
  assert.equal(resolveArchetype('C-MCL-04', entryFor('C-MCL-04').valid_action_space), 'line-position');
});

test("C-MCL-01: resolveArchetype still yields 'option-select' too -- it reaches a REGISTERED surface at the plan level, distinct from C-MCL-04's case (as of 10e-0, option-select-logic.ts resolves it for real rather than refusing it at render time -- see c-option-select-numeral-options-resolution.test.ts)", () => {
  assert.equal(resolveArchetype('C-MCL-01', entryFor('C-MCL-01').valid_action_space), 'option-select');
});
