// The `named-integer-fields` archetype surface (10f, C-BT-01..04). Renders `task.prompt_text`
// verbatim, the task's `prompt_payload` numbers as read-only labelled tokens (every one of these
// four templates' `prompt_text` points at a quantity it never states -- "Show THIS NUMBER using tens
// and ones", "Trade ten ones for one ten" against a starting state -- and `interactive_assets` is
// `{}` on all twenty exemplars, so the tokens are the only place those numbers are visible at all),
// and one entry box per `integer-field` key `resolveNamedIntegerFieldsSpec` finds in
// `valid_action_space`, one shared `DigitKeypad` below. `null` resolution renders
// `FailClosedFrame`, matching c-session-screen.tsx's own convention (support code =
// `task.request_id`). `onSubmit` receives the raw per-key values object -- `handleSubmit`
// (c-session-screen.tsx) already runs `encodeActionPayload` on it; this file does not duplicate that
// step and does not modify `handleSubmit`.
//
// TWO ROWS, SAME BOX STYLE. The GIVEN payload value(s) (`target_number`, or `pre_tens`/`pre_ones`)
// render alone in their own row directly under the prompt (tight `promptBlock` gap, halved from the
// container's own -- 2026-08-26 request); the entry fields render as their own row below that. Both
// rows share one box style (`payloadToken`/`payloadColumn`/`payloadLabel`, reproduced from
// `value-report-surface.tsx` exactly, not a redesign) so a given value and an entry field still read
// as the same kind of thing, without forcing every column onto one combined line -- an earlier
// single-row version (2026-08-26) put all of C-BT-02's four columns (Number + Hundreds + Tens +
// Ones) in one row, which the owner rejected as "not like that": splitting into two rows is what
// lets both rows share one comfortable box size without wrapping or squeezing.
//
// DISPLAY ORDER IS A COSMETIC REORDERING, NEVER A CHANGE TO WHAT IS SUBMITTED. `spec.fields` stays in
// the wire's own key order (named-integer-fields-logic.ts's own contract, unchanged); this file
// alone reorders the ON-SCREEN boxes by `PLACE_VALUE_RANK` so "Hundreds, Tens, Ones" reads
// left-to-right in descending place value (2026-08-26 correction: the wire's own alphabetical key
// order put "Ones" before "Tens", which reads backwards against the prompt text and against how a
// child is taught to write place value). `useNamedFieldEntry` keys its state by field KEY, not by
// display position, so this reordering can never misattribute a value to the wrong submitted key --
// see named-field-row.tsx's own header. A field name outside the known place-value vocabulary sorts
// to the end, stable, rather than crashing or silently misplacing itself -- this is a display-only
// convenience over a known, small, real vocabulary (hundreds/tens/ones and their pre_/post_
// variants), not a second labelling table: it never changes what text a field shows, only where it
// sits in the row.
//
// ONE SCENE, TWO AND THREE FIELDS ALIKE, WITH NO BRANCH BETWEEN THEM. C-BT-02 declares three action
// keys and the other three templates declare two; nothing in this file distinguishes those cases --
// `spec.fields` is mapped, not counted. There is no `game_task_template_id` read anywhere here, and
// no `C-BT-*` literal; `c-named-integer-fields-no-template-branch.test.ts` holds that line.
//
// NO AUTO-CARRY, NO AUTO-BORROW, NO PRE-FILL (master work order §10f row, verbatim). Fields start
// empty and are never seeded from `target_number` or `pre_tens`/`pre_ones`; no field's value is
// computed from another's; and SUBMIT is NOT gated on the fields decomposing `target_number` or
// correctly effecting the trade. `c-named-integer-fields-no-client-arithmetic.test.ts` holds that
// line.
//
// C-EG-02 (10g) RENDERS `ArrayGrid` IN PLACE OF THE GIVEN-VALUE ROW, WHEN `spec.grid !== null`.
// `spec.grid.rows`/`.cols` reach exactly one place in this file -- `ArrayGrid`'s own props -- and
// are never rendered as text: see named-integer-fields-logic.ts's own header for why printing either
// would leak 2 of the 3 answers (both are simultaneously GIVEN and declared `valid_action_space`
// keys here). `spec.direction` is likewise carried through resolution but rendered NOWHERE in this
// file and branched on NOWHERE -- 10a's own standing ruling for `C-NP-04.direction`, applied
// unchanged. `c-named-integer-fields-no-dimension-leak.test.ts` holds both lines.

