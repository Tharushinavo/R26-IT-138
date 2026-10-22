// The `object-set-action` archetype surface (10e, C-CC-01/C-CC-02). Renders `task.prompt_text`
// verbatim, an optional `targetValue` numeral token (C-CC-02 only), and one of two scenes chosen
// off `resolveObjectSetActionSpec`'s `totalKey` discriminant -- NEVER off
// `task.game_task_template_id` (c-object-set-action-no-template-branch.test.ts proves this by
// source scan):
//
//   - `totalKey !== null` -- `SelectAndCountScene` (C-CC-01): the whole pool is one undifferentiated
//     `ObjectPool` the child taps to select from, plus a `DigitKeypad` field for `submitted_total`.
//     Counting the selection IS the assessed skill here, so `submitted_total` is never auto-filled
//     from `selectedIds.size` -- see object-set-action-logic.ts's header for the full reasoning.
//   - `totalKey === null` -- `PlaceIntoBoxScene` (C-CC-02): two `ObjectPool`s, one showing the
//     available objects and one showing "the box"; tapping an object moves its id between the two
//     pools. `placed_object_ids` is exactly the box's current contents, in the order ids were
//     placed. No client check that the box's size matches `target_n` -- SUBMIT is never gated on it,
//     matching the sequence doc's "Does NOT deliver ... that the partition is exhaustive" doctrine
//     applied here to a set rather than a partition.
//
// `null` resolution renders `FailClosedFrame`, matching every other archetype surface's own
// convention (support code = `task.request_id`). `onSubmit` receives the raw per-key values object;
// `handleSubmit` (c-session-screen.tsx) already runs `encodeActionPayload` on it -- this file does
// not duplicate that step and does not modify `handleSubmit`.
//
// Visual design is reused, not reinvented (master work order §5A): the screen chrome, question
// rendering, `SubmitButton` and the payload-token shape are reproduced from
// `value-report-surface.tsx`'s own `styles`/`SubmitButton`/token pattern (neither is exported from
// that file, so this file reproduces their shape rather than importing a private symbol), using the
// PLAIN `TOKEN_TOUCH_TARGET_SIZE`/`TOKEN_SPACING` sizing (matching `line-traversal-surface.tsx`'s
// own choice, not `option-select-surface.tsx`'s/`value-report-surface.tsx`'s 1.6x enlargement --
// that enlargement was a specific, scoped user request, not a standing rule this file inherits).
// `ObjectPool` is the one new primitive this sub-phase introduces.
//
// Client-side authority boundary: this file never compares a selection or box size against
// `target_n`, never styles or filters objects by whether they came from `valid_object_ids` or
// `distractor_object_ids` (the resolver has already flattened that distinction away -- see
// object-set-action-logic.ts's header), and never de-duplicates or repairs a selection.

import { useEffect, useMemo, useRef, useState } from 'react';
import { Animated, Pressable, StyleSheet, View } from 'react-native';
import type { StyleProp, ViewStyle } from 'react-native';

import { AppText } from '@/src/components/app-text';
import type { ArchetypeSurfaceProps } from '@/src/features/c-session/archetype-surfaces';
import { resolveObjectSetActionSpec } from '@/src/features/c-session/archetypes/object-set-action-logic';
import { FailClosedFrame } from '@/src/features/c-session/fail-closed-frame';
import { accentForGameFamily } from '@/src/features/c-session/game-family-accents';
import { ANIMATION_DURATION_MS, HIT_SLOP, TOKEN_SPACING, TOKEN_TOUCH_TARGET_SIZE } from '@/src/features/c-session/motor-constants';
import { DigitKeypad } from '@/src/features/c-session/primitives/digit-keypad';
import { ObjectPool } from '@/src/features/c-session/primitives/object-pool';
import { TaskPromptCard } from '@/src/features/c-session/task-prompt-card';
import { colors, radius, spacing, typography } from '@/src/theme/tokens';
import { TASK_SURFACE_PADDING } from '@/src/features/c-session/task-layout';

