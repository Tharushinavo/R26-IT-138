// One accent colour per Component C game family, and the only place those hex values are written.
//
// Two screens need the same answer and must not disagree: the Play hub paints each menu card's
// numbered circle with its family's accent, and the task screen paints the ground behind the task
// panel with the accent of the family the task came from. Holding the value twice would let the
// hub say a game is blue while the game itself opens green.
//
// It lives under c-session rather than under game-hub because the dependency already runs that way
// -- game-hub imports the archetype registry and surface table from here, and nothing under
// c-session imports game-hub. Putting the shared value in the hub would invert that and make a
// task surface depend on the menu that happens to link to it.
//
// This module decides nothing. It takes a family id and returns a colour; it reads no task state,
// no difficulty and no scaffold level, and there is no branch here that could.
//
// `colors` is imported from the deprecated leaf `@/src/theme/colors`, not the `@/src/theme/tokens`
// barrel, on purpose: `tokens` re-exports `createGlobalStyles` from `theme/styles.ts`, which has a
// genuine VALUE import of `StyleSheet` from `react-native` -- and `node --import tsx --test` cannot
// transform react-native's own Flow-typed `index.js`. Any test whose import graph reaches this file
// would fail to load, not fail an assertion. `theme/colors.ts` re-exports from `theme/theme.ts`,
// whose only react-native reference is `import type { TextStyle, ViewStyle }` -- erased entirely at
// compile time, so nothing here ever touches the real react-native package. Do not "fix" this back
// to the tokens barrel; that is what broke it the first time.

import { colors } from '@/src/theme/colors';

/**
 * Keyed by `game_family_id` as it appears on the wire (`CNextTaskResponse.game_family_id`, and the
 * catalogue's own `C-GF-01`..`C-GF-08`). Presentation only -- no accent carries meaning about a
 * family's content, difficulty or readiness.
 */
export const GAME_FAMILY_ACCENTS: Record<string, string> = {
  'C-GF-01': '#ff6b68',
  'C-GF-02': '#3ca6f8',
  'C-GF-03': '#7bd3aa',
  'C-GF-04': '#f2cd38',
  'C-GF-05': '#9a64df',
  'C-GF-06': '#ffb51f',
  'C-GF-07': '#ffb7c5',
  'C-GF-08': '#85c2ea',
};

/**
 * The accent for one family id, or a neutral surface colour for an id this table does not carry.
 *
 * Falls back rather than throwing, deliberately: this is called during render, from a screen whose
 * whole job is to keep working when the wire says something unexpected. An unknown family id is a
 * reason to draw a plain background, never a reason to take down a task a child is part-way
 * through. It is also NOT a fail-closed condition -- fail-closed is about refusing to render an
 * INPUT surface that cannot be trusted (see archetype-surfaces.ts and planTaskSurface), and a
 * background colour is not an input. Nothing about this function's fallback changes what happens
 * to an unresolvable template or a missing surface.
 *
 * Own-property lookup, never bare access, so a drifted or hostile id like "constructor" or
 * "__proto__" cannot resolve to an inherited Object.prototype member.
 */
export function accentForGameFamily(gameFamilyId: string): string {
  if (!Object.prototype.hasOwnProperty.call(GAME_FAMILY_ACCENTS, gameFamilyId)) {
    return colors.surface3;
  }
  return GAME_FAMILY_ACCENTS[gameFamilyId];
}