import { useMemo } from 'react';
import { Pressable, StyleSheet, View } from 'react-native';

import { AppText } from '@/src/components/app-text';
import type { ArchetypeSurfaceProps } from '@/src/features/c-session/archetype-surfaces';
import { resolveNamedIntegerFieldsSpec } from '@/src/features/c-session/archetypes/named-integer-fields-logic';
import { FailClosedFrame } from '@/src/features/c-session/fail-closed-frame';
import { accentForGameFamily } from '@/src/features/c-session/game-family-accents';
import { TOKEN_SPACING, TOKEN_TOUCH_TARGET_SIZE, HIT_SLOP } from '@/src/features/c-session/motor-constants';
import { ArrayGrid } from '@/src/features/c-session/primitives/array-grid';
import { DigitKeypad } from '@/src/features/c-session/primitives/digit-keypad';
import {
  NamedFieldBox,
  useNamedFieldEntry,
  type NamedField,
} from '@/src/features/c-session/primitives/named-field-row';
import { taskPromptCardStyle } from '@/src/features/c-session/task-prompt-card';
import { colors, radius, spacing, typography } from '@/src/theme/tokens';
import { TASK_SURFACE_PADDING } from '@/src/features/c-session/task-layout';

// A SMALLER, FIXED SIZE THAN `value-report-surface.tsx`'s own payload token, DELIBERATELY (2026-08-26
// correction, found by the owner testing C-BT-02: the wider `* 1.6` size wraps a 4-column row --
// Number + Hundreds + Tens + Ones, this scene's own maximum -- onto two lines on a typical phone
// width, which the owner rejected: "they all should be at the same level"). `TOKEN_TOUCH_TARGET_SIZE`
// itself, with NO multiplier, is what fits all four columns on one row while staying at or above
// SPEC §10's 48px floor -- and because the field boxes ARE real touch targets (unlike
// `value-report`'s read-only tokens), that floor genuinely governs here, so this could not have
// shrunk further than this constant regardless. A single fixed constant, never a function of field
// count or `difficulty_level`: C-BT-01/03/04's 3-column row (Number + 2 fields) uses the exact same
// size as C-BT-02's 4-column row, so motor constancy holds across every template and level alike --
// only the WIDTH OF THE ROW increases with column count, never the size of any one target.
// `named-field-row.tsx`'s own `FIELD_BOX_SIZE` matches this value exactly (see that file's header)
// so payload tokens and entry fields still sit level, at one shared size, in one row.
const PAYLOAD_TOKEN_SIZE = TOKEN_TOUCH_TARGET_SIZE;
const PAYLOAD_LABEL_FONT_SIZE = Math.round(typography.fontSize.sm * 1.5);
const PAYLOAD_LABEL_LINE_HEIGHT = Math.round(typography.lineHeight.sm * 1.5);
const PAYLOAD_LABEL_BLOCK_HEIGHT = PAYLOAD_LABEL_LINE_HEIGHT * 2;

// See the header's "DISPLAY ORDER IS A COSMETIC REORDERING" paragraph. A field key outside this
// table (a future template's genuinely new key) sorts to the end, stable -- never a crash, never a
// misattributed value, since sorting never touches `field.key` itself.
const PLACE_VALUE_RANK: Record<string, number> = {
  hundreds: 0,
  tens: 1,
  ones: 2,
  pre_hundreds: 0,
  pre_tens: 1,
  pre_ones: 2,
  post_hundreds: 0,
  post_tens: 1,
  post_ones: 2,
};

