// Shared types for the answer-renderer registry (Batch 8).
//
// A `RendererSpec` is the *only* thing that decides how an opportunity's answer surface is drawn
// and what string leaves the device. It is produced by `resolveRenderer` (registry.ts) and
// consumed by `encodeSubmittedValue` (encode.ts) and, from Batch 9 onward, by the session screen.
//
// Nothing here encodes catalogue content. A choice spec carries the server's `presented_choices`
// verbatim, in the server's order; the relation symbols, conservation words, distractor numbers
// and every other answer string live in the backend item catalogue and are relayed through, never
// restated. See registry.ts for the fail-closed rules.

// The three answer surfaces Component B's nine response formats reduce to.
//   'choice'          — a fixed set of tappable options, taken verbatim from presented_choices.
//   'free-entry'      — a raw text field (expanded_form); the child types the whole answer.
//   'count-selection' — the child builds/selects a set and the surface yields a count
//                       (interactive_set_selection).
export type RendererKind = 'choice' | 'free-entry' | 'count-selection';

export type ChoiceRendererSpec = {
  kind: 'choice';
  responseFormat: string;
  // How many choices this format must arrive with. A mismatch is structural drift and is rejected
  // by resolveRenderer rather than rendered with a partial or padded option list.
  expectedChoiceCount: number;
  // Server-given order, preserved exactly. Never re-sorted client-side.
  choices: readonly string[];
};

export type FreeEntryRendererSpec = {
  kind: 'free-entry';
  responseFormat: string;
  expectedChoiceCount: 0;
};

export type CountSelectionRendererSpec = {
  kind: 'count-selection';
  responseFormat: string;
  expectedChoiceCount: 0;
};

export type RendererSpec = ChoiceRendererSpec | FreeEntryRendererSpec | CountSelectionRendererSpec;

// What the answer surface currently holds. `chosenIndex` indexes into the spec's own `choices`,
// so a choice answer can only ever be one of the strings the server presented — the surface has
// no way to express an answer the server did not offer.
export type ChoiceAnswerState = { kind: 'choice'; chosenIndex: number };
export type FreeEntryAnswerState = { kind: 'free-entry'; rawInput: string };
export type CountSelectionAnswerState = { kind: 'count-selection'; count: number };

export type AnswerState = ChoiceAnswerState | FreeEntryAnswerState | CountSelectionAnswerState;
