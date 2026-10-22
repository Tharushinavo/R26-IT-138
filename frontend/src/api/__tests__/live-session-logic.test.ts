import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, resolve } from 'node:path';

// Lives in src/api/__tests__/ because that is the glob `npm run test:contract` runs.
// live-session-logic.ts is pure and imports nothing from react/react-native/expo, so this needs
// none of the module patching pending-session-command.test.ts requires. The screen and the three
// renderer components are not covered here — they are layout only, and RNTL is Batch 15.
import type { PendingSessionCommand, PendingSubmitResponseCommand } from '@/src/api/contracts';
import { ApiClientError } from '@/src/api/errors';
import type {
  AttemptResponse,
  OpportunityPresentationResponse,
} from '@/src/api/generated/openapi-types';
import { isPresentationAckResponse } from '@/src/api/runtime-validation';
import {
  classifyAttemptOutcome,
  classifyFailure,
  decidePendingReplay,
  failureRequestId,
  formatSkillLabel,
  initialAnswerState,
  outcomeView,
  planPresentation,
  readPromptInstruction,
  readPromptStem,
} from '@/src/features/session/live-session-logic';
import { encodeSubmittedValue } from '@/src/features/session/renderers/encode';
import { acceptLanguageHeader, readLearnerLocale } from '@/src/config/locale';

const here = dirname(fileURLToPath(import.meta.url));
const frontendRoot = resolve(here, '..', '..', '..');

// --- skill label ------------------------------------------------------------------------------

test('formatSkillLabel underscore-splits and title-cases a skill id', () => {
  assert.equal(formatSkillLabel('number_sense'), 'Number Sense');
  assert.equal(formatSkillLabel('place_value_to_1000'), 'Place Value To 1000');
  assert.equal(formatSkillLabel('addition'), 'Addition');
});

test('formatSkillLabel normalizes casing rather than trusting the id', () => {
  assert.equal(formatSkillLabel('NUMBER_SENSE'), 'Number Sense');
  assert.equal(formatSkillLabel('Number_Sense'), 'Number Sense');
});

test('formatSkillLabel degrades to an empty string instead of throwing on a blank id', () => {
  assert.equal(formatSkillLabel(''), '');
  assert.equal(formatSkillLabel('___'), '');
  assert.equal(formatSkillLabel('   '), '');
});

// --- prompt stem --------------------------------------------------------------------------------

test('readPromptStem takes only the stem and ignores every other prompt key', () => {
  assert.equal(
    readPromptStem({ stem: 'What is 12 + 3?', numbers: [12, 3], direction: 'ascending' }),
    'What is 12 + 3?',
  );
});

test('readPromptStem returns null for a missing, non-string or blank stem', () => {
  assert.equal(readPromptStem({}), null);
  assert.equal(readPromptStem({ stem: 42 }), null);
  assert.equal(readPromptStem({ stem: '   ' }), null);
});

// --- planPresentation ----------------------------------------------------------------------------

function presentation(
  overrides: Partial<OpportunityPresentationResponse> = {},
): OpportunityPresentationResponse {
  return {
    difficulty_level: 'CORE',
    grade: 3,
    item_instance_id: 'item-instance-1',
    item_opportunity_id: 'opportunity-1',
    presentation_token: 'token-1',
    presented_choices: ['10', '3', '9', '100'],
    prompt: { stem: 'Which number is largest?' },
    representation_type: 'numeral',
    request_id: 'req-present-1',
    response_format: 'single_integer',
    server_timeout_deadline_utc: '2026-07-29T12:05:00Z',
    skill_id: 'number_sense',
    ...overrides,
  };
}

// planPresentation takes the request id separately (see its own comment): the inline question on
// an advance response is an OpportunityPresentationFields with no request_id of its own. These
// cases all come from POST /opportunities, so they pass that response's own request id.
function planFor(response: OpportunityPresentationResponse) {
  return planPresentation(response, response.request_id);
}

// --- presentation acknowledgement ------------------------------------------------------------------
//
// The call that starts the answering clock at the render. Its response carries the server's
// anchored deadline, which the screen adopts in place of the selection-time one.

