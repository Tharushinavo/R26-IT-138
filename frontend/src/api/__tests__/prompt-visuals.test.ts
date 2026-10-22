import { test } from 'node:test';
import assert from 'node:assert/strict';

import {
  MAX_RENDERABLE_OBJECTS,
  resolvePromptVisual,
} from '@/src/features/session/prompt-visuals/registry';

// Payloads below are the real wire shapes, dumped from the live generator through
// LiveEngineAdapter.build_task_instance rather than transcribed from a doc.

// --- the three payload shapes that resolve ------------------------------------------------------

test('B-CNT02 / B-CNT03 object-count payloads resolve to an object set', () => {
  const spec = resolvePromptVisual({
    stem: 'How many objects are there?',
    object_count: 6,
    layout: 'scattered',
    task: 'count_objects',
  });
  assert.deepEqual(spec, { kind: 'object-set', count: 6, layout: 'scattered' });
});

test('B-NS02 resolves to an object set even though its payload has no layout key', () => {
  const spec = resolvePromptVisual({
    stem: 'Which numeral matches the quantity?',
    object_count: 19,
    options_range: [0, 20],
  });
  assert.deepEqual(spec, { kind: 'object-set', count: 19, layout: null });
});

test('B-NS03 resolves to two sets, preserving the payload order', () => {
  const spec = resolvePromptVisual({
    stem: 'Compare the two sets.',
    set_a: 11,
    set_b: 9,
    options: ['<', '>', '='],
  });
  assert.deepEqual(spec, { kind: 'two-sets', setA: 11, setB: 9 });
});

test('two equal sets resolve — equality is a real case, not a degenerate one', () => {
  assert.deepEqual(resolvePromptVisual({ stem: 'Compare the two sets.', set_a: 1, set_b: 1 }), {
    kind: 'two-sets',
    setA: 1,
    setB: 1,
  });
});

test('B-CNT04 resolves to a selectable pool and does not carry the target into the visual', () => {
  const spec = resolvePromptVisual({
    stem: 'Select exactly 6 objects.',
    target: 6,
    pool_size: 14,
  });
  assert.deepEqual(spec, { kind: 'selectable-pool', poolSize: 14 });
  // The target must not reach the visual layer: carrying it would invite a progress cue against it,
  // which is exactly the measurement this item takes.
  assert.equal('target' in (spec ?? {}), false);
});

// --- stem-only ---------------------------------------------------------------------------------

test('a stem-only payload resolves to null (stem-only rendering, unchanged behaviour)', () => {
  assert.equal(resolvePromptVisual({ stem: 'What is 12 + 3?' }), null);
});

test('a Grade 3 arithmetic payload is unaffected and stays stem-only', () => {
  // The scaffold tier: these templates are answerable today and this batch must not touch them.
  assert.equal(
    resolvePromptVisual({ stem: 'Put the two groups together: 10 and 2.', operator: '+' }),
    null,
  );
  assert.equal(
    resolvePromptVisual({ stem: '46, 47, 48, __', sequence_shown: [46, 47, 48], blank_position: 'terminal' }),
    null,
  );
  assert.equal(resolvePromptVisual({ stem: 'Order these ascending.', numbers: [3, 9, 10], direction: 'ascending' }), null);
});

test('B-NS07 without delta still stays stem-only', () => {
  // FE-3h Part 0 put delta on the wire, so this is now the drift case rather than the normal one.
  // Without a magnitude the "after" panel is not drawable, and drawing only the transformations whose
  // delta happens to be inferable would make the presence of a visual a cue for one answer value.
  for (const transformation of ['rearrange', 'add', 'remove']) {
    assert.equal(
      resolvePromptVisual({
        stem: 'Is the quantity the same or changed?',
        initial_count: 12,
        transformation,
        options: ['same', 'changed'],
      }),
      null,
      `${transformation} without delta must stay stem-only`,
    );
  }
});

// --- B-NS07 with delta (FE-3h Part 0) -------------------------------------------------------------

test('B-NS07 resolves to before/after once delta is present', () => {
  const added = resolvePromptVisual({
    stem: 'Is the quantity the same or changed?',
    initial_count: 12,
    transformation: 'add',
    delta: 3,
    options: ['same', 'changed'],
  });
  assert.deepEqual(added, { kind: 'before-after', before: 12, after: 15 });

  const removed = resolvePromptVisual({
    stem: 'Is the quantity the same or changed?',
    initial_count: 12,
    transformation: 'remove',
    delta: -3,
    options: ['same', 'changed'],
  });
  assert.deepEqual(removed, { kind: 'before-after', before: 12, after: 9 });
});

test('a rearrange (delta 0) yields two identical panel counts', () => {
  // Identical, not subtly different: the delta-0 case is the "same" answer, and any visible
  // difference would be a false cue. Equally, it must still RENDER — a visual that appeared only for
  // add/remove would be just as reliable a cue in the other direction.
  const spec = resolvePromptVisual({
    stem: 'Is the quantity the same or changed?',
    initial_count: 7,
    transformation: 'rearrange',
    delta: 0,
    options: ['same', 'changed'],
  });
  assert.deepEqual(spec, { kind: 'before-after', before: 7, after: 7 });
});

