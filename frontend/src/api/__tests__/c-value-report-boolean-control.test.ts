// AC 7: C-TC-04 and C-JB-04 each render one extra `exchange_performed` field, and that field is
// derived from `valid_action_space` like any other declared key -- never hardcoded as "the two
// templates with a boolean." Proven by feeding the resolver a synthetic `valid_action_space` shaped
// like a NINTH value-report template under an unrelated key name and asserting it still produces a
// boolean extra field, without the resolver ever comparing against 'C-TC-04' / 'C-JB-04' or
// 'exchange_performed' as literals.

import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, resolve } from 'node:path';

import type { CNextTaskResponse } from '@/src/api/generated/openapi-types';
import { EXEMPLAR_ENTRIES } from '@/src/api/generated/c-prompt-exemplars';
import { resolveValueReportSpec } from '@/src/features/c-session/archetypes/value-report-logic';

function makeTask(overrides: Partial<CNextTaskResponse> = {}): CNextTaskResponse {
  return {
    blanks: null,
    c_task_instance_id: 'task-1',
    difficulty_level: 1,
    game_family_id: 'C-GF-06',
    game_task_template_id: 'C-TC-01',
    interactive_assets: {},
    prompt_payload: { placeholder_value: 1 },
    prompt_text: 'placeholder',
    representation_mode: 'TEST_FIXTURE_ONLY_REPRESENTATION',
    request_id: 'req-1',
    scaffold_state: 'C0',
    skill_id: 'number-sense',
    task_index: 1,
    technical_status: 'OK',
    valid_action_space: { submitted_remainder: 'int' },
    ...overrides,
  };
}

for (const templateId of ['C-TC-04', 'C-JB-04']) {
  test(`${templateId}: real exemplar produces exactly one boolean extra field named exchange_performed`, () => {
    const entry = EXEMPLAR_ENTRIES.find((candidate) => candidate.game_task_template_id === templateId)!;
    const spec = resolveValueReportSpec(
      makeTask({
        game_task_template_id: entry.game_task_template_id,
        prompt_payload: entry.prompt_payload,
        prompt_text: entry.prompt_text,
        valid_action_space: entry.valid_action_space,
      }),
    );
    assert.notEqual(spec, null);
    assert.equal(spec!.extraFields.length, 1);
    assert.equal(spec!.extraFields[0]!.key, 'exchange_performed');
    assert.equal(spec!.extraFields[0]!.binding.kind, 'boolean-control');
  });
}

test('a synthetic ninth value-report shape with a differently-named boolean key still renders a boolean extra field', () => {
  const task = makeTask({
    game_task_template_id: 'C-TC-01',
    valid_action_space: { submitted_remainder: 'int', regrouping_used: 'bool' },
  });
  const spec = resolveValueReportSpec(task);
  assert.notEqual(spec, null);
  assert.equal(spec!.extraFields.length, 1);
  assert.equal(spec!.extraFields[0]!.key, 'regrouping_used');
  assert.equal(spec!.extraFields[0]!.binding.kind, 'boolean-control');
});

test('the resolver never branches on a template id or on the literal string "exchange_performed" (source scan, comment-stripped)', () => {
  const here = dirname(fileURLToPath(import.meta.url));
  const filePath = resolve(here, '..', '..', 'features', 'c-session', 'archetypes', 'value-report-logic.ts');
  const source = readFileSync(filePath, 'utf-8').replace(/\/\*[\s\S]*?\*\//g, '').replace(/\/\/.*$/gm, '');
  assert.equal(/C-TC-04|C-JB-04|exchange_performed/.test(source), false);
});
