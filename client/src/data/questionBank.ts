/**
 * MathsMate Question Bank — 3 Sets × 20 Questions = 60 Questions
 * Bilingual: English + Sinhala
 * Each question has 4 answer options for the activity screen.
 */
import { animalForTopic, type AnimalId } from '../assets/animalImages';

export interface BankQuestion {
  id: string;
  set: 1 | 2 | 3;
  topic: 'Counting' | 'Addition' | 'Subtraction' | 'Number Comparison' | 'Division';
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
    id: 'S1-Q003', set: 1, topic: 'Number Comparison', difficulty: 'Easy',
    question_text: 'Which number is bigger: 6 or 9?',
    question_text_si: '6 සහ 9 අතරින් විශාල සංඛ්‍යාව කුමක්ද?',
    correct_answer: '9', options: ['6', '9', '3', '12'], mascot: m('Number Comparison'),
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
    id: 'S1-Q008', set: 1, topic: 'Number Comparison', difficulty: 'Medium',
    question_text: 'Which number is smaller: 18 or 12?',
    question_text_si: '18 සහ 12 අතරින් කුඩා සංඛ්‍යාව කුමක්ද?',
    correct_answer: '12', options: ['18', '12', '15', '10'], mascot: m('Number Comparison'),
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
    id: 'S1-Q013', set: 1, topic: 'Number Comparison', difficulty: 'Medium',
    question_text: 'Which is greater: 24 or 29?',
    question_text_si: '24 සහ 29 අතරින් විශාල සංඛ්‍යාව කුමක්ද?',
    correct_answer: '29', options: ['24', '29', '26', '31'], mascot: m('Number Comparison'),
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
    id: 'S1-Q016', set: 1, topic: 'Number Comparison', difficulty: 'Hard',
    question_text: 'Arrange smallest to biggest: 42, 24, 36',
    question_text_si: '42, 24, 36 කුඩාම සිට විශාලම දක්වා සකසන්න',
    correct_answer: '24, 36, 42', options: ['24, 36, 42', '36, 24, 42', '42, 36, 24', '24, 42, 36'], mascot: m('Number Comparison'),
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
    id: 'S1-Q019', set: 1, topic: 'Number Comparison', difficulty: 'Hard',
    question_text: 'Which number is closest to 50: 47, 39, or 62?',
    question_text_si: '50 ට වඩාත් ආසන්න සංඛ්‍යාව කුමක්ද: 47, 39, හෝ 62?',
    correct_answer: '47', options: ['47', '39', '62', '50'], mascot: m('Number Comparison'),
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
    id: 'S2-Q003', set: 2, topic: 'Number Comparison', difficulty: 'Easy',
    question_text: 'Which number is bigger: 5 or 8?',
    question_text_si: '5 සහ 8 අතරින් විශාල සංඛ්‍යාව කුමක්ද?',
    correct_answer: '8', options: ['5', '8', '3', '10'], mascot: m('Number Comparison'),
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
    id: 'S2-Q008', set: 2, topic: 'Number Comparison', difficulty: 'Medium',
    question_text: 'Which number is smaller: 21 or 14?',
    question_text_si: '21 සහ 14 අතරින් කුඩා සංඛ්‍යාව කුමක්ද?',
    correct_answer: '14', options: ['21', '14', '17', '11'], mascot: m('Number Comparison'),
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
    id: 'S2-Q013', set: 2, topic: 'Number Comparison', difficulty: 'Medium',
    question_text: 'Which is greater: 31 or 27?',
    question_text_si: '31 සහ 27 අතරින් විශාල සංඛ්‍යාව කුමක්ද?',
    correct_answer: '31', options: ['31', '27', '29', '33'], mascot: m('Number Comparison'),
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
    id: 'S2-Q016', set: 2, topic: 'Number Comparison', difficulty: 'Hard',
    question_text: 'Arrange smallest to biggest: 54, 35, 48',
    question_text_si: '54, 35, 48 කුඩාම සිට විශාලම දක්වා සකසන්න',
    correct_answer: '35, 48, 54', options: ['35, 48, 54', '48, 35, 54', '54, 48, 35', '35, 54, 48'], mascot: m('Number Comparison'),
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
    id: 'S3-Q003', set: 3, topic: 'Number Comparison', difficulty: 'Easy',
    question_text: 'Which number is bigger: 7 or 4?',
    question_text_si: '7 සහ 4 අතරින් විශාල සංඛ්‍යාව කුමක්ද?',
    correct_answer: '7', options: ['7', '4', '5', '9'], mascot: m('Number Comparison'),
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
    id: 'S3-Q008', set: 3, topic: 'Number Comparison', difficulty: 'Medium',
    question_text: 'Which number is smaller: 26 or 19?',
    question_text_si: '26 සහ 19 අතරින් කුඩා සංඛ්‍යාව කුමක්ද?',
    correct_answer: '19', options: ['26', '19', '22', '16'], mascot: m('Number Comparison'),
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
    id: 'S3-Q013', set: 3, topic: 'Number Comparison', difficulty: 'Medium',
    question_text: 'Which is greater: 38 or 34?',
    question_text_si: '38 සහ 34 අතරින් විශාල සංඛ්‍යාව කුමක්ද?',
    correct_answer: '38', options: ['38', '34', '36', '40'], mascot: m('Number Comparison'),
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
    id: 'S3-Q016', set: 3, topic: 'Number Comparison', difficulty: 'Hard',
    question_text: 'Arrange smallest to biggest: 63, 41, 57',
    question_text_si: '63, 41, 57 කුඩාම සිට විශාලම දක්වා සකසන්න',
    correct_answer: '41, 57, 63', options: ['41, 57, 63', '57, 41, 63', '63, 57, 41', '41, 63, 57'], mascot: m('Number Comparison'),
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
    id: 'S3-Q019', set: 3, topic: 'Number Comparison', difficulty: 'Hard',
    question_text: 'Which number is closest to 70: 68, 59, or 81?',
    question_text_si: '70 ට වඩාත් ආසන්න සංඛ්‍යාව කුමක්ද: 68, 59, හෝ 81?',
    correct_answer: '68', options: ['68', '59', '81', '70'], mascot: m('Number Comparison'),
  },
  {
    id: 'S3-Q020', set: 3, topic: 'Division', difficulty: 'Hard',
    question_text: '64 ÷ 8 = ?',
    question_text_si: '64 ÷ 8 = ?',
    correct_answer: '8', options: numOpts(8), mascot: m('Division'),
  },
];

export const QUESTION_BANK: BankQuestion[] = [...SET1, ...SET2, ...SET3];