test('the acknowledgement response validator requires a usable deadline', () => {
  const ok = {
    item_opportunity_id: 'opportunity-1',
    server_timeout_deadline_utc: '2026-09-27T12:05:00Z',
    anchored: true,
    request_id: 'req-ack-1',
  };
  assert.equal(isPresentationAckResponse(ok), true);
  // A replay is a valid response, not a failure -- it simply did not anchor.
  assert.equal(isPresentationAckResponse({ ...ok, anchored: false }), true);

  assert.equal(isPresentationAckResponse({ ...ok, server_timeout_deadline_utc: '' }), false);
  assert.equal(isPresentationAckResponse({ ...ok, item_opportunity_id: '' }), false);
  assert.equal(isPresentationAckResponse({ ...ok, anchored: 'yes' }), false);
  assert.equal(isPresentationAckResponse({ ...ok, request_id: undefined }), false);
  assert.equal(isPresentationAckResponse(null), false);
});

test('the session screen acknowledges once per opportunity and adopts the anchored deadline', () => {
  const source = readFileSync(resolve(frontendRoot, 'src/features/session/live-session-screen.tsx'), 'utf-8');
  // Only from the rendered question -- acknowledging a loading or failed phase would start the
  // clock on something the child cannot see, which is the whole bug this closes.
  assert.match(source, /if \(phase\.kind !== 'question' \|\| !api\) return;/);
  // Guarded so a re-render does not re-send.
  assert.match(source, /ackedOpportunityRef\.current === opportunityId/);
  // The server's deadline replaces the selection-time one.
  assert.match(source, /timeoutDeadlineUtc: ack\.server_timeout_deadline_utc/);
});

// --- the authored instruction sentence ------------------------------------------------------------
//
// Server-supplied, for the few templates whose stem is not a question on its own (a bare
// "2, 3, 4, __"). The app relays it and never composes one -- see the backend's
// app/domain/live_engine/prompt_instructions.py.

test('readPromptInstruction accepts a real sentence and rejects anything else', () => {
  assert.equal(readPromptInstruction({ instruction: 'Guess the next number.' }), 'Guess the next number.');
  assert.equal(readPromptInstruction({ instruction: '  Guess the next number.  ' }), 'Guess the next number.');
  assert.equal(readPromptInstruction({ instruction: '   ' }), null);
  assert.equal(readPromptInstruction({ instruction: '' }), null);
  assert.equal(readPromptInstruction({ instruction: 42 }), null);
  assert.equal(readPromptInstruction({ instruction: null }), null);
  assert.equal(readPromptInstruction({ stem: 'no instruction here' }), null);
  assert.equal(readPromptInstruction({}), null);
});

test('planPresentation carries the instruction through when the server sends one', () => {
  const plan = planFor(
    presentation({ prompt: { stem: '2, 3, 4, __', instruction: 'Guess the next number.', blank_position: 'terminal' } }),
  );
  assert.equal(plan.kind, 'render');
  if (plan.kind !== 'render') return;
  assert.equal(plan.instruction, 'Guess the next number.');
  // The stem is still the stem: the instruction is additive, never a replacement.
  assert.equal(plan.stem, '2, 3, 4, __');
});

test('a missing instruction is null and never blocks the question', () => {
  const plan = planFor(presentation());
  assert.equal(plan.kind, 'render');
  if (plan.kind !== 'render') return;
  // Unlike a missing stem, this is the normal case for most templates -- still 'render'.
  assert.equal(plan.instruction, null);
});

test('an item with an instruction but no stem is still unrenderable', () => {
  const plan = planFor(presentation({ prompt: { instruction: 'Guess the next number.' } }));
  assert.equal(plan.kind, 'unrenderable');
  if (plan.kind !== 'unrenderable') return;
  assert.equal(plan.reason, 'missing-stem');
});

test('planPresentation renders a known format with its stem, skill label and spec', () => {
  const plan = planFor(presentation());
  assert.equal(plan.kind, 'render');
  if (plan.kind !== 'render') return;
  assert.equal(plan.stem, 'Which number is largest?');
  assert.equal(plan.skillLabel, 'Number Sense');
  assert.equal(plan.itemOpportunityId, 'opportunity-1');
  assert.equal(plan.spec.kind, 'choice');
  assert.equal(plan.spec.expectedChoiceCount, 4);
});

test('planPresentation preserves server-given choice order, unsorted', () => {
  // The server sorts lexicographically, so 10, 3, 9 is what a child legitimately sees. Re-sorting
  // here would be the client transforming server data (backend Risk 1, tracked separately).
  const plan = planFor(presentation({ presented_choices: ['10', '3', '9', '100'] }));
  assert.equal(plan.kind, 'render');
  if (plan.kind !== 'render' || plan.spec.kind !== 'choice') return;
  assert.deepEqual(plan.spec.choices, ['10', '3', '9', '100']);
});

