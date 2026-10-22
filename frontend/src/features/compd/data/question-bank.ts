/**
 * MathsMate Question Bank — 3 Sets × 20 Questions = 60 Questions
 * Bilingual: English + Sinhala
 * Each question has 4 answer options for the activity screen.
 */
import { animalForTopic, type AnimalId } from '@/src/features/compd/assets/animal-images';

export interface BankQuestion {
  id: string;
  set: 1 | 2 | 3;
  topic: 'Counting' | 'Addition' | 'Subtraction' | 'Division';
  difficulty: 'Easy' | 'Medium' | 'Hard';
  question_text: string;
  question_text_si: string;
  correct_answer: string;
  options: string[];
  /** Animal mascot ID (1-18) shown with this question */
  mascot: AnimalId;
}

/** Shuffle an array (Fisher–Yates) */
export function shuffle<T>(arr: T[]): T[] {
  const a = [...arr];
  for (let i = a.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [a[i], a[j]] = [a[j], a[i]];
  }
  return a;
}

/** Pick `count` random questions from the bank with shuffled options */
export function pickQuestions(count: number = 10, setFilter?: 1 | 2 | 3): BankQuestion[] {
  let pool = [...QUESTION_BANK];
  if (setFilter) pool = pool.filter((q) => q.set === setFilter);
  const picked = shuffle(pool).slice(0, count);
  return picked.map((q) => ({
    ...q,
    options: shuffle(q.options),
  }));
}

/** Pick a random animal image ID for a topic (from TOPIC_ANIMALS registry) */
function m(topic: BankQuestion['topic']): AnimalId {
  return animalForTopic(topic);
}

// Helper: generate 4 numeric options including the correct one
function numOpts(correct: number, spread = 3): string[] {
  const opts = new Set<string>([String(correct)]);
  while (opts.size < 4) {
    const delta = Math.floor(Math.random() * spread * 2 + 1) - spread;
    const candidate = correct + delta;
    if (candidate >= 0 && candidate !== correct) opts.add(String(candidate));
  }
  return Array.from(opts);
}

// ════════════════════════════════════════════════════════════
// SET 01 — 20 QUESTIONS
// ════════════════════════════════════════════════════════════

