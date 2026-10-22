// 10a's fixture-template-selector addition to dev-fixture-exemplars.ts: default behaviour is
// unchanged when EXPO_PUBLIC_COMPONENT_C_DEV_FIXTURE_TEMPLATE is unset, a set var selects the
// requested exemplar, and an unknown (template, level) pair throws the same way the pre-existing
// missing-entry path already did -- never a silent fall-back to the first template.

import { test } from 'node:test';
import assert from 'node:assert/strict';

import { loadFixtureTaskExemplar } from '@/src/api/dev-fixture-exemplars';

function withEnv<T>(vars: Record<string, string | undefined>, run: () => T): T {
  const originals: Record<string, string | undefined> = {};
  for (const key of Object.keys(vars)) {
    originals[key] = process.env[key];
    const value = vars[key];
    if (value === undefined) delete process.env[key];
    else process.env[key] = value;
  }
  try {
    return run();
  } finally {
    for (const key of Object.keys(originals)) {
      const original = originals[key];
      if (original === undefined) delete process.env[key];
      else process.env[key] = original;
    }
  }
}

test('default (both env vars unset) still yields C-BT-01 at difficulty_level 1', () => {
  const entry = withEnv(
    {
      EXPO_PUBLIC_COMPONENT_C_DEV_FIXTURE_DIFFICULTY: undefined,
      EXPO_PUBLIC_COMPONENT_C_DEV_FIXTURE_TEMPLATE: undefined,
    },
    () => loadFixtureTaskExemplar(),
  );
  assert.equal(entry.game_task_template_id, 'C-BT-01');
  assert.equal(entry.difficulty_level, 1);
});

test('a set template var selects that template at the default difficulty_level 1', () => {
  const entry = withEnv(
    {
      EXPO_PUBLIC_COMPONENT_C_DEV_FIXTURE_DIFFICULTY: undefined,
      EXPO_PUBLIC_COMPONENT_C_DEV_FIXTURE_TEMPLATE: 'C-NP-01',
    },
    () => loadFixtureTaskExemplar(),
  );
  assert.equal(entry.game_task_template_id, 'C-NP-01');
  assert.equal(entry.difficulty_level, 1);
});

test('a set template var plus a set difficulty var selects that exact exemplar', () => {
  const entry = withEnv(
    {
      EXPO_PUBLIC_COMPONENT_C_DEV_FIXTURE_DIFFICULTY: '4',
      EXPO_PUBLIC_COMPONENT_C_DEV_FIXTURE_TEMPLATE: 'C-NP-01',
    },
    () => loadFixtureTaskExemplar(),
  );
  assert.equal(entry.game_task_template_id, 'C-NP-01');
  assert.equal(entry.difficulty_level, 4);
  assert.deepEqual(entry.prompt_payload.shown_sequence, [60, 61, 62, 63]);
});

test('negative control: an unknown template id throws rather than falling back to the first template', () => {
  assert.throws(() =>
    withEnv(
      {
        EXPO_PUBLIC_COMPONENT_C_DEV_FIXTURE_DIFFICULTY: undefined,
        EXPO_PUBLIC_COMPONENT_C_DEV_FIXTURE_TEMPLATE: 'C-DOES-NOT-EXIST',
      },
      () => loadFixtureTaskExemplar(),
    ),
  );
});

test('negative control: a known template at an unknown difficulty_level throws', () => {
  assert.throws(() =>
    withEnv(
      {
        EXPO_PUBLIC_COMPONENT_C_DEV_FIXTURE_DIFFICULTY: '99',
        EXPO_PUBLIC_COMPONENT_C_DEV_FIXTURE_TEMPLATE: 'C-NP-01',
      },
      () => loadFixtureTaskExemplar(),
    ),
  );
});

test('negative control: a non-integer difficulty var throws', () => {
  assert.throws(() =>
    withEnv(
      {
        EXPO_PUBLIC_COMPONENT_C_DEV_FIXTURE_DIFFICULTY: 'not-a-number',
        EXPO_PUBLIC_COMPONENT_C_DEV_FIXTURE_TEMPLATE: 'C-NP-01',
      },
      () => loadFixtureTaskExemplar(),
    ),
  );
});
