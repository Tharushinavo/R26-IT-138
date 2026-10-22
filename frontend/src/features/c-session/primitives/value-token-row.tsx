// The shared token-row primitive (Phase 10 Sub-Phase Sequence v1.1 §3.2): "ordered/reorderable
// integer tokens", bound to `list[int]`. Two modes, selected by the caller, never inferred here:
//   - `display-with-entry`: fixed, read-only tokens from the server's `shown_sequence`, followed by
//     `blanks` editable slots the child fills via `DigitKeypad`. Used by `ordered-value-sequence`'s
//     entry scene (NP-01/02/03).
//   - `reorder`: every token is the same draggable control, and the child's on-screen order IS the
//     value. Used by `ordered-value-sequence`'s arrangement scene (NP-04).
//
// Built only for what `ordered-value-sequence` needs. `partition-allocation` (10g/10h) reuses this
// component unmodified per the sequence doc; no partition-allocation-specific behaviour (bin
// labels, totals, etc.) lives here.
//
// Motor constancy: every token's size and spacing is TOKEN_TOUCH_TARGET_SIZE / TOKEN_SPACING
// (motor-constants.ts) -- module-level constants, never a function of how many tokens this row
// happens to render. `display-with-entry` renders the shown sequence and the entry slots as ONE
// row that wraps onto further lines, in that order, rather than scrolling horizontally: the entry
// slots always end up on screen because there is nowhere for the row to run off to, and they sit on
// whichever line has room after the shown values rather than always starting a fresh line of their
// own. `reorder` (NP-04) still scrolls horizontally -- its whole token count is draggable and can
// run longer than a row -- and never shrinks a token to fit more of them, mirroring section 5.1's
// line-archetype ruling and B's prompt-visual registry's own layout-bound doctrine.

import { useState } from 'react';
import { Pressable, ScrollView, StyleSheet, View } from 'react-native';
import { Gesture, GestureDetector } from 'react-native-gesture-handler';
import Animated, {
  runOnJS,
  useAnimatedStyle,
  useSharedValue,
  withTiming,
} from 'react-native-reanimated';

import { AppText } from '@/src/components/app-text';
import { DigitKeypad } from '@/src/features/c-session/primitives/digit-keypad';
import {
  ANIMATION_DURATION_MS,
  GESTURE_LONG_PRESS_MS,
  HIT_SLOP,
  TOKEN_SPACING,
  TOKEN_TOUCH_TARGET_SIZE,
  TOUCH_TARGET_MIN_SIZE,
} from '@/src/features/c-session/motor-constants';
import { colors, radius, typography } from '@/src/theme/tokens';

// TWO DIFFERENT TOKEN SIZES, SPLIT DELIBERATELY (2026-08-26). `display-with-entry`'s shown/entry
// tokens (NP-01..03, and `partition-allocation`'s reuse of this mode -- 10g) are pinned to
// TOUCH_TARGET_MIN_SIZE (48, SPEC section 10's own accessibility floor): the owner found
// `partition-allocation`'s C-EG-01 at difficulty 5 needed all 5 entry slots to fit one row on a
// typical phone width, and this is the smallest a touch-pressed token is allowed to shrink to.
// `reorder`'s draggable tokens (NP-04 only) stay at the ORIGINAL, larger TOKEN_TOUCH_TARGET_SIZE
// (56): the owner separately asked for NP-04's own cards to be "a bit bigger" once shown at 48px,
// and NP-04 typically renders only 3-4 tokens with comfortable room, unlike partition-allocation's
// worst case. These are genuinely different scenes with different fit constraints, not one style a
// single constant should serve -- forcing them to share a number is what caused this back-and-forth
// in the first place. `TOKEN_STRIDE` (driving the reorder-mode drag gesture's slot-movement math)
// is derived from `TOKEN_TOUCH_TARGET_SIZE` specifically, matching the size the DRAGGED token
// actually renders at -- an latent bug from this file's brief single-constant period, where
// `TOKEN_STRIDE` would have silently used the wrong token's size the moment the two sizes diverged.
const ENTRY_TOKEN_SIZE = TOUCH_TARGET_MIN_SIZE;
const REORDER_TOKEN_SIZE = TOKEN_TOUCH_TARGET_SIZE;

const TOKEN_STRIDE = REORDER_TOKEN_SIZE + TOKEN_SPACING;