test('planPresentation does not branch on representation_type', () => {
  const numeral = planFor(presentation({ representation_type: 'numeral' }));
  const other = planFor(presentation({ representation_type: 'some_future_form' }));
  assert.equal(numeral.kind, 'render');
  assert.equal(other.kind, 'render');
});

test('planPresentation fails closed on an unknown response_format', () => {
  const plan = planFor(presentation({ response_format: 'not_a_real_format' }));
  assert.equal(plan.kind, 'unrenderable');
  if (plan.kind !== 'unrenderable') return;
  assert.equal(plan.reason, 'unsupported-format');
  assert.equal(plan.requestId, 'req-present-1');
});

test('planPresentation fails closed on a choice-count mismatch', () => {
  const plan = planFor(
    presentation({ response_format: 'relation_choice', presented_choices: ['a', 'b', 'c', 'd'] }),
  );
  assert.equal(plan.kind, 'unrenderable');
});

test('planPresentation fails closed on a non-choice format that arrived with choices', () => {
  const plan = planFor(
    presentation({ response_format: 'expanded_form', presented_choices: ['100 + 20 + 3'] }),
  );
  assert.equal(plan.kind, 'unrenderable');
});

test('planPresentation fails closed on a missing stem, distinguishably from a format problem', () => {
  const plan = planFor(presentation({ prompt: { numbers: [1, 2] } }));
  assert.equal(plan.kind, 'unrenderable');
  if (plan.kind !== 'unrenderable') return;
  assert.equal(plan.reason, 'missing-stem');
});

test('planPresentation renders the free-entry and count-selection formats', () => {
  const freeEntry = planFor(
    presentation({ response_format: 'expanded_form', presented_choices: [] }),
  );
  const countSelection = planFor(
    presentation({ response_format: 'interactive_set_selection', presented_choices: [] }),
  );
  assert.equal(freeEntry.kind === 'render' && freeEntry.spec.kind, 'free-entry');
  assert.equal(countSelection.kind === 'render' && countSelection.spec.kind, 'count-selection');
});

// --- initial answer state -------------------------------------------------------------------------

test('initialAnswerState seeds each surface as not-yet-answered, so submit starts unavailable', () => {
  for (const [responseFormat, choices] of [
    ['single_choice', ['a', 'b', 'c', 'd']],
    ['expanded_form', []],
    ['interactive_set_selection', []],
  ] as const) {
    const plan = planFor(presentation({ response_format: responseFormat, presented_choices: [...choices] }));
    assert.equal(plan.kind, 'render');
    if (plan.kind !== 'render') return;
    const seed = initialAnswerState(plan.spec);
    assert.equal(
      encodeSubmittedValue(plan.spec, seed),
      null,
      `${responseFormat} must start with nothing submittable`,
    );
  }
});

test('a count of 0 is a real, submittable answer — only the -1 seed is not', () => {
  const plan = planFor(
    presentation({ response_format: 'interactive_set_selection', presented_choices: [] }),
  );
  assert.equal(plan.kind, 'render');
  if (plan.kind !== 'render') return;
  assert.equal(encodeSubmittedValue(plan.spec, { kind: 'count-selection', count: 0 }), '0');
  assert.equal(encodeSubmittedValue(plan.spec, { kind: 'count-selection', count: -1 }), null);
});

// --- pending-command replay -----------------------------------------------------------------------

const savedSubmit: PendingSubmitResponseCommand = {
  body: { client_elapsed_ms: 4231, submitted_value: '7' },
  createdAt: '2026-07-29T12:00:00.000Z',
  endpoint: '/api/v1/b/sessions/{sessionId}/opportunities/{itemOpportunityId}/responses',
  idempotencyKey: 'key-1',
  itemOpportunityId: 'opportunity-1',
  kind: 'submit_response',
  sessionId: 'session-1',
};

test('decidePendingReplay replays a saved submit for the same opportunity, verbatim', () => {
  const decision = decidePendingReplay(savedSubmit, 'session-1', 'opportunity-1');
  assert.equal(decision.action, 'replay');
  if (decision.action !== 'replay') return;
  // Same key AND same body: the key makes the server return the original attempt instead of
  // recording a second one, and the body must be the saved one because the server fingerprints it
  // into the idempotency record.
  assert.equal(decision.command.idempotencyKey, 'key-1');
  assert.deepEqual(decision.command.body, { client_elapsed_ms: 4231, submitted_value: '7' });
  assert.equal(decision.command, savedSubmit);
});

test('decidePendingReplay discards a saved submit for a different opportunity', () => {
  assert.deepEqual(decidePendingReplay(savedSubmit, 'session-1', 'opportunity-2'), {
    action: 'discard',
  });
});