// Generic over anything keyed like a field or a payload value (2026-08-26 extension: the GIVEN
// row -- `pre_tens`/`pre_ones` -- needed the identical reordering once the owner pointed out its
// wire-alphabetical order ("Ones to start" before "Tens to start") no longer lined up, column for
// column, with the entry row beneath it once THAT row got reordered. One rank table, applied to
// both rows, is what keeps a place-value column (e.g. "Tens") stacked directly under its own given
// value rather than under an unrelated one.
function displayOrder<T extends { key: string }>(items: readonly T[]): readonly T[] {
  return [...items].sort((a, b) => {
    const rankA = PLACE_VALUE_RANK[a.key] ?? Number.MAX_SAFE_INTEGER;
    const rankB = PLACE_VALUE_RANK[b.key] ?? Number.MAX_SAFE_INTEGER;
    return rankA - rankB;
  });
}

export function NamedIntegerFieldsSurface({ onSubmit, task }: ArchetypeSurfaceProps) {
  const spec = useMemo(() => resolveNamedIntegerFieldsSpec(task), [task]);

  if (spec === null) {
    return <FailClosedFrame onExit={() => {}} supportCode={task.request_id} />;
  }

  // The family's own accent, read from the wire -- never a colour chosen per archetype or per
  // template. game-family-accents.ts is the one place this colour is written.
  const accent = accentForGameFamily(task.game_family_id);

  return <NamedIntegerFieldsScene accent={accent} onSubmit={onSubmit} spec={spec} />;
}

type NamedIntegerFieldsSceneProps = {
  accent: string;
  spec: NonNullable<ReturnType<typeof resolveNamedIntegerFieldsSpec>>;
  onSubmit: (payload: Record<string, unknown>) => void | Promise<void>;
};

function NamedIntegerFieldsScene({ accent, onSubmit, spec }: NamedIntegerFieldsSceneProps) {
  const orderedFields = useMemo(() => displayOrder(spec.fields), [spec.fields]);
  const orderedPayloadValues = useMemo(() => displayOrder(spec.payloadValues), [spec.payloadValues]);
  const entry = useNamedFieldEntry(spec.fields);

  // Not a correctness condition -- see the header. `encodeActionPayload` requires a value for every
  // declared key, so a partially-filled submission could not be encoded at all.
  const canSubmit = entry.values.every((value) => value !== null);

  const handleSubmitPress = () => {
    if (!canSubmit) return;
    const payload: Record<string, unknown> = {};
    spec.fields.forEach((field, fieldIndex) => {
      payload[field.key] = entry.values[fieldIndex];
    });
    void onSubmit(payload);
  };

  return (
    <View style={styles.container}>
      <View style={styles.promptAndFieldsGroup}>
        <View style={styles.promptBlock}>
          <AppText style={styles.promptText} variant="title">
            {spec.promptText}
          </AppText>
          {spec.grid !== null ? (
            // C-EG-02 only. `spec.grid.rows`/`.cols` reach exactly this one place -- ArrayGrid's own
            // props -- and are never rendered as text anywhere in this file; see the header's
            // "C-EG-02 IS SUPPORTED HERE" paragraph and c-named-integer-fields-no-dimension-leak.test.ts.
            <View style={styles.gridWrapper}>
              <ArrayGrid accent={accent} cols={spec.grid.cols} rows={spec.grid.rows} />
            </View>
          ) : null}
        </View>
        {spec.grid !== null ? (
          <EquationFieldsRow accent={accent} entry={entry} fields={spec.fields} />
        ) : (
          /* ONE ROW, given values and entry boxes together (owner instruction, 2026-10-10).
             
             These were two stacked rows -- the given number in `promptBlock`, the entry boxes in a
             sibling `fieldsRow` -- so "Number 7" sat on its own line above "Tens | Ones". A
             decomposition reads as one statement, and splitting it across two lines made the given
             number look like part of the question text rather than one of the quantities.
             
             EVERY LABEL IS NOW BELOW ITS BOX, including the given value's, which previously sat
             ABOVE it. That is not cosmetic: with the two kinds of column side by side, mixed label
             placement would put the boxes at different heights within the row (one column being
             label-then-box, the other box-then-label), so the numbers would not line up. Uniform
             placement is what makes a single row legible, and it follows the 2026-08-26 request
             that moved the entry labels below in the first place. */
          <View style={styles.valuesRow}>
            {orderedPayloadValues.map((payloadValue, index) => (
              <View key={`${payloadValue.key}-${index}`} style={styles.payloadColumn}>
                <View style={styles.payloadToken}>
                  <AppText style={styles.payloadTokenText}>{payloadValue.value}</AppText>
                </View>
                <View style={styles.payloadLabelBlockBelow}>
                  <AppText style={[styles.payloadLabel, { color: accent }]}>{payloadValue.label}</AppText>
                </View>
              </View>
            ))}
            {orderedFields.map((field) => (
              <View key={field.key} style={styles.payloadColumn}>
                <NamedFieldBox
                  accent={accent}
                  field={field}
                  focused={entry.focusedKey === field.key}
                  onPress={() => entry.setFocusedKey(field.key)}
                  value={entry.buffers[field.key] ?? ''}
                />
                <View style={styles.payloadLabelBlockBelow}>
                  <AppText style={[styles.payloadLabel, { color: accent }]}>{field.label}</AppText>
                </View>
              </View>
            ))}
          </View>
        )}
      </View>
      <View style={styles.keypadWrapper}>
        <DigitKeypad onDelete={entry.handleDelete} onDigit={entry.handleDigit} />
      </View>
      <SubmitButton disabled={!canSubmit} onPress={handleSubmitPress} />
    </View>
  );
}

