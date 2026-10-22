// Rendered in place of the archetype surface, inside `c-session-screen.tsx`'s existing task card,
// after a submission -- never alongside it. That "instead of, not over" placement is a correctness
// requirement, not a layout choice: while this panel is showing, no archetype surface is mounted
// and so no `onSubmit` can fire, which is what structurally prevents a second submission on the
// same task instance. That matters concretely: a CORRECT answer writes the one terminal event a
// task instance may ever have (`task_service.py`'s `has_terminal_for_instance` guard), and
// resubmitting a completed instance is refused with `task_already_terminal`
// (`task_service.py:573-576`) -- a 409 `classifySessionFailure` routes to the technical-block
// screen. A child seeing that would read it as the app breaking, not as "you already answered
// this". This panel existing at all is what keeps that path unreachable.
//
// Two states, one action each, both child-initiated:
//   - not matched -> "Try again": clears the panel and lets the same task remount for a fresh
//     attempt. The backend allows unlimited retries on a wrong answer (no terminal event is
//     written on that path) and escalates `scaffold_level` each time -- this panel displays that
//     escalation, never computes or overrides it.
//   - matched -> "Next": advances to the next task via the caller's own `loadNextTask`.
// Advancing is never automatic. An auto-advance timer would introduce a new timing constant, and
// SPEC section 10 / `motor-constants.ts` own every timing constant in this codebase; a button sidesteps
// that question entirely and lets the child set their own pace, matching every other advance-only
// control here (SubmitButton, NeutralMessageScreen's exit button).
//
// THE WORDING BELOW IS FLAGGED, NOT SETTLED (`ESCALATIONS.md`). Component B's own results view
// documents that its copy is "identical for every possible outcome history" and "contains nothing
// evaluative" -- a per-task correct/incorrect panel is a deliberate departure from that house
// precedent, and whether immediate correct/incorrect framing is right for this population is a
// pedagogical question this file does not answer. The copy here is neutral and non-punitive on the
// not-matched path (no "wrong", no "incorrect", no score) precisely so shipping it does not
// pre-empt that ruling by accident.
//
// This component computes nothing about correctness. It takes the server's own verdict as a prop
// and renders one of two fixed states; it holds no state of its own about the task, the payload,
// or scoring, matching `DigitKeypad`'s and `UnitStepper`'s own "holds no state of its own" doctrine
// for a stateless, caller-driven primitive.
//
// VISUAL TREATMENT matches Component B's own per-question outcome popup
// (live-session-screen.tsx's `outcomePopup`/`outcomeIcon`/`outcomeCorrect`/`outcomeIncorrect`)
// exactly on request: same icon choice (checkmark / heart-outline), same
// success/accentRed colouring, same ZoomIn entrance. B's version sits on a FrostedScrim; this one
// deliberately does NOT, since 2026-10-10 -- Component C's task card carries a background image and
// the blur is applied to that image directly, leaving this panel transparent. That is the one point
// where the two components' verdicts differ, and it is a consequence of C having artwork B has not.
// This is a STYLING match only -- it changes
// nothing about which text is shown (still the neutral, non-punitive copy flagged above) and
// nothing about placement: this panel still renders INSTEAD OF the archetype surface, never
// alongside it, so the double-submission guarantee this file's own docstring opens with is
// completely unaffected by how it looks.

import { Ionicons } from '@expo/vector-icons';
import { Pressable, StyleSheet, View } from 'react-native';
import Animated, { ZoomIn } from 'react-native-reanimated';

import { AppText } from '@/src/components/app-text';
import { HIT_SLOP } from '@/src/features/c-session/motor-constants';
import { colors, radius, spacing, typography } from '@/src/theme/tokens';
import { TASK_SURFACE_PADDING } from '@/src/features/c-session/task-layout';

export type AnswerFeedbackPanelProps = {
  matched: boolean;
  /** The server's own `scaffold_level`, relayed verbatim -- never interpreted by this file. */
  scaffoldLevel: string;
  onTryAgain: () => void;
  onNext: () => void;
};