test('before/after fails closed on a delta that would make the after set impossible', () => {
  const base = { stem: 'x', initial_count: 3, transformation: 'remove' };
  assert.equal(resolvePromptVisual({ ...base, delta: -10 }), null); // after would be negative
  assert.equal(resolvePromptVisual({ ...base, delta: 1.5 }), null);
  assert.equal(resolvePromptVisual({ ...base, delta: '2' }), null);
  assert.equal(resolvePromptVisual({ ...base, delta: 10_000 }), null);
});

// --- HAZARD 1: place (chart) vs places (blocks) ------------------------------------------------------

test('place SINGULAR resolves to a place-value chart, never to blocks', () => {
  const spec = resolvePromptVisual({ stem: 'In 42, what is the tens digit?', n: 42, place: 'tens' });
  assert.deepEqual(spec, {
    kind: 'place-value-chart',
    value: 42,
    places: ['tens', 'ones'],
    askedPlace: 'tens',
  });
});

test('places PLURAL resolves to base-ten blocks, never to a chart', () => {
  const spec = resolvePromptVisual({
    stem: 'Write 342 in expanded form.',
    n: 342,
    places: ['hundreds', 'tens', 'ones'],
  });
  assert.deepEqual(spec, {
    kind: 'base-ten-blocks',
    value: 342,
    places: ['hundreds', 'tens', 'ones'],
  });
});

test('a chart payload carrying the blocks key does not become a chart, and vice versa', () => {
  // One character apart, completely different visuals. Exact own-key matching means neither payload
  // can satisfy the other's requirement, and the plural check runs first so the more specific form
  // wins if a future payload ever carried both.
  const withBoth = { stem: 'x', n: 342, place: 'tens', places: ['hundreds', 'tens', 'ones'] };
  assert.equal(resolvePromptVisual(withBoth)?.kind, 'base-ten-blocks');

  // `place` holding an array, or `places` holding a string, is drift and must not cross-resolve.
  assert.equal(resolvePromptVisual({ stem: 'x', n: 42, place: ['tens', 'ones'] }), null);
  assert.equal(resolvePromptVisual({ stem: 'x', n: 42, places: 'tens' }), null);
});

test('B-PV03 three-digit charts show all three places', () => {
  const spec = resolvePromptVisual({ stem: 'In 342, what is the hundreds digit?', n: 342, place: 'hundreds' });
  assert.deepEqual(spec, {
    kind: 'place-value-chart',
    value: 342,
    places: ['hundreds', 'tens', 'ones'],
    askedPlace: 'hundreds',
  });
});

test('place-value payloads fail closed on an unknown place name or out-of-range value', () => {
  assert.equal(resolvePromptVisual({ stem: 'x', n: 42, place: 'thousands' }), null);
  assert.equal(resolvePromptVisual({ stem: 'x', n: 42, places: ['thousands', 'ones'] }), null);
  assert.equal(resolvePromptVisual({ stem: 'x', n: 1234, place: 'tens' }), null);
  assert.equal(resolvePromptVisual({ stem: 'x', n: -5, place: 'tens' }), null);
  assert.equal(resolvePromptVisual({ stem: 'x', n: 42, places: [] }), null);
});

// --- HAZARD 2: total is not distinctive ---------------------------------------------------------------

test('total + removed resolves to take-away', () => {
  const spec = resolvePromptVisual({
    stem: 'There are 9. Take away 4.',
    total: 9,
    removed: 4,
    operator: '-',
  });
  assert.deepEqual(spec, { kind: 'take-away', total: 9, removed: 4 });
});

test('the two division payloads resolve to null, NOT to a take-away visual', () => {
  // `total` alone is shared by three templates with completely different questions. B-DIV01 sends
  // total + recipients ("share 20 between 2"); B-DIV02 sends total + group_size ("put 20 into groups
  // of 5"). Drawing either as "some of these are taken away" would misrepresent the question
  // entirely, so the full total+removed pair is required.
  assert.equal(
    resolvePromptVisual({
      stem: 'Share 20 equally between 2. How many each?',
      total: 20,
      recipients: 2,
    }),
    null,
  );
  assert.equal(
    resolvePromptVisual({
      stem: 'Put 20 into groups of 5. How many groups?',
      total: 20,
      group_size: 5,
    }),
    null,
  );
  // And bare `total` on its own.
  assert.equal(resolvePromptVisual({ stem: 'x', total: 20 }), null);
});

test('take-away fails closed when more is removed than exists', () => {
  assert.equal(resolvePromptVisual({ stem: 'x', total: 4, removed: 9 }), null);
  assert.equal(resolvePromptVisual({ stem: 'x', total: 4, removed: -1 }), null);
  assert.equal(resolvePromptVisual({ stem: 'x', total: 4, removed: 1.5 }), null);
});

