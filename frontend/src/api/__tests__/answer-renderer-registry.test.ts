import { test } from 'node:test';
import assert from 'node:assert/strict';

// Lives in src/api/__tests__/ because that is the glob `npm run test:contract` runs. The registry
// modules themselves import nothing from react-native, so this stays a plain node:test file with
// no module patching (unlike pending-session-command.test.ts).
import { resolveRenderer } from '@/src/features/session/renderers/registry';
import { encodeSubmittedValue } from '@/src/features/session/renderers/encode';
import type { RendererSpec } from '@/src/features/session/renderers/types';

// Placeholder choice strings only. Real relation symbols and conservation words are catalogue
// content that arrives in presented_choices; nothing in src/ restates them, and neither does this
// file beyond the round-trip cases that assert verbatim relay.
const fourChoices = ['a', 'b', 'c', 'd'];
const threeChoices = ['x', 'y', 'z'];
const twoChoices = ['p', 'q'];

const CHOICE_FORMATS: readonly (readonly [string, string[]])[] = [
  ['single_integer', fourChoices],
  ['single_integer_or_choice', fourChoices],
  ['single_choice_or_integer', fourChoices],
  ['single_choice', fourChoices],
  ['ordered_list', fourChoices],
  ['relation_choice', threeChoices],
  ['binary_or_choice', twoChoices],
];

function resolveOrThrow(responseFormat: string, choices: readonly string[]): RendererSpec {
  const spec = resolveRenderer(responseFormat, choices);
  assert.ok(spec, `expected ${responseFormat} to resolve`);
  return spec;
}

// --- resolveRenderer: all nine formats -------------------------------------------------------

for (const [responseFormat, choices] of CHOICE_FORMATS) {
  test(`resolveRenderer resolves ${responseFormat} as a choice surface with ${choices.length} choices`, () => {
    const spec = resolveOrThrow(responseFormat, choices);
    assert.equal(spec.kind, 'choice');
    assert.equal(spec.responseFormat, responseFormat);
    assert.equal(spec.expectedChoiceCount, choices.length);
    assert.deepEqual(spec.kind === 'choice' ? spec.choices : null, choices);
  });
}

test('resolveRenderer resolves expanded_form as a free-entry surface with no choices', () => {
  const spec = resolveOrThrow('expanded_form', []);
  assert.equal(spec.kind, 'free-entry');
  assert.equal(spec.responseFormat, 'expanded_form');
  assert.equal(spec.expectedChoiceCount, 0);
});

test('resolveRenderer resolves interactive_set_selection as a count-selection surface with no choices', () => {
  const spec = resolveOrThrow('interactive_set_selection', []);
  assert.equal(spec.kind, 'count-selection');
  assert.equal(spec.responseFormat, 'interactive_set_selection');
  assert.equal(spec.expectedChoiceCount, 0);
});

// --- resolveRenderer: the three fail-closed paths ---------------------------------------------

test('resolveRenderer returns null for an unrecognized response_format', () => {
  assert.equal(resolveRenderer('some_future_format_not_yet_known', fourChoices), null);
  assert.equal(resolveRenderer('', []), null);
  assert.equal(resolveRenderer('SINGLE_CHOICE', fourChoices), null);
});

test('resolveRenderer returns null when a choice format arrives with the wrong choice count', () => {
  assert.equal(resolveRenderer('single_choice', threeChoices), null);
  assert.equal(resolveRenderer('relation_choice', fourChoices), null);
  assert.equal(resolveRenderer('binary_or_choice', threeChoices), null);
  assert.equal(resolveRenderer('ordered_list', []), null);
});

test('resolveRenderer returns null when a non-choice format arrives with choices', () => {
  assert.equal(resolveRenderer('expanded_form', ['100 + 20 + 3']), null);
  assert.equal(resolveRenderer('interactive_set_selection', twoChoices), null);
});

// --- resolveRenderer: prototype-pollution guard ------------------------------------------------

test('resolveRenderer returns null for inherited Object.prototype keys', () => {
  for (const hostile of ['constructor', 'toString', '__proto__', 'hasOwnProperty', 'valueOf']) {
    assert.equal(resolveRenderer(hostile, fourChoices), null, `${hostile} must not resolve`);
    assert.equal(resolveRenderer(hostile, []), null, `${hostile} must not resolve`);
  }
});

// --- resolveRenderer: ordering ------------------------------------------------------------------

test('resolveRenderer returns choices in server-given order, unsorted', () => {
  // The server sorts lexicographically, so a child can legitimately be shown 10, 3, 9. Re-sorting
  // here would be the client transforming server data (backend Risk 1, tracked separately).
  const serverOrder = ['10', '3', '9', '100'];
  const spec = resolveOrThrow('single_integer', serverOrder);
  assert.deepEqual(spec.kind === 'choice' ? spec.choices : null, ['10', '3', '9', '100']);
});