const SET1: BankQuestion[] = [
  {
    id: 'S1-Q001', set: 1, topic: 'Counting', difficulty: 'Easy',
    question_text: 'Count the apples: 🍎 🍎 🍎 🍎',
    question_text_si: 'ඇපල් ගණන් කරන්න: 🍎 🍎 🍎 🍎',
    correct_answer: '4', options: numOpts(4), mascot: m('Counting'),
  },
  {
    id: 'S1-Q002', set: 1, topic: 'Addition', difficulty: 'Easy',
    question_text: '2 + 3 = ?',
    question_text_si: '2 + 3 = ?',
    correct_answer: '5', options: numOpts(5), mascot: m('Addition'),
  },
  {
    id: 'S1-Q021', set: 1, topic: 'Counting', difficulty: 'Easy',
    question_text: 'Find the missing number: 4, 5, __, 7',
    question_text_si: 'හිස්තැනට ගැළපෙන සංඛ්‍යාව සොයන්න: 4, 5, __, 7',
    correct_answer: '6', options: numOpts(6), mascot: m('Counting'),
  },
  {
    id: 'S1-Q004', set: 1, topic: 'Subtraction', difficulty: 'Easy',
    question_text: '7 - 2 = ?',
    question_text_si: '7 - 2 = ?',
    correct_answer: '5', options: numOpts(5), mascot: m('Subtraction'),
  },
  {
    id: 'S1-Q005', set: 1, topic: 'Counting', difficulty: 'Easy',
    question_text: 'How many stars: ⭐ ⭐ ⭐ ⭐ ⭐ ⭐',
    question_text_si: 'තරු කීයක් තිබේද: ⭐ ⭐ ⭐ ⭐ ⭐ ⭐',
    correct_answer: '6', options: numOpts(6), mascot: m('Counting'),
  },
  {
    id: 'S1-Q006', set: 1, topic: 'Addition', difficulty: 'Medium',
    question_text: '8 + 5 = ?',
    question_text_si: '8 + 5 = ?',
    correct_answer: '13', options: numOpts(13), mascot: m('Addition'),
  },
  {
    id: 'S1-Q007', set: 1, topic: 'Subtraction', difficulty: 'Medium',
    question_text: '14 - 6 = ?',
    question_text_si: '14 - 6 = ?',
    correct_answer: '8', options: numOpts(8), mascot: m('Subtraction'),
  },
  {
    id: 'S1-Q022', set: 1, topic: 'Counting', difficulty: 'Medium',
    question_text: 'Count by 2s: 10, 12, __, 16',
    question_text_si: '2 බැගින් ගණන් කරන්න: 10, 12, __, 16',
    correct_answer: '14', options: numOpts(14), mascot: m('Counting'),
  },
  {
    id: 'S1-Q009', set: 1, topic: 'Counting', difficulty: 'Medium',
    question_text: 'Count by 2s: 2, 4, 6, __',
    question_text_si: '2 බැගින් ගණන් කරන්න: 2, 4, 6, __',
    correct_answer: '8', options: numOpts(8), mascot: m('Counting'),
  },
  {
    id: 'S1-Q010', set: 1, topic: 'Addition', difficulty: 'Medium',
    question_text: '12 + 7 = ?',
    question_text_si: '12 + 7 = ?',
    correct_answer: '19', options: numOpts(19), mascot: m('Addition'),
  },
  {
    id: 'S1-Q011', set: 1, topic: 'Subtraction', difficulty: 'Medium',
    question_text: '20 - 9 = ?',
    question_text_si: '20 - 9 = ?',
    correct_answer: '11', options: numOpts(11), mascot: m('Subtraction'),
  },
  {
    id: 'S1-Q012', set: 1, topic: 'Division', difficulty: 'Medium',
    question_text: '12 ÷ 3 = ?',
    question_text_si: '12 ÷ 3 = ?',
    correct_answer: '4', options: numOpts(4), mascot: m('Division'),
  },
  {
    id: 'S1-Q023', set: 1, topic: 'Counting', difficulty: 'Medium',
    question_text: 'Count by 5s: 20, 25, __, 35',
    question_text_si: '5 බැගින් ගණන් කරන්න: 20, 25, __, 35',
    correct_answer: '30', options: numOpts(30), mascot: m('Counting'),
  },
  {
    id: 'S1-Q014', set: 1, topic: 'Addition', difficulty: 'Hard',
    question_text: '18 + 16 = ?',
    question_text_si: '18 + 16 = ?',
    correct_answer: '34', options: numOpts(34, 4), mascot: m('Addition'),
  },
  {
    id: 'S1-Q015', set: 1, topic: 'Subtraction', difficulty: 'Hard',
    question_text: '35 - 17 = ?',
    question_text_si: '35 - 17 = ?',
    correct_answer: '18', options: numOpts(18, 4), mascot: m('Subtraction'),
  },
  {
    id: 'S1-Q024', set: 1, topic: 'Counting', difficulty: 'Hard',
    question_text: 'Count backward by 2s: 30, 28, __, 24',
    question_text_si: '2 බැගින් පසුපසට ගණන් කරන්න: 30, 28, __, 24',
    correct_answer: '26', options: numOpts(26), mascot: m('Counting'),
  },
  {
    id: 'S1-Q017', set: 1, topic: 'Counting', difficulty: 'Medium',
    question_text: 'Count by 5s: 5, 10, 15, __',
    question_text_si: '5 බැගින් ගණන් කරන්න: 5, 10, 15, __',
    correct_answer: '20', options: numOpts(20), mascot: m('Counting'),
  },
  {
    id: 'S1-Q018', set: 1, topic: 'Division', difficulty: 'Hard',
    question_text: '36 ÷ 6 = ?',
    question_text_si: '36 ÷ 6 = ?',
    correct_answer: '6', options: numOpts(6), mascot: m('Division'),
  },
  {
    id: 'S1-Q025', set: 1, topic: 'Counting', difficulty: 'Hard',
    question_text: 'Count by 10s: 15, 25, __, 45',
    question_text_si: '10 බැගින් ගණන් කරන්න: 15, 25, __, 45',
    correct_answer: '35', options: numOpts(35), mascot: m('Counting'),
  },
  {
    id: 'S1-Q020', set: 1, topic: 'Counting', difficulty: 'Hard',
    question_text: 'Count backward by 3s: 15, 12, 9, __',
    question_text_si: '3 බැගින් පසුපසට ගණන් කරන්න: 15, 12, 9, __',
    correct_answer: '6', options: numOpts(6), mascot: m('Counting'),
  },
];

