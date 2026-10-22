// planTaskSurface's own tests: the pure composition of planTask + surface resolution that makes
// the screen's mount decision provable without a rendering library (see the function's own doc
// comment in c-session-logic.ts). The resolver is injected as a fake here -- never the real
// archetype-surfaces.ts table -- so these tests exercise the decision in isolation from what is or
// is not registered today.

import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, resolve } from 'node:path';
import type { ComponentType } from 'react';

import type { CNextTaskResponse } from '@/src/api/generated/openapi-types';
import type { ArchetypeSurfaceProps } from '@/src/features/c-session/archetype-surfaces';
import type { ArchetypeId } from '@/src/features/c-session/archetypes/registry';
import { planTaskSurface } from '@/src/features/c-session/c-session-logic';

function makeTask(overrides: Partial<CNextTaskResponse> = {}): CNextTaskResponse {
  return {
    blanks: 1,
    c_task_instance_id: 'task-1',
    difficulty_level: 1,
    game_family_id: 'C-GF-02',
    game_task_template_id: 'C-NP-01',
    interactive_assets: {},
    prompt_payload: { shown_sequence: [1, 2, 3] },
    prompt_text: 'Write what comes next in the pattern.',
    representation_mode: 'TEST_FIXTURE_ONLY_REPRESENTATION',
    request_id: 'req-1',
    scaffold_state: 'C0',
    skill_id: 'number-sense',
    task_index: 1,
    technical_status: 'OK',
    valid_action_space: { entered_values: 'list[int]' },
    ...overrides,
  };
}

// A stand-in component reference -- never rendered, only checked for identity. Its shape does not
// matter to planTaskSurface, which treats it as an opaque value to carry through.
const FakeSurface = (() => null) as unknown as ComponentType<ArchetypeSurfaceProps>;

function resolverReturning(
  surface: typeof FakeSurface | null,
): (archetypeId: ArchetypeId) => typeof FakeSurface | null {
  return () => surface;
}

// --- mount outcome ------------------------------------------------------------------------------

test('a registered archetype yields the mount outcome, carrying the task and the surface', () => {
  const task = makeTask();
  const plan = planTaskSurface(task, resolverReturning(FakeSurface));
  assert.equal(plan.kind, 'mount');
  if (plan.kind === 'mount') {
    assert.equal(plan.task, task);
    assert.equal(plan.Surface, FakeSurface);
  }
});

// --- fail-closed: resolved archetype, no surface registered --------------------------------------

test('a resolved archetype with no registered surface fails closed with reason "no-surface-registered"', () => {
  const plan = planTaskSurface(makeTask(), resolverReturning(null));
  assert.equal(plan.kind, 'fail-closed');
  if (plan.kind === 'fail-closed') {
    assert.equal(plan.reason, 'no-surface-registered');
  }
});

test('negative control: the no-surface-registered plan never carries a task or a Surface', () => {
  const plan = planTaskSurface(makeTask(), resolverReturning(null));
  assert.equal('task' in plan, false);
  assert.equal('Surface' in plan, false);
});

// --- fail-closed: unresolvable template -----------------------------------------------------------

test('an unresolvable template fails closed with reason "unresolvable-template", without ever calling the resolver', () => {
  let resolverCalled = false;
  const resolver = (): typeof FakeSurface | null => {
    resolverCalled = true;
    return FakeSurface;
  };
  const plan = planTaskSurface(makeTask({ game_task_template_id: 'C-NOT-A-REAL-TEMPLATE' }), resolver);
  assert.equal(plan.kind, 'fail-closed');
  if (plan.kind === 'fail-closed') {
    assert.equal(plan.reason, 'unresolvable-template');
  }
  // The resolver has nothing to resolve an archetype id against when planTask itself already
  // failed closed -- proving this is what actually distinguishes the two reasons, rather than both
  // paths happening to produce the same string by coincidence.
  assert.equal(resolverCalled, false);
});

test('negative control: an unbound declared type in valid_action_space also fails closed as unresolvable-template', () => {
  const plan = planTaskSurface(
    makeTask({ valid_action_space: { entered_values: 'not_a_real_type' } }),
    resolverReturning(FakeSurface),
  );
  assert.equal(plan.kind, 'fail-closed');
  if (plan.kind === 'fail-closed') {
    assert.equal(plan.reason, 'unresolvable-template');
  }
});

// --- the two fail-closed reasons stay distinguishable ---------------------------------------------

test('the two fail-closed reasons are distinguishable from each other, not merely both falsy', () => {
  const unresolvable = planTaskSurface(
    makeTask({ game_task_template_id: 'C-NOT-A-REAL-TEMPLATE' }),
    resolverReturning(FakeSurface),
  );
  const noSurface = planTaskSurface(makeTask(), resolverReturning(null));
  assert.equal(unresolvable.kind, 'fail-closed');
  assert.equal(noSurface.kind, 'fail-closed');
  if (unresolvable.kind === 'fail-closed' && noSurface.kind === 'fail-closed') {
    assert.notEqual(unresolvable.reason, noSurface.reason);
  }
});

const here = dirname(fileURLToPath(import.meta.url));

// --- the invisible spacer that ate SUBMIT ----------------------------------------------------
//
// 2026-09-28, found by driving the real app in a browser. The task panel's two layout spacers are
// empty Views with a percentage height. They are also real, hit-testable elements, and the bottom
// one is the LAST sibling -- so it paints over whatever the middle area overflows. Once a surface
// grew taller than that area (the question card did it), the bottom spacer landed exactly on top
// of SUBMIT: the button was enabled, visible, `pointerEvents: auto`, and completely untappable,
// with nothing logged anywhere because the whole submit path is silent on failure by construction.
//
// A spacer must never receive a touch. This is a source scan rather than a render test because the
// failure is a LAYOUT overlap that only exists at real viewport sizes -- the render harness would
// not reproduce it, and did not.

test('the task panel spacers cannot receive touches', () => {
  const source = readFileSync(
    resolve(here, '..', '..', 'features', 'c-session', 'c-session-screen.tsx'),
    'utf-8',
  );
  for (const spacer of ['taskContentSpacerTop', 'taskContentSpacerBottom']) {
    // Plain substring, not a regex: the exact JSX is short and stable, and a regex here was its
    // own small bug the first time round.
    const expected = `<View pointerEvents="none" style={styles.${spacer}} />`;
    assert.ok(source.includes(expected), `${spacer} must be rendered as: ${expected}`);
  }
});