// C-CC-02's target_n token, enlarged 60% over the plain TOKEN_TOUCH_TARGET_SIZE (2026-08-26
// request) -- matching value-report-surface.tsx's own PAYLOAD_TOKEN_SIZE precedent exactly. No
// label above it (2026-08-26 removal, direct user request): target_n is the GIVEN size of the set
// to build, not the answer (object-set-action-logic.ts's header has the full reasoning for why
// that makes it safe to render bare), so nothing here disambiguates it the way value-report's
// multi-operand labels have to.
const TARGET_TOKEN_SIZE = Math.round(TOKEN_TOUCH_TARGET_SIZE * 1.6);
// 2026-08-26 request: the number inside that token, 50% larger than the shared body-text size.
const TARGET_TOKEN_FONT_SIZE = Math.round(typography.fontSize.lg * 1.5);

// Matches `styles.submitButton`'s own `minHeight` -- the place-into-box scene's own
// `placeIntoBoxContainer` reserves this much space (plus a spacing gap) at its bottom so SUBMIT's
// fixed position never overlaps the available pool's own clipped viewport above it.
const SUBMIT_ANCHOR_HEIGHT = 56;

// 2026-08-26 request: the target token and "the box" frame both get the same neutral fill as
// c-session-screen.tsx's own screen ground (`TASK_SCREEN_BACKGROUND`, #F4F4F6) -- not imported
// from there since that constant is private to its own file, and the two are conceptually
// independent surfaces that happen to share a colour by explicit request, not by shared ownership.
const BOX_BACKGROUND = '#F4F4F6';

// A DigitKeypad answer field cannot hold more digits than this render width comfortably shows --
// mirrors `ordered-value-sequence-surface.tsx`'s own entry-slot doctrine of a fixed, non-difficulty-
// dependent maximum entry length, never derived from the pool size.
const MAX_TOTAL_DIGITS = 3;

// A LAYOUT threshold, keyed on the resolved POOL SIZE, never on `difficulty_level` directly (this
// file never reads that field at all -- c-object-set-action-motor-constancy.test.ts's own scan
// proves it). Below this many objects, the pool + answer token + keypad + SUBMIT all fit on one
// screen together and `SelectAndCountScene` renders them that way, with no ADD ANSWER/VIEW staging
// at all (2026-08-26 request, explicit trade-off accepted against SPEC section 10's motor-constancy
// doctrine: this makes the SCREEN FLOW itself vary with content size, where every other archetype
// in this codebase keeps flow fixed and only lets magnitude vary -- flagged here rather than left
// silent, since it departs from a rule this project otherwise treats as non-negotiable). Chosen
// from C-CC-01's own five real exemplar pool sizes (3, 6, 10, 15, 22 across L1-L5): 8 sits in the
// gap between L2's 6 (fits alongside a keypad without staging) and L3's 10 (does not), so only L1
// and L2 use the single-screen layout; L3-L5 stage. Not a considered claim that 8 is the largest
// pool any keypad can share a screen with in general -- only that it is where THIS boundary falls
// for this template's own real data.
const STAGED_FLOW_MIN_POOL_SIZE = 8;

export function ObjectSetActionSurface({ onSubmit, task }: ArchetypeSurfaceProps) {
  const spec = useMemo(() => resolveObjectSetActionSpec(task), [task]);

  if (spec === null) {
    return <FailClosedFrame onExit={() => {}} supportCode={task.request_id} />;
  }

  const accent = accentForGameFamily(task.game_family_id);

  if (spec.totalKey !== null) {
    return <SelectAndCountScene accent={accent} onSubmit={onSubmit} spec={spec} totalKey={spec.totalKey} />;
  }

  return <PlaceIntoBoxScene accent={accent} onSubmit={onSubmit} spec={spec} />;
}

