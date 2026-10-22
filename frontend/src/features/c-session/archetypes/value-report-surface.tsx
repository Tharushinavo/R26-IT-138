// The `value-report` archetype surface (10b). Renders `task.prompt_text` verbatim, the task's
// `prompt_payload` numbers as read-only tokens (every one of these eight templates' `prompt_text`
// points at a quantity -- "the amount shown", "the two numbers" -- that the text itself never
// states, and `interactive_assets` is `{}` for every real exemplar, so the tokens are the only
// place those numbers are visible at all), and a single `DigitKeypad`-backed answer field for the
// one `integer-field`-kind key `resolveValueReportSpec` finds in `valid_action_space`, plus one
// boolean toggle per extra declared key (in this batch's real data, `exchange_performed` for
// C-TC-04/C-JB-04, and nothing for the other six). `null` resolution renders `FailClosedFrame`,
// matching c-session-screen.tsx's own convention (support code = `task.request_id`). `onSubmit`
// receives the raw per-key values object -- `handleSubmit` (c-session-screen.tsx) already runs
// `encodeActionPayload` on it; this file does not duplicate that step and does not modify
// `handleSubmit`.
//
// Visual design is reused, not reinvented (10b work order, 5A): the screen chrome, question
// rendering and SUBMIT button shapes below are reproduced from `ordered-value-sequence-surface.tsx`'s
// own `styles`/`SubmitButton` (neither is exported from that file, so this file reproduces their
// exact shape rather than importing a private symbol) -- not a redesign. The boolean extra field
// uses the shared `BooleanToggle` (`primitives/boolean-toggle.tsx`, extracted 2026-08-26) rather
// than a third local reproduction -- see that file's own header for why its two-button shape
// replaced 10a's original single-switch one everywhere. The read-only payload tokens reuse
// `value-token-row.tsx`'s own `token`/`tokenText` style and `TOKEN_TOUCH_TARGET_SIZE`/
// `TOKEN_SPACING` constants (motor-constants.ts) rather than a new size -- `ValueTokenRow` itself
// is not reused directly because its only display mode (`display-with-entry`) always couples shown
// values to its OWN entry slots and keypad, which would duplicate this surface's separate answer
// field. No new geometry is introduced; only the token's read-only shape is reproduced.

import { useMemo, useState } from 'react';
import { Pressable, StyleSheet, View } from 'react-native';

import { AppText } from '@/src/components/app-text';
import type { ArchetypeSurfaceProps } from '@/src/features/c-session/archetype-surfaces';
import { resolveValueReportSpec } from '@/src/features/c-session/archetypes/value-report-logic';
import { FailClosedFrame } from '@/src/features/c-session/fail-closed-frame';
import { accentForGameFamily } from '@/src/features/c-session/game-family-accents';
import { HIT_SLOP, TOKEN_SPACING, TOKEN_TOUCH_TARGET_SIZE } from '@/src/features/c-session/motor-constants';
import { BooleanToggle } from '@/src/features/c-session/primitives/boolean-toggle';
import { DigitKeypad } from '@/src/features/c-session/primitives/digit-keypad';
import { TaskPromptCard } from '@/src/features/c-session/task-prompt-card';
import { colors, radius, spacing, typography } from '@/src/theme/tokens';
import { TASK_SURFACE_PADDING } from '@/src/features/c-session/task-layout';

// The payload tokens are a passive, read-only display -- not a touch target -- so sizing them apart
// from TOKEN_TOUCH_TARGET_SIZE does not reopen the motor-constancy question that constant exists to
// pin down (SPEC section 10 governs interactive geometry: touch targets, hit-slop, gesture
// thresholds; it says nothing about a label a child never presses). Both multipliers below are
// still derived from the shared constants (never a bare literal), per user-requested sizing
// (2026-08-26): the token 60% larger, the label 50% larger.
const PAYLOAD_TOKEN_SIZE = Math.round(TOKEN_TOUCH_TARGET_SIZE * 1.6);
const PAYLOAD_LABEL_FONT_SIZE = Math.round(typography.fontSize.sm * 1.5);
// A two-line-tall reserved height for every label, regardless of how many lines its own text
// actually wraps to ("Taken away" wraps to two lines in its narrow flex:1 column; "Start" and
// "Answer" do not) -- otherwise the shorter labels leave their token one line's height higher than
// the wrapped one, and the three boxes no longer sit level with each other (2026-08-26 finding).
// Bottom-aligned within that reserved height (`justifyContent: 'flex-end'` on the wrapper below) so
// a one-line label's text still sits immediately above its token, exactly where a two-line label's
// second line would.
const PAYLOAD_LABEL_LINE_HEIGHT = Math.round(typography.lineHeight.sm * 1.5);
const PAYLOAD_LABEL_BLOCK_HEIGHT = PAYLOAD_LABEL_LINE_HEIGHT * 2;

// The answer field's own label, alongside the payload labels, in the same row (2026-08-26 request:
// the answer belongs in the same row as the given numbers, in its own evenly-sized column, not set
// apart below them). Fixed across all eight templates -- what the child is filling in is always
// "the answer", regardless of which scoreKey (`submitted_remainder`, `submitted_sum`, ...) the wire
// names it, so this is an archetype-level constant, not a per-template label.
const ANSWER_LABEL = 'Answer';

