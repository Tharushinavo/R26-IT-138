// The Play tab's game catalogue: the eight Component C game families (C-GF-01..C-GF-08), one
// button per family on the hub screen.
//
// WHAT IS HARDCODED HERE AND WHAT IS NOT. Only three things are written down per family: its
// catalogue id, its child-facing title/subtitle, and its template ids. Everything else -- which
// archetype each family needs, and whether that archetype has a surface built yet -- is COMPUTED,
// at call time, from the two tables that already own those facts (archetypes/registry.ts and
// archetype-surfaces.ts). That is deliberate. A hardcoded "built: true/false" column is exactly
// the kind of claim this project has repeatedly watched go stale: it would be correct the day it
// was typed and wrong the moment 10b lands. `readinessOf` below cannot go stale, because it reads
// the same SURFACE_TABLE the task loop reads.
//
// The template ids are the one genuinely static fact -- they come from the frozen template
// registry (30 templates, asserted set-equal to this file's own union by
// c-game-hub-catalogue.test.ts), and that registry is a frozen backend artefact, not a moving target.
//
// This module decides nothing about a task. It does not choose difficulty, does not read or write
// session state, and does not compute correctness. It is a menu.
//
// It also imports NOTHING that reaches React Native -- in particular not archetype-surfaces.ts,
// which pulls in a real surface component and therefore the whole RN runtime. That is why
// `readinessOf` takes the surface lookup as an argument instead of importing it: the same
// injection c-plan-task-surface.test.ts already uses for the same reason ("the resolver is
// injected as a fake here -- never the real archetype-surfaces.ts table"). The screen passes the
// real one; the tests pass a fake and stay runnable under `node --test`.

import { resolveArchetype, type ArchetypeId } from '@/src/features/c-session/archetypes/registry';
import { accentForGameFamily } from '@/src/features/c-session/game-family-accents';

export type GameFamilyId =
  | 'C-GF-01'
  | 'C-GF-02'
  | 'C-GF-03'
  | 'C-GF-04'
  | 'C-GF-05'
  | 'C-GF-06'
  | 'C-GF-07'
  | 'C-GF-08';

/**
 * `playable` -- every archetype this family needs has a surface registered, so a task from it
 * renders a real interactive scene.
 * `partial` -- some but not all of them do. Such a family renders real tasks for some templates
 * and the fail-closed frame for the rest, which is the honest thing to show rather than rounding
 * in either direction.
 * `coming-soon` -- none of them do. Tapping still opens a session; it renders the fail-closed
 * frame, which is the design working, not a crash.
 */
export type GameReadiness = 'playable' | 'partial' | 'coming-soon';

/**
 * An expo-router destination, given as a pathname plus params rather than a hand-built query
 * string. Typed routes reject the string form, and the split shape is the one that cannot
 * accidentally ship an unescaped value.
 */
export type GameSessionRoute = {
  pathname: '/(learner)/c-session';
  params: { grade: string; sessionMode: 'c_only' };
};

export type GameFamilyEntry = {
  familyId: GameFamilyId;
  title: string;
  subtitle: string;
  /** The grade band the family's catalogue entry belongs to. Passed to the session route. */
  grade: number;
  /** Frozen-registry template ids belonging to this family. */
  templateIds: readonly string[];
};

