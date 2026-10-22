// The `ordered-value-sequence` archetype surface (10a). Renders `task.prompt_text` verbatim and a
// `ValueTokenRow` configured by `resolveOrderedValueSequenceSpec`; `null` resolution renders
// `FailClosedFrame`, matching c-session-screen.tsx's own convention (support code =
// `task.request_id`). `onSubmit` receives the raw per-key values object -- `handleSubmit`
// (c-session-screen.tsx) already runs `encodeActionPayload` on it; this file does not duplicate
// that step and does not modify `handleSubmit`.
//
// `GenericExtraField` exists for the two-layer rule's own sake: `resolveOrderedValueSequenceSpec`
// collects any declared `valid_action_space` key beyond the scene key generically (field-kinds.ts),
// per the approved design's "a future extra key needs no structural change here." No NP template
// declares one today -- `extraFields` is always empty against the real registry -- so this renders
// nothing in practice; it exists so the promise is real rather than aspirational.
//
// Its `boolean-control` branch uses the shared `BooleanToggle` (`primitives/boolean-toggle.tsx`,
// 2026-08-26) rather than a local single-switch control. The original local version defaulted to
// showing "NO" before the child had touched it at all, which read as an answer already given
// rather than an open question, even though SUBMIT correctly stayed disabled until a value was
// actually set -- see that file's own header for the full reasoning.

import { useMemo, useState } from 'react';
import { Pressable, StyleSheet, View } from 'react-native';

import { AppText } from '@/src/components/app-text';
import type { ArchetypeSurfaceProps } from '@/src/features/c-session/archetype-surfaces';
import {
  resolveOrderedValueSequenceSpec,
  type ExtraField,
} from '@/src/features/c-session/archetypes/ordered-value-sequence-logic';
import { FailClosedFrame } from '@/src/features/c-session/fail-closed-frame';
import { HIT_SLOP } from '@/src/features/c-session/motor-constants';
import { BooleanToggle } from '@/src/features/c-session/primitives/boolean-toggle';
import { DigitKeypad } from '@/src/features/c-session/primitives/digit-keypad';
import { ValueTokenRow } from '@/src/features/c-session/primitives/value-token-row';
import { TaskPromptCard } from '@/src/features/c-session/task-prompt-card';
import { colors, radius, spacing, typography } from '@/src/theme/tokens';
import { TASK_SURFACE_PADDING } from '@/src/features/c-session/task-layout';

export function OrderedValueSequenceSurface({ onSubmit, task }: ArchetypeSurfaceProps) {
  const spec = useMemo(() => resolveOrderedValueSequenceSpec(task), [task]);

  if (spec === null) {
    return <FailClosedFrame onExit={() => {}} supportCode={task.request_id} />;
  }

  if (spec.scene === 'entry') {
    return <EntrySceneSurface onSubmit={onSubmit} spec={spec} />;
  }
  return <ArrangeSceneSurface onSubmit={onSubmit} spec={spec} />;
}

// --- entry scene (NP-01/02/03) ------------------------------------------------------------------

type EntrySceneSurfaceProps = {
  spec: Extract<ReturnType<typeof resolveOrderedValueSequenceSpec>, { scene: 'entry' }>;
  onSubmit: (payload: Record<string, unknown>) => void | Promise<void>;
};

function EntrySceneSurface({ onSubmit, spec }: EntrySceneSurfaceProps) {
  const [entryValues, setEntryValues] = useState<readonly (number | null)[]>(() =>
    Array.from({ length: spec.blanks }, () => null),
  );
  const [extraValues, setExtraValues] = useState<Record<string, unknown>>({});

  const canSubmit =
    entryValues.every((value) => value !== null) &&
    spec.extraFields.every((field) => Object.prototype.hasOwnProperty.call(extraValues, field.key));

  const handleSubmitPress = () => {
    if (!canSubmit) return;
    void onSubmit({
      [spec.entryKey]: entryValues,
      ...extraValues,
    });
  };

  return (
    <View style={styles.container}>
      {/* The card holds the question alone here: what sits below it is the answer
          surface itself -- the child drags or taps it -- not something they only look at. */}
      <TaskPromptCard>
        <AppText style={styles.promptText} variant="title">
          {spec.promptText}
        </AppText>
      </TaskPromptCard>
      <ValueTokenRow
        blanks={spec.blanks}
        entryValues={entryValues}
        mode="display-with-entry"
        onChangeEntryValues={setEntryValues}
        shownSequence={spec.shownSequence}
      />
      {spec.extraFields.map((field) => (
        <GenericExtraField
          field={field}
          key={field.key}
          onChange={(value) => setExtraValues((prev) => ({ ...prev, [field.key]: value }))}
          value={extraValues[field.key]}
        />
      ))}
      <SubmitButton disabled={!canSubmit} onPress={handleSubmitPress} />
    </View>
  );
}

// --- arrangement scene (NP-04) -------------------------------------------------------------------

type ArrangeSceneSurfaceProps = {
  spec: Extract<ReturnType<typeof resolveOrderedValueSequenceSpec>, { scene: 'arrange' }>;
  onSubmit: (payload: Record<string, unknown>) => void | Promise<void>;
};

