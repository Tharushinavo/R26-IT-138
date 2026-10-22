// The guard that would have caught the dev-fixture defect: component-c-api.ts's fixture nextTask()
// once omitted `blanks` and `prompt_text` (both required on CNextTaskResponse since 5d2c1ab), which
// `npx tsc --noEmit` alone could not have caught before `typecheck` existed as a script, and which
// nothing at runtime asserted either. This test asserts the fixture's actual output -- not a
// reconstruction of it -- passes isCNextTaskResponse, with negative controls proving the assertion
// is not vacuous: it must fail when a required field is dropped from a copy of that same output.
//
// withDevFixtureEnv mirrors c-dev-fixture-task-loop.test.ts's own helper: save/restore the two env
// vars getDevelopmentFixture() reads, rather than mutating process.env at module scope, since
// `node --test` can run multiple test files in one process.

import { test } from 'node:test';
import assert from 'node:assert/strict';

import { createComponentCApi } from '@/src/api/component-c-api';
import { isCNextTaskResponse } from '@/src/api/runtime-validation';

function withDevFixtureEnv<T>(run: () => T): T {
  const originalAppEnv = process.env.EXPO_PUBLIC_APP_ENV;
  const originalFixture = process.env.EXPO_PUBLIC_COMPONENT_C_DEV_FIXTURE;
  try {
    process.env.EXPO_PUBLIC_APP_ENV = 'development';
    process.env.EXPO_PUBLIC_COMPONENT_C_DEV_FIXTURE = 'active';
    return run();
  } finally {
    if (originalAppEnv === undefined) delete process.env.EXPO_PUBLIC_APP_ENV;
    else process.env.EXPO_PUBLIC_APP_ENV = originalAppEnv;
    if (originalFixture === undefined) delete process.env.EXPO_PUBLIC_COMPONENT_C_DEV_FIXTURE;
    else process.env.EXPO_PUBLIC_COMPONENT_C_DEV_FIXTURE = originalFixture;
  }
}

test('the development fixture\'s nextTask() output passes isCNextTaskResponse', async () => {
  const task = await withDevFixtureEnv(() => {
    const api = createComponentCApi();
    return api.nextTask('dev-c-session-id', 'dev-access-token');
  });
  assert.equal(isCNextTaskResponse(task), true);
});

test('negative control: isCNextTaskResponse rejects the fixture output with blanks dropped', async () => {
  const task = await withDevFixtureEnv(() => {
    const api = createComponentCApi();
    return api.nextTask('dev-c-session-id', 'dev-access-token');
  });
  const { blanks: _omit, ...withoutBlanks } = task;
  assert.equal(isCNextTaskResponse(withoutBlanks), false);
});

test('negative control: isCNextTaskResponse rejects the fixture output with prompt_text dropped', async () => {
  const task = await withDevFixtureEnv(() => {
    const api = createComponentCApi();
    return api.nextTask('dev-c-session-id', 'dev-access-token');
  });
  const { prompt_text: _omit, ...withoutPromptText } = task;
  assert.equal(isCNextTaskResponse(withoutPromptText), false);
});