// Ordered by catalogue id, which is also the order a child reads them in. This is NOT the build
// order (10a..10h) -- that ordering exists to keep each sub-phase's archetype cost low and has no
// meaning to a learner looking at a menu.
const GAME_FAMILIES: readonly GameFamilyEntry[] = [
  {
    familyId: 'C-GF-01',
    title: 'Count and Collect',
    subtitle: 'Count the things and put them in the box',
    grade: 2,
    templateIds: ['C-CC-01', 'C-CC-02', 'C-CC-03', 'C-CC-04'],
  },
  {
    familyId: 'C-GF-02',
    title: 'Number Path and Order',
    subtitle: 'Find what comes next in the pattern',
    grade: 2,
    templateIds: ['C-NP-01', 'C-NP-02', 'C-NP-03', 'C-NP-04'],
  },
  {
    familyId: 'C-GF-03',
    title: 'Match, Compare, Locate',
    subtitle: 'Pick the one that matches',
    grade: 2,
    templateIds: ['C-MCL-01', 'C-MCL-02', 'C-MCL-03', 'C-MCL-04'],
  },
  {
    familyId: 'C-GF-04',
    title: 'Build and Trade',
    subtitle: 'Build numbers out of tens and ones',
    grade: 2,
    templateIds: ['C-BT-01', 'C-BT-02', 'C-BT-03', 'C-BT-04'],
  },
  {
    familyId: 'C-GF-05',
    title: 'Join and Bridge',
    subtitle: 'Put groups together and jump along the line',
    grade: 2,
    templateIds: ['C-JB-01', 'C-JB-02', 'C-JB-03', 'C-JB-04'],
  },
  {
    familyId: 'C-GF-06',
    title: 'Take Away and Compare',
    subtitle: 'Take some away and see what is left',
    grade: 2,
    templateIds: ['C-TC-01', 'C-TC-02', 'C-TC-03', 'C-TC-04'],
  },
  {
    familyId: 'C-GF-07',
    title: 'Equal Groups and Arrays',
    subtitle: 'Make groups that are all the same size',
    grade: 3,
    templateIds: ['C-EG-01', 'C-EG-02', 'C-EG-03'],
  },
  {
    familyId: 'C-GF-08',
    title: 'Share Fairly',
    subtitle: 'Share things out so everyone gets the same',
    grade: 3,
    templateIds: ['C-SF-01', 'C-SF-02', 'C-SF-03'],
  },
];

/**
 * This family's accent colour. Read through the shared table rather than stored on the entry, so
 * the hub and the task screen cannot drift into disagreeing about what colour a game is.
 */
export function accentOf(entry: GameFamilyEntry): string {
  return accentForGameFamily(entry.familyId);
}

/** The eight families, in catalogue order. */
export function listGameFamilies(): readonly GameFamilyEntry[] {
  return GAME_FAMILIES;
}

/**
 * The archetype ids one family's templates resolve to, deduplicated, in first-seen order.
 *
 * `resolveArchetype` is called with an EMPTY valid action space on purpose. Its second check --
 * that every declared type in the action space is bound by the field-kind layer -- is vacuous over
 * an empty object, so what comes back is the template-to-archetype table's own answer and nothing
 * else. That is precisely what a menu wants: which scene does this family need, asked
 * independently of any one live task's wire payload. It is NOT a substitute for the real
 * resolution the task loop performs, which must and does pass the task's actual
 * `valid_action_space`.
 *
 * A template id absent from the table yields `null` and is skipped rather than guessed at.
 */
export function archetypesForFamily(entry: GameFamilyEntry): readonly ArchetypeId[] {
  const seen: ArchetypeId[] = [];
  for (const templateId of entry.templateIds) {
    const archetypeId = resolveArchetype(templateId, {});
    if (archetypeId !== null && !seen.includes(archetypeId)) seen.push(archetypeId);
  }
  return seen;
}

/** Answers "is a rendering surface registered for this archetype yet". See `readinessOf`. */
export type SurfaceRegisteredPredicate = (archetypeId: ArchetypeId) => boolean;

/**
 * Whether this family renders real surfaces today, computed from whatever surface table
 * `hasSurface` consults -- never from a written-down flag. The screen hands it the live
 * archetype-surfaces.ts lookup, so as 10b..10h register surfaces the hub's badges move on their
 * own, with no edit here and none in this module's tests.
 */
export function readinessOf(entry: GameFamilyEntry, hasSurface: SurfaceRegisteredPredicate): GameReadiness {
  const archetypeIds = archetypesForFamily(entry);
  if (archetypeIds.length === 0) return 'coming-soon';

  const registered = archetypeIds.filter((id) => hasSurface(id)).length;
  if (registered === 0) return 'coming-soon';
  if (registered === archetypeIds.length) return 'playable';
  return 'partial';
}

/**
 * The session route one game button navigates to. The hub supplies `grade` and `sessionMode` as
 * query params because `c-session.tsx` already reads and validates exactly those two, and
 * `decideSessionBootstrap` deliberately invents neither -- the route's own comment names a caller
 * supplying them "most likely via route params" as the anticipated shape. This is that caller.
 *
 * The family id is NOT passed. Nothing downstream accepts one: which task is served is the
 * server's decision (or, under the development fixture, the fixture's env-driven one). A family
 * param the session ignored would be a promise the hub cannot keep.
 */
export function sessionRouteFor(entry: GameFamilyEntry): GameSessionRoute {
  return {
    pathname: '/(learner)/c-session',
    params: { grade: String(entry.grade), sessionMode: 'c_only' },
  };
}
