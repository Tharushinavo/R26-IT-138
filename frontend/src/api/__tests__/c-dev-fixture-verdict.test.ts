// EXPO_PUBLIC_COMPONENT_C_DEV_FIXTURE_VERDICT (component-c-api.ts) -- lets the dev fixture's
// `submitAction` return `correct`, `incorrect`, or `alternate` (a walkable retry cycle), so the
// feedback + retry loop can be exercised in a browser without a real backend. See that file's own
// comment for why this is still not evaluation: the env var selects which fixed literal comes
// back, never a comparison against the submitted payload.

import assert from 'node:assert/strict';
import { test } from 'node:test';

import { createComponentCApi } from '@/src/api/component-c-api';

// MUST be async and MUST `await run()` before restoring env in `finally` -- an earlier version of
// this helper was a plain (synchronous) function that called `return run()` without awaiting it.
// Since `run` is always an async callback, that version returned control to the caller (and hit
// `finally`, restoring the env vars) the instant `run` reached its own first `await` -- which, for
// every callback below, is the very first line (`await api.submitAction(...)`). The result: every
// assertion in every callback actually ran AFTER the env vars had already been reset to their
// original values, not while the intended verdict was active. Caught because the "incorrect" and
// "alternate" tests below could not have passed by coincidence the way "correct" and "unset" could
// -- their expected values (`false`, escalating levels) do not match the default fixture behaviour,
// so the bug surfaced immediately as real assertion failures rather than a silent false pass.
async function withDevFixtureEnv<T>(verdict: string | undefined, run: () => Promise<T>): Promise<T> {
  const originalAppEnv = process.env.EXPO_PUBLIC_APP_ENV;
  const originalFixture = process.env.EXPO_PUBLIC_COMPONENT_C_DEV_FIXTURE;
  const originalVerdict = process.env.EXPO_PUBLIC_COMPONENT_C_DEV_FIXTURE_VERDICT;
  process.env.EXPO_PUBLIC_APP_ENV = 'development';
  process.env.EXPO_PUBLIC_COMPONENT_C_DEV_FIXTURE = 'active';
  if (verdict === undefined) delete process.env.EXPO_PUBLIC_COMPONENT_C_DEV_FIXTURE_VERDICT;
  else process.env.EXPO_PUBLIC_COMPONENT_C_DEV_FIXTURE_VERDICT = verdict;
  try {
    return await run();
  } finally {
    if (originalAppEnv === undefined) delete process.env.EXPO_PUBLIC_APP_ENV;
    else process.env.EXPO_PUBLIC_APP_ENV = originalAppEnv;
    if (originalFixture === undefined) delete process.env.EXPO_PUBLIC_COMPONENT_C_DEV_FIXTURE;
    else process.env.EXPO_PUBLIC_COMPONENT_C_DEV_FIXTURE = originalFixture;
    if (originalVerdict === undefined) delete process.env.EXPO_PUBLIC_COMPONENT_C_DEV_FIXTURE_VERDICT;
    else process.env.EXPO_PUBLIC_COMPONENT_C_DEV_FIXTURE_VERDICT = originalVerdict;
  }
}

test('unset (and default) verdict preserves today\'s behaviour -- always matched, C0', async () => {
  await withDevFixtureEnv(undefined, async () => {
    const api = createComponentCApi();
    const result = await api.submitAction('s', 't', { action_payload: {} }, 'tok');
    assert.equal(result.response_matched, true);
    assert.equal(result.scaffold_level, 'C0');
  });
});

test('an unrecognised verdict string falls back to "correct" rather than throwing or defaulting silently to incorrect', async () => {
  await withDevFixtureEnv('not-a-real-verdict', async () => {
    const api = createComponentCApi();
    const result = await api.submitAction('s', 't', { action_payload: {} }, 'tok');
    assert.equal(result.response_matched, true);
  });
});

test('"correct" always returns matched, every call', async () => {
  await withDevFixtureEnv('correct', async () => {
    const api = createComponentCApi();
    for (let i = 0; i < 3; i += 1) {
      const result = await api.submitAction('s', 't', { action_payload: {} }, 'tok');
      assert.equal(result.response_matched, true);
    }
  });
});

test('"incorrect" always returns not-matched, and escalates scaffold_level across repeated calls', async () => {
  await withDevFixtureEnv('incorrect', async () => {
    const api = createComponentCApi();
    const levels: string[] = [];
    for (let i = 0; i < 5; i += 1) {
      const result = await api.submitAction('s', 't', { action_payload: {} }, 'tok');
      assert.equal(result.response_matched, false);
      levels.push(result.scaffold_level);
    }
    assert.deepEqual(levels, ['C0', 'C1', 'C2', 'C3', 'C4']);
  });
});

test('"incorrect" never exceeds C4, even past five calls -- the vocabulary ceiling holds', async () => {
  await withDevFixtureEnv('incorrect', async () => {
    const api = createComponentCApi();
    let lastLevel = '';
    for (let i = 0; i < 8; i += 1) {
      const result = await api.submitAction('s', 't', { action_payload: {} }, 'tok');
      lastLevel = result.scaffold_level;
    }
    assert.equal(lastLevel, 'C4');
  });
});

test('"alternate" walks not-matched, matched, not-matched, matched -- a full retry cycle', async () => {
  await withDevFixtureEnv('alternate', async () => {
    const api = createComponentCApi();
    const submit = () => api.submitAction('s', 't', { action_payload: {} }, 'tok');

    const first = await submit();
    assert.equal(first.response_matched, false);
    assert.equal(first.scaffold_level, 'C0');

    const second = await submit();
    assert.equal(second.response_matched, true);

    const third = await submit();
    assert.equal(third.response_matched, false);
    assert.equal(third.scaffold_level, 'C1', 'the not-matched scaffold level should escalate across cycles');

    const fourth = await submit();
    assert.equal(fourth.response_matched, true);
  });
});

// The structural proof this is still not evaluation: no branch of submitAction reads the `body`
// (the submitted action_payload) it is called with, at all -- the verdict comes only from the env
// var and each fixture instance's own internal call counter, never from what was actually handed
// to it. Compared here across two INDEPENDENT api instances (independent counters), each called
// exactly once, so the comparison isolates payload content as the only difference -- `alternate`'s
// own call-count-based flip (proven above) is not a confound here, since both calls are each the
// first call of their own instance.
test('submitAction ignores its own submitted payload entirely, regardless of verdict mode', async () => {
  for (const verdict of ['correct', 'incorrect', 'alternate'] as const) {
    // eslint-disable-next-line no-await-in-loop -- sequential by design, isolating env per verdict
    await withDevFixtureEnv(verdict, async () => {
      const withEmptyPayload = await createComponentCApi().submitAction(
        's',
        't',
        { action_payload: {} },
        'tok',
      );
      const withDifferentPayload = await createComponentCApi().submitAction(
        's',
        't',
        { action_payload: { anything: 'goes-here-but-must-not-matter' } },
        'tok',
      );
      // Whatever this verdict mode returns on a first call, it must be identical regardless of
      // payload content -- a real evaluation would differ based on what was submitted; this
      // fixture must not.
      assert.equal(withEmptyPayload.response_matched, withDifferentPayload.response_matched);
      assert.equal(withEmptyPayload.scaffold_level, withDifferentPayload.scaffold_level);
    });
  }
});
