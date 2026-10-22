import React, { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react';

import { readCompdLearnerState, writeCompdLearnerState } from '@/src/features/compd/compd-state-cache';
import { translations, type Language, type TranslationKeys } from '@/src/features/compd/i18n/translations';
import { useCompdApi } from '@/src/features/compd/use-compd-api';

interface LanguageContextValue {
  lang: Language;
  t: TranslationKeys;
  setLanguage: (lang: Language) => void;
  toggleLanguage: () => void;
}

const LanguageContext = createContext<LanguageContextValue>({
  lang: 'en',
  t: translations.en,
  setLanguage: () => {},
  toggleLanguage: () => {},
});

/**
 * compD's language, kept ON THE SERVER (`/api/v1/d/learner/state`) rather than in device storage,
 * so it follows the learner to another device -- the same reason the intro flag lives there.
 *
 * It starts from the cached server answer the gate already fetched, falls back to asking the
 * server when there is none (a reload straight onto a compD page), and applies a change at once
 * for the child while it is saved in the background. A failed save keeps the child's choice on
 * screen for this session; the server's last saved value is what the next app start shows.
 *
 * Affects compD only (plan v5 Q5): MathMingo's own locale is a separate build-time setting.
 */
export function LanguageProvider({ children }: { children: ReactNode }) {
  const { call, subject } = useCompdApi();
  const [lang, setLangState] = useState<Language>(() => readCompdLearnerState(subject)?.language ?? 'en');

  useEffect(() => {
    if (readCompdLearnerState(subject)) return;
    let cancelled = false;
    call((api, accessToken) => api.getLearnerState(accessToken)).then(
      (state) => {
        writeCompdLearnerState(subject, state);
        if (!cancelled) setLangState(state.language);
      },
      () => undefined,
    );
    return () => {
      cancelled = true;
    };
  }, [call, subject]);

  const setLanguage = useCallback(
    (next: Language) => {
      setLangState(next);
      const cached = readCompdLearnerState(subject);
      if (cached) writeCompdLearnerState(subject, { ...cached, language: next });
      call((api, accessToken) => api.updateLearnerState({ language: next }, accessToken)).then(
        (state) => writeCompdLearnerState(subject, state),
        () => undefined,
      );
    },
    [call, subject],
  );

  const toggleLanguage = useCallback(() => setLanguage(lang === 'en' ? 'si' : 'en'), [lang, setLanguage]);

  const value = useMemo(
    () => ({ lang, t: translations[lang], setLanguage, toggleLanguage }),
    [lang, setLanguage, toggleLanguage],
  );

  return <LanguageContext.Provider value={value}>{children}</LanguageContext.Provider>;
}

export function useLanguage() {
  return useContext(LanguageContext);
}
