// The game hub's non-scrolling guarantee.
//
// The guarantee is structural rather than dimensional: the screen mounts no scrolling container at
// all, and its eight rows share the panel's height through flex, so a shorter viewport compresses
// the rows instead of pushing the eighth one out of sight. There is no solved size to assert, so
// what is asserted here is the structure itself.

import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, resolve } from 'node:path';

import { listGameFamilies } from '@/src/features/game-hub/game-catalogue';

const here = dirname(fileURLToPath(import.meta.url));
const screenPath = resolve(here, '..', '..', 'features', 'game-hub', 'game-hub-screen.tsx');

/** Comments stripped before scanning. This file's own prose names ScrollView repeatedly, and a
 * guard that fires on a mere mention is the comment-stripping trap the build-steps doc records
 * this project hitting four separate times. */
function strippedSource(text: string): string {
  return text.replace(/\/\*[\s\S]*?\*\//g, '').replace(/^\s*\/\/.*$/gm, '');
}

test('the hub screen mounts no scrolling container -- the guarantee is structural', () => {
  const source = strippedSource(readFileSync(screenPath, 'utf8'));
  for (const scroller of ['ScrollView', 'FlatList', 'SectionList', 'VirtualizedList']) {
    assert.ok(!source.includes(scroller), `game-hub-screen.tsx references ${scroller}`);
  }
});

// The negative control for the guard above: it must fire on a real violation, not merely stay
// quiet on clean source. A guard proven in only one direction is not proven.
test('the no-scroller guard fires on source that mounts one, and ignores a mere mention', () => {
  assert.ok(strippedSource('const a = <ScrollView />;').includes('ScrollView'), 'missed a real mount');
  assert.ok(
    !strippedSource('// never use a ScrollView here\nconst a = 1;').includes('ScrollView'),
    'fired on a comment',
  );
});

test('the grid, its rows and its cards all flex, so no viewport can push a card out of sight', () => {
  const source = strippedSource(readFileSync(screenPath, 'utf8'));
  // None of the three pins a pixel height. A fixed height on any of them is what would let the
  // last pair fall off a short viewport.
  assert.match(source, /grid: \{[^}]*flex: 1/);
  assert.match(source, /gridRow: \{[^}]*flex: 1/);
  assert.match(source, /card: \{[^}]*flex: 1/);
});

test('the eight families divide evenly into rows of two -- no row left half empty', () => {
  const families = listGameFamilies();
  assert.equal(families.length, 8);
  assert.equal(families.length % 2, 0);
});
