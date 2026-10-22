import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, resolve } from 'node:path';

const here = dirname(fileURLToPath(import.meta.url));
const frontendRoot = resolve(here, '..', '..', '..');

// FE-0d removed two authorization bypasses that both keyed off EXPO_PUBLIC_APP_ENV ===
// 'development': app/_layout.tsx forced learner access / skipped onboarding, and app/index.tsx
// unconditionally redirected to (learner)/home. A grep-as-a-test is inelegant, but it is exactly
// what stops this regression class cold — a future "just for dev" shortcut in either file would
// reintroduce an authorization decision keyed off an env var rather than the real auth/onboarding
// status. Do not delete this for being ugly; it is standing in for the fact that neither file has
// any other structural way to prevent the bypass pattern from coming back. A fixture flag (e.g.
// EXPO_PUBLIC_COMPONENT_B_DEV_FIXTURE, still present in component-b-api.ts) may legitimately
// substitute response *data*; it must never flip an authorization *decision*.
const guardedFiles = ['app/_layout.tsx', 'app/index.tsx'];

for (const relativePath of guardedFiles) {
  test(`${relativePath} contains no EXPO_PUBLIC_APP_ENV authorization bypass`, () => {
    const source = readFileSync(resolve(frontendRoot, relativePath), 'utf-8');
    assert.equal(
      source.includes('EXPO_PUBLIC_APP_ENV'),
      false,
      `${relativePath} must not branch authorization on EXPO_PUBLIC_APP_ENV`,
    );
  });
}
