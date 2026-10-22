// compD's hint button, LOCAL ONLY (plan v5, N2). compD used to ask a server endpoint and then Gemini
// directly from the app; MathMingo's architecture excludes LLM-generated hints, so the child gets
// the same short, topic-based nudge compD already used as its fallback -- with no network call.

export interface MathHint {
  text: string;
}

const HINTS: Record<'en' | 'si', { match: string[]; text: string }[]> = {
  en: [
    { match: ['addition'], text: 'Try counting up from the bigger number!' },
    { match: ['subtraction'], text: 'Think: what do I add to the small number to get the big one?' },
    { match: ['division'], text: 'Try splitting into equal groups!' },
    { match: ['comparison'], text: 'Compare the first digits (tens place) first!' },
    { match: ['counting'], text: 'Count carefully, one by one!' },
  ],
  si: [
    { match: ['addition', 'එකතු'], text: 'විශාල සංඛ්‍යාවේ සිට ඉහළට ගණන් කරන්න!' },
    { match: ['subtraction', 'අඩු'], text: 'කුඩා සංඛ්‍යාවට කොපමණ එකතු කළ යුතුදැයි සිතන්න!' },
    { match: ['division', 'බෙදීම'], text: 'සමාන කණ්ඩායම් වලට බෙදා බලන්න!' },
    { match: ['comparison', 'සංසන්දනය'], text: 'පළමුව වම් පස ඇති ඉලක්කම් සංසන්දනය කරන්න!' },
    { match: ['counting', 'ගණන්'], text: 'සෙමින්, එකින් එක ගණන් කරන්න!' },
  ],
};

const DEFAULT_HINT = {
  en: 'Take a breath and read the question again. Think step by step!',
  si: 'හුස්ම ගන්න, ප්‍රශ්නය නැවත කියවන්න. පියවර අනුව සිතන්න!',
};

export function localMathHint(topic: string, language: 'en' | 'si' = 'en'): MathHint {
  const t = (topic || '').toLowerCase();
  const found = HINTS[language].find((hint) => hint.match.some((word) => t.includes(word)));
  return { text: found?.text ?? DEFAULT_HINT[language] };
}

/** Same signature compD's screen calls; the question text is no longer sent anywhere. */
export async function generateMathHint(_question: string, topic: string, language: 'en' | 'si' = 'en'): Promise<MathHint> {
  return localMathHint(topic, language);
}
