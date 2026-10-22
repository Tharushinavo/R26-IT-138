// The `partition-allocation` archetype surface (10g, C-EG-01; also lights up C-SF-01). Renders
// `task.prompt_text` verbatim, the task's remaining `prompt_payload` numbers as read-only labelled
// tokens (both real templates' `prompt_text` name a quantity -- "the groups shown", "the total" --
// without stating it, and `interactive_assets` is `{}` on every real exemplar, so the tokens are the
// only place those numbers are visible at all; the bin-count payload key itself is excluded here,
// already visible as the number of rendered slots -- see partition-allocation-logic.ts's own
// header), and one `ValueTokenRow` (`display-with-entry`, `shownSequence: []`) sized to
// `spec.binCount`. `null` resolution renders `FailClosedFrame`, matching c-session-screen.tsx's own
// convention (support code = `task.request_id`). `onSubmit` receives the raw per-key values object --
// `handleSubmit` (c-session-screen.tsx) already runs `encodeActionPayload` on it; this file does not
// duplicate that step and does not modify `handleSubmit`.
//
// `VALUETOKENROW` IS REUSED UNMODIFIED, PER ITS OWN HEADER AND MASTER WORK ORDER §5A. No bin label,
// no per-bin styling, no totals rendered by this file into that component -- an empty
// `shownSequence` and `blanks: spec.binCount` is the entire composition. Do not add a label prop to
// `value-token-row.tsx` for this archetype; that was explicitly declined for the same-shaped
// decision `named-field-row.tsx`'s own header documents for 10f (10f built a NEW primitive rather
// than extend a shared one for exactly this reason: partition bins are positional and unlabeled,
// unlike 10f's named place-value fields, so no such extension is even needed here).
//
// NO CLIENT-SIDE VALIDATION AT ALL (work order, `partition-allocation` section, verbatim: "No
// validation that groups are equal, that a partition is exhaustive, or that a product is right. The
// client submits; the server evaluates."). SUBMIT gates on exactly one, non-correctness condition:
// every bin has a value. This is NOT optional bookkeeping -- `field-kinds.ts`'s
// `ordered-integer-collection` check accepts an EMPTY array, so without this gate an entirely
// unfilled partition would encode cleanly through `encodeActionPayload` and reach the wire.
// `c-partition-allocation-no-client-validation.test.ts` holds the "no correctness check" half of
// this line; the "still gated on completeness" half is its own behavioural test.
//
// ONE SCENE FOR BOTH REAL TEMPLATES, WITH NO BRANCH BETWEEN THEM. C-EG-01 and C-SF-01 declare
// different bin-count and collection-key names, but nothing in this file distinguishes them --
// `spec.binCount`/`spec.binsKey` are read generically. There is no `game_task_template_id` read
// anywhere here, and no `C-EG-01`/`C-SF-01` literal; `c-partition-allocation-no-template-branch.test.ts`
// holds that line.

import { useMemo, useState } from 'react';
import { Pressable, StyleSheet, View } from 'react-native';

import { AppText } from '@/src/components/app-text';
import type { ArchetypeSurfaceProps } from '@/src/features/c-session/archetype-surfaces';
import { resolvePartitionAllocationSpec } from '@/src/features/c-session/archetypes/partition-allocation-logic';
import { FailClosedFrame } from '@/src/features/c-session/fail-closed-frame';
import { accentForGameFamily } from '@/src/features/c-session/game-family-accents';
import { HIT_SLOP, TOKEN_SPACING, TOKEN_TOUCH_TARGET_SIZE } from '@/src/features/c-session/motor-constants';
import { ValueTokenRow } from '@/src/features/c-session/primitives/value-token-row';
import { taskPromptCardStyle } from '@/src/features/c-session/task-prompt-card';
import { colors, radius, spacing, typography } from '@/src/theme/tokens';
import { TASK_SURFACE_PADDING } from '@/src/features/c-session/task-layout';

// Reproduced from `named-integer-fields-surface.tsx`'s own payload-token sizing (itself reproduced
// from `value-report-surface.tsx`), for the same stated reason: a payload token is a read-only
// display the child never presses, so SPEC §10's interactive-touch-target floor does not govern it.
const PAYLOAD_TOKEN_SIZE = TOKEN_TOUCH_TARGET_SIZE;
const PAYLOAD_LABEL_FONT_SIZE = Math.round(typography.fontSize.sm * 1.5);
const PAYLOAD_LABEL_LINE_HEIGHT = Math.round(typography.lineHeight.sm * 1.5);
const PAYLOAD_LABEL_BLOCK_HEIGHT = PAYLOAD_LABEL_LINE_HEIGHT * 2;

export function PartitionAllocationSurface({ onSubmit, task }: ArchetypeSurfaceProps) {
  const spec = useMemo(() => resolvePartitionAllocationSpec(task), [task]);

  if (spec === null) {
    return <FailClosedFrame onExit={() => {}} supportCode={task.request_id} />;
  }

  // The family's own accent, read from the wire -- never a colour chosen per archetype or per
  // template. game-family-accents.ts is the one place this colour is written.
  const accent = accentForGameFamily(task.game_family_id);

  return <PartitionAllocationScene accent={accent} onSubmit={onSubmit} spec={spec} />;
}

type PartitionAllocationSceneProps = {
  accent: string;
  spec: NonNullable<ReturnType<typeof resolvePartitionAllocationSpec>>;
  onSubmit: (payload: Record<string, unknown>) => void | Promise<void>;
};

function PartitionAllocationScene({ accent, onSubmit, spec }: PartitionAllocationSceneProps) {
  const [entryValues, setEntryValues] = useState<readonly (number | null)[]>(() =>
    Array.from({ length: spec.binCount }, () => null),
  );

  // Not a correctness condition -- see the header. `encodeActionPayload` requires a value for every
  // declared key, so a partially-filled submission could not be encoded at all, and the collection
  // kind itself would otherwise happily accept an EMPTY array with none of the bins filled.
  const canSubmit = entryValues.length === spec.binCount && entryValues.every((value) => value !== null);

  const handleSubmitPress = () => {
    if (!canSubmit) return;
    void onSubmit({ [spec.binsKey]: entryValues });
  };

  return (
    <View style={styles.container}>
      <View style={styles.promptBlock}>
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
      </View>
      <ValueTokenRow
        blanks={spec.binCount}
        entryValues={entryValues}
        mode="display-with-entry"
        onChangeEntryValues={setEntryValues}
        shownSequence={[]}
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
  // Reduced by a further 2/3 from spacing.lg / 4 (2026-08-26 request), so the given-value token
  // sits close under the prompt.
  // The question-and-items card (owner instruction, 2026-09-28). This wrapper already held
  // exactly the right content, so it takes the card's own style rather than gaining a component
  // around it -- see task-prompt-card.tsx.
  promptBlock: {
    ...taskPromptCardStyle,
    gap: spacing.lg / 12,
  },
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
  payloadLabelBlock: {
    height: PAYLOAD_LABEL_BLOCK_HEIGHT,
    justifyContent: 'flex-end',
  },
  payloadRow: {
    alignItems: 'center',
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: TOKEN_SPACING,
    justifyContent: 'center',
    rowGap: TOKEN_SPACING * 1.5,
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
