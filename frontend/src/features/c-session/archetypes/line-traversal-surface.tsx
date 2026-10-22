// The `line-traversal` archetype surface (10c, C-JB-02 only). Renders `task.prompt_text` verbatim,
// the task's other `prompt_payload` numbers as read-only labelled tokens (the same disambiguation
// `value-report-surface.tsx` established -- a bare number gives a child no way to tell which is
// which), and a `UnitStepper` the child steps forward/back to make each unit jump from `start`,
// with the resulting `JumpAccumulator` record of jumps made. `null` resolution renders
// `FailClosedFrame`, matching `c-session-screen.tsx`'s own convention (support code =
// `task.request_id`). `onSubmit` receives the raw per-key values object -- `handleSubmit`
// (c-session-screen.tsx) already runs `encodeActionPayload` on it; this file does not duplicate
// that step and does not modify `handleSubmit`.
//
// THERE IS NO SEPARATE "type where you landed" FIELD (2026-08-26 correction to this file's first
// draft, found by the user looking at the running surface). The marker on `UnitStepper`'s own line
// already shows the landed position -- circled, at the current tick -- so a second field asking the
// child to re-type a number already on screen was pure redundancy, not a second thing being
// assessed. `final_position` is derived as `spec.startValue + jumps.length` and submitted alongside
// `jumps` when SUBMIT is pressed. This is NOT the client computing an answer it shouldn't: it is
// packaging what the child's own actions already produced and made visible (the marker's own
// position uses the identical `originValue + forwardSteps` arithmetic inside `UnitStepper`) --
// unlike the forbidden `addend_a + addend_b`, `startValue` and `jumps.length` are never the
// answer itself, only a readout of where the child's own jumps landed. SUBMIT is gated on having
// made at least one jump, since with zero jumps there is nothing to submit that reflects any
// action the child took.
//
// Visual design is reused, not reinvented (master work order §5A): the screen chrome, question
// rendering, `SubmitButton` and the payload-token shapes below are reproduced from
// `value-report-surface.tsx`'s own `styles`/`SubmitButton`/token pattern (neither is exported from
// that file, so this file reproduces their shape rather than importing a private symbol) -- not a
// redesign. The payload tokens here use the PLAIN `TOKEN_TOUCH_TARGET_SIZE`/`TOKEN_SPACING`
// (motor-constants.ts), not `value-report-surface.tsx`'s own 1.6x/1.5x enlargement -- that
// enlargement was a direct, specific user request scoped to that one screen, not a standing design
// rule this file should assume carries over. `UnitStepper` and `JumpAccumulator` are the two new
// primitives this sub-phase introduces (master work order §5A: "the new primitive is the only new
// visual surface any sub-phase should introduce").
//
// Client-side authority boundary: this file never counts, sums, or validates the jumps the child
// makes against a target, and never derives anything from `addend_a + addend_b` -- see
// `line-traversal-logic.ts`'s header for why (the client relaying rather than judging is what keeps
// it from doing part of the server's own evaluation).

import { useMemo, useState } from 'react';
import { Pressable, StyleSheet, View } from 'react-native';

import { AppText } from '@/src/components/app-text';
import type { ArchetypeSurfaceProps } from '@/src/features/c-session/archetype-surfaces';
import { resolveLineTraversalSpec } from '@/src/features/c-session/archetypes/line-traversal-logic';
import { FailClosedFrame } from '@/src/features/c-session/fail-closed-frame';
import { accentForGameFamily } from '@/src/features/c-session/game-family-accents';
import { HIT_SLOP, TOKEN_SPACING, TOKEN_TOUCH_TARGET_SIZE } from '@/src/features/c-session/motor-constants';
import { JumpAccumulator } from '@/src/features/c-session/primitives/jump-accumulator';
import { UnitStepper } from '@/src/features/c-session/primitives/unit-stepper';
import { TaskPromptCard } from '@/src/features/c-session/task-prompt-card';
import { colors, radius, spacing, typography } from '@/src/theme/tokens';
import { TASK_SURFACE_PADDING } from '@/src/features/c-session/task-layout';

// Two-line-tall, bottom-aligned label block, same mechanism `value-report-surface.tsx` uses so a
// label that happens to wrap does not sit its token lower than a one-line label's token.
const PAYLOAD_LABEL_LINE_HEIGHT = Math.round(typography.lineHeight.sm);
const PAYLOAD_LABEL_BLOCK_HEIGHT = PAYLOAD_LABEL_LINE_HEIGHT * 2;

export function LineTraversalSurface({ onSubmit, task }: ArchetypeSurfaceProps) {
  const spec = useMemo(() => resolveLineTraversalSpec(task), [task]);

  if (spec === null) {
    return <FailClosedFrame onExit={() => {}} supportCode={task.request_id} />;
  }

  const accent = accentForGameFamily(task.game_family_id);

  return <LineTraversalScene accent={accent} onSubmit={onSubmit} spec={spec} />;
}

type LineTraversalSceneProps = {
  accent: string;
  spec: NonNullable<ReturnType<typeof resolveLineTraversalSpec>>;
  onSubmit: (payload: Record<string, unknown>) => void | Promise<void>;
};

function LineTraversalScene({ accent, onSubmit, spec }: LineTraversalSceneProps) {
  const [jumps, setJumps] = useState<readonly number[]>([]);

  const canSubmit = jumps.length > 0;

  const handleSubmitPress = () => {
    if (!canSubmit) return;
    void onSubmit({
      [spec.positionKey]: spec.startValue + jumps.length,
      [spec.jumpsKey]: jumps,
    });
  };

  return (
    <View style={styles.container}>
      {/* Question and items in one card; the controls below stay on the ground. */}
      <TaskPromptCard>
        <AppText style={styles.promptText} variant="title">
          {spec.promptText}
        </AppText>
        {spec.payloadValues.length > 0 && (
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
          </View>
        )}
      </TaskPromptCard>

      <UnitStepper
        forwardSteps={jumps.length}
        onStepBack={() => setJumps((prev) => prev.slice(0, -1))}
        onStepForward={() => setJumps((prev) => [...prev, 1])}
        originValue={spec.startValue}
      />

      <JumpAccumulator jumps={jumps} />

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
  container: {
    flex: 1,
    gap: spacing.lg,
    justifyContent: 'space-between',
    padding: TASK_SURFACE_PADDING,
  },
  payloadColumn: {
    alignItems: 'center',
    flex: 1,
    gap: 4,
  },
  payloadLabel: {
    fontFamily: typography.fonts.bold,
    fontSize: typography.fontSize.sm,
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
    height: TOKEN_TOUCH_TARGET_SIZE,
    justifyContent: 'center',
    width: TOKEN_TOUCH_TARGET_SIZE,
  },
  payloadTokenText: {
    fontFamily: typography.fonts.bold,
    fontSize: typography.fontSize.lg,
  },
  pressed: { opacity: 0.72 },
  // Half of typography.fontSize.title / lineHeight.title (40/46), per instruction -- same as
  // every other archetype surface.
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