// --- C-CC-01: select every object, then type how many were selected --------------------------------
// SIZE-GATED FLOW (2026-08-26): below `STAGED_FLOW_MIN_POOL_SIZE` objects, everything renders on
// one screen at once (pool, answer token, keypad, SUBMIT -- no ADD ANSWER/VIEW at all), the same
// shape this scene had before staging existed. At or above that size, the two-phase flow below
// applies. See `STAGED_FLOW_MIN_POOL_SIZE`'s own comment for what this trades away.
//
// THE STAGED FLOW ITSELF, for pools at or above the threshold (2026-08-26, corrected twice after
// the user tested at difficulty 5's ~22-object pool): `'selecting' -> 'answering'`. The pool is
// visible immediately on mount (a brief entrance
// fade/slide, `ANIMATION_DURATION_MS` from motor-constants.ts -- no gating button needed to see it;
// an earlier draft put a VIEW button in front of the pool at mount and the user corrected that: the
// pool being visible on load IS the intended landing state) with ADD ANSWER below it. ADD ANSWER is
// ALWAYS enabled, with no minimum-selection requirement -- an intermediate draft disabled it until
// at least one object was selected, and the user corrected that too: a child who believes NONE of
// the objects should count is entitled to advance and type `0`, which a selection-count gate would
// have made impossible to reach. `submitted_total` is validated server-side, not gated by this
// client on any assumption about what a "reasonable" count is. Selecting and answering never share
// the screen -- `scrollable={false}` on the pool means every object renders at once with no internal
// scroll, since the pool is the only thing on screen during `'selecting'`.
//
// `'answering'`: the pool is replaced by the answer token, keypad, and SUBMIT -- but neither
// `selectedIds` nor `totalDigits` is ever cleared on a phase change (2026-08-26 correction: an
// earlier draft nested a read-only pool preview under the keypad instead of navigating; the user
// clarified VIEW should return to the FULL selecting screen, "the difference is now the balls are
// selected"). A VIEW button sits directly above SUBMIT; pressing it sets `phase` back to
// `'selecting'` -- the same pool the child already tapped, still showing exactly what was
// selected, still fully interactive (a child can add or remove a selection on the way back through,
// same as the first pass) -- and ADD ANSWER returns them to `'answering'` again with `totalDigits`
// intact. This is a real back-and-forth between the two phases, not a preview stacked on top of
// one of them.
//
// No accent-colored LABEL on the answer token (2026-08-26 removal, direct user request): the
// token's own "?" placeholder already communicates what to fill in, matching digit-keypad-driven
// entry elsewhere in this codebase that also has no adjacent label (ordered-value-sequence's own
// entry slots). `accent` is still threaded through to `ObjectPool` (pool objects coloured with the
// family's own accent, per accentForGameFamily.ts) and is NOT used for ADD ANSWER or VIEW, which
// are fixed to `colors.accentGreen` -- the standing palette green `UnitStepper`'s own jump control
// already uses, not a per-family colour (these buttons mean the same thing everywhere they appear).

type SelectAndCountPhase = 'selecting' | 'answering';

type SelectAndCountSceneProps = {
  accent: string;
  spec: NonNullable<ReturnType<typeof resolveObjectSetActionSpec>>;
  totalKey: string;
  onSubmit: (payload: Record<string, unknown>) => void | Promise<void>;
};

