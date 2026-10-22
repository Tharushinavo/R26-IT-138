// The dev fixture's task-serving half (10.0b-i, owner ruling 2026-08-24).
//
// CLOSES A 10.0a GAP, not new-only work: 10.0a's own acceptance criteria required "the same test
// asserting it cannot activate outside development" that contract-freeze.test.ts:58 has for
// Component B's fixture (getComponentBDevelopmentFixture). No such test was ever written for
// Component C -- `getComponentCDevelopmentFixture` (component-c-api.ts) has been exported since
// 10.0a with zero test coverage and zero non-test callers anywhere in the repo, verified by grep
// across the whole frontend tree before this batch started. The first test below is that missing
// assertion, written now because this batch's own acceptance criterion 5 ("the fixture cannot
// activate outside EXPO_PUBLIC_APP_ENV=development, still asserted") requires it to exist and
// pass, and "still" was false until this file.

import { test } from 'node:test';
import assert from 'node:assert/strict';

import { createComponentCApi, getComponentCDevelopmentFixture } from '@/src/api/component-c-api';
import { loadFixtureTaskExemplar } from '@/src/api/dev-fixture-exemplars';

function withDevFixtureEnv<T>(fixtureValue: string, run: () => T): T {
  const originalAppEnv = process.env.EXPO_PUBLIC_APP_ENV;
  const originalFixture = process.env.EXPO_PUBLIC_COMPONENT_C_DEV_FIXTURE;
  try {
    process.env.EXPO_PUBLIC_APP_ENV = 'development';
    process.env.EXPO_PUBLIC_COMPONENT_C_DEV_FIXTURE = fixtureValue;
    return run();
  } finally {
    if (originalAppEnv === undefined) delete process.env.EXPO_PUBLIC_APP_ENV;
    else process.env.EXPO_PUBLIC_APP_ENV = originalAppEnv;
    if (originalFixture === undefined) delete process.env.EXPO_PUBLIC_COMPONENT_C_DEV_FIXTURE;
    else process.env.EXPO_PUBLIC_COMPONENT_C_DEV_FIXTURE = originalFixture;
  }
}

test('the Component C dev fixture cannot activate outside EXPO_PUBLIC_APP_ENV=development', () => {
  const originalAppEnv = process.env.EXPO_PUBLIC_APP_ENV;
  const originalFixture = process.env.EXPO_PUBLIC_COMPONENT_C_DEV_FIXTURE;
  try {
    process.env.EXPO_PUBLIC_COMPONENT_C_DEV_FIXTURE = 'active';

    for (const appEnv of ['staging', 'production', undefined]) {
      if (appEnv === undefined) delete process.env.EXPO_PUBLIC_APP_ENV;
      else process.env.EXPO_PUBLIC_APP_ENV = appEnv;
      assert.equal(
        getComponentCDevelopmentFixture(),
        null,
        `fixture must be null when EXPO_PUBLIC_APP_ENV=${appEnv}`,
      );
    }

    process.env.EXPO_PUBLIC_APP_ENV = 'development';
    assert.equal(getComponentCDevelopmentFixture(), 'active');
  } finally {
    if (originalAppEnv === undefined) delete process.env.EXPO_PUBLIC_APP_ENV;
    else process.env.EXPO_PUBLIC_APP_ENV = originalAppEnv;
    if (originalFixture === undefined) delete process.env.EXPO_PUBLIC_COMPONENT_C_DEV_FIXTURE;
    else process.env.EXPO_PUBLIC_COMPONENT_C_DEV_FIXTURE = originalFixture;
  }
});

test('nextTask relays prompt_payload, interactive_assets and valid_action_space verbatim from the exemplar entry', async () => {
  await withDevFixtureEnv('active', async () => {
    const api = createComponentCApi();
    const task = await api.nextTask('dev-c-session-new-opaque', 'dev-token');

    // Verbatim relay, asserted by direct comparison against the same artefact-driven loader
    // nextTask itself uses -- not merely structural plausibility.
    const exemplar = loadFixtureTaskExemplar();
    assert.equal(task.game_task_template_id, exemplar.game_task_template_id);
    assert.equal(task.difficulty_level, exemplar.difficulty_level);
    assert.deepEqual(task.prompt_payload, exemplar.prompt_payload);
    assert.deepEqual(task.interactive_assets, exemplar.interactive_assets);
    assert.deepEqual(task.valid_action_space, exemplar.valid_action_space);
    assert.ok(Object.keys(task.valid_action_space).length > 0, 'valid_action_space must not be empty');

    // Fixture-supplied marker fields, per owner correction 2026-08-24: real vocabulary where one
    // exists, honest markers where none does.
    assert.equal(task.technical_status, 'OK');
    assert.equal(task.scaffold_state, 'C0');
    assert.equal(task.task_index, 1);
    assert.equal(task.representation_mode, 'TEST_FIXTURE_ONLY_REPRESENTATION');
    assert.equal(task.game_family_id, 'development-fixture-only');
    assert.equal(task.skill_id, 'development-fixture-only');
  });
});

test('submitAction returns a canned CSubmitActionResult; response_matched is a fixture value, not a computed verdict', async () => {
  await withDevFixtureEnv('active', async () => {
    const api = createComponentCApi();
    const result = await api.submitAction('dev-c-session-new-opaque', 'dev-c-task-fixture-only', { action_payload: {} }, 'dev-token');
    assert.equal(typeof result.response_matched, 'boolean');
    assert.equal(result.scaffold_level, 'C0');
    assert.ok(result.request_id.length > 0);
  });
});

// abandonSession and completeSession are asserted to throw INDIVIDUALLY -- 10.0a's own build-log
// entry records that per-item assertions caught a gap a reconciled test count did not. The owner
// ruling that lets nextTask/submitAction serve task content says nothing about these two, and
// that silence must not be read as an invitation to widen it.
test('abandonSession still throws under the dev fixture', async () => {
  await withDevFixtureEnv('active', async () => {
    const api = createComponentCApi();
    await assert.rejects(() => api.abandonSession('dev-c-session-new-opaque', 'dev-token'));
  });
});

test('completeSession still throws under the dev fixture', async () => {
  await withDevFixtureEnv('active', async () => {
    const api = createComponentCApi();
    await assert.rejects(() =>
      api.completeSession('dev-c-session-new-opaque', { attendance_status: 'attended' }, 'dev-token'),
    );
  });
});
