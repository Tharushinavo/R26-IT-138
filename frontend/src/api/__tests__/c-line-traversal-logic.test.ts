// `resolveLineTraversalSpec` (10c): resolution over the one approved `line-traversal` template
// (C-JB-02), plus fail-closed negative controls, each proving the guard fires. Also carries a cheap
// regression assertion that C-JB-01/03/04 -- built as `value-report` in 10b -- still resolve there,
// since the master work order's stale §2.3 named C-JB-04 as 10c's own two-layer falsification test;
// that test already passed inside 10b (c-value-report-boolean-control.test.ts), and this file does
// not repeat it, only confirms the archetype table still agrees.

import { test } from 'node:test';
import assert from 'node:assert/strict';

import type { CNextTaskResponse } from '@/src/api/generated/openapi-types';
import { EXEMPLAR_ENTRIES, type ExemplarEntry } from '@/src/api/generated/c-prompt-exemplars';
import { resolveLineTraversalSpec } from '@/src/features/c-session/archetypes/line-traversal-logic';
import { resolveArchetype } from '@/src/features/c-session/archetypes/registry';

function makeTask(entry: ExemplarEntry): CNextTaskResponse {
  return {
    blanks: entry.blanks,
    c_task_instance_id: 'task-1',
    difficulty_level: entry.difficulty_level,
    game_family_id: 'C-GF-05',
    game_task_template_id: entry.game_task_template_id,
    interactive_assets: entry.interactive_assets,
    prompt_payload: entry.prompt_payload,
    prompt_text: entry.prompt_text,
    representation_mode: 'TEST_FIXTURE_ONLY_REPRESENTATION',
    request_id: 'req-1',
    scaffold_state: 'C0',
    skill_id: 'number-sense',
    task_index: 1,
    technical_status: 'OK',
    valid_action_space: entry.valid_action_space,
  };
}

const JB02_ENTRIES = EXEMPLAR_ENTRIES.filter((entry) => entry.game_task_template_id === 'C-JB-02');

test('C-JB-02: exactly 5 exemplar rows (difficulty 1-5), all present in the frozen fixture', () => {
  assert.equal(JB02_ENTRIES.length, 5);
});

test('C-JB-02: resolves at every difficulty level with the correct positionKey/jumpsKey', () => {
  for (const entry of JB02_ENTRIES) {
    const spec = resolveLineTraversalSpec(makeTask(entry));
    if (spec === null) {
      assert.fail(`C-JB-02 level ${entry.difficulty_level} failed to resolve`);
      continue;
    }
    assert.equal(spec.positionKey, 'final_position', `level ${entry.difficulty_level}`);
    assert.equal(spec.jumpsKey, 'jumps', `level ${entry.difficulty_level}`);
    assert.equal(spec.promptText, entry.prompt_text);
    assert.deepEqual(spec.interactiveAssets, entry.interactive_assets);

    const payload = entry.prompt_payload as { addend_a: number; addend_b: number; start: number };
    assert.equal(spec.startValue, payload.start, `level ${entry.difficulty_level}`);
    assert.equal(spec.startValue, Math.max(payload.addend_a, payload.addend_b), `level ${entry.difficulty_level} (start === larger addend)`);
  }
});

test("C-JB-02: `start` is excluded from payloadValues -- rendering it again as a token would duplicate the larger addend's number on screen", () => {
  const entry = JB02_ENTRIES[0]!;
  const spec = resolveLineTraversalSpec(makeTask(entry));
  assert.notEqual(spec, null);
  assert.equal(spec!.payloadValues.some((value) => value.key === 'start'), false);
});

test('C-JB-02: payloadValues carries addend_a/addend_b through, in wire order, each labelled', () => {
  const entry = JB02_ENTRIES[JB02_ENTRIES.length - 1]!; // difficulty 5
  const spec = resolveLineTraversalSpec(makeTask(entry));
  assert.notEqual(spec, null);
  assert.deepEqual(
    spec!.payloadValues.map((value) => value.key),
    ['addend_a', 'addend_b'],
  );
  assert.equal(spec!.payloadValues[0]!.label, 'First number');
  assert.equal(spec!.payloadValues[1]!.label, 'Second number');
});

// --- fail-closed negative controls, each derived from a real, resolving exemplar ------------------

function baseTask(): CNextTaskResponse {
  return makeTask(JB02_ENTRIES[0]!);
}

test('sanity: the base fixture used by every negative control below resolves on its own', () => {
  assert.notEqual(resolveLineTraversalSpec(baseTask()), null);
});