function SelectAndCountScene({ accent, onSubmit, spec, totalKey }: SelectAndCountSceneProps) {
  const [selectedIds, setSelectedIds] = useState<ReadonlySet<string>>(new Set());
  const [totalDigits, setTotalDigits] = useState('');
  const [phase, setPhase] = useState<SelectAndCountPhase>('selecting');
  const revealProgress = useRef(new Animated.Value(0)).current;
  const usesStagedFlow = spec.objectIds.length >= STAGED_FLOW_MIN_POOL_SIZE;

  // Replays the entrance animation every time `'selecting'` becomes visible again -- including a
  // return trip from `'answering'` via VIEW (2026-08-26 correction: VIEW navigates fully back to
  // this phase, it does not stack the pool underneath the keypad -- see the phase header comment).
  // A no-op when `!usesStagedFlow`, since `phase` is never read outside the staged branch below.
  useEffect(() => {
    if (phase !== 'selecting') return;
    revealProgress.setValue(0);
    Animated.timing(revealProgress, {
      duration: ANIMATION_DURATION_MS,
      toValue: 1,
      useNativeDriver: true,
    }).start();
  }, [phase, revealProgress]);

  const canSubmit = totalDigits.length > 0;

  const handleToggle = (id: string) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const handleSubmitPress = () => {
    if (!canSubmit) return;
    void onSubmit({
      [spec.idSetKey]: Array.from(selectedIds),
      [totalKey]: Number(totalDigits),
    });
  };

  const answerControls = (
    <>
      <View style={styles.answerRow}>
        <View style={styles.payloadToken}>
          <AppText style={styles.payloadTokenText}>{totalDigits.length > 0 ? totalDigits : '?'}</AppText>
        </View>
      </View>

      <DigitKeypad
        onDelete={() => setTotalDigits((prev) => prev.slice(0, -1))}
        onDigit={(digit) => setTotalDigits((prev) => (prev.length >= MAX_TOTAL_DIGITS ? prev : prev + digit))}
      />
    </>
  );

  // Small pool: everything on one screen at once, no ADD ANSWER/VIEW staging -- see
  // STAGED_FLOW_MIN_POOL_SIZE's own comment for the accepted trade-off this represents.
  if (!usesStagedFlow) {
    return (
      <View style={styles.container}>
        {/* The card holds the question alone here: what sits below it is the answer
            surface itself -- the child drags or taps it -- not something they only look at. */}
        <TaskPromptCard>
          <AppText style={styles.promptText} variant="title">
            {spec.promptText}
          </AppText>
        </TaskPromptCard>

        <ObjectPool accent={accent} objectIds={spec.objectIds} onToggle={handleToggle} scrollable={false} selectedIds={selectedIds} />

        {answerControls}

        <SubmitButton disabled={!canSubmit} onPress={handleSubmitPress} />
      </View>
    );
  }

  return (
    <View style={styles.container}>
      {/* The card holds the question alone here: what sits below it is the answer
          surface itself -- the child drags or taps it -- not something they only look at. */}
      <TaskPromptCard>
        <AppText style={styles.promptText} variant="title">
          {spec.promptText}
        </AppText>
      </TaskPromptCard>

      {phase === 'selecting' && (
        <>
          <Animated.View
            style={{
              opacity: revealProgress,
              transform: [{ translateY: revealProgress.interpolate({ inputRange: [0, 1], outputRange: [-24, 0] }) }],
            }}>
            <ObjectPool
              accent={accent}
              objectIds={spec.objectIds}
              onToggle={handleToggle}
              scrollable={false}
              selectedIds={selectedIds}
            />
          </Animated.View>
          <RevealButton label="ADD ANSWER" onPress={() => setPhase('answering')} />
        </>
      )}

      {phase === 'answering' && (
        <>
          {answerControls}

          <RevealButton label="VIEW" onPress={() => setPhase('selecting')} />

          <SubmitButton disabled={!canSubmit} onPress={handleSubmitPress} />
        </>
      )}
    </View>
  );
}

function RevealButton({ disabled = false, label, onPress }: { disabled?: boolean; label: string; onPress: () => void }) {
  return (
    <Pressable
      accessibilityLabel={label.toLowerCase()}
      accessibilityRole="button"
      accessibilityState={{ disabled }}
      disabled={disabled}
      hitSlop={HIT_SLOP}
      onPress={onPress}
      style={({ pressed }) => [
        styles.addAnswerButton,
        disabled && styles.submitButtonDisabled,
        pressed && !disabled && styles.pressed,
      ]}>
      <AppText style={styles.addAnswerButtonText}>{label}</AppText>
    </Pressable>
  );
}

// --- C-CC-02: put a given number of objects into the box -------------------------------------------

type PlaceIntoBoxSceneProps = {
  accent: string;
  spec: NonNullable<ReturnType<typeof resolveObjectSetActionSpec>>;
  onSubmit: (payload: Record<string, unknown>) => void | Promise<void>;
};

