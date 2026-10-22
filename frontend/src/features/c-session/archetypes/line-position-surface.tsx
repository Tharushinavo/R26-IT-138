// The `line-position` archetype surface (10d, C-MCL-04 only). Renders `task.prompt_text` verbatim,
// any other `prompt_payload` numbers as read-only labelled tokens (empty on every real exemplar
// today, but the treatment mirrors `line-traversal-surface.tsx`'s own for the same reason), and a
// `UnitStepper` spanning the task's own `interval_max` range with a flag marking `target_position`.
// `null` resolution renders `FailClosedFrame`, matching every other archetype surface's own
// convention (support code = `task.request_id`). `onSubmit` receives the raw per-key values object
// -- `handleSubmit` (c-session-screen.tsx) already runs `encodeActionPayload` on it; this file does
// not duplicate that step and does not modify `handleSubmit`.
//
// COARSE + FINE STEPPING, NOT UNIT-ONLY (10d work order §2.2, owner decision this session). Unlike
// `line-traversal-surface.tsx`, this surface passes `unit-stepper.tsx`'s new `coarseStep` prop
// (`LINE_POSITION_COARSE_STEP`, fixed at 10 -- see `line-position-logic.ts`'s header for the full
// interaction-cost reasoning and measured tap counts). The line's own extent
// (`maxForwardSteps={spec.intervalMax}`) is legitimately derived from the payload here, unlike
// `line-traversal`'s corruption-only bound -- `interval_max` is the task's own stated range, not an
// answer to protect.
//
// `marker_position` IS DERIVED, NEVER A SEPARATE TYPED FIELD -- the same shape
// `line-traversal-surface.tsx` settled on after its own correction: the marker's own visible
// position on the line (`originValue + forwardSteps`, with `originValue` fixed at 0 -- the line
// always starts at 0, per every real exemplar) already shows the child what they are about to
// submit, so a second field asking them to re-type it would be pure redundancy. SUBMIT is gated on
// having moved the marker at least once (`forwardSteps > 0`), matching `line-traversal`'s own gate.
//
// Visual design is reused, not reinvented (master work order §5A): the screen chrome, question
// rendering, `SubmitButton` and the payload-token shapes are reproduced from
// `line-traversal-surface.tsx`'s own `styles`/`SubmitButton`/token pattern (neither is exported from
// that file, so this file reproduces their shape rather than importing a private symbol) -- not a
// redesign. `UnitStepper`'s own coarse-stepping and target-flag additions are the only new visual
// behaviour this sub-phase introduces, per §5A's "the new primitive is the only new visual surface
// any sub-phase should introduce" (here, an addition to an existing primitive rather than a new one,
// since `unit-stepper.tsx` was built generic for exactly this reuse).
//
// Client-side authority boundary: this file never compares the submitted position against
// `target_position`, never reads `tolerance` (which never reaches the client at all -- it lives in
// `correct_answer_payload`), and never renders `target_position` as a numeral outside the line
// itself -- see `line-position-logic.ts`'s header for why the line's own tick labels are not the
// same kind of leak a separate token would be.

import { useMemo, useState } from 'react';
import { Pressable, StyleSheet, View } from 'react-native';

import { AppText } from '@/src/components/app-text';
import type { ArchetypeSurfaceProps } from '@/src/features/c-session/archetype-surfaces';
import { LINE_POSITION_COARSE_STEP, resolveLinePositionSpec } from '@/src/features/c-session/archetypes/line-position-logic';
import { FailClosedFrame } from '@/src/features/c-session/fail-closed-frame';
import { accentForGameFamily } from '@/src/features/c-session/game-family-accents';
import { HIT_SLOP, TOKEN_SPACING, TOKEN_TOUCH_TARGET_SIZE } from '@/src/features/c-session/motor-constants';
import { UnitStepper } from '@/src/features/c-session/primitives/unit-stepper';
import { TaskPromptCard } from '@/src/features/c-session/task-prompt-card';
import { colors, radius, spacing, typography } from '@/src/theme/tokens';
import { TASK_SURFACE_PADDING } from '@/src/features/c-session/task-layout';

const PAYLOAD_LABEL_LINE_HEIGHT = Math.round(typography.lineHeight.sm);
const PAYLOAD_LABEL_BLOCK_HEIGHT = PAYLOAD_LABEL_LINE_HEIGHT * 2;

// The line's own start -- fixed, not read from the wire. Every real C-MCL-04 exemplar's implicit
// range is 0..interval_max (target_position is itself always within that span), and `interval_max`
// already carries the line's upper bound; there is no separate "lower bound" key on the wire at all.
const LINE_ORIGIN = 0;

export function LinePositionSurface({ onSubmit, task }: ArchetypeSurfaceProps) {
  const spec = useMemo(() => resolveLinePositionSpec(task), [task]);

  if (spec === null) {
    return <FailClosedFrame onExit={() => {}} supportCode={task.request_id} />;
  }

  const accent = accentForGameFamily(task.game_family_id);

  return <LinePositionScene accent={accent} onSubmit={onSubmit} spec={spec} />;
}

type LinePositionSceneProps = {
  accent: string;
  spec: NonNullable<ReturnType<typeof resolveLinePositionSpec>>;
  onSubmit: (payload: Record<string, unknown>) => void | Promise<void>;
};

function LinePositionScene({ accent, onSubmit, spec }: LinePositionSceneProps) {
  const [forwardSteps, setForwardSteps] = useState(0);

  const canSubmit = forwardSteps > 0;

  const handleSubmitPress = () => {
    if (!canSubmit) return;
    void onSubmit({ [spec.positionKey]: LINE_ORIGIN + forwardSteps });
  };

  const clampForward = (next: number) => Math.max(0, Math.min(spec.intervalMax, next));

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

      {/* THE DISCOVERABILITY HINT (2026-08-26, owner decision): a bucketed range, never the exact
          target -- see line-position-logic.ts's own "THE DISCOVERABILITY HINT" comment for why a
          5-wide window is safe where a bare digit would not be. Without this, a target far down a
          200-unit line was entirely undiscoverable: the stepper only auto-scrolls to the MARKER
          (starting at 0), never to the target. */}
      <AppText style={[styles.targetHint, { color: accent }]}>
        {`Target is between ${spec.targetRangeStart} and ${spec.targetRangeEnd}`}
      </AppText>

      <UnitStepper
        coarseStep={LINE_POSITION_COARSE_STEP}
        forwardSteps={forwardSteps}
        maxForwardSteps={spec.intervalMax}
        onCoarseBack={() => setForwardSteps((prev) => clampForward(prev - LINE_POSITION_COARSE_STEP))}
        onCoarseForward={() => setForwardSteps((prev) => clampForward(prev + LINE_POSITION_COARSE_STEP))}
        onStepBack={() => setForwardSteps((prev) => clampForward(prev - 1))}
        onStepForward={() => setForwardSteps((prev) => clampForward(prev + 1))}
        originValue={LINE_ORIGIN}
        targetForwardOffset={spec.targetPosition}
      />

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
  targetHint: {
    fontFamily: typography.fonts.bold,
    fontSize: typography.fontSize.body,
    textAlign: 'center',
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