function ArrangeSceneSurface({ onSubmit, spec }: ArrangeSceneSurfaceProps) {
  const [order, setOrder] = useState<readonly number[]>(spec.values);
  const [extraValues, setExtraValues] = useState<Record<string, unknown>>({});

  const canSubmit = spec.extraFields.every((field) =>
    Object.prototype.hasOwnProperty.call(extraValues, field.key),
  );

  const handleSubmitPress = () => {
    if (!canSubmit) return;
    void onSubmit({
      [spec.arrangeKey]: order,
      ...extraValues,
    });
  };

  return (
    <View style={styles.arrangeContainer}>
      <View style={styles.arrangeTopBlock}>
        {/* The card holds the question alone here: what sits below it is the answer
            surface itself -- the child drags or taps it -- not something they only look at. */}
        <TaskPromptCard>
          <AppText style={styles.promptText} variant="title">
            {spec.promptText}
          </AppText>
        </TaskPromptCard>
        <View style={styles.arrangeRowWrapper}>
          <ValueTokenRow mode="reorder" onChangeOrder={setOrder} values={order} />
        </View>
      </View>
      {spec.extraFields.map((field) => (
        <GenericExtraField
          field={field}
          key={field.key}
          onChange={(value) => setExtraValues((prev) => ({ ...prev, [field.key]: value }))}
          value={extraValues[field.key]}
        />
      ))}
      <SubmitButton disabled={!canSubmit} onPress={handleSubmitPress} />
    </View>
  );
}

// --- shared bits -----------------------------------------------------------------------------

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

function GenericExtraField({
  field,
  onChange,
  value,
}: {
  field: ExtraField;
  value: unknown;
  onChange: (value: unknown) => void;
}) {
  if (field.binding.kind === 'boolean-control') {
    return <BooleanToggle fieldKey={field.key} onChange={onChange} value={value} />;
  }

  if (field.binding.kind === 'exact-choice-control') {
    return (
      <View style={styles.choiceRow}>
        {field.binding.alternatives.map((alternative) => (
          <Pressable
            accessibilityLabel={alternative}
            accessibilityRole="button"
            accessibilityState={{ selected: value === alternative }}
            key={alternative}
            onPress={() => onChange(alternative)}
            style={[styles.toggle, value === alternative && styles.toggleOn]}>
            <AppText style={styles.toggleText}>{alternative}</AppText>
          </Pressable>
        ))}
      </View>
    );
  }

  // integer-field / numeric-field: a single-slot digit keypad. numeric-field never needs a decimal
  // point for anything this archetype's real registry entries declare, so no decimal key is drawn.
  const buffer = typeof value === 'string' ? value : '';
  return (
    <View>
      <AppText>{buffer.length === 0 ? '' : buffer}</AppText>
      <DigitKeypad
        onDelete={() => onChange(buffer.slice(0, -1))}
        onDigit={(digit) => {
          const nextBuffer = buffer + digit;
          onChange(Number.parseInt(nextBuffer, 10));
        }}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  choiceRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: spacing.smPlus,
  },
  // `flex: 1` so this fills the task screen's middle wrapper (c-session-screen.tsx's
  // `taskContentMiddle`) rather than sizing to its own content; `space-between` then pins the
  // question to the top of that space and SUBMIT to the bottom, with `gap` as the minimum spacing
  // between the elements in between and any leftover room showing as extra white space rather than
  // drifting the question or SUBMIT off their fixed card-edge gaps.
  container: {
    flex: 1,
    gap: spacing.lg,
    justifyContent: 'space-between',
    padding: TASK_SURFACE_PADDING,
  },
  // The arrange (NP-04) scene's own layout, scoped apart from `container`/`promptText` above
  // (still used unchanged by the entry scene, NP-01..03) -- 2026-08-26 correction, found by the
  // owner testing NP-04 in the browser. `container`'s `flex: 1` + `justifyContent: 'space-between'`
  // distributes ALL leftover vertical space into the ONE gap between the prompt and the token row
  // (there being only one middle child), which is what produced the large empty bands above and
  // below the row the owner flagged. This scene instead packs its content from the top with small,
  // fixed gaps (`arrangeContainer`'s own `gap`, `arrangeTopBlock`'s own `gap` and `marginTop`) and
  // leaves any true leftover height at the BOTTOM of the screen, below SUBMIT, rather than
  // distributing it as floating whitespace between the question and the cards.
  arrangeContainer: {
    flex: 1,
    gap: spacing.lg / 2,
    padding: TASK_SURFACE_PADDING,
  },
  // Groups the prompt and the token row at a small, fixed gap, with a small top margin so the
  // prompt sits slightly lower than the very top edge (2026-08-26 request).
  arrangeTopBlock: {
    gap: spacing.lg / 2,
    marginTop: spacing.lg / 2,
  },
  // Centers the (horizontally-scrolling) token row within the card's own width (2026-08-26
  // request) -- `ValueTokenRow`'s own `reorder` mode content otherwise left-aligns.
  arrangeRowWrapper: {
    alignItems: 'center',
  },
  pressed: { opacity: 0.72 },
  // Half of typography.fontSize.title / lineHeight.title (40/46), per instruction.
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
  toggle: {
    alignItems: 'center',
    backgroundColor: colors.surface1,
    borderColor: colors.border,
    borderRadius: radius.md,
    borderWidth: 2,
    justifyContent: 'center',
    minHeight: 48,
    paddingHorizontal: spacing.md,
  },
  toggleOn: {
    backgroundColor: colors.primarySoft,
    borderColor: colors.primary,
  },
  toggleText: {
    fontFamily: typography.fonts.bold,
  },
});
