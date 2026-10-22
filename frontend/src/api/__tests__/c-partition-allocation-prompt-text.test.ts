// `prompt_text` is rendered verbatim, never synthesized -- mirroring
// c-ordered-value-sequence-prompt-text.test.ts's own convention. `resolvePartitionAllocationSpec`
// carries `task.prompt_text` through unchanged; this file proves that structurally (no template
// string builds a substitute) and behaviourally (every real exemplar's exact string survives).

import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, resolve } from 'node:path';

import type { CNextTaskResponse } from '@/src/api/generated/openapi-types';
import { EXEMPLAR_ENTRIES } from '@/src/api/generated/c-prompt-exemplars';
import { resolvePartitionAllocationSpec } from '@/src/features/c-session/archetypes/partition-allocation-logic';

const here = dirname(fileURLToPath(import.meta.url));

function makeTask(entry: (typeof EXEMPLAR_ENTRIES)[number]): CNextTaskResponse {
  return {
    blanks: entry.blanks,
    c_task_instance_id: 'task-1',
    difficulty_level: entry.difficulty_level,
    game_family_id: 'C-GF-07',
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

test('every C-EG-01 and C-SF-01 exemplar\'s prompt_text survives resolution unchanged', () => {
  for (const entry of EXEMPLAR_ENTRIES) {
    if (entry.game_task_template_id !== 'C-EG-01' && entry.game_task_template_id !== 'C-SF-01') continue;
    const spec = resolvePartitionAllocationSpec(makeTask(entry));
    assert.notEqual(spec, null);
    assert.equal(spec!.promptText, entry.prompt_text);
  }
});

test('C-EG-01\'s carries real authored wording, not a placeholder or an empty string', () => {
  const entry = EXEMPLAR_ENTRIES.find((e) => e.game_task_template_id === 'C-EG-01')!;
  // What this is really for is catching a stale or empty generated exemplar, so it checks
  // that rather than the copy -- which the backend artefact pins, with a checksum.
  assert.equal(typeof entry.prompt_text, 'string');
  assert.ok(entry.prompt_text.trim().length > 10, entry.prompt_text);
  assert.equal(entry.prompt_text.trim(), entry.prompt_text);
  assert.doesNotMatch(entry.prompt_text, /TODO|PLACEHOLDER/);
});

test('partition-allocation-logic.ts never builds a substitute prompt string (no template literal touching promptText)', () => {
  const source = readFileSync(
    resolve(here, '..', '..', 'features', 'c-session', 'archetypes', 'partition-allocation-logic.ts'),
    'utf-8',
  );
  assert.equal(/promptText:\s*`/.test(source), false);
  assert.match(source, /promptText:\s*task\.prompt_text/);
});
