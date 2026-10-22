// `resolveValueReportSpec` (10b): resolution over the eight approved `value-report` templates
// (C-TC-01/03/04, C-JB-01/03/04, C-EG-03, C-SF-03), plus fail-closed negative controls, each
// proving the guard fires.

import { test } from 'node:test';
import assert from 'node:assert/strict';

import type { CNextTaskResponse } from '@/src/api/generated/openapi-types';
import { EXEMPLAR_ENTRIES, type ExemplarEntry } from '@/src/api/generated/c-prompt-exemplars';
import { resolveValueReportSpec } from '@/src/features/c-session/archetypes/value-report-logic';

const APPROVED_TEMPLATE_IDS = [
  'C-TC-01',
  'C-TC-03',
  'C-TC-04',
  'C-JB-01',
  'C-JB-03',
  'C-JB-04',
  'C-EG-03',
  'C-SF-03',
] as const;

const SCORE_KEY_BY_TEMPLATE: Record<(typeof APPROVED_TEMPLATE_IDS)[number], string> = {
  'C-TC-01': 'submitted_remainder',
  'C-TC-03': 'submitted_difference',
  'C-TC-04': 'submitted_difference',
  'C-JB-01': 'submitted_total',
  'C-JB-03': 'submitted_sum',
  'C-JB-04': 'submitted_sum',
  'C-EG-03': 'submitted_product',
  'C-SF-03': 'submitted_quotient',
};

const BOOLEAN_EXTRA_TEMPLATES = new Set(['C-TC-04', 'C-JB-04']);

function makeTask(entry: ExemplarEntry): CNextTaskResponse {
  return {
    blanks: entry.blanks,
    c_task_instance_id: 'task-1',
    difficulty_level: entry.difficulty_level,
    game_family_id: 'C-GF-06',
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

for (const templateId of APPROVED_TEMPLATE_IDS) {
  const entries = EXEMPLAR_ENTRIES.filter((entry) => entry.game_task_template_id === templateId);

  test(`${templateId}: exactly 5 exemplar rows (difficulty 1-5), all present in the frozen fixture`, () => {
    assert.equal(entries.length, 5);
  });

  test(`${templateId}: resolves at every difficulty level with the correct scoreKey`, () => {
    for (const entry of entries) {
      const spec = resolveValueReportSpec(makeTask(entry));
      if (spec === null) {
        assert.fail(`${templateId} level ${entry.difficulty_level} failed to resolve`);
        continue;
      }
      assert.equal(spec.scoreKey, SCORE_KEY_BY_TEMPLATE[templateId], `${templateId} level ${entry.difficulty_level}`);
      assert.equal(spec.promptText, entry.prompt_text);
      assert.deepEqual(spec.interactiveAssets, entry.interactive_assets);

      // payloadValues carries every prompt_payload entry through, in the wire's own key order,
      // untouched -- the numbers a child needs to see to do the task at all.
      const expectedPayloadEntries = Object.entries(entry.prompt_payload);
      assert.equal(spec.payloadValues.length, expectedPayloadEntries.length, `${templateId} level ${entry.difficulty_level}`);
      spec.payloadValues.forEach((payloadValue, index) => {
        const [expectedKey, expectedValue] = expectedPayloadEntries[index]!;
        assert.equal(payloadValue.key, expectedKey, `${templateId} level ${entry.difficulty_level}`);
        assert.equal(payloadValue.value, expectedValue, `${templateId} level ${entry.difficulty_level}`);
      });

      if (BOOLEAN_EXTRA_TEMPLATES.has(templateId)) {
        assert.equal(spec.extraFields.length, 1, `${templateId} level ${entry.difficulty_level}`);
        assert.equal(spec.extraFields[0]!.key, 'exchange_performed');
        assert.equal(spec.extraFields[0]!.binding.kind, 'boolean-control');
      } else {
        assert.deepEqual(spec.extraFields, []);
      }
    }
  });
}

// --- fail-closed negative controls, each derived from a real, resolving exemplar --------------

function baseTask(): CNextTaskResponse {
  const entry = EXEMPLAR_ENTRIES.find((candidate) => candidate.game_task_template_id === 'C-TC-01')!;
  return makeTask(entry);
}

test('sanity: the base fixture used by every negative control below resolves on its own', () => {
  assert.notEqual(resolveValueReportSpec(baseTask()), null);
});

test('fails closed: prompt_text absent', () => {
  const task = baseTask();
  // @ts-expect-error -- deliberately malformed for the fail-closed control
  delete task.prompt_text;
  assert.equal(resolveValueReportSpec(task), null);
});

test('fails closed: prompt_text empty', () => {
  const task = baseTask();
  task.prompt_text = '';
  assert.equal(resolveValueReportSpec(task), null);
});

test('fails closed: prompt_payload absent', () => {
  const task = baseTask();
  // @ts-expect-error -- deliberately malformed for the fail-closed control
  task.prompt_payload = undefined;
  assert.equal(resolveValueReportSpec(task), null);
});

test('fails closed: prompt_payload not an object (null)', () => {
  const task = baseTask();
  // @ts-expect-error -- deliberately malformed for the fail-closed control
  task.prompt_payload = null;
  assert.equal(resolveValueReportSpec(task), null);
});

test('fails closed: prompt_payload is an empty object', () => {
  const task = baseTask();
  task.prompt_payload = {};
  assert.equal(resolveValueReportSpec(task), null);
});

test('fails closed: prompt_payload contains a non-numeric value', () => {
  const task = baseTask();
  task.prompt_payload = { ...task.prompt_payload, directed: false };
  assert.equal(resolveValueReportSpec(task), null);
});

test('fails closed: valid_action_space declares no key', () => {
  const task = baseTask();
  task.valid_action_space = {};
  assert.equal(resolveValueReportSpec(task), null);
});

test('fails closed: valid_action_space declares an unbound type', () => {
  const task = baseTask();
  task.valid_action_space = { submitted_remainder: 'unbound_type' };
  assert.equal(resolveValueReportSpec(task), null);
});

test('fails closed: two int keys (no single scene key)', () => {
  const task = baseTask();
  task.valid_action_space = { submitted_remainder: 'int', another_total: 'int' };
  assert.equal(resolveValueReportSpec(task), null);
});

test('fails closed: zero int keys (only a boolean declared)', () => {
  const task = baseTask();
  task.valid_action_space = { exchange_performed: 'bool' };
  assert.equal(resolveValueReportSpec(task), null);
});

test('fails closed: an extra declared key bound to a non-boolean kind', () => {
  const task = baseTask();
  task.valid_action_space = { submitted_remainder: 'int', groups: 'list[int]' };
  assert.equal(resolveValueReportSpec(task), null);
});

test('fails closed: blanks is not null', () => {
  const task = baseTask();
  task.blanks = 1;
  assert.equal(resolveValueReportSpec(task), null);
});

test('resolves: a synthetic second boolean-bearing shape (proves the boolean branch is type-derived, not a two-template allowlist)', () => {
  const task = baseTask();
  task.valid_action_space = { submitted_remainder: 'int', some_future_flag: 'bool' };
  const spec = resolveValueReportSpec(task);
  assert.notEqual(spec, null);
  assert.equal(spec!.extraFields.length, 1);
  assert.equal(spec!.extraFields[0]!.key, 'some_future_flag');
});