function PlaceIntoBoxScene({ accent, onSubmit, spec }: PlaceIntoBoxSceneProps) {
  // `placed`, in the order ids were placed -- `placed_object_ids` submits exactly this array.
  const [placed, setPlaced] = useState<readonly string[]>([]);

  const placedSet = new Set(placed);
  const available = spec.objectIds.filter((id) => !placedSet.has(id));

  const canSubmit = placed.length > 0;

  const handlePoolToggle = (id: string) => {
    setPlaced((prev) => [...prev, id]);
  };

  const handleBoxToggle = (id: string) => {
    setPlaced((prev) => prev.filter((placedId) => placedId !== id));
  };

  const handleSubmitPress = () => {
    if (!canSubmit) return;
    void onSubmit({ [spec.idSetKey]: placed });
  };

  return (
    <View style={[styles.container, styles.placeIntoBoxContainer]}>
      {/* The card holds the question alone here: what sits below it is the answer
          surface itself -- the child drags or taps it -- not something they only look at. */}
      <TaskPromptCard>
        <AppText style={styles.promptText} variant="title">
          {spec.promptText}
        </AppText>
      </TaskPromptCard>

      {spec.targetValue !== null && (
        <View style={styles.answerRow}>
          <View style={styles.targetToken}>
            <AppText style={styles.targetTokenText}>{spec.targetValue.value}</AppText>
          </View>
        </View>
      )}

      <View style={[styles.boxFrame, { borderColor: accent }]}>
        <ObjectPool
          accent={accent}
          disabled={placed.length === 0}
          objectIds={placed}
          onToggle={handleBoxToggle}
          scrollable={false}
          selectedIds={new Set()}
        />
      </View>

      {/* The remaining-available pool is VISIBLE, in the white space between the box and SUBMIT
          (2026-08-26 correction: an earlier draft hid this pool entirely behind SUBMIT, which the
          user rejected -- it should only disappear once it runs OUT of room, not always). This
          viewport fills exactly the space left over above SUBMIT's own fixed reserved band
          (`placeIntoBoxContainer`'s `paddingBottom`) and clips anything past its own bottom edge --
          so a pool that fits shows in full, and a pool with more objects than fit shows only as
          many as the space allows, with the rest appearing to emerge from underneath as more are
          placed/removed, never by pushing SUBMIT itself. */}
      <View style={styles.availablePoolViewport}>
        <ObjectPool accent={accent} objectIds={available} onToggle={handlePoolToggle} scrollable={false} selectedIds={new Set()} />
      </View>

      {/* SUBMIT is pinned to a fixed position (2026-08-26 correction: it must never move, not even
          slightly, as the box above grows). */}
      <View style={styles.submitAnchor}>
        <SubmitButton
          disabled={!canSubmit}
          disabledStyle={styles.submitButtonDisabledOpaque}
          onPress={handleSubmitPress}
        />
      </View>
    </View>
  );
}

function SubmitButton({
  disabled,
  disabledStyle = styles.submitButtonDisabled,
  onPress,
  style,
}: {
  disabled: boolean;
  onPress: () => void;
  /** The disabled-state style. Defaults to the standard opacity dim; the place-into-box scene
   *  overrides this to an OPAQUE muted colour instead, because the available pool's own clipped
   *  viewport (`availablePoolViewport`) can sit directly behind SUBMIT's fixed position, and a
   *  translucent disabled state would let it show through there -- see that scene's own comment. */
  disabledStyle?: StyleProp<ViewStyle>;
  /** Extra style merged on top of the shared button look -- e.g. `placeIntoBoxScene`'s own
   *  fixed-position override, below. */
  style?: StyleProp<ViewStyle>;
}) {
  return (
    <Pressable
      accessibilityRole="button"
      accessibilityState={{ disabled }}
      disabled={disabled}
      hitSlop={HIT_SLOP}
      onPress={onPress}
      style={({ pressed }) => [
        styles.submitButton,
        style,
        disabled && disabledStyle,
        pressed && !disabled && styles.pressed,
      ]}>
      <AppText style={styles.submitButtonText}>SUBMIT</AppText>
    </Pressable>
  );
}