test('decidePendingReplay discards a saved submit for a different session', () => {
  assert.deepEqual(decidePendingReplay(savedSubmit, 'session-2', 'opportunity-1'), {
    action: 'discard',
  });
});

test('decidePendingReplay leaves commands of other kinds alone (the store slot is shared)', () => {
  const startCommand: PendingSessionCommand = {
    createdAt: '2026-07-29T11:59:00.000Z',
    endpoint: '/api/v1/b/sessions',
    idempotencyKey: 'start-key',
    kind: 'start_session',
  };
  assert.deepEqual(decidePendingReplay(startCommand, 'session-1', 'opportunity-1'), { action: 'none' });
  assert.deepEqual(decidePendingReplay(null, 'session-1', 'opportunity-1'), { action: 'none' });
});

// --- outcome classification -------------------------------------------------------------------------

function attempt(overrides: Partial<AttemptResponse> = {}): AttemptResponse {
  return {
    attempt_index: 1,
    event_kind: 'RESPONSE',
    item_opportunity_id: 'opportunity-1',
    request_id: 'req-attempt-1',
    response_matched: true,
    server_submitted_at_utc: '2026-07-29T12:01:00Z',
    ...overrides,
  } as AttemptResponse;
}

test('classifyAttemptOutcome maps a matched RESPONSE to correct', () => {
  assert.equal(classifyAttemptOutcome(attempt({ response_matched: true })), 'correct');
});

test('classifyAttemptOutcome maps an unmatched RESPONSE to incorrect', () => {
  assert.equal(classifyAttemptOutcome(attempt({ response_matched: false })), 'incorrect');
});

test('classifyAttemptOutcome maps a TIMEOUT to timeout, never to incorrect', () => {
  const timedOut = attempt({ event_kind: 'TIMEOUT', response_matched: null });
  assert.equal(classifyAttemptOutcome(timedOut), 'timeout');
  assert.notEqual(classifyAttemptOutcome(timedOut), 'incorrect');
});

test('a timeout is not presented as a wrong answer and does not offer a retry', () => {
  const view = outcomeView('timeout');
  assert.equal(view.canTryAgain, false);
  const copy = `${view.title} ${view.detail}`.toLowerCase();
  for (const blaming of ['wrong', 'incorrect', 'missed', 'failed']) {
    assert.ok(!copy.includes(blaming), `timeout copy must not say "${blaming}"`);
  }
});

test('an incorrect answer always offers another try — there is no client-side attempt cap', () => {
  assert.equal(outcomeView('incorrect').canTryAgain, true);
  assert.equal(outcomeView('correct').canTryAgain, false);
});

// --- failure classification ----------------------------------------------------------------------

test('classifyFailure routes a 409 to the resync path', () => {
  assert.equal(classifyFailure(new ApiClientError('conflict', 'conflict', 409, 'req-409')), 'conflict');
});

test('classifyFailure groups the remaining API failures', () => {
  assert.equal(classifyFailure(new ApiClientError('unauthenticated', 'x', 401)), 'authentication');
  assert.equal(classifyFailure(new ApiClientError('forbidden', 'x', 403)), 'authentication');
  assert.equal(classifyFailure(new ApiClientError('network', 'x')), 'network');
  assert.equal(classifyFailure(new ApiClientError('timeout', 'x')), 'network');
  assert.equal(classifyFailure(new ApiClientError('server', 'x', 500)), 'technical');
  assert.equal(classifyFailure(new ApiClientError('invalid-response', 'x')), 'technical');
});

test('classifyFailure treats a non-API error as technical rather than guessing', () => {
  assert.equal(classifyFailure(new Error('boom')), 'technical');
  assert.equal(classifyFailure(null), 'technical');
});

test('failureRequestId surfaces the support code only when the server sent one', () => {
  assert.equal(failureRequestId(new ApiClientError('server', 'x', 500, 'req-500')), 'req-500');
  assert.equal(failureRequestId(new ApiClientError('network', 'x')), null);
  assert.equal(failureRequestId(new Error('boom')), null);
});

// --- learner locale --------------------------------------------------------------------------
//
// The app never translates a question; it says which language it wants and relays whatever the
// server sends. These pin the fallback that keeps unreviewed Sinhala away from a child by default.

