// One accent palette per Component B skill, mirroring c-session's game-family-accents.ts: the
// same idea (an id on the wire maps to a presentation-only colour, with a neutral fallback for an
// id this table does not carry) applied to Component B's own `skill_id` instead of Component C's
// `game_family_id`. Kept as B's own file rather than imported from c-session, matching that file's
// own note on dependency direction — B does not depend on C, so it does not reach into C's module
// for a colour table shaped for a different id space.
//
// Three colours per skill, not one: `border` edges the question card (the loud, high-saturation
// tone), `soft` is a pale tint for the skill pill's background, and `text` is a darker shade of
// the same hue for the pill's label and icon — legible on `soft` without needing to compute
// contrast at render time. This is the same border/soft/foreground shape the rest of the palette
// already uses (`colors.primary` / `primarySoft` / `primaryShadow`), just one triple per skill
// instead of one triple for the whole app.
//
// This module decides nothing beyond colour: it reads no difficulty, no mastery and no question
// content, and there is no branch here that could.

import { colors } from '@/src/theme/colors';

type SkillPalette = { border: string; soft: string; text: string };

/** Keyed by `skill_id` as it appears on the wire (`OpportunityPresentationFields.skill_id`). */
const SKILL_PALETTES: Record<string, SkillPalette> = {
  addition: { border: colors.primary, soft: colors.primarySoft, text: colors.primaryShadow },
  counting: { border: colors.accentGreen, soft: '#e9f8f1', text: '#1f7a54' },
  division: { border: '#ffb51f', soft: '#fff3e0', text: '#9a5b00' },
  multiplication: { border: '#9a64df', soft: '#f2ebfc', text: '#6a3fae' },
  number_sense: { border: colors.accentWingPink, soft: '#fff0f4', text: '#c33a5c' },
  place_value: {
    border: colors.secondaryShadow,
    soft: colors.secondarySoft,
    text: colors.secondaryForeground,
  },
  subtraction: { border: colors.accentBlue, soft: '#e7f4fe', text: '#155a8a' },
};

const FALLBACK_PALETTE: SkillPalette = {
  border: colors.surface3,
  soft: colors.primarySoft,
  text: colors.primaryShadow,
};

/**
 * Own-property lookup, never bare access, so a drifted or hostile id like "constructor" cannot
 * resolve to an inherited Object.prototype member. Falls back rather than throwing: called during
 * render, from a screen that must keep working when the wire sends a skill id this table has not
 * been taught yet — never a reason to change what question is shown.
 */
function paletteForSkill(skillId: string): SkillPalette {
  if (!Object.prototype.hasOwnProperty.call(SKILL_PALETTES, skillId)) return FALLBACK_PALETTE;
  return SKILL_PALETTES[skillId];
}

/** The question card's border colour for one skill id. */
export function accentForSkill(skillId: string): string {
  return paletteForSkill(skillId).border;
}

/** The skill pill's background and label/icon colours for one skill id. */
export function pillColorsForSkill(skillId: string): { soft: string; text: string } {
  const { soft, text } = paletteForSkill(skillId);
  return { soft, text };
}

// The "five game-type colours" the screen's background gradient draws from — the same five hex
// values `learner-home-screen.tsx`'s own `PATH_NODE_POSITIONS` already uses to colour each path
// node/game type on the home screen (that array is private to its own file, so these are the same
// literal values reproduced here, not an import — the two are independent, and a change to the
// path's own five colours does not need to ripple into this one automatically). Deliberately not
// all seven `SKILL_PALETTES` border colours: number_sense and place_value are left out, matching
// the home screen's own five-colour set exactly rather than inventing a different one here.
const GAME_TYPE_BACKGROUND_COLORS = [
  colors.primary,
  colors.accentBlue,
  colors.accentGreen,
  '#ffb51f',
  '#9a64df',
] as const;

/**
 * Two distinct colours drawn at random from the five game-type colours, for the screen background
 * gradient — never including `excludeColor` (the current question's own card-border accent), so
 * the background can never accidentally match the card's edge. Returns a fresh pair on every call;
 * callers that want it stable across re-renders (this screen re-randomises once per question, not
 * once per render) are expected to memoise the result themselves, keyed on whatever should trigger
 * a new pick.
 */
export function pickBackgroundGradientColors(excludeColor: string): readonly [string, string] {
  const pool = GAME_TYPE_BACKGROUND_COLORS.filter((color) => color !== excludeColor);
  const first = pool[Math.floor(Math.random() * pool.length)];
  const remaining = pool.filter((color) => color !== first);
  const second = remaining[Math.floor(Math.random() * remaining.length)];
  return [first, second];
}
