// The regression this batch exists to prevent: a task phase whose render branch mounts nothing and
// shows only static content, exactly like c-session-screen.tsx's own dead placeholder before this
// batch. A pure test of planTaskSurface cannot see this -- it proves the DECISION is right, not that
// the SCREEN acts on it -- so this is a comment-stripped source scan of the real file, the same
// method c-motor-constants.test.ts and the 10a no-representation-mode tests already use, since this
// project's devDependencies carry no rendering library to mount a tree with instead.

import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, resolve } from 'node:path';

const here = dirname(fileURLToPath(import.meta.url));
const screenPath = resolve(here, '..', '..', 'features', 'c-session', 'c-session-screen.tsx');

function stripComments(source: string): string {
  return source.replace(/\/\*[\s\S]*?\*\//g, '').replace(/\/\/.*$/gm, '');
}

/**
 * Does the source reference `<Surface` as JSX, outside comments? `Surface` here is not a generic
 * word this project uses elsewhere -- it is specifically the resolved-component variable
 * `planTaskSurface`'s mount outcome carries, destructured from `phase` in the task branch and
 * nowhere else in this file. A file whose task branch renders only static content (the old
 * placeholder: an icon, a title, a LEAVE SESSION button) has no reason to contain this JSX tag at
 * all.
 */
function taskBranchMountsTheResolvedSurface(source: string): boolean {
  return /<Surface\b/.test(stripComments(source));
}

test('c-session-screen.tsx\'s task branch references the resolved surface as JSX', () => {
  const source = readFileSync(screenPath, 'utf-8');
  assert.equal(taskBranchMountsTheResolvedSurface(source), true);
});

test('negative control: a task branch rendering only static content does not pass the scan (proves it fires red on the regression)', () => {
  const staticOnlyBranch = `
  // phase.kind === 'task'. No archetype surface exists in this batch, so this branch is currently
  // unreachable in practice (loadNextTask only sets it once resolveArchetypeSurface returns a
  // component) -- kept because the loop must already know how to render one when 10a...10h land.
  return (
    <ScreenShell centered>
      <View style={styles.iconCircle}>
        <Ionicons color={colors.primary} name="hourglass-outline" size={44} />
      </View>
      <AppText align="center" variant="title">
        Getting ready…
      </AppText>
      <Pressable
        accessibilityRole="button"
        onPress={() => void leaveSession()}
        style={({ pressed }) => [styles.leaveButton, pressed && styles.pressed]}>
        <AppText style={styles.leaveButtonText}>LEAVE SESSION</AppText>
      </Pressable>
    </ScreenShell>
  );
}
`;
  assert.equal(taskBranchMountsTheResolvedSurface(staticOnlyBranch), false);
});

test('negative control: the JSX tag kept only in a comment does not pass the scan (proves comment-stripping works)', () => {
  const commentOnly = '// must eventually render <Surface onSubmit={x} task={y} />\nconst z = 1;';
  assert.equal(taskBranchMountsTheResolvedSurface(commentOnly), false);
});

test('the checker fires true on a fabricated mount, proving it is not vacuous', () => {
  const fabricatedMount = 'return <Surface onSubmit={submitFromSurface} task={task} />;';
  assert.equal(taskBranchMountsTheResolvedSurface(fabricatedMount), true);
});
