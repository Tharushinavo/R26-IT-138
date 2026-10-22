// Development-fixture-only. Reads the frozen prompt-exemplar artefact via the generated,
// bundler-safe local copy (src/api/generated/c-prompt-exemplars.ts), not off disk, so the dev
// fixture's nextTask can relay a real generator-produced task rather than inventing content --
// per owner ruling (10.0-work-order.md §3, "Owner rulings applied, 2026-08-24") and per the
// 10.0b-fix owner ruling (option B: a generated, bundler-safe local copy of the exemplar data,
// mirroring the existing generate-contract-types.mjs / openapi-types.ts pattern).
//
// 10.0b-i shipped this file reading backend/contract/c-prompt-exemplars.json and
// c-template-registry.json directly via node:fs + import.meta.url-relative resolution. That is a
// static Hermes bundling failure for iOS/Android, not a runtime branch: `import.meta` is not
// supported in Hermes, and node:fs has no React Native equivalent. Neither problem can be fixed
// by gating -- the import is static, so Metro resolves it at bundle time regardless of whether
// the environment gate ever opens. This file now imports no node builtin and uses no
// `import.meta`; the generated module it reads is pure data and types.
//
// Ordering note: 10.0b-i derived the fixture's chosen template id from c-template-registry.json's
// alphabetically-first template_id. This file now derives it from EXEMPLAR_ENTRIES itself instead
// of reading the registry a second time. That is not a behaviour change: the frozen exemplars
// artefact's own freeze test (c-prompt-exemplars-freeze.test.ts, "the exemplars artefact has
// exactly 150 entries: 30 templates x levels 1-5, complete") asserts 150 entries, no duplicate
// (template_id, level) pairs, and complete 5-level coverage for every one of the registry's 30
// template ids. 30 ids x 5 levels already accounts for all 150 entries, so there is no room left
// for the exemplars artefact to contain a template id absent from the registry, or to omit one the
// registry has -- the two id-sets are forced equal by a test that is already committed and already
// run every time. The alphabetically-first id among EXEMPLAR_ENTRIES's own template ids is
// therefore provably the same value as the alphabetically-first id in the registry, not merely
// observed to match today.

import { EXEMPLAR_ENTRIES, type ExemplarEntry } from '@/src/api/generated/c-prompt-exemplars';

export type { ExemplarEntry };

// 10a addition: EXPO_PUBLIC_COMPONENT_C_DEV_FIXTURE_TEMPLATE (and its companion
// EXPO_PUBLIC_COMPONENT_C_DEV_FIXTURE_DIFFICULTY) let a developer select which exemplar the fixture
// serves. Without it the fixture can only ever serve the alphabetically-first template
// (`C-BT-01`, 10f's `named-integer-fields`), which has no surface until 10f lands -- so 10a's own
// surface could never be exercised in the running app. Unset, behaviour is byte-for-byte unchanged
// from before this addition. Set to an id/level pair with no matching exemplar entry, it throws the
// same way the pre-existing missing-entry path already did -- never a silent fall-back to the
// first template, which would make a typo look like a correctly-configured fixture serving the
// wrong task.

function findExemplarOrThrow(templateId: string, difficultyLevel: number): ExemplarEntry {
  const entry = EXEMPLAR_ENTRIES.find(
    (candidate) => candidate.game_task_template_id === templateId && candidate.difficulty_level === difficultyLevel,
  );
  if (!entry) {
    throw new Error(
      `Development fixture: no exemplar entry found for ${templateId} at difficulty_level ${difficultyLevel}.`,
    );
  }
  return entry;
}

/**
 * Artefact-driven pick of exactly one exemplar.
 *
 * Default (both env vars unset): the alphabetically-first template id among the generated exemplar
 * entries, at difficulty_level 1. Never a hardcoded template id -- if a future regeneration changes
 * which id sorts first, this fixture moves with it rather than silently serving a stale choice.
 *
 * When EXPO_PUBLIC_COMPONENT_C_DEV_FIXTURE_TEMPLATE is set, that template id is used instead, at
 * difficulty_level from EXPO_PUBLIC_COMPONENT_C_DEV_FIXTURE_DIFFICULTY (default 1 if unset). A
 * non-integer difficulty value, or an (id, level) pair absent from the exemplar artefact, throws.
 */
export function loadFixtureTaskExemplar(): ExemplarEntry {
  const selectedTemplateId = process.env.EXPO_PUBLIC_COMPONENT_C_DEV_FIXTURE_TEMPLATE?.trim() || null;

  if (selectedTemplateId === null) {
    const sortedIds = EXEMPLAR_ENTRIES.map((entry) => entry.game_task_template_id).sort();
    return findExemplarOrThrow(sortedIds[0], 1);
  }

  const rawDifficulty = process.env.EXPO_PUBLIC_COMPONENT_C_DEV_FIXTURE_DIFFICULTY?.trim();
  let difficultyLevel = 1;
  if (rawDifficulty) {
    const parsed = Number(rawDifficulty);
    if (!Number.isInteger(parsed)) {
      throw new Error(
        `Development fixture: EXPO_PUBLIC_COMPONENT_C_DEV_FIXTURE_DIFFICULTY must be an integer, got "${rawDifficulty}".`,
      );
    }
    difficultyLevel = parsed;
  }

  return findExemplarOrThrow(selectedTemplateId, difficultyLevel);
}