const styles = StyleSheet.create({
  // Fixed to the standing palette green, not a per-family accent -- see the scene header comment.
  addAnswerButton: {
    alignItems: 'center',
    backgroundColor: colors.accentGreen,
    borderRadius: radius.md,
    justifyContent: 'center',
    minHeight: 56,
    paddingHorizontal: spacing.lg,
  },
  addAnswerButtonText: {
    color: colors.surface1,
    fontFamily: typography.fonts.bold,
    fontSize: typography.fontSize.lg,
  },
  answerRow: {
    alignItems: 'center',
    flexDirection: 'row',
    gap: TOKEN_SPACING * 2,
    justifyContent: 'center',
  },
  // borderColor is applied inline from the family accent (2026-08-26 request) -- the static value
  // here is only ever a fallback default, overridden everywhere this style is actually used.
  boxFrame: {
    backgroundColor: BOX_BACKGROUND,
    borderColor: colors.border,
    borderRadius: radius.md,
    borderStyle: 'dashed',
    borderWidth: 2,
    minHeight: TOKEN_TOUCH_TARGET_SIZE + TOKEN_SPACING,
    padding: TOKEN_SPACING,
  },
  container: {
    flex: 1,
    gap: spacing.lg,
    justifyContent: 'space-between',
    padding: TASK_SURFACE_PADDING,
  },
  // Overrides `container`'s own `justifyContent: 'space-between'` for the place-into-box scene only
  // (2026-08-26 request): the box is now unbounded and grows with `placed.length`
  // (`ObjectPool`'s own `scrollable={false}`, so every placed object stays visible rather than
  // scrolling), and SUBMIT is meant to sit directly after it, not pinned to the bottom of the card
  // regardless of how tall the box gets. `flex-start` lets content stack top-down in JSX order --
  // box, SUBMIT, then the remaining-available pool last -- so a bigger box pushes the (de-prioritised,
  // "how many are left" is not something the child needs to read off) available pool further down
  // or off the visible card, rather than pushing SUBMIT itself.
  // `position: 'relative'` so `submitAnchor` (absolute) below is positioned relative to THIS
  // container, not the whole screen. `paddingBottom` reserves room for the fixed SUBMIT so the
  // growing box's own content does not render underneath it before the box gets tall.
  placeIntoBoxContainer: {
    justifyContent: 'flex-start',
    paddingBottom: SUBMIT_ANCHOR_HEIGHT + spacing.lg,
    position: 'relative',
  },
  // Anchored to the container's own bottom edge -- absolute, so it is decoupled entirely from the
  // normal document flow above it and cannot be pushed by the box growing (2026-08-26 correction:
  // "the button stays exactly the same place it never moves").
  submitAnchor: {
    bottom: spacing.lg,
    left: spacing.lg,
    position: 'absolute',
    right: spacing.lg,
  },
  // Fills whatever vertical space is left between the box above and SUBMIT's own reserved band
  // below (`placeIntoBoxContainer`'s `paddingBottom`) -- `flex: 1` inside a `flex-start` column, so
  // it grows to take all the leftover room rather than shrinking to its content. `overflow:
  // 'hidden'` clips anything past its own bottom edge; since that edge sits right where SUBMIT's
  // reserved band begins, a pool with more objects than fit appears to run out and disappear right
  // where SUBMIT is, matching the "appear to emerge from underneath" effect requested -- while a
  // pool that DOES fit renders in full, visible in the white space, not hidden regardless of size.
  availablePoolViewport: {
    flex: 1,
    overflow: 'hidden',
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
  // 20/23 (this file's own prior baseline, matching every other archetype surface) x1.15, per
  // 2026-08-26 request -- scoped to this file only, not a change to the shared baseline other
  // archetype surfaces still use.
  promptText: { color: colors.textPrimary, fontSize: 23, lineHeight: 26 },
  targetToken: {
    alignItems: 'center',
    backgroundColor: BOX_BACKGROUND,
    borderColor: colors.border,
    borderRadius: radius.md,
    borderWidth: 2,
    height: TARGET_TOKEN_SIZE,
    justifyContent: 'center',
    width: TARGET_TOKEN_SIZE,
  },
  targetTokenText: {
    fontFamily: typography.fonts.bold,
    fontSize: TARGET_TOKEN_FONT_SIZE,
    fontWeight: 'bold',
  },
  submitButton: {
    alignItems: 'center',
    backgroundColor: colors.primary,
    borderRadius: radius.md,
    justifyContent: 'center',
    minHeight: 56,
    paddingHorizontal: spacing.lg,
  },
  submitButtonDisabled: { opacity: 0.5 },
  // OPAQUE, not translucent (2026-08-26 fix) -- `place-into-box`'s SUBMIT sits directly over the
  // hidden pool band (`hiddenBehindSubmit`); the standard opacity-0.5 disabled state let that pool
  // show through, which is exactly the "not intended" bug the user reported. `colors.borderStrong`
  // is a muted, clearly-inert grey that still fully covers whatever is behind it.
  submitButtonDisabledOpaque: { backgroundColor: colors.borderStrong },
  submitButtonText: {
    color: colors.surface1,
    fontFamily: typography.fonts.bold,
    fontSize: typography.fontSize.lg,
  },
});
