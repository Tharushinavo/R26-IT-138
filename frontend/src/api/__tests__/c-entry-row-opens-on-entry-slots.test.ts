// value-token-row.tsx's entry scene must always show its entry slots without a scroll gesture.
//
// WHY THIS IS A CORRECTNESS GUARD AND NOT A STYLE ONE. `DisplayWithEntryRow` used to render the
// shown sequence and the entry slots in one horizontally-scrolling row, and had to scroll itself to
// the entry slots on mount so a long `shown_sequence` did not push the only interactive part of the
// scene past the right edge with no visible way to reach it. That design was replaced twice: first
// with the shown sequence and the entry slots on two separate wrapping rows, then merged back into
// ONE row (shown values, then entry slots, in that order) that wraps onto further lines -- so the
// entry slots land on whichever line has room after the shown values, rather than always starting a
// line of their own. Either way there is nowhere for the row to run off to, so the entry slots are
// always on screen with no scroll-to-offset choreography needed at all. This guard asserts that
// property directly -- no ScrollView in `DisplayWithEntryRow`, and its row wraps -- rather than
// re-asserting the scroll-on-mount mechanics the original design needed and this one does not have.
//
// WHAT THIS FILE CANNOT DO, STATED PLAINLY. It does not observe a render. This project has no
// rendering library in devDependencies, so nothing here can mount the row, measure a viewport, and
// assert the entry slots are on screen. What is proven is strictly what the source says. The
// behavioural half is a supervisor observation to make in a browser at a long `shown_sequence`.

import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, resolve } from 'node:path';

const here = dirname(fileURLToPath(import.meta.url));
const rowPath = resolve(
  here, '..', '..', 'features', 'c-session', 'primitives', 'value-token-row.tsx',
);

/**
 * Comments stripped before any scan. The fix's own comments explain the row's shape at length and
 * name every token these guards look for, so a guard reading raw bytes would pass on a file whose
 * comments merely discuss the fix while the JSX carries none of it -- the comment-stripping trap
 * the build-steps doc records this project hitting at least four times.
 */
function strippedSource(text: string): string {
  return text.replace(/\/\*[\s\S]*?\*\//g, '').replace(/^\s*\/\/.*$/gm, '');
}

/**
 * The body of one top-level `function <name>(` declaration, from its signature to the next
 * top-level declaration. Both guards below are per-function on purpose: `DisplayWithEntryRow` and
 * `ReorderRow` render structurally similar things, and a whole-file scan could not tell which one
 * it had found -- it would pass while the fix sat in the wrong component, or while ReorderRow had
 * been changed out of scope.
 */
export function functionBody(source: string, name: string): string | null {
  const stripped = strippedSource(source);
  const start = stripped.search(new RegExp(`^function ${name}\\b`, 'm'));
  if (start === -1) return null;
  const rest = stripped.slice(start);
  const nextTop = rest.slice(1).search(/^(function |const |type |export )/m);
  return nextTop === -1 ? rest : rest.slice(0, nextTop + 1);
}

/** True when the given function body renders one non-scrolling, wrapping row (shown values then
 *  entry slots) rather than a ScrollView. */
export function rendersOneWrappingRow(body: string | null): boolean {
  if (body === null) return false;
  const noScrollView = !/<ScrollView/.test(body);
  const hasEntryTokenRow = /styles\.entryTokenRow/.test(body);
  return noScrollView && hasEntryTokenRow;
}

/** True when the given function body uses a ScrollView (the reorder row's own, unchanged, shape). */
export function usesScrollView(body: string | null): boolean {
  if (body === null) return false;
  return /<ScrollView/.test(body);
}

const realSource = () => readFileSync(rowPath, 'utf8');

// --- the real file ------------------------------------------------------------------------------

test('DisplayWithEntryRow renders one wrapping row, not a ScrollView', () => {
  assert.ok(rendersOneWrappingRow(functionBody(realSource(), 'DisplayWithEntryRow')));
});

test('entryTokenRow wraps rather than running off-screen, so the entry slots never need a scroll to reach', () => {
  const source = strippedSource(realSource());
  const entryTokenRowStyle = source.match(/entryTokenRow:\s*\{[^}]*\}/);
  assert.ok(entryTokenRowStyle, 'entryTokenRow style not found');
  assert.match(entryTokenRowStyle![0], /flexWrap:\s*'wrap'/);
});

test('shown values come before entry slots in the row, so entry slots trail the shown sequence rather than leading it', () => {
  const body = functionBody(realSource(), 'DisplayWithEntryRow');
  assert.ok(body);
  const shownMapIndex = body!.search(/shownSequence\.map/);
  const buffersMapIndex = body!.search(/buffers\.map/);
  assert.notEqual(shownMapIndex, -1);
  assert.notEqual(buffersMapIndex, -1);
  assert.ok(shownMapIndex < buffersMapIndex, 'entry slots are rendered before the shown sequence');
});

test('ReorderRow is unchanged: still a ScrollView, indicator still suppressed', () => {
  const body = functionBody(realSource(), 'ReorderRow');
  assert.ok(usesScrollView(body), 'ReorderRow no longer uses a ScrollView, and is out of scope');
  assert.match(body!, /showsHorizontalScrollIndicator=\{false\}/);
});

test('the two functions are found as distinct bodies, so neither guard read the wrong one', () => {
  const entry = functionBody(realSource(), 'DisplayWithEntryRow');
  const reorder = functionBody(realSource(), 'ReorderRow');
  assert.notEqual(entry, null);
  assert.notEqual(reorder, null);
  assert.ok(!entry!.includes('function ReorderRow'), 'the entry body swallowed ReorderRow');
  assert.ok(!reorder!.includes('function DisplayWithEntryRow'), 'the reorder body swallowed the entry row');
});

// --- negative controls on each clause, so no clause is vacuous -----------------------------------

const MERGED_ROW_BODY = [
  'function DisplayWithEntryRow() {',
  '  return (',
  '    <View style={styles.entryTokenRow}>',
  '      {shownSequence.map(x => x)}',
  '      {buffers.map(x => x)}',
  '    </View>',
  '  );',
  '}',
].join('\n');

test('the row guard recognises a correct body, so it is not vacuously false', () => {
  assert.equal(rendersOneWrappingRow(MERGED_ROW_BODY), true);
});

test('the row guard fires when a ScrollView is reintroduced', () => {
  assert.equal(
    rendersOneWrappingRow(
      MERGED_ROW_BODY.replace('<View style={styles.entryTokenRow}>', '<ScrollView>').replace(
        '</View>\n  );',
        '</ScrollView>\n  );',
      ),
    ),
    false,
  );
});

test('the row guard fires when entryTokenRow is missing', () => {
  assert.equal(
    rendersOneWrappingRow(MERGED_ROW_BODY.replace('styles.entryTokenRow', 'styles.somethingElse')),
    false,
  );
});

test('both guards return false for a function that does not exist, rather than throwing', () => {
  assert.equal(rendersOneWrappingRow(functionBody(realSource(), 'NoSuchComponent')), false);
  assert.equal(usesScrollView(functionBody(realSource(), 'NoSuchComponent')), false);
});

test('the comment-stripper defeats a file that only discusses the fix in prose', () => {
  const commentOnly = [
    'function DisplayWithEntryRow() {',
    '  // styles.entryTokenRow, no ScrollView here',
    '  /* <ScrollView> */',
    '  return <ScrollView />;',
    '}',
  ].join('\n');
  assert.equal(rendersOneWrappingRow(functionBody(commentOnly, 'DisplayWithEntryRow')), false);
});
