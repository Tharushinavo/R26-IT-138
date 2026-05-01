import type { InteractionEvent } from '../api/client';

export interface Question {
  id: string;
  type: InteractionEvent['question_type'];
  difficulty: number;
  prompt: string;
  options: number[];
  answer: number;
}

function randInt(min: number, max: number) {
  return Math.floor(Math.random() * (max - min + 1)) + min;
}

function shuffle<T>(arr: T[]): T[] {
  const a = [...arr];
  for (let i = a.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [a[i], a[j]] = [a[j], a[i]];
  }
  return a;
}

function buildQuestion(id: string): Question {
  const kinds = ['addition', 'subtraction', 'multiplication', 'number_sense'] as const;
  const type = kinds[randInt(0, kinds.length - 1)];

  let a = 0;
  let b = 0;
  let answer = 0;
  let prompt = '';
  let difficulty = 1;

  switch (type) {
    case 'addition': {
      a = randInt(1, 20);
      b = randInt(1, 20);
      answer = a + b;
      prompt = `${a} + ${b} = ?`;
      difficulty = a + b > 20 ? 2 : 1;
      break;
    }
    case 'subtraction': {
      a = randInt(5, 25);
      b = randInt(1, a);
      answer = a - b;
      prompt = `${a} − ${b} = ?`;
      difficulty = a > 15 ? 2 : 1;
      break;
    }
    case 'multiplication': {
      a = randInt(2, 9);
      b = randInt(2, 9);
      answer = a * b;
      prompt = `${a} × ${b} = ?`;
      difficulty = 3;
      break;
    }
    case 'number_sense': {
      a = randInt(10, 99);
      b = randInt(10, 99);
      answer = Math.max(a, b);
      prompt = `Which number is bigger? ${a} or ${b}`;
      difficulty = 1;
      break;
    }
  }

  // Generate distractor options
  const distractors = new Set<number>();
  while (distractors.size < 3) {
    const delta = randInt(-5, 5);
    const cand = type === 'number_sense' ? (delta >= 0 ? a : b) : answer + delta;
    if (cand !== answer && cand >= 0) distractors.add(cand);
  }
  const options =
    type === 'number_sense'
      ? shuffle([a, b, Math.max(a, b) + randInt(1, 5), Math.min(a, b) - randInt(1, 5)].filter((v, i, arr) => arr.indexOf(v) === i)).slice(0, 4)
      : shuffle([answer, ...Array.from(distractors)]);

  return {
    id,
    type,
    difficulty,
    prompt,
    options: options.length >= 2 ? options : [answer, answer + 1, answer - 1, answer + 2],
    answer,
  };
}

export function generateQuestions(count: number = 8): Question[] {
  return Array.from({ length: count }, (_, i) => buildQuestion(`q_${Date.now()}_${i}`));
}