test('removing all or none of the objects is still a real question', () => {
  assert.deepEqual(resolvePromptVisual({ stem: 'x', total: 5, removed: 5 }), {
    kind: 'take-away',
    total: 5,
    removed: 5,
  });
  assert.deepEqual(resolvePromptVisual({ stem: 'x', total: 5, removed: 0 }), {
    kind: 'take-away',
    total: 5,
    removed: 0,
  });
});

// --- validation: malformed values fail closed -----------------------------------------------------

test('a non-integer, negative or non-numeric count resolves to null', () => {
  for (const bad of [-1, 1.5, Number.NaN, Number.POSITIVE_INFINITY, '6', null, undefined, {}, [6]]) {
    assert.equal(
      resolvePromptVisual({ stem: 'x', object_count: bad }),
      null,
      `object_count ${JSON.stringify(bad)} must not render`,
    );
  }
});

test('a count above the layout bound resolves to null rather than rendering a broken layout', () => {
  assert.notEqual(resolvePromptVisual({ stem: 'x', object_count: MAX_RENDERABLE_OBJECTS }), null);
  assert.equal(resolvePromptVisual({ stem: 'x', object_count: MAX_RENDERABLE_OBJECTS + 1 }), null);
  assert.equal(resolvePromptVisual({ stem: 'x', object_count: 100_000 }), null);
});

test('the bound comfortably covers every real generator value', () => {
  // object_count/set_a/set_b are 1..20 and pool_size reaches 28 (target 1..20 plus 3..8). The bound
  // is a layout guard, not a restatement of those ranges.
  assert.ok(MAX_RENDERABLE_OBJECTS >= 28);
  assert.notEqual(resolvePromptVisual({ stem: 'x', pool_size: 28 }), null);
});

test('a zero object count renders (an empty set is a real quantity) but a zero pool does not', () => {
  assert.deepEqual(resolvePromptVisual({ stem: 'x', object_count: 0 }), {
    kind: 'object-set',
    count: 0,
    layout: null,
  });
  // A pool of nothing is not a surface the child can act on.
  assert.equal(resolvePromptVisual({ stem: 'x', pool_size: 0 }), null);
});

test('two sets resolve to null if either side is malformed', () => {
  assert.equal(resolvePromptVisual({ stem: 'x', set_a: 5, set_b: -2 }), null);
  assert.equal(resolvePromptVisual({ stem: 'x', set_a: '5', set_b: 2 }), null);
  assert.equal(resolvePromptVisual({ stem: 'x', set_a: 5, set_b: 1.5 }), null);
});

test('a half-present two-set payload does not fall through to a wrong visual', () => {
  // set_a alone is not a two-set payload, and must not be reinterpreted as an object set.
  assert.equal(resolvePromptVisual({ stem: 'x', set_a: 5 }), null);
  assert.equal(resolvePromptVisual({ stem: 'x', set_b: 5 }), null);
});

// --- precedence ---------------------------------------------------------------------------------

test('precedence is deterministic when several keys are present', () => {
  // Most specific first: two-sets, then selectable-pool, then object-set. No real template carries
  // more than one of these today; the point is that a future payload cannot make the result depend
  // on key insertion order.
  const all = { stem: 'x', set_a: 3, set_b: 4, pool_size: 9, object_count: 5 };
  assert.deepEqual(resolvePromptVisual(all), { kind: 'two-sets', setA: 3, setB: 4 });

  const reordered = { object_count: 5, pool_size: 9, stem: 'x', set_b: 4, set_a: 3 };
  assert.deepEqual(resolvePromptVisual(reordered), resolvePromptVisual(all));

  assert.deepEqual(resolvePromptVisual({ stem: 'x', pool_size: 9, object_count: 5 }), {
    kind: 'selectable-pool',
    poolSize: 9,
  });
});

test('a malformed higher-precedence payload fails closed rather than falling through', () => {
  // set_a/set_b present but invalid must NOT silently render the object_count instead — that would
  // show the child a different quantity from the one the question is about.
  assert.equal(resolvePromptVisual({ stem: 'x', set_a: -1, set_b: 4, object_count: 5 }), null);
});

// --- hostile and unknown keys ---------------------------------------------------------------------

test('unknown keys are ignored silently and never throw', () => {
  assert.equal(
    resolvePromptVisual({ stem: 'x', some_future_key: 42, another: { nested: true } }),
    null,
  );
});

test('inherited Object.prototype keys cannot be mistaken for a payload', () => {
  // hasOwnProperty guard, same discipline as FE-3a's renderer registry: bare access would resolve
  // "constructor" to an inherited member.
  assert.equal(resolvePromptVisual({ stem: 'x' }), null);
  assert.equal(resolvePromptVisual(Object.create({ object_count: 6 }) as Record<string, unknown>), null);
  assert.equal(resolvePromptVisual({ stem: 'x', object_count: undefined }), null);
});

test('an empty payload does not throw', () => {
  assert.equal(resolvePromptVisual({}), null);
});
