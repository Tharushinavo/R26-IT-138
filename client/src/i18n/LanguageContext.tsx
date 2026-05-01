import React, { createContext, useContext, useState, useCallback, ReactNode } from 'react';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { translations, type Language, type TranslationKeys } from './translations';

const LANG_KEY = 'mm.language';

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

export function LanguageProvider({ children }: { children: ReactNode }) {
  const [lang, setLangState] = useState<Language>('en');

  // Load persisted language on mount
  React.useEffect(() => {
    (async () => {
      const stored = await AsyncStorage.getItem(LANG_KEY);
      if (stored === 'si' || stored === 'en') {
        setLangState(stored);
      }
    })();
  }, []);

  const setLanguage = useCallback((newLang: Language) => {
    setLangState(newLang);
    AsyncStorage.setItem(LANG_KEY, newLang);
  }, []);

  const toggleLanguage = useCallback(() => {
    setLangState((prev) => {
      const next = prev === 'en' ? 'si' : 'en';
      AsyncStorage.setItem(LANG_KEY, next);
      return next;
    });
  }, []);

  return (
    <LanguageContext.Provider value={{ lang, t: translations[lang], setLanguage, toggleLanguage }}>
      {children}
    </LanguageContext.Provider>
  );
}

export function useLanguage() {
  return useContext(LanguageContext);
}