// Shown in the answer token in place of an empty string while the child hasn't typed a digit yet
// (2026-08-26 request: a visual cue for which box is theirs to fill in, alongside the given values
// which are never blank). Cleared the moment the first digit is entered.
const ANSWER_PLACEHOLDER = '?';

export function ValueReportSurface({ onSubmit, task }: ArchetypeSurfaceProps) {
  const spec = useMemo(() => resolveValueReportSpec(task), [task]);

  if (spec === null) {
    return <FailClosedFrame onExit={() => {}} supportCode={task.request_id} />;
  }

  // The family's own accent (the same value the hub card and the task screen's ground already use
  // -- game-family-accents.ts is the one place this colour is written) is what "the accent of that
  // particular background" resolves to: whichever family the task belongs to, read from the wire,
  // never a colour chosen per archetype or per template.
  const accent = accentForGameFamily(task.game_family_id);

  return <ValueReportScene accent={accent} onSubmit={onSubmit} spec={spec} />;
}

type ValueReportSceneProps = {
  accent: string;
  spec: NonNullable<ReturnType<typeof resolveValueReportSpec>>;
  onSubmit: (payload: Record<string, unknown>) => void | Promise<void>;
};

function ValueReportScene({ accent, onSubmit, spec }: ValueReportSceneProps) {
  const [buffer, setBuffer] = useState('');
  const [extraValues, setExtraValues] = useState<Record<string, unknown>>({});

  const scoreValue = buffer.length === 0 ? null : Number.parseInt(buffer, 10);
  const canSubmit =
    scoreValue !== null &&
    spec.extraFields.every((field) => Object.prototype.hasOwnProperty.call(extraValues, field.key));

  const handleSubmitPress = () => {
    if (!canSubmit) return;
    void onSubmit({
      [spec.scoreKey]: scoreValue,
      ...extraValues,
    });
  };

  return (
    <View style={styles.container}>
      {/* Question and the values it reports on, in one card. The keypad, toggles and SUBMIT
          below are the answer surface and stay on the ground. */}
      <TaskPromptCard>
        <AppText style={styles.promptText} variant="title">
          {spec.promptText}
        </AppText>
        <View style={styles.payloadRow}>
        {spec.payloadValues.map((payloadValue, index) => (
          <View key={`${payloadValue.key}-${index}`} style={styles.payloadColumn}>
            <View style={styles.payloadLabelBlock}>
              <AppText style={[styles.payloadLabel, { color: accent }]}>{payloadValue.label}</AppText>
            </View>
            <View style={styles.payloadToken}>
              <AppText style={styles.payloadTokenText}>{payloadValue.value}</AppText>
            </View>
          </View>
        ))}
        <View style={styles.payloadColumn}>
          <View style={styles.payloadLabelBlock}>
            <AppText style={[styles.payloadLabel, { color: accent }]}>{ANSWER_LABEL}</AppText>
          </View>
          <View style={styles.payloadToken}>
            <AppText style={styles.payloadTokenText}>{buffer.length === 0 ? ANSWER_PLACEHOLDER : buffer}</AppText>
          </View>
          </View>
        </View>
      </TaskPromptCard>
      <View>
        <DigitKeypad
          onDelete={() => setBuffer((prev) => prev.slice(0, -1))}
          onDigit={(digit) => setBuffer((prev) => prev + digit)}
        />
      </View>
      {spec.extraFields.map((field) => (
        <BooleanToggle
          fieldKey={field.key}
          key={field.key}
          onChange={(value) => setExtraValues((prev) => ({ ...prev, [field.key]: value }))}
          value={extraValues[field.key]}
        />
      ))}
      <SubmitButton disabled={!canSubmit} onPress={handleSubmitPress} />
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
  // `flex: 1` so this fills the task screen's middle wrapper (c-session-screen.tsx's
  // `taskContentMiddle`) rather than sizing to its own content; `space-between` then pins the
  // question to the top of that space and SUBMIT to the bottom, matching
  // `ordered-value-sequence-surface.tsx`'s own container shape exactly.
  container: {
    flex: 1,
    gap: spacing.lg,
    justifyContent: 'space-between',
    padding: TASK_SURFACE_PADDING,
  },
  payloadColumn: {
    // `flex: 1` on every column -- given values AND the answer alike -- so the row divides itself
    // evenly across however many columns are present (2 given values + 1 answer for most of these
    // eight templates, 1 given value + 1 answer for C-SF-03), per the 2026-08-26 request that the
    // answer sit in the same row, in its own equally-sized share of the width.
    alignItems: 'center',
    flex: 1,
    gap: 4,
  },
  payloadLabel: {
    fontFamily: typography.fonts.bold,
    fontSize: PAYLOAD_LABEL_FONT_SIZE,
    lineHeight: PAYLOAD_LABEL_LINE_HEIGHT,
    textAlign: 'center',
  },
  payloadLabelBlock: {
    height: PAYLOAD_LABEL_BLOCK_HEIGHT,
    justifyContent: 'flex-end',
  },
  payloadRow: {
    alignItems: 'center',
    flexDirection: 'row',
    gap: TOKEN_SPACING * 2,
    justifyContent: 'center',
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
  // Half of typography.fontSize.title / lineHeight.title (40/46), per instruction -- same as 10a.
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