type DisplayWithEntryProps = {
  mode: 'display-with-entry';
  shownSequence: readonly number[];
  blanks: number;
  disabled?: boolean;
  // One entry per blank slot: the integer the child has composed there, or `null` while empty.
  // The caller (the surface) owns this state; this component reports composition, it does not
  // decide submittability.
  entryValues: readonly (number | null)[];
  onChangeEntryValues: (next: readonly (number | null)[]) => void;
};

type ReorderProps = {
  mode: 'reorder';
  values: readonly number[];
  disabled?: boolean;
  onChangeOrder: (next: readonly number[]) => void;
};

export type ValueTokenRowProps = DisplayWithEntryProps | ReorderProps;

export function ValueTokenRow(props: ValueTokenRowProps) {
  if (props.mode === 'display-with-entry') return <DisplayWithEntryRow {...props} />;
  return <ReorderRow {...props} />;
}

// --- display-with-entry -----------------------------------------------------------------------

function DisplayWithEntryRow({
  blanks,
  disabled = false,
  entryValues,
  onChangeEntryValues,
  shownSequence,
}: DisplayWithEntryProps) {
  const [focusedSlot, setFocusedSlot] = useState(0);
  // Per-slot digit buffer, independent of the parsed integer the caller holds -- this is what
  // lets "12" render as "12" while it is being typed rather than re-deriving digits from a number
  // (which would silently eat a leading zero the child may still be about to correct).
  const [buffers, setBuffers] = useState<string[]>(() => Array.from({ length: blanks }, () => ''));

  const commit = (nextBuffers: string[]) => {
    setBuffers(nextBuffers);
    onChangeEntryValues(nextBuffers.map((buffer) => (buffer.length === 0 ? null : Number.parseInt(buffer, 10))));
  };

  const handleDigit = (digit: string) => {
    if (disabled) return;
    const next = [...buffers];
    next[focusedSlot] = (next[focusedSlot] ?? '') + digit;
    commit(next);
  };

  const handleDelete = () => {
    if (disabled) return;
    const next = [...buffers];
    next[focusedSlot] = (next[focusedSlot] ?? '').slice(0, -1);
    commit(next);
  };

  void entryValues; // Reported upward via onChangeEntryValues; the buffer, not this prop, drives display.

  return (
    <View>
      {/* One wrapping row, shown values followed by entry slots, in that order -- so the entry
          slots land right after the last shown value rather than always starting a fresh row of
          their own. At four tokens per line this is what puts the entry slots on the same row as
          however many shown values are left over, instead of stranding them below alone. */}
      <View style={styles.entryTokenRow}>
        {shownSequence.map((value, index) => (
          <View key={`shown-${index}`} style={[styles.token, styles.entryTokenSize]}>
            <AppText style={styles.tokenText}>{value}</AppText>
          </View>
        ))}
        {buffers.map((buffer, slotIndex) => (
          <Pressable
            accessibilityLabel={`entry slot ${slotIndex + 1}`}
            accessibilityRole="button"
            disabled={disabled}
            hitSlop={HIT_SLOP}
            key={`slot-${slotIndex}`}
            onPress={() => setFocusedSlot(slotIndex)}
            style={[
              styles.token,
              styles.entryTokenSize,
              styles.entrySlot,
              focusedSlot === slotIndex && styles.entrySlotFocused,
            ]}>
            <AppText style={styles.tokenText}>{buffer.length === 0 ? '' : buffer}</AppText>
          </Pressable>
        ))}
      </View>
      <View style={styles.keypadSpacer}>
        <DigitKeypad disabled={disabled} onDelete={handleDelete} onDigit={handleDigit} />
      </View>
    </View>
  );
}

// --- reorder -----------------------------------------------------------------------------------

function ReorderRow({ disabled = false, onChangeOrder, values }: ReorderProps) {
  return (
    <ScrollView contentContainerStyle={styles.row} horizontal showsHorizontalScrollIndicator={false}>
      {values.map((value, index) => (
        <DraggableToken
          disabled={disabled}
          index={index}
          key={`${index}-${value}`}
          onDrop={(fromIndex, toIndex) => {
            if (fromIndex === toIndex) return;
            const next = [...values];
            const [moved] = next.splice(fromIndex, 1);
            next.splice(toIndex, 0, moved);
            onChangeOrder(next);
          }}
          total={values.length}
          value={value}
        />
      ))}
    </ScrollView>
  );
}

type DraggableTokenProps = {
  value: number;
  index: number;
  total: number;
  disabled: boolean;
  onDrop: (fromIndex: number, toIndex: number) => void;
};

