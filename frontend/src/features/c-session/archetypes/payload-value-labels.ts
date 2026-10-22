// Child-facing labels for a `prompt_payload` number, shared across archetypes (originally 10b
// correction, 2026-08-26; generalised for 10c since `line-traversal`'s `start`/`addend_a`/
// `addend_b` need the same treatment `value-report` already established).
//
// Several `prompt_text` strings across `value-report` and `line-traversal` name an operation
// ("Take away the amount shown", "Add the two numbers", "Start at the larger number and count on")
// without ever stating the numbers themselves, and `interactive_assets` is `{}` on every real
// exemplar for both -- so bare number tokens on screen give a child no way to tell which number is
// which, or in what order to use them ("is it 4-2 or 2-4?", found by hand-testing the running
// surface). This module supplies the missing disambiguation as a label per `prompt_payload` key,
// read alongside the number.
//
// A fixed lookup table over the real key vocabulary these archetypes' templates declare, keyed by
// `prompt_payload` key name -- not by template id or archetype, so a key reused across templates or
// archetypes (e.g. `addend_a`, shared by `value-report`'s C-JB-03 and `line-traversal`'s C-JB-02) is
// labelled identically with zero code change. A key not in the table (a future template's genuinely
// new key) falls back to a mechanical humanisation of the key itself (`removed_count` -> "Removed
// Count") rather than failing the whole task closed -- unlike `valid_action_space`, a
// `prompt_payload` key outside this table is a content gap, not a wire-shape violation the
// archetype cannot render at all.

const FRIENDLY_LABELS: Record<string, string> = {
  initial_count: 'Start',
  removed_count: 'Taken away',
  minuend: 'Start',
  subtrahend: 'Taken away',
  count_a: 'First group',
  count_b: 'Second group',
  addend_a: 'First number',
  addend_b: 'Second number',
  operand_a: 'First number',
  operand_b: 'Second number',
  multiplicand: 'First number',
  multiplier: 'Second number',
  dividend: 'Number',
  // `line-traversal` (10c, C-JB-02 only). `start` is already the larger of the two addends, per
  // the generator's own prompt_text ("Start at the larger number") -- this label states that
  // fact, it does not compute or re-derive it.
  start: 'Start',
  // `object-set-action` (10e, C-CC-02 only). `target_n` is the GIVEN size of the set the child must
  // build, not the answer -- see object-set-action-logic.ts's header for why it is safe to render
  // as a plain numeral, unlike option-select-logic.ts's quantity field on the numeral-options path.
  target_n: 'How many',
  // `named-integer-fields` (10f, C-BT-01..04). These are PAYLOAD keys -- the numbers the child
  // reads -- so the table applies to them as it always has. The ACTION keys of the same templates
  // (`tens`, `ones`, `post_tens`, ...) deliberately do NOT come through here: see
  // named-integer-fields-logic.ts's own `humanizeActionKey` and the header paragraph explaining why
  // an action-space key must never be routed through a client-side name table.
  target_number: 'Number',
  // "to start" rather than a bare "Tens"/"Ones": BT-03/04 show the BEFORE state while the child
  // enters the AFTER state, and two unqualified "Tens" labels on one screen would be ambiguous.
  pre_tens: 'Tens to start',
  pre_ones: 'Ones to start',
  // `partition-allocation` (10g, C-EG-01/C-SF-01). The bin-COUNT payload keys
  // (`number_of_groups`/`recipient_count`) are excluded from `payloadValues` entirely, consumed
  // structurally by partition-allocation-logic.ts -- see that file's header. `group_size` and
  // `total` are the only payload keys that ever reach this table for these two templates.
  group_size: 'Size of each group',
  total: 'Total',
};

function humanizeKey(key: string): string {
  return key
    .split('_')
    .filter((part) => part.length > 0)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ');
}

/**
 * The child-facing label for one `prompt_payload` key. Own-property lookup against the fixed
 * table: `key` originates on the wire, and a key named `constructor` or `toString` must not
 * resolve to an inherited `Object.prototype` member.
 */
export function labelForPayloadKey(key: string): string {
  if (Object.prototype.hasOwnProperty.call(FRIENDLY_LABELS, key)) {
    return FRIENDLY_LABELS[key]!;
  }
  return humanizeKey(key);
}
