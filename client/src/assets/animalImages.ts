/**
 * Animal images registry.
 * Metro bundler requires static require() calls — paths cannot be dynamic.
 * Each animal is keyed by its numeric ID (1-18) matching assets/animals/{id}.png.
 */

export type AnimalId =
  | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9
  | 10 | 11 | 12 | 13 | 14 | 15 | 16 | 17 | 18;

export const ANIMAL_IMAGES: Record<AnimalId, number> = {
  1: require('../../assets/animals/1.png'),   // Duck (yellow)
  2: require('../../assets/animals/2.png'),   // Elephant (gray)
  3: require('../../assets/animals/3.png'),   // Turtle
  4: require('../../assets/animals/4.png'),   // Clownfish
  5: require('../../assets/animals/5.png'),   // Lion
  6: require('../../assets/animals/6.png'),   // Duckling
  7: require('../../assets/animals/7.png'),   // Green dragon
  8: require('../../assets/animals/8.png'),   // Pigeon officer
  9: require('../../assets/animals/9.png'),   // Koala
  10: require('../../assets/animals/10.png'), // Puppy with ball
  11: require('../../assets/animals/11.png'), // Fox
  12: require('../../assets/animals/12.png'), // Giraffe
  13: require('../../assets/animals/13.png'), // Gecko / lizard
  14: require('../../assets/animals/14.png'), // Dalmatian
  15: require('../../assets/animals/15.png'), // Penguin
  16: require('../../assets/animals/16.png'), // Parrot
  17: require('../../assets/animals/17.png'), // Cow
  18: require('../../assets/animals/18.png'), // Panda
};

export const ANIMAL_NAMES: Record<AnimalId, string> = {
  1: 'Duck', 2: 'Elephant', 3: 'Turtle', 4: 'Fish', 5: 'Lion',
  6: 'Duckling', 7: 'Dragon', 8: 'Officer Pigeon', 9: 'Koala',
  10: 'Puppy', 11: 'Fox', 12: 'Giraffe', 13: 'Gecko',
  14: 'Dalmatian', 15: 'Penguin', 16: 'Parrot', 17: 'Cow', 18: 'Panda',
};

/** Animal IDs grouped by topic — used as question mascots */
export const TOPIC_ANIMALS: Record<string, AnimalId[]> = {
  'Counting': [1, 6, 15, 16],              // Ducks, penguin, parrot
  'Addition': [5, 18, 7],                   // Lion, panda, dragon
  'Subtraction': [9, 11, 14],               // Koala, fox, dalmatian
  'Number Comparison': [12, 2, 17],         // Giraffe, elephant, cow
  'Division': [10, 3, 4, 13],               // Puppy, turtle, fish, gecko
};

/** Celebration / hero animals shown after correct answers or milestones */
export const CELEBRATION_ANIMALS: AnimalId[] = [5, 18, 7, 11, 16, 8];

/** Pick a random animal ID for a given topic */
export function animalForTopic(topic: string): AnimalId {
  const pool = TOPIC_ANIMALS[topic] ?? [5];
  return pool[Math.floor(Math.random() * pool.length)];
}

/** Pick a random celebration animal */
export function randomCelebrationAnimal(): AnimalId {
  return CELEBRATION_ANIMALS[Math.floor(Math.random() * CELEBRATION_ANIMALS.length)];
}