// One token, draggable via a long-press-then-pan gesture (GESTURE_LONG_PRESS_MS activation, per
// the sequence doc's ruling that the line/token archetypes use a discrete, deliberate gesture
// rather than an immediate drag that could be triggered by an accidental touch). Position resets
// to its slot on drop; the reported order comes from which slot the drop landed nearest, not from
// the token's own transient pixel position, so a partial or cancelled drag never desyncs the
// visual order from the value the surface will submit.
function DraggableToken({ disabled, index, onDrop, total, value }: DraggableTokenProps) {
  const translateX = useSharedValue(0);
  const isDragging = useSharedValue(false);

  const dropAt = (toIndexRaw: number) => {
    const toIndex = Math.max(0, Math.min(total - 1, toIndexRaw));
    onDrop(index, toIndex);
  };

  const pan = Gesture.Pan()
    .enabled(!disabled)
    .activateAfterLongPress(GESTURE_LONG_PRESS_MS)
    .onUpdate((event) => {
      translateX.value = event.translationX;
    })
    .onEnd((event) => {
      const slotsMoved = Math.round(event.translationX / TOKEN_STRIDE);
      translateX.value = withTiming(0, { duration: ANIMATION_DURATION_MS });
      isDragging.value = false;
      runOnJS(dropAt)(index + slotsMoved);
    })
    .onStart(() => {
      isDragging.value = true;
    });

  const animatedStyle = useAnimatedStyle(() => ({
    transform: [{ translateX: translateX.value }],
    zIndex: isDragging.value ? 1 : 0,
  }));

  return (
    <GestureDetector gesture={pan}>
      <Animated.View
        accessibilityLabel={`value ${value}, position ${index + 1} of ${total}`}
        accessibilityRole="adjustable"
        style={[styles.token, styles.reorderTokenSize, styles.reorderToken, animatedStyle]}>
        <AppText style={styles.tokenText}>{value}</AppText>
      </Animated.View>
    </GestureDetector>
  );
}

const styles = StyleSheet.create({
  entrySlot: {
    backgroundColor: colors.surface1,
    borderColor: colors.border,
    borderStyle: 'dashed',
  },
  entrySlotFocused: {
    borderColor: colors.primary,
    borderStyle: 'solid',
  },
  keypadSpacer: {
    marginTop: TOKEN_SPACING,
  },
  reorderToken: {
    backgroundColor: colors.primarySoft,
    borderColor: colors.primary,
  },
  // DisplayWithEntryRow's single row: shown tokens then entry slots, wrapping onto further lines
  // rather than scrolling. Named apart from `row` below (ReorderRow's ScrollView content style,
  // which must NOT wrap -- it is a single horizontally-scrolling line) so the two never collide.
  //
  // Gap halved from TOKEN_SPACING (2026-08-26 request, found by the owner testing
  // `partition-allocation`'s C-EG-01 at difficulty 5 -- 5 entry slots at the full gap wrapped to
  // 4+1 on a typical phone width). A SHARED style: this also governs NP-01..04's own entry slots
  // (10a), re-verified in the browser as part of this change per the owner's own explicit choice,
  // rather than forked into a second, archetype-scoped constant -- one primitive, one look, per
  // master work order §5A. Still a constant, never a function of token count or `difficulty_level`.
  entryTokenRow: {
    alignItems: 'center',
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: TOKEN_SPACING / 2,
    // Centers the row horizontally (2026-08-26 request, found by the owner testing C-SF-01: a
    // short row -- 2 entry slots, no shown values -- otherwise left-aligns against the card's own
    // edge rather than sitting under the centered prompt/payload token above it). A SHARED style:
    // this also governs NP-01..03's own entry rows (10a), re-verified in the browser as part of
    // this change.
    justifyContent: 'center',
    paddingVertical: TOKEN_SPACING,
  },
  row: {
    alignItems: 'center',
    flexDirection: 'row',
    gap: TOKEN_SPACING,
    paddingVertical: TOKEN_SPACING,
  },
  // Size-less base shape, shared by both modes. Size itself comes from `entryTokenSize` or
  // `reorderTokenSize` below -- see this file's header for why the two are deliberately different.
  token: {
    alignItems: 'center',
    borderRadius: radius.md,
    borderWidth: 2,
    justifyContent: 'center',
  },
  entryTokenSize: {
    height: ENTRY_TOKEN_SIZE,
    width: ENTRY_TOKEN_SIZE,
  },
  reorderTokenSize: {
    height: REORDER_TOKEN_SIZE,
    width: REORDER_TOKEN_SIZE,
  },
  tokenText: {
    fontFamily: typography.fonts.bold,
    fontSize: typography.fontSize.lg,
  },
});