// A DISPLAY-ONLY override, scoped to this one component, for this one key -- the resolver's own
// `spec.fields` label for `submitted_product` stays "Submitted Product" (humanizeActionKey's
// mechanical output, unchanged, still what every other consumer of `spec.fields` sees); this row
// alone shows the shorter "Product" so the equation reads "Cols x Rows = Product" without the long
// label forcing this row to wrap (2026-08-26 request, found by the owner testing C-EG-02: the
// unabbreviated label was wide enough to push a 3rd column onto its own line). A narrow, named
// exception over a single real key, the same shape as `displayOrder`'s own PLACE_VALUE_RANK
// override above -- cosmetic only, never touching what is submitted or what `spec.fields` itself
// reports.
const EQUATION_FIELD_LABEL_OVERRIDE: Record<string, string> = {
  submitted_product: 'Product',
};

type EquationFieldsRowProps = {
  accent: string;
  fields: readonly NamedField[];
  entry: ReturnType<typeof useNamedFieldEntry>;
};

// C-EG-02's own field layout: "Cols x Rows = Product", one row, three same-size boxes, never
// wrapping -- see the header's own "C-EG-02 IS SUPPORTED HERE" paragraph for why this scene renders
// differently from the generic wrapped `fieldsRow` every other named-integer-fields template uses.
function EquationFieldsRow({ accent, entry, fields }: EquationFieldsRowProps) {
  const colsField = fields.find((field) => field.key === 'cols');
  const rowsField = fields.find((field) => field.key === 'rows');
  const productField = fields.find((field) => field.key === 'submitted_product');

  // Every real C-EG-02 exemplar declares exactly these three keys (see
  // c-named-integer-fields-eg02-fails-closed.test.ts); a task that reaches this branch
  // (`spec.grid !== null`) but is missing one is a corrupted shape this component cannot render --
  // fail closed rather than guess at a partial equation.
  if (colsField === undefined || rowsField === undefined || productField === undefined) {
    return null;
  }

  const renderBox = (field: NamedField, labelOverride?: string) => (
    <View style={styles.equationColumn}>
      <NamedFieldBox
        accent={accent}
        field={field}
        focused={entry.focusedKey === field.key}
        onPress={() => entry.setFocusedKey(field.key)}
        value={entry.buffers[field.key] ?? ''}
      />
      <View style={styles.payloadLabelBlockBelow}>
        <AppText style={[styles.payloadLabel, { color: accent }]}>{labelOverride ?? field.label}</AppText>
      </View>
    </View>
  );

  return (
    <View style={styles.equationRow}>
      {renderBox(colsField)}
      <AppText style={[styles.equationOperator, { color: accent }]}>x</AppText>
      {renderBox(rowsField)}
      <AppText style={[styles.equationOperator, { color: accent }]}>=</AppText>
      {renderBox(productField, EQUATION_FIELD_LABEL_OVERRIDE.submitted_product)}
    </View>
  );
}

