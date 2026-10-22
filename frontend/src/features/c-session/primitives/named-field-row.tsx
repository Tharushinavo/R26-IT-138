// The labelled multi-field entry control (10f, `named-integer-fields`). One shared `DigitKeypad`
// retargeted to whichever field currently has focus -- the mechanism the master work order §5A
// names for this archetype: "One shared `DigitKeypad` instance, retargeted to whichever field
// currently has focus, exactly as `value-token-row`'s entry scene already retargets it per slot."
//
// WHY THIS IS A NEW PRIMITIVE RATHER THAN A MODE ON `value-token-row` (owner decision, 2026-08-26).
// The two look similar and share the focus/buffer mechanism, but they are different scenes:
// `value-token-row`'s entry slots are POSITIONAL blanks in an ordered sequence (10a's
// `ordered-value-sequence`), while these are NAMED fields whose label carries the whole meaning
// ("Tens", "Ones"). Extending `value-token-row` additively was declined for the same reason
// `unit-stepper.tsx`'s side effect on `line-traversal` (10d) got flagged: a later style change to a
// shared file would otherwise reach two shipped surfaces at once.
//
// SHAPE (2026-08-26 correction, found by the owner testing C-BT-01 in the browser): fields render
// beside the read-only payload token, in ONE row, at the SAME box size -- mirroring
// `value-report-surface.tsx`'s own layout, where the answer field sits in the given values' own row
// rather than in a visually separate block below. This module therefore exposes state and a single
// box renderer (`useNamedFieldEntry` / `NamedFieldBox`), not a self-contained row-plus-keypad
// component -- the surface composes the merged row itself, alongside its own payload tokens, and
// renders one `DigitKeypad` below the whole row.
//
// STATE IS KEYED BY FIELD KEY, NOT BY DISPLAY POSITION. `useNamedFieldEntry` holds a
// `Record<string, string>` buffer map rather than a positional array, so the surface is free to
// reorder `NamedFieldBox` elements for legibility (see that file's own place-value ordering) without
// the reorder ever touching which value lands under which submitted key.
//
// NO PRE-FILL, NO AUTO-COMPLETION (master work order §10f: "No auto-carry, no auto-borrow, no
// pre-fill"). Every buffer starts EMPTY and changes only in response to a keypad press on the
// focused field. Nothing here reads another field's value, and there is no arithmetic in this file
// beyond string-buffer manipulation and the integer parse that reports a buffer upward.
//
// Motor constancy (SPEC §10): `NamedFieldBox` is sized identically to `value-report-surface.tsx`'s
// own passive payload token (`TOKEN_TOUCH_TARGET_SIZE * 1.6`) -- a deliberate visual match, not a
// second independent size decision -- and every box is the same size regardless of field count or
// `difficulty_level`.

import { useState } from 'react';
import { Pressable, StyleSheet } from 'react-native';

import { AppText } from '@/src/components/app-text';
import { HIT_SLOP, TOKEN_TOUCH_TARGET_SIZE } from '@/src/features/c-session/motor-constants';
import { colors, radius, typography } from '@/src/theme/tokens';

export type NamedField = {
  key: string;
  label: string;
};

export type NamedFieldEntry = {
  /** One buffer per field key; empty string while that field has no digits yet. */
  buffers: Readonly<Record<string, string>>;
  focusedKey: string | null;
  setFocusedKey: (key: string) => void;
  handleDigit: (digit: string) => void;
  handleDelete: () => void;
  /** Parsed values, one per field key, `null` while that field's buffer is empty. Aligned to
   *  `fields` (the array `useNamedFieldEntry` was called with), same order, same length. */
  values: readonly (number | null)[];
};

/**
 * Owns focus + per-field digit buffers for a `NamedField[]`, keyed by field key so callers may
 * render the boxes in any order without disturbing which value belongs to which submitted key.
 */
export function useNamedFieldEntry(fields: readonly NamedField[]): NamedFieldEntry {
  const [focusedKey, setFocusedKey] = useState<string | null>(fields[0]?.key ?? null);
  const [buffers, setBuffers] = useState<Record<string, string>>(() => {
    const initial: Record<string, string> = {};
    for (const field of fields) initial[field.key] = '';
    return initial;
  });

  const handleDigit = (digit: string) => {
    if (focusedKey === null) return;
    setBuffers((prev) => ({ ...prev, [focusedKey]: (prev[focusedKey] ?? '') + digit }));
  };

  const handleDelete = () => {
    if (focusedKey === null) return;
    setBuffers((prev) => ({ ...prev, [focusedKey]: (prev[focusedKey] ?? '').slice(0, -1) }));
  };

  const values = fields.map((field) => {
    const buffer = buffers[field.key] ?? '';
    return buffer.length === 0 ? null : Number.parseInt(buffer, 10);
  });

  return { buffers, focusedKey, setFocusedKey, handleDigit, handleDelete, values };
}

// Matches `named-integer-fields-surface.tsx`'s own `PAYLOAD_TOKEN_SIZE` exactly
// (`TOKEN_TOUCH_TARGET_SIZE`, no multiplier) -- see that file's header for why: the widest real row
// (C-BT-02's Number + Hundreds + Tens + Ones, 4 columns) must fit on one line, and this is the
// largest fixed size that does so while staying at SPEC §10's 48px floor, which genuinely governs
// this box since it is a real touch target.
const FIELD_BOX_SIZE = TOKEN_TOUCH_TARGET_SIZE;

export type NamedFieldBoxProps = {
  field: NamedField;
  /** The current buffer text for this field, or `''` while empty. */
  value: string;
  focused: boolean;
  accent: string;
  disabled?: boolean;
  onPress: () => void;
};

/** One field's box + its label, styled to match a `value-report` payload token exactly, so the two
 *  sit level with each other in the same row. */
export function NamedFieldBox({ accent, disabled = false, field, focused, onPress, value }: NamedFieldBoxProps) {
  return (
    <Pressable
      accessibilityLabel={`${field.label} entry field`}
      accessibilityRole="button"
      accessibilityState={{ disabled, selected: focused }}
      disabled={disabled}
      hitSlop={HIT_SLOP}
      onPress={onPress}
      style={[
        styles.fieldBox,
        { borderColor: accent },
        focused ? styles.fieldBoxFocused : styles.fieldBoxUnfocused,
      ]}>
      <AppText style={styles.fieldValue}>{value}</AppText>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  fieldBox: {
    alignItems: 'center',
    backgroundColor: colors.surface1,
    borderRadius: radius.md,
    borderWidth: 2,
    height: FIELD_BOX_SIZE,
    justifyContent: 'center',
    width: FIELD_BOX_SIZE,
  },
  // Unfocused fields are dashed rather than solid so a child can tell at a glance which box is
  // currently receiving keypad input, while both states stay in the family's own accent colour
  // (2026-08-26 correction: the unfocused state was previously a neutral grey, which read as
  // disabled rather than simply "not focused yet").
  fieldBoxFocused: { borderStyle: 'solid' },
  fieldBoxUnfocused: { borderStyle: 'dashed' },
  fieldValue: {
    color: colors.textPrimary,
    fontFamily: typography.fonts.bold,
    fontSize: typography.fontSize.lg,
  },
});
