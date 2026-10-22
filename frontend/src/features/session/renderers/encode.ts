// This module serializes a choice the child made. That is all it does.
//
// It never parses, canonicalizes, compares, reorders or validates an answer. It does not decide
// whether an answer is right, well-formed, or even plausible — the server owns correctness and
// the server owns normalization (`normalize_answer` strips leading zeros, so whether "03" equals
// "3" is the server's business, not ours).
//
// Concretely:
//   - choice          → the chosen presented_choices string, byte-for-byte. No trimming, no case
//                       folding, no re-joining. "12,45,300" keeps its exact spacing; "same" stays
//                       "same", never "Same".
//   - free-entry      → the raw input with leading/trailing whitespace trimmed and NOTHING else.
//                       No internal whitespace collapsing, no reordering of terms, no case
//                       folding, no symbol substitution. " 100 + 20 + 3 " becomes
//                       "100 + 20 + 3", spacing between the terms untouched.
//   - count-selection → String(count).
//
// A `null` return means "there is nothing submittable here" (kind mismatch, out-of-range
// selection, non-integer count, or an empty free-entry field). Callers must not invent a
// substitute value; Batch 9 simply keeps submit unavailable.

import type { AnswerState, RendererSpec } from '@/src/features/session/renderers/types';

export function encodeSubmittedValue(spec: RendererSpec, state: AnswerState): string | null {
  // The surface's state must belong to the surface the registry resolved. A mismatch is a client
  // bug, not something to paper over with a coerced value.
  if (spec.kind !== state.kind) return null;

  if (spec.kind === 'choice' && state.kind === 'choice') {
    const { chosenIndex } = state;
    if (!Number.isInteger(chosenIndex)) return null;
    if (chosenIndex < 0 || chosenIndex >= spec.choices.length) return null;
    return spec.choices[chosenIndex];
  }

  if (spec.kind === 'free-entry' && state.kind === 'free-entry') {
    const trimmed = state.rawInput.trim();
    return trimmed.length === 0 ? null : trimmed;
  }

  if (spec.kind === 'count-selection' && state.kind === 'count-selection') {
    const { count } = state;
    if (!Number.isInteger(count) || count < 0) return null;
    return String(count);
  }

  return null;
}
