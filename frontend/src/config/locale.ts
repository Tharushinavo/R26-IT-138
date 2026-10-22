// Which language the learner reads questions in.
//
// The learners this app is built for speak Sinhala first, and until 2026-09-28 every string in the
// product was hard-coded English. The question text itself is authored and resolved on the SERVER
// (backend/app/domain/live_engine/prompt_wording.py), so the only thing the app has to do is say
// which language it wants -- it never translates anything itself, exactly as it never composes a
// stem itself.
//
// `Accept-Language` is how that is said: it is the standard header for it, it is CORS-safelisted
// so it needs no preflight or server allow-list change, and it needs no contract field. A request
// that omits it gets English, so this is additive in both directions -- an older build keeps
// today's behaviour, and a server without the header support ignores it.
//
// ENGLISH IS THE DEFAULT, deliberately. The Sinhala wording is a first draft that has NOT been
// reviewed by a Sinhala-speaking primary teacher, and it must not reach a child until it has.
// Setting EXPO_PUBLIC_LEARNER_LOCALE=si is a conscious act, which is the point: it lets the
// wording be tested and corrected without shipping it to a classroom by default.

export type LearnerLocale = 'en' | 'si';

export const DEFAULT_LEARNER_LOCALE: LearnerLocale = 'en';

const SUPPORTED: readonly LearnerLocale[] = ['en', 'si'];

/**
 * The locale to ask the server for. Anything unrecognised -- including an unset variable or a
 * typo -- falls back to English rather than failing: a child must always get a readable question,
 * and a misconfigured build is not a reason to break one.
 */
export function readLearnerLocale(): LearnerLocale {
  const raw = process.env.EXPO_PUBLIC_LEARNER_LOCALE?.trim().toLowerCase();
  if (!raw) return DEFAULT_LEARNER_LOCALE;
  const primary = raw.split('-')[0] as LearnerLocale;
  return SUPPORTED.includes(primary) ? primary : DEFAULT_LEARNER_LOCALE;
}

/**
 * The `Accept-Language` value for a locale. Sinhala is sent as `si-LK,si` with English after it,
 * so a server that has no Sinhala for a given item can still negotiate down rather than being told
 * Sinhala-or-nothing.
 */
export function acceptLanguageHeader(locale: LearnerLocale = readLearnerLocale()): string {
  return locale === 'si' ? 'si-LK,si;q=0.9,en;q=0.5' : 'en';
}