test('the learner locale is English unless deliberately set', () => {
  const previous = process.env.EXPO_PUBLIC_LEARNER_LOCALE;
  try {
    delete process.env.EXPO_PUBLIC_LEARNER_LOCALE;
    assert.equal(readLearnerLocale(), 'en');
    process.env.EXPO_PUBLIC_LEARNER_LOCALE = '';
    assert.equal(readLearnerLocale(), 'en');
    // A typo must not silently ship a half-translated build.
    process.env.EXPO_PUBLIC_LEARNER_LOCALE = 'sinhala';
    assert.equal(readLearnerLocale(), 'en');
    process.env.EXPO_PUBLIC_LEARNER_LOCALE = 'ta';
    assert.equal(readLearnerLocale(), 'en');
  } finally {
    if (previous === undefined) delete process.env.EXPO_PUBLIC_LEARNER_LOCALE;
    else process.env.EXPO_PUBLIC_LEARNER_LOCALE = previous;
  }
});

test('Sinhala is accepted in both bare and regional form, and negotiates down to English', () => {
  const previous = process.env.EXPO_PUBLIC_LEARNER_LOCALE;
  try {
    for (const value of ['si', 'si-LK', 'SI', ' si ']) {
      process.env.EXPO_PUBLIC_LEARNER_LOCALE = value;
      assert.equal(readLearnerLocale(), 'si', value);
    }
    // English is offered at lower priority so an item with no Sinhala wording can still resolve.
    const header = acceptLanguageHeader('si');
    assert.match(header, /^si-LK,si;q=0\.9,en;q=0\.5$/);
    assert.equal(acceptLanguageHeader('en'), 'en');
  } finally {
    if (previous === undefined) delete process.env.EXPO_PUBLIC_LEARNER_LOCALE;
    else process.env.EXPO_PUBLIC_LEARNER_LOCALE = previous;
  }
});

// --- pre-advance -----------------------------------------------------------------------------
//
// The next question is requested while the child reads the verdict, so "Next question" renders
// instead of waiting. Its safety rests entirely on one invariant: advancing CLOSES the current
// opportunity, so it must never run while the child can still retry that same question.

test('only terminal outcomes forgo a retry, which is what gates the pre-advance', () => {
  // If this ever flips for 'incorrect', the pre-advance would close a question out from under a
  // child about to press TRY AGAIN, and the retry would hit a server that has moved on.
  assert.equal(outcomeView('incorrect').canTryAgain, true);
  assert.equal(outcomeView('correct').canTryAgain, false);
  assert.equal(outcomeView('timeout').canTryAgain, false);
});

test('the session screen pre-advances only when the child cannot try again', () => {
  const source = readFileSync(resolve(frontendRoot, 'src/features/session/live-session-screen.tsx'), 'utf-8');
  const effect = source.slice(source.indexOf('// PRE-ADVANCE.'), source.indexOf('const tryAgain'));
  assert.ok(effect.length > 0, 'the pre-advance effect must exist');
  // 2026-10-10: the body moved into `primeAdvance` so a press-in can reuse it (see
  // b-pre-advance-intent.test.ts). The PROPERTY is unchanged -- the automatic pre-advance still
  // fires only for an outcome the child cannot retry -- so this matches the guard rather than the
  // exact expression it used to be written as.
  assert.match(effect, /outcomeView\(outcome\)\.canTryAgain\) return;/);
  // Only from a rendered question with a verdict on screen.
  assert.match(effect, /phase\.kind !== 'question' \|\| outcome === null/);
  // Keyed per opportunity, so a finished question's advance can never be applied to a new one.
  assert.match(effect, /advancePrefetchRef\.current\?\.itemOpportunityId === itemOpportunityId/);
});

test('a failed pre-advance is retried under its ORIGINAL idempotency key, never a fresh one', () => {
  // The fingerprint is {session_id, item_opportunity_id}: replaying the same key returns the
  // original advance, while a new key risks closing the opportunity twice and skipping a question.
  const source = readFileSync(resolve(frontendRoot, 'src/features/session/live-session-screen.tsx'), 'utf-8');
  assert.match(source, /const command = prefetched\?\.command \?\? buildAdvanceCommand\(itemOpportunityId\)/);
  // The retry path reuses `command`, and does not build a second one.
  // Bounded to `advance` itself: the pre-advance effect below it builds the FIRST command and
  // legitimately calls the same helper, so a looser slice would count two.
  const advanceBody = source.slice(
    source.indexOf('const advance = useCallback'),
    source.indexOf('// PRE-ADVANCE.'),
  );
  assert.equal((advanceBody.match(/buildAdvanceCommand\(/g) ?? []).length, 1);
  assert.match(advanceBody, /response = await sendAdvance\(command\);/);
});