export function AnswerFeedbackPanel({ matched, onNext, onTryAgain, scaffoldLevel }: AnswerFeedbackPanelProps) {
  return (
    <View style={styles.container}>
      {/* NO BACKGROUND AND NO BLUR LAYER HERE, deliberately (owner instruction, 2026-10-10).
          
          This panel is fully transparent: the verdict's icon, its text and the action button sit
          directly on the task card. The blur the child sees belongs to the card's own background
          IMAGE, applied as that Image's `blurRadius` in c-session-screen.tsx -- see the note there.
          
          Every attempt to produce the effect from this side instead (a scrim band, a frosted
          popup, a full-area overlay) tinted the card, because expo-blur ties its blur radius and
          its white backgroundColor to one `intensity` value. Do not reintroduce a scrim here. */}
      <View style={styles.popupCenter}>
        <Animated.View
          entering={ZoomIn.duration(280).springify().damping(14)}
          style={[styles.popup, matched ? styles.popupCorrect : styles.popupIncorrect]}>
          <View style={[styles.popupIcon, matched ? styles.popupIconCorrect : styles.popupIconIncorrect]}>
            <Ionicons color={colors.primaryForeground} name={matched ? 'checkmark' : 'heart-outline'} size={30} />
          </View>
          <AppText
            align="center"
            style={[styles.popupTitle, matched ? styles.popupTextCorrect : styles.popupTextIncorrect]}
            variant="title">
            {matched ? 'Nice work!' : "Let's try that again."}
          </AppText>
          {!matched ? (
            <AppText
              align="center"
              style={[styles.scaffoldText, styles.popupTextIncorrect]}>{`Support level: ${scaffoldLevel}`}</AppText>
          ) : null}
        </Animated.View>
      </View>
      <Pressable
        accessibilityLabel={matched ? 'Next question' : 'Try again'}
        accessibilityRole="button"
        hitSlop={HIT_SLOP}
        onPress={matched ? onNext : onTryAgain}
        style={({ pressed }) => [styles.actionButton, pressed && styles.pressed]}>
        <AppText style={styles.actionButtonText}>{matched ? 'NEXT' : 'TRY AGAIN'}</AppText>
      </Pressable>
    </View>
  );
}

const styles = StyleSheet.create({
  actionButton: {
    alignItems: 'center',
    backgroundColor: colors.primary,
    borderRadius: radius.md,
    justifyContent: 'center',
    minHeight: 56,
    paddingHorizontal: spacing.lg,
  },
  actionButtonText: {
    color: colors.surface1,
    fontFamily: typography.fonts.bold,
    fontSize: typography.fontSize.lg,
  },
  // Mirrors every archetype surface's own `container` shape (e.g.
  // `ordered-value-sequence-surface.tsx`'s `styles.container`): `flex:1`,
  // `justifyContent:'space-between'`, `padding: spacing.lg` -- the message pinned to the top of the
  // card's own content area, the action button pinned to the bottom, matching where the question
  // and SUBMIT sit on every surface this panel replaces.
  container: {
    flex: 1,
    justifyContent: 'space-between',
    padding: TASK_SURFACE_PADDING,
  },
  // Every value below mirrors live-session-screen.tsx's own outcomePopup/outcomeIcon/outcomeCorrect
  // /outcomeIncorrect/outcomeText styles exactly, on request -- same blur intensity/tint, same
  // glow-via-shadow technique (no solid card background of its own), same icon circle size, same
  // success/accentRed colours.
  popup: {
    alignItems: 'center',
    borderRadius: radius.lg,
    elevation: 10,
    gap: spacing.xs,
    justifyContent: 'center',
    padding: spacing.md,
    shadowOffset: { width: 0, height: 0 },
    shadowOpacity: 1,
    shadowRadius: 50,
    width: '80%',
  },

  popupCenter: { alignItems: 'center', flex: 1, justifyContent: 'center', position: 'relative' },
  popupCorrect: { shadowColor: '#e9f8f1' },
  popupIncorrect: { shadowColor: colors.secondarySoft },
  popupIcon: { alignItems: 'center', borderRadius: radius.pill, height: 56, justifyContent: 'center', width: 56 },
  popupIconCorrect: { backgroundColor: colors.success },
  popupIconIncorrect: { backgroundColor: colors.accentRed },
  popupTextCorrect: { color: colors.success },
  popupTextIncorrect: { color: colors.accentRed },
  popupTitle: { fontFamily: typography.fonts.display, fontSize: typography.fontSize.subtitle, lineHeight: typography.lineHeight.subtitle },
  pressed: { opacity: 0.85 },
  scaffoldText: { fontFamily: typography.fonts.body, fontSize: typography.fontSize.sm },
});