function SubmitButton({ disabled, onPress }: { disabled: boolean; onPress: () => void }) {
  return (
    <Pressable
      accessibilityRole="button"
      accessibilityState={{ disabled }}
      disabled={disabled}
      hitSlop={HIT_SLOP}
      onPress={onPress}
      style={({ pressed }) => [
        styles.submitButton,
        disabled && styles.submitButtonDisabled,
        pressed && !disabled && styles.pressed,
      ]}>
      <AppText style={styles.submitButtonText}>SUBMIT</AppText>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    gap: spacing.lg,
    justifyContent: 'space-between',
    padding: TASK_SURFACE_PADDING,
  },
  // Same row shape as `payloadRow` below -- kept as its own name only so this file's JSX reads
  // clearly ("the fields row"), not because the styling itself differs.
  // Holds the given values AND the entry boxes, in that order, on one line -- see the note at its
  // JSX. `flexWrap` is kept: a task with enough quantities to exceed the card's width must wrap
  // rather than overflow, and `rowGap` keeps those wrapped lines from touching.
  valuesRow: {
    alignItems: 'center',
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: TOKEN_SPACING,
    justifyContent: 'center',
    rowGap: TOKEN_SPACING * 1.5,
  },
  // C-EG-02 only. Deliberately NOT `flexWrap: 'wrap'`: three same-size boxes plus two operator
  // glyphs comfortably fit one line once `EQUATION_FIELD_LABEL_OVERRIDE` shortens the widest label
  // ("Submitted Product" -> "Product") -- the wrap this row would otherwise need was the actual bug
  // the owner flagged, not a case §5.1's "wrap rather than compress" doctrine should cover.
  equationRow: {
    alignItems: 'center',
    flexDirection: 'row',
    gap: TOKEN_SPACING / 2,
    justifyContent: 'center',
  },
  // No `minWidth` (unlike `payloadColumn`): all three boxes are the same fixed size regardless
  // (NamedFieldBox's own FIELD_BOX_SIZE), so nothing here needs to resist shrinking.
  equationColumn: {
    alignItems: 'center',
    gap: 4,
  },
  equationOperator: {
    fontFamily: typography.fonts.bold,
    fontSize: typography.fontSize.lg,
  },
  // Groups the prompt block and the fields row at half the container's own gap (2026-08-26
  // request), so the fields sit close under the given number rather than at the container's normal
  // spacing (which still separates this whole group from the keypad and SUBMIT below it).
  // THE QUESTION CARD (owner instruction, 2026-09-28). It was `promptBlock` below, which holds the
  // question and the given number but NOT the entry boxes -- so "Tens" and "Ones" sat outside the
  // card, visually separated from the number they decompose. This group is the right boundary: it
  // already contains both, and the child reads the whole thing as one question.
  promptAndFieldsGroup: {
    ...taskPromptCardStyle,
    gap: spacing.lg / 2,
  },
  // Pulls the keypad up to half the container's own gap below the fields row (2026-08-26 request) --
  // `marginTop` set to the negative of the difference (container gap minus the wanted half-gap),
  // rather than moving the gap declaration itself, so the gap between the keypad and SUBMIT below it
  // (also `container`'s own spacing) is untouched.
  keypadWrapper: {
    marginTop: -(spacing.lg / 2),
  },
  // Deliberately NOT `flex: 1` (2026-08-26 correction, found by the owner testing C-BT-02: with
  // `flex: 1` inside a `flexWrap: 'wrap'` row, RN Web's flex-shrink default lets every column
  // compress to fit ONE line rather than actually wrapping -- the same pitfall object-pool.tsx's own
  // header already documents for a ScrollView. `minWidth` pinned to the box's own size is what makes
  // a column refuse to shrink below its content, so a 4-column row (Number + Hundreds + Tens + Ones,
  // C-BT-02's own shape) genuinely wraps onto a second line instead of squeezing every label into
  // illegibility. The box size itself -- and therefore every column's `minWidth` -- stays IDENTICAL
  // regardless of field count or `difficulty_level`, so this is a wrap, never a per-level resize.
  payloadColumn: {
    alignItems: 'center',
    gap: 4,
    minWidth: PAYLOAD_TOKEN_SIZE,
  },
  payloadLabel: {
    fontFamily: typography.fonts.bold,
    fontSize: PAYLOAD_LABEL_FONT_SIZE,
    lineHeight: PAYLOAD_LABEL_LINE_HEIGHT,
    textAlign: 'center',
  },
  // Label placement for EVERY column in the values row, given values and entry boxes alike: BELOW
  // its box (2026-08-26 request, extended to the given values on 2026-10-10 when the two rows were
  // merged into one -- see the note at the JSX). `flex-start` keeps a wrapped two-line label
  // starting immediately under the box instead of floating away from it, and the fixed
  // `PAYLOAD_LABEL_BLOCK_HEIGHT` is what keeps every box in the row at the same height whether its
  // label wraps or not.
  //
  // There was a second, mirrored `payloadLabelBlock` here that put the given value's label ABOVE
  // its box. It went when the rows merged: mixed placement within one row would sit the boxes at
  // different heights, which is exactly what a decomposition must not do.
  payloadLabelBlockBelow: {
    height: PAYLOAD_LABEL_BLOCK_HEIGHT,
    justifyContent: 'flex-start',
  },
  // C-EG-02 only: centers ArrayGrid in place of the (otherwise-empty) payload-token row.
  gridWrapper: {
    alignItems: 'center',
  },
  // Groups the prompt and the GIVEN value(s) alone, at half the container's own gap (2026-08-26
  // request), separate from the entry-fields row below -- see the header's "TWO ROWS" note.
  // Plain again: the card moved out to `promptAndFieldsGroup` so the entry boxes are inside it.
  promptBlock: {
    gap: spacing.lg / 2,
  },
  payloadToken: {
    alignItems: 'center',
    backgroundColor: colors.surface1,
    borderColor: colors.border,
    borderRadius: radius.md,
    borderWidth: 2,
    height: PAYLOAD_TOKEN_SIZE,
    justifyContent: 'center',
    width: PAYLOAD_TOKEN_SIZE,
  },
  payloadTokenText: {
    fontFamily: typography.fonts.bold,
    fontSize: typography.fontSize.lg,
  },
  pressed: { opacity: 0.72 },
  promptText: { color: colors.textPrimary, fontSize: 20, lineHeight: 23 },
  submitButton: {
    alignItems: 'center',
    backgroundColor: colors.primary,
    borderRadius: radius.md,
    justifyContent: 'center',
    minHeight: 56,
    paddingHorizontal: spacing.lg,
  },
  submitButtonDisabled: { opacity: 0.5 },
  submitButtonText: {
    color: colors.surface1,
    fontFamily: typography.fonts.bold,
    fontSize: typography.fontSize.lg,
  },
});