// ════════════════════════════════════════════════════════════
// SET 02 — 20 QUESTIONS
// ════════════════════════════════════════════════════════════

const SET2: BankQuestion[] = [
  {
    id: 'S2-Q001', set: 2, topic: 'Counting', difficulty: 'Easy',
    question_text: 'Count the bananas: 🍌 🍌 🍌',
    question_text_si: 'කෙසෙල් ගණන් කරන්න: 🍌 🍌 🍌',
    correct_answer: '3', options: numOpts(3), mascot: m('Counting'),
  },
  {
    id: 'S2-Q002', set: 2, topic: 'Addition', difficulty: 'Easy',
    question_text: '4 + 2 = ?',
    question_text_si: '4 + 2 = ?',
    correct_answer: '6', options: numOpts(6), mascot: m('Addition'),
  },
  {
    id: 'S2-Q021', set: 2, topic: 'Counting', difficulty: 'Easy',
    question_text: 'Find the missing number: 6, 7, __, 9',
    question_text_si: 'හිස්තැනට ගැළපෙන සංඛ්‍යාව සොයන්න: 6, 7, __, 9',
    correct_answer: '8', options: numOpts(8), mascot: m('Counting'),
  },
  {
    id: 'S2-Q004', set: 2, topic: 'Subtraction', difficulty: 'Easy',
    question_text: '9 - 4 = ?',
    question_text_si: '9 - 4 = ?',
    correct_answer: '5', options: numOpts(5), mascot: m('Subtraction'),
  },
  {
    id: 'S2-Q005', set: 2, topic: 'Counting', difficulty: 'Easy',
    question_text: 'How many balls: ⚽ ⚽ ⚽ ⚽ ⚽',
    question_text_si: 'බෝල කීයක් තිබේද: ⚽ ⚽ ⚽ ⚽ ⚽',
    correct_answer: '5', options: numOpts(5), mascot: m('Counting'),
  },
  {
    id: 'S2-Q006', set: 2, topic: 'Addition', difficulty: 'Medium',
    question_text: '7 + 6 = ?',
    question_text_si: '7 + 6 = ?',
    correct_answer: '13', options: numOpts(13), mascot: m('Addition'),
  },
  {
    id: 'S2-Q007', set: 2, topic: 'Subtraction', difficulty: 'Medium',
    question_text: '16 - 7 = ?',
    question_text_si: '16 - 7 = ?',
    correct_answer: '9', options: numOpts(9), mascot: m('Subtraction'),
  },
  {
    id: 'S2-Q022', set: 2, topic: 'Counting', difficulty: 'Medium',
    question_text: 'Count by 2s: 12, 14, __, 18',
    question_text_si: '2 බැගින් ගණන් කරන්න: 12, 14, __, 18',
    correct_answer: '16', options: numOpts(16), mascot: m('Counting'),
  },
  {
    id: 'S2-Q009', set: 2, topic: 'Counting', difficulty: 'Medium',
    question_text: 'Count by 2s: 4, 6, 8, __',
    question_text_si: '2 බැගින් ගණන් කරන්න: 4, 6, 8, __',
    correct_answer: '10', options: numOpts(10), mascot: m('Counting'),
  },
  {
    id: 'S2-Q010', set: 2, topic: 'Addition', difficulty: 'Medium',
    question_text: '15 + 8 = ?',
    question_text_si: '15 + 8 = ?',
    correct_answer: '23', options: numOpts(23), mascot: m('Addition'),
  },
  {
    id: 'S2-Q011', set: 2, topic: 'Subtraction', difficulty: 'Medium',
    question_text: '25 - 11 = ?',
    question_text_si: '25 - 11 = ?',
    correct_answer: '14', options: numOpts(14), mascot: m('Subtraction'),
  },
  {
    id: 'S2-Q012', set: 2, topic: 'Division', difficulty: 'Medium',
    question_text: '12 ÷ 4 = ?',
    question_text_si: '12 ÷ 4 = ?',
    correct_answer: '3', options: numOpts(3), mascot: m('Division'),
  },
  {
    id: 'S2-Q023', set: 2, topic: 'Counting', difficulty: 'Medium',
    question_text: 'Count by 5s: 25, 30, __, 40',
    question_text_si: '5 බැගින් ගණන් කරන්න: 25, 30, __, 40',
    correct_answer: '35', options: numOpts(35), mascot: m('Counting'),
  },
  {
    id: 'S2-Q014', set: 2, topic: 'Addition', difficulty: 'Hard',
    question_text: '24 + 19 = ?',
    question_text_si: '24 + 19 = ?',
    correct_answer: '43', options: numOpts(43, 4), mascot: m('Addition'),
  },
  {
    id: 'S2-Q015', set: 2, topic: 'Subtraction', difficulty: 'Hard',
    question_text: '42 - 18 = ?',
    question_text_si: '42 - 18 = ?',
    correct_answer: '24', options: numOpts(24, 4), mascot: m('Subtraction'),
  },
  {
    id: 'S2-Q024', set: 2, topic: 'Counting', difficulty: 'Hard',
    question_text: 'Count backward by 2s: 40, 38, __, 34',
    question_text_si: '2 බැගින් පසුපසට ගණන් කරන්න: 40, 38, __, 34',
    correct_answer: '36', options: numOpts(36), mascot: m('Counting'),
  },
  {
    id: 'S2-Q017', set: 2, topic: 'Counting', difficulty: 'Medium',
    question_text: 'Count by 5s: 10, 15, 20, __',
    question_text_si: '5 බැගින් ගණන් කරන්න: 10, 15, 20, __',
    correct_answer: '25', options: numOpts(25), mascot: m('Counting'),
  },
  {
    id: 'S2-Q018', set: 2, topic: 'Division', difficulty: 'Hard',
    question_text: '48 ÷ 8 = ?',
    question_text_si: '48 ÷ 8 = ?',
    correct_answer: '6', options: numOpts(6), mascot: m('Division'),
  },
  {
    id: 'S2-Q019', set: 2, topic: 'Subtraction', difficulty: 'Hard',
    question_text: '60 - 27 = ?',
    question_text_si: '60 - 27 = ?',
    correct_answer: '33', options: numOpts(33, 4), mascot: m('Subtraction'),
  },
  {
    id: 'S2-Q020', set: 2, topic: 'Division', difficulty: 'Hard',
    question_text: '36 ÷ 9 = ?',
    question_text_si: '36 ÷ 9 = ?',
    correct_answer: '4', options: numOpts(4), mascot: m('Division'),
  },
];

