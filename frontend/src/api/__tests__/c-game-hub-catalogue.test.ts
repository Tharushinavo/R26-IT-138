// The Play tab hub's catalogue: coverage and readiness.
//
// The point of these tests is that the hub cannot quietly drift out of agreement with the two
// things it presents. Its template ids are checked set-equal to the frozen registry's own 30 (not
// merely counted), and its readiness badges are checked to be COMPUTED from the live surface table
// rather than asserted -- the readiness tests below are written so that they keep passing, with no
// edit, as 10b..10h register surfaces. A test that had to be updated by every future sub-phase
// would just be a second place for the stale claim to live.

import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, resolve } from 'node:path';

import { archetypeTableTemplateIds, type ArchetypeId } from '@/src/features/c-session/archetypes/registry';
import {
  archetypesForFamily,
  listGameFamilies,
  readinessOf,
  sessionRouteFor,
} from '@/src/features/game-hub/game-catalogue';

// The surface lookup is injected as a FAKE here, never the real archetype-surfaces.ts table --
// the same discipline, for the same two reasons, as c-plan-task-surface.test.ts. Importing the
// real table would drag a React Native component into `node --test` (it does not load), and it
// would pin these assertions to whichever surfaces happen to be registered today, so every one
// of 10b..10h would have to come back and edit this file. Injection means readiness is tested as
// a RULE over an arbitrary surface set, which is the thing that is actually true of it.
const noSurfaces = () => false;
const allSurfaces = () => true;
const onlyOrderedValueSequence = (id: ArchetypeId) => id === 'ordered-value-sequence';

const here = dirname(fileURLToPath(import.meta.url));
const repoRoot = resolve(here, '..', '..', '..', '..');
const registryPath = resolve(repoRoot, 'backend', 'contract', 'c-template-registry.json');

// The artefact is a bare top-level ARRAY of entries, not an object with a `templates` key -- see
// c-template-registry-freeze.test.ts, which reads the same file the same way.
function registryTemplateIds(): string[] {
  const parsed = JSON.parse(readFileSync(registryPath, 'utf8')) as { template_id: string }[];
  return parsed.map((entry) => entry.template_id);
}

test('the hub lists exactly the eight game families, C-GF-01 through C-GF-08, in catalogue order', () => {
  const familyIds = listGameFamilies().map((entry) => entry.familyId);
  assert.deepEqual(familyIds, [
    'C-GF-01',
    'C-GF-02',
    'C-GF-03',
    'C-GF-04',
    'C-GF-05',
    'C-GF-06',
    'C-GF-07',
    'C-GF-08',
  ]);
});

test("the hub's template ids are set-equal to the frozen registry's 30 -- every template reachable, none invented", () => {
  const fromHub = listGameFamilies().flatMap((entry) => [...entry.templateIds]);
  assert.deepEqual([...fromHub].sort(), registryTemplateIds().sort());
});

test('no template id appears in two families', () => {
  const fromHub = listGameFamilies().flatMap((entry) => [...entry.templateIds]);
  assert.equal(new Set(fromHub).size, fromHub.length);
});

test('every hub template id resolves to an archetype -- no family carries an unresolvable template', () => {
  const known = new Set(archetypeTableTemplateIds());
  for (const entry of listGameFamilies()) {
    for (const templateId of entry.templateIds) {
      assert.ok(known.has(templateId), `${entry.familyId} lists ${templateId}, absent from the archetype table`);
    }
    assert.ok(archetypesForFamily(entry).length > 0, `${entry.familyId} resolved no archetype`);
  }
});

// The anti-staleness tests: readiness stated as a rule over an injected surface set, so no future
// sub-phase has to edit them.
test('with no surface registered, every family reads coming-soon', () => {
  for (const entry of listGameFamilies()) {
    assert.equal(readinessOf(entry, noSurfaces), 'coming-soon', `${entry.familyId}`);
  }
});

test('with every surface registered, every family reads playable', () => {
  for (const entry of listGameFamilies()) {
    assert.equal(readinessOf(entry, allSurfaces), 'playable', `${entry.familyId}`);
  }
});

test('a family is playable exactly when every archetype it needs has a surface -- partial otherwise', () => {
  for (const entry of listGameFamilies()) {
    const archetypeIds = archetypesForFamily(entry);
    const registered = archetypeIds.filter(onlyOrderedValueSequence).length;
    const expected =
      registered === 0 ? 'coming-soon' : registered === archetypeIds.length ? 'playable' : 'partial';
    assert.equal(readinessOf(entry, onlyOrderedValueSequence), expected, `${entry.familyId}`);
  }
});

// The negative control for the badge that matters: the ONE surface that exists today must light
// exactly one family, and it must be C-GF-02 (10a's ordered-value-sequence). If a later batch
// wires a second family to that archetype, this goes red rather than silently mislabelling a
// menu button as ready.
test('the ordered-value-sequence surface makes C-GF-02 playable and no other family', () => {
  const playable = listGameFamilies()
    .filter((entry) => readinessOf(entry, onlyOrderedValueSequence) === 'playable')
    .map((entry) => entry.familyId);
  assert.deepEqual(playable, ['C-GF-02']);
});

test('every game button navigates to the C session route carrying its own grade and c_only mode', () => {
  for (const entry of listGameFamilies()) {
    assert.deepEqual(
      sessionRouteFor(entry),
      { pathname: '/(learner)/c-session', params: { grade: String(entry.grade), sessionMode: 'c_only' } },
      `${entry.familyId}`,
    );
    // Grade is a real catalogue fact, never invented: the two Grade-3 families are the only ones
    // that may carry 3.
    const expectedGrade = entry.familyId === 'C-GF-07' || entry.familyId === 'C-GF-08' ? 3 : 2;
    assert.equal(entry.grade, expectedGrade, `${entry.familyId}`);
  }
});

test('the hub route passes no family id -- nothing downstream accepts one', () => {
  for (const entry of listGameFamilies()) {
    assert.ok(!JSON.stringify(sessionRouteFor(entry)).includes(entry.familyId));
  }
});

test('every family has non-empty child-facing copy', () => {
  for (const entry of listGameFamilies()) {
    assert.ok(entry.title.trim().length > 0, `${entry.familyId} title`);
    assert.ok(entry.subtitle.trim().length > 0, `${entry.familyId} subtitle`);
    // No digits in the menu copy, the same no-digits discipline the prompt-wording artefact holds.
    assert.ok(!/\d/.test(entry.subtitle), `${entry.familyId} subtitle contains a digit`);
  }
});
