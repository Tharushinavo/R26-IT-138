// One child-friendly display name per Component C game family, shown in the task screen's top
// pill (c-session-screen.tsx). Mirrors game-family-accents.ts's own shape and reasoning exactly:
// a family id in, a presentation value out, nothing about task state or content decided here.
//
// These are the "Child-friendly name" column values, not the "Current technical name" column
// (game-hub/game-catalogue.ts's own `title` field carries the latter, e.g. "Number Path and
// Order") -- the two tables serve different audiences and are kept as two separate constants
// rather than one doing double duty.

/**
 * Keyed by `game_family_id` as it appears on the wire (`CNextTaskResponse.game_family_id`), same
 * as `GAME_FAMILY_ACCENTS`.
 */
export const GAME_FAMILY_NAMES: Record<string, string> = {
  'C-GF-01': 'Count & Collect',
  'C-GF-02': 'Number Path',
  'C-GF-03': 'Find & Compare',
  'C-GF-04': 'Build Numbers',
  'C-GF-05': 'Join Numbers',
  'C-GF-06': 'Take Away',
  'C-GF-07': 'Make Equal Groups',
  'C-GF-08': 'Share Fairly',
};

/**
 * The child-friendly name for one family id, or a neutral fallback for an id this table does not
 * carry. Falls back rather than throwing, for the same reason `accentForGameFamily` does: this
 * runs during render of a task the child is already partway through, and an unrecognised id is a
 * reason to show a plain label, never a reason to take the screen down.
 *
 * Own-property lookup, never bare access, so a drifted or hostile id like "constructor" or
 * "__proto__" cannot resolve to an inherited Object.prototype member.
 */
export function nameForGameFamily(gameFamilyId: string): string {
  if (!Object.prototype.hasOwnProperty.call(GAME_FAMILY_NAMES, gameFamilyId)) {
    return 'Maths';
  }
  return GAME_FAMILY_NAMES[gameFamilyId];
}