// --- encodeSubmittedValue -----------------------------------------------------------------------

test('encodeSubmittedValue relays a chosen ordered_list value verbatim, spacing untouched', () => {
  const spec = resolveOrThrow('ordered_list', ['12,45,300', '300,45,12', '45,12,300', '12,300,45']);
  assert.equal(encodeSubmittedValue(spec, { kind: 'choice', chosenIndex: 0 }), '12,45,300');
  assert.equal(encodeSubmittedValue(spec, { kind: 'choice', chosenIndex: 1 }), '300,45,12');
});

test('encodeSubmittedValue relays a chosen word verbatim without case folding', () => {
  const spec = resolveOrThrow('binary_or_choice', ['same', 'changed']);
  assert.equal(encodeSubmittedValue(spec, { kind: 'choice', chosenIndex: 0 }), 'same');
  assert.equal(encodeSubmittedValue(spec, { kind: 'choice', chosenIndex: 1 }), 'changed');
});

test('encodeSubmittedValue relays a chosen relation string verbatim', () => {
  const spec = resolveOrThrow('relation_choice', threeChoices);
  assert.equal(encodeSubmittedValue(spec, { kind: 'choice', chosenIndex: 2 }), 'z');
});

test('encodeSubmittedValue leaves a leading-zero choice alone (the server normalizes, not us)', () => {
  const spec = resolveOrThrow('single_integer', ['03', '3', '30', '300']);
  assert.equal(encodeSubmittedValue(spec, { kind: 'choice', chosenIndex: 0 }), '03');
});

test('encodeSubmittedValue returns null for an out-of-range or non-integer choice index', () => {
  const spec = resolveOrThrow('single_choice', fourChoices);
  assert.equal(encodeSubmittedValue(spec, { kind: 'choice', chosenIndex: -1 }), null);
  assert.equal(encodeSubmittedValue(spec, { kind: 'choice', chosenIndex: 4 }), null);
  assert.equal(encodeSubmittedValue(spec, { kind: 'choice', chosenIndex: 1.5 }), null);
});

test('encodeSubmittedValue trims expanded_form input and touches nothing else', () => {
  const spec = resolveOrThrow('expanded_form', []);
  assert.equal(
    encodeSubmittedValue(spec, { kind: 'free-entry', rawInput: ' 100 + 20 + 3 ' }),
    '100 + 20 + 3',
  );
  // No internal whitespace collapsing, no reordering, no case folding.
  assert.equal(
    encodeSubmittedValue(spec, { kind: 'free-entry', rawInput: '100  +  20+3' }),
    '100  +  20+3',
  );
  assert.equal(encodeSubmittedValue(spec, { kind: 'free-entry', rawInput: '3 + 20 + 100' }), '3 + 20 + 100');
});

test('encodeSubmittedValue returns null for a blank expanded_form field', () => {
  const spec = resolveOrThrow('expanded_form', []);
  assert.equal(encodeSubmittedValue(spec, { kind: 'free-entry', rawInput: '' }), null);
  assert.equal(encodeSubmittedValue(spec, { kind: 'free-entry', rawInput: '   ' }), null);
});

test('encodeSubmittedValue stringifies an interactive_set_selection count', () => {
  const spec = resolveOrThrow('interactive_set_selection', []);
  assert.equal(encodeSubmittedValue(spec, { kind: 'count-selection', count: 7 }), '7');
  assert.equal(encodeSubmittedValue(spec, { kind: 'count-selection', count: 0 }), '0');
});

test('encodeSubmittedValue returns null for a negative or non-integer count', () => {
  const spec = resolveOrThrow('interactive_set_selection', []);
  assert.equal(encodeSubmittedValue(spec, { kind: 'count-selection', count: -1 }), null);
  assert.equal(encodeSubmittedValue(spec, { kind: 'count-selection', count: 2.5 }), null);
  assert.equal(encodeSubmittedValue(spec, { kind: 'count-selection', count: Number.NaN }), null);
});

test('encodeSubmittedValue returns null when the answer state does not match the surface', () => {
  const choiceSpec = resolveOrThrow('single_choice', fourChoices);
  const freeEntrySpec = resolveOrThrow('expanded_form', []);
  const countSpec = resolveOrThrow('interactive_set_selection', []);
  assert.equal(encodeSubmittedValue(choiceSpec, { kind: 'free-entry', rawInput: '123' }), null);
  assert.equal(encodeSubmittedValue(freeEntrySpec, { kind: 'choice', chosenIndex: 0 }), null);
  assert.equal(encodeSubmittedValue(countSpec, { kind: 'free-entry', rawInput: '7' }), null);
});