test('fails closed: prompt_text empty', () => {
  const task = baseTask();
  task.prompt_text = '';
  assert.equal(resolveLineTraversalSpec(task), null);
});

test('fails closed: prompt_payload not an object (null)', () => {
  const task = baseTask();
  // @ts-expect-error -- deliberately malformed for the fail-closed control
  task.prompt_payload = null;
  assert.equal(resolveLineTraversalSpec(task), null);
});

test('fails closed: prompt_payload missing the line-origin key ("start")', () => {
  const task = baseTask();
  const { start: _start, ...withoutStart } = task.prompt_payload as Record<string, unknown>;
  task.prompt_payload = withoutStart;
  assert.equal(resolveLineTraversalSpec(task), null);
});

test('fails closed: "start" is not a finite integer (fractional)', () => {
  const task = baseTask();
  task.prompt_payload = { ...task.prompt_payload, start: 2.5 };
  assert.equal(resolveLineTraversalSpec(task), null);
});

test('fails closed: "start" is not a number at all (string)', () => {
  const task = baseTask();
  task.prompt_payload = { ...task.prompt_payload, start: '2' };
  assert.equal(resolveLineTraversalSpec(task), null);
});

test('fails closed: a non-origin prompt_payload value is not a finite number', () => {
  const task = baseTask();
  task.prompt_payload = { ...task.prompt_payload, addend_a: 'two' };
  assert.equal(resolveLineTraversalSpec(task), null);
});

test('fails closed: valid_action_space declares no key', () => {
  const task = baseTask();
  task.valid_action_space = {};
  assert.equal(resolveLineTraversalSpec(task), null);
});

test('fails closed: valid_action_space declares an unbound type', () => {
  const task = baseTask();
  task.valid_action_space = { final_position: 'int', jumps: 'weird_type' };
  assert.equal(resolveLineTraversalSpec(task), null);
});

test('fails closed: two integer-field keys, no list[int] key', () => {
  const task = baseTask();
  task.valid_action_space = { final_position: 'int', another_int: 'int' };
  assert.equal(resolveLineTraversalSpec(task), null);
});

test('fails closed: two list[int] keys, no integer-field key', () => {
  const task = baseTask();
  task.valid_action_space = { jumps: 'list[int]', another_list: 'list[int]' };
  assert.equal(resolveLineTraversalSpec(task), null);
});

test('fails closed: zero integer-field keys and zero list[int] keys (only a bool declared)', () => {
  const task = baseTask();
  task.valid_action_space = { exchange_performed: 'bool' };
  assert.equal(resolveLineTraversalSpec(task), null);
});

test('fails closed: a third declared key of any other kind alongside the required two (this scene has nowhere to render it)', () => {
  const task = baseTask();
  task.valid_action_space = { final_position: 'int', jumps: 'list[int]', extra_flag: 'bool' };
  assert.equal(resolveLineTraversalSpec(task), null);
});

test('fails closed: blanks is not null', () => {
  const task = baseTask();
  task.blanks = 1;
  assert.equal(resolveLineTraversalSpec(task), null);
});

test('resolves: a synthetic differently-named key pair still resolves (proves classification is type-derived, not a hardcoded key-name pair)', () => {
  const task = baseTask();
  task.valid_action_space = { landing_spot: 'int', hops: 'list[int]' };
  const spec = resolveLineTraversalSpec(task);
  assert.notEqual(spec, null);
  assert.equal(spec!.positionKey, 'landing_spot');
  assert.equal(spec!.jumpsKey, 'hops');
});

// --- regression: C-JB-01/03/04 (built in 10b) still resolve to value-report -----------------------
// The falsification-test the master work order's stale §2.3 assigned to 10c (C-JB-04's second
// declared key) already ran inside 10b's own value-report-boolean-control test. This is not a
// repeat of that proof -- only confirmation the archetype table this file's own resolver sits
// beside has not silently drifted.

for (const templateId of ['C-JB-01', 'C-JB-03', 'C-JB-04']) {
  test(`${templateId}: still resolves to 'value-report' (unaffected by line-traversal landing)`, () => {
    const entry = EXEMPLAR_ENTRIES.find((candidate) => candidate.game_task_template_id === templateId)!;
    assert.equal(resolveArchetype(templateId, entry.valid_action_space), 'value-report');
  });
}

test("C-JB-02 resolves to 'line-traversal', not 'value-report'", () => {
  const entry = JB02_ENTRIES[0]!;
  assert.equal(resolveArchetype('C-JB-02', entry.valid_action_space), 'line-traversal');
});