// ════════════════════════════════════════════════════════════
// SET 03 — 20 QUESTIONS
// ════════════════════════════════════════════════════════════

const SET3: BankQuestion[] = [
  {
    id: 'S3-Q001', set: 3, topic: 'Counting', difficulty: 'Easy',
    question_text: 'Count the flowers: 🌸 🌸 🌸 🌸 🌸',
    question_text_si: 'මල් ගණන් කරන්න: 🌸 🌸 🌸 🌸 🌸',
    correct_answer: '5', options: numOpts(5), mascot: m('Counting'),
  },
  {
    id: 'S3-Q002', set: 3, topic: 'Addition', difficulty: 'Easy',
    question_text: '3 + 4 = ?',
    question_text_si: '3 + 4 = ?',
    correct_answer: '7', options: numOpts(7), mascot: m('Addition'),
  },
  {
    id: 'S3-Q021', set: 3, topic: 'Counting', difficulty: 'Easy',
    question_text: 'Find the missing number: 8, 9, __, 11',
    question_text_si: 'හිස්තැනට ගැළපෙන සංඛ්‍යාව සොයන්න: 8, 9, __, 11',
    correct_answer: '10', options: numOpts(10), mascot: m('Counting'),
  },
  {
    id: 'S3-Q004', set: 3, topic: 'Subtraction', difficulty: 'Easy',
    question_text: '8 - 3 = ?',
    question_text_si: '8 - 3 = ?',
    correct_answer: '5', options: numOpts(5), mascot: m('Subtraction'),
  },
  {
    id: 'S3-Q005', set: 3, topic: 'Counting', difficulty: 'Easy',
    question_text: 'How many pencils: ✏️ ✏️ ✏️ ✏️',
    question_text_si: 'පැන්සල් කීයක් තිබේද: ✏️ ✏️ ✏️ ✏️',
    correct_answer: '4', options: numOpts(4), mascot: m('Counting'),
  },
  {
    id: 'S3-Q006', set: 3, topic: 'Addition', difficulty: 'Medium',
    question_text: '9 + 7 = ?',
    question_text_si: '9 + 7 = ?',
    correct_answer: '16', options: numOpts(16), mascot: m('Addition'),
  },
  {
    id: 'S3-Q007', set: 3, topic: 'Subtraction', difficulty: 'Medium',
    question_text: '18 - 9 = ?',
    question_text_si: '18 - 9 = ?',
    correct_answer: '9', options: numOpts(9), mascot: m('Subtraction'),
  },
  {
    id: 'S3-Q022', set: 3, topic: 'Counting', difficulty: 'Medium',
    question_text: 'Count by 2s: 16, 18, __, 22',
    question_text_si: '2 බැගින් ගණන් කරන්න: 16, 18, __, 22',
    correct_answer: '20', options: numOpts(20), mascot: m('Counting'),
  },
  {
    id: 'S3-Q009', set: 3, topic: 'Counting', difficulty: 'Medium',
    question_text: 'Count by 2s: 6, 8, 10, __',
    question_text_si: '2 බැගින් ගණන් කරන්න: 6, 8, 10, __',
    correct_answer: '12', options: numOpts(12), mascot: m('Counting'),
  },
  {
    id: 'S3-Q010', set: 3, topic: 'Addition', difficulty: 'Medium',
    question_text: '14 + 9 = ?',
    question_text_si: '14 + 9 = ?',
    correct_answer: '23', options: numOpts(23), mascot: m('Addition'),
  },
  {
    id: 'S3-Q011', set: 3, topic: 'Subtraction', difficulty: 'Medium',
    question_text: '30 - 12 = ?',
    question_text_si: '30 - 12 = ?',
    correct_answer: '18', options: numOpts(18), mascot: m('Subtraction'),
  },
  {
    id: 'S3-Q012', set: 3, topic: 'Division', difficulty: 'Medium',
    question_text: '15 ÷ 3 = ?',
    question_text_si: '15 ÷ 3 = ?',
    correct_answer: '5', options: numOpts(5), mascot: m('Division'),
  },
  {
    id: 'S3-Q023', set: 3, topic: 'Counting', difficulty: 'Medium',
    question_text: 'Count by 5s: 30, 35, __, 45',
    question_text_si: '5 බැගින් ගණන් කරන්න: 30, 35, __, 45',
    correct_answer: '40', options: numOpts(40), mascot: m('Counting'),
  },
  {
    id: 'S3-Q014', set: 3, topic: 'Addition', difficulty: 'Hard',
    question_text: '29 + 17 = ?',
    question_text_si: '29 + 17 = ?',
    correct_answer: '46', options: numOpts(46, 4), mascot: m('Addition'),
  },
  {
    id: 'S3-Q015', set: 3, topic: 'Subtraction', difficulty: 'Hard',
    question_text: '55 - 28 = ?',
    question_text_si: '55 - 28 = ?',
    correct_answer: '27', options: numOpts(27, 4), mascot: m('Subtraction'),
  },
  {
    id: 'S3-Q024', set: 3, topic: 'Counting', difficulty: 'Hard',
    question_text: 'Count backward by 2s: 50, 48, __, 44',
    question_text_si: '2 බැගින් පසුපසට ගණන් කරන්න: 50, 48, __, 44',
    correct_answer: '46', options: numOpts(46), mascot: m('Counting'),
  },
  {
    id: 'S3-Q017', set: 3, topic: 'Counting', difficulty: 'Medium',
    question_text: 'Count by 5s: 15, 20, 25, __',
    question_text_si: '5 බැගින් ගණන් කරන්න: 15, 20, 25, __',
    correct_answer: '30', options: numOpts(30), mascot: m('Counting'),
  },
  {
    id: 'S3-Q018', set: 3, topic: 'Division', difficulty: 'Hard',
    question_text: '56 ÷ 7 = ?',
    question_text_si: '56 ÷ 7 = ?',
    correct_answer: '8', options: numOpts(8), mascot: m('Division'),
  },
  {
    id: 'S3-Q025', set: 3, topic: 'Counting', difficulty: 'Hard',
    question_text: 'Count by 10s: 25, 35, __, 55',
    question_text_si: '10 බැගින් ගණන් කරන්න: 25, 35, __, 55',
    correct_answer: '45', options: numOpts(45), mascot: m('Counting'),
  },
  {
    id: 'S3-Q020', set: 3, topic: 'Division', difficulty: 'Hard',
    question_text: '64 ÷ 8 = ?',
    question_text_si: '64 ÷ 8 = ?',
    correct_answer: '8', options: numOpts(8), mascot: m('Division'),
  },
];

export const QUESTION_BANK: BankQuestion[] = [...SET1, ...SET2, ...SET3];
