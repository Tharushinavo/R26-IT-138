// The renderer registry: the single client-side owner of the `response_format` → answer-surface
// mapping. `runtime-validation.ts` deliberately accepts any non-empty `response_format` string
// (see its comment above `isOpportunityPresentationFields`) precisely so that this table is the
// only list of known formats in the client; a second list there would be a second thing to drift.
//
// The table below is verified against the backend item generator. Choice formats relay whichever
// strings the server presented — the relation symbols, the conservation words, the numeric
// distractors are all catalogue content and are never restated here.
//
// | response_format            | choices | kind            | submitted_value            |
// | -------------------------- | ------- | --------------- | -------------------------- |
// | single_integer             |    4    | choice          | chosen string verbatim     |
// | single_integer_or_choice   |    4    | choice          | chosen string verbatim     |
// | single_choice_or_integer   |    4    | choice          | chosen string verbatim     |
// | single_choice              |    4    | choice          | chosen string verbatim     |
// | ordered_list               |    4    | choice          | chosen string verbatim     |
// | relation_choice            |    3    | choice          | chosen string verbatim     |
// | binary_or_choice           |    2    | choice          | chosen string verbatim     |
// | expanded_form              |    0    | free-entry      | trimmed raw input          |
// | interactive_set_selection  |    0    | count-selection | String(count)              |
//
// `ordered_list` is a plain choice format: the server has already comma-joined each candidate
// ordering into one presented_choices entry (e.g. "12,45,300"). The client picks one of those
// whole strings. It does not assemble an ordering out of parts — answer construction is not the
// client's job.

import type { RendererKind, RendererSpec } from '@/src/features/session/renderers/types';

type FormatEntry = { kind: RendererKind; expectedChoiceCount: number };

const FORMAT_TABLE: Record<string, FormatEntry> = {
  single_integer: { kind: 'choice', expectedChoiceCount: 4 },
  single_integer_or_choice: { kind: 'choice', expectedChoiceCount: 4 },
  single_choice_or_integer: { kind: 'choice', expectedChoiceCount: 4 },
  single_choice: { kind: 'choice', expectedChoiceCount: 4 },
  ordered_list: { kind: 'choice', expectedChoiceCount: 4 },
  relation_choice: { kind: 'choice', expectedChoiceCount: 3 },
  binary_or_choice: { kind: 'choice', expectedChoiceCount: 2 },
  expanded_form: { kind: 'free-entry', expectedChoiceCount: 0 },
  interactive_set_selection: { kind: 'count-selection', expectedChoiceCount: 0 },
};

/**
 * Resolve the answer surface for one opportunity, or `null` if the presentation is structurally
 * inconsistent with the format it claims.
 *
 * Returns `null` in exactly three cases, all of them server/client drift:
 *   1. `responseFormat` is not one of the nine known formats;
 *   2. a choice format arrived with the wrong number of presented choices;
 *   3. a non-choice format (expanded_form, interactive_set_selection) arrived with choices.
 *
 * There is no fallback surface. In particular a failed resolve never degrades to a free-text box:
 * a text field shown against, say, `relation_choice` would let a child type something the item
 * cannot accept and then be marked wrong for it — exactly the failure the authority boundary
 * exists to prevent. Batch 9 renders `null` as a neutral error screen with a support code and one
 * way home.
 *
 * `presentedChoices` is passed through in the server's order. It is not sorted, deduped or
 * relabelled here; the server's ordering is the ordering the child sees.
 */
export function resolveRenderer(
  responseFormat: string,
  presentedChoices: readonly string[],
): RendererSpec | null {
  // hasOwnProperty, never bare `FORMAT_TABLE[responseFormat]`: a drifted or hostile format string
  // like "constructor", "toString" or "__proto__" resolves to an inherited Object.prototype
  // member under bare access and would hand back a bogus spec.
  if (!Object.prototype.hasOwnProperty.call(FORMAT_TABLE, responseFormat)) return null;
  const entry = FORMAT_TABLE[responseFormat];

  if (entry.kind === 'choice') {
    if (presentedChoices.length !== entry.expectedChoiceCount) return null;
    return {
      kind: 'choice',
      responseFormat,
      expectedChoiceCount: entry.expectedChoiceCount,
      choices: presentedChoices,
    };
  }

  if (presentedChoices.length !== 0) return null;
  return { kind: entry.kind, responseFormat, expectedChoiceCount: 0 };
}
