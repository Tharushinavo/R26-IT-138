// The C session shell: state wiring and the actual network calls only. Every decision lives in
// c-session-logic.ts, mirroring live-session-screen.tsx / live-session-logic.ts's split for
// Component B.
//
// The loop is create/resume -> nextTask -> planTaskSurface (composing planTask with surface
// resolution) -> mount the resolved surface -> submitAction via handleSubmit. `ordered-value-
// sequence` is the only archetype with a registered surface so far (10a); every other template
// still renders FailClosedFrame, and archetype-surfaces.ts's own table is what 10b...10h extend --
// this file does not change again when they do.
//
// This file does not implement Component B's refresh-on-401 retry (`withToken` in
// live-session-screen.tsx). That is a deliberate simplification, not a hidden gap: the C API client
// has never issued a live request in this project (session creation refuses while seven parameter
// families are unsigned), so there is nothing yet to exercise a refresh against, and adding it
// speculatively would be more than this batch's own loop needs. Recorded in the register entry.
//
// `api` is resolved the same null-safe way Component B's screen resolves it
// (live-session-screen.tsx:87-90): `readPublicConfig()` first, and `createComponentCApi` is called
// only when there is a config to give it OR the development fixture is active (which needs no
// config). Calling `createComponentCApi()` unconditionally with no config, as an earlier draft of
// this file did, throws inside `useMemo` during render whenever neither is true -- a render-time
// throw the component's own failure path can never catch, since it never runs. `api` can therefore
// be `null`, and every function below checks for that before using it.

import { Ionicons } from '@expo/vector-icons';
import { router } from 'expo-router';
import type { ComponentType } from 'react';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { ActivityIndicator, AppState, Image, Pressable, StyleSheet, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { createComponentCApi, getComponentCDevelopmentFixture } from '@/src/api/component-c-api';
import { takeCSessionPrefetch } from '@/src/features/c-session/c-session-prefetch-cache';
import { ApiClientError } from '@/src/api/errors';
import type { CNextTaskResponse, CreateCSessionRequest } from '@/src/api/generated/openapi-types';
import { useAuth } from '@/src/auth/auth-context';
import { AppText } from '@/src/components/app-text';
import { artwork } from '@/src/utils/artwork';
import { ScreenShell } from '@/src/components/screen-shell';
import { readPublicConfig } from '@/src/config/env';
import { resolveArchetypeSurface, type ArchetypeSurfaceProps } from '@/src/features/c-session/archetype-surfaces';
import { encodeActionPayload } from '@/src/features/c-session/archetypes/encode-action-payload';
import { HIT_SLOP, TOUCH_TARGET_MIN_SIZE } from '@/src/features/c-session/motor-constants';
import {
  classifySessionFailure,
  createSubmitGate,
  decideSessionBootstrap,
  isDuplicateSubmissionConflict,
  planSubmissionOutcome,
  planTaskSurface,
} from '@/src/features/c-session/c-session-logic';
import { AnswerFeedbackPanel } from '@/src/features/c-session/answer-feedback-panel';
import { ChallengeCompleteScreen } from '@/src/features/c-session/challenge-complete-screen';
import {
  isRunComplete,
  type ChallengeLength,
  type ChallengeRunResult,
} from '@/src/features/c-session/challenge-length';
import { FailClosedFrame } from '@/src/features/c-session/fail-closed-frame';
import { accentForGameFamily } from '@/src/features/c-session/game-family-accents';
import {
  GRADIENT_WASH_ALPHA,
  RotatingGradientBackground,
  SCREEN_GRADIENT_DURATION_MS,
  withAlpha,
} from '@/src/features/session/rotating-gradient-background';
import { pickBackgroundGradientColors } from '@/src/features/session/session-skill-accents';
import { nameForGameFamily } from '@/src/features/c-session/game-family-names';
import { NeutralMessageScreen } from '@/src/features/c-session/neutral-message-screen';
import { TechnicalBlockScreen } from '@/src/features/c-session/technical-block-screen';
import {
  recordActionSubmitted,
  recordBackgrounded,
  recordForegrounded,
  recordTaskOffered,
  recordTaskStarted,
  recordTechnicalIssue,
} from '@/src/features/c-session/telemetry';
import { colors, radius, spacing, typography } from '@/src/theme/tokens';
import { TASK_PANEL_PADDING } from '@/src/features/c-session/task-layout';

/**
 * The task's own DIFFICULTY level as a child-facing chip (owner instruction, 2026-10-10).
 *
 * This chip used to show `scaffold_state` (`C0`..`C4`, shown as "Lv 1".."Lv 5"), which is the
 * SUPPORT level -- how much help the engine is giving -- not how hard the game is. Read as "Lv N"
 * on the card it looked like the game's level and was not, so it is now sourced from
 * `CNextTaskResponse.difficulty_level`, the integer the adaptation engine actually moves up and
 * down per task (`c_task_instances.difficulty_level`).
 *
 * NO "N of 3", deliberately. The governed bundle declares no maximum: it carries
 * `familiarization_difficulty_level: 1`, `fallback_difficulty_level: 1` and caps of 2, and no
 * catalogue template carries a difficulty field at all. Printing a denominator would be the UI
 * asserting a bound the approved configuration does not define -- the same mistake as rendering a
 * prior as evidence. If a ceiling is ever approved, it belongs in the bundle and should be read
 * from the server, not written here.
 *
 * Tolerant in the same spirit as the scaffold label it replaces: anything that is not a positive
 * integer yields `null` and the chip is simply not rendered, never a crash or a raw value leaking
 * to the screen.
 */
function difficultyLevelLabel(difficultyLevel: number): string | null {
  if (!Number.isInteger(difficultyLevel) || difficultyLevel < 1) return null;
  return `Lv ${difficultyLevel}`;
}

/**
 * One height for all three controls in the chrome band -- exit, game name, difficulty level -- so
 * they read as one row rather than three separately-sized objects (owner instruction, 2026-10-10).
 *
 * WHY A SHARED NUMBER RATHER THAN PADDING. Each was previously sized by its own content: the pills
 * by their text's line height plus padding, the exit button by `TOUCH_TARGET_MIN_SIZE`. That made
 * the exit button noticeably taller than its neighbours, and left the two pills a hair apart from
 * each other once only one of them carried a border. A single explicit height is what actually
 * guarantees they match; it is a `minHeight`, so text that grows under OS font scaling still
 * expands the pill rather than being clipped by it.
 *
 * 34 is the tallest of the three natural heights (the exit icon's 22 plus its padding and border),
 * so nothing has to shrink to meet it.
 *
 * THE EXIT BUTTON'S TOUCH TARGET IS NOT REDUCED BY THIS. It no longer fills
 * `TOUCH_TARGET_MIN_SIZE` (48) visually, but it carries `HIT_SLOP` of 8 on every side, so its
 * tappable area is 34 + 16 = 50 -- still above the 48 minimum that constant exists to enforce.
 * Shrinking the visual without the hit slop would be a real motor-accessibility regression in a
 * tool used by Grade 2-3 children; do not remove one without the other.
 */
const CHROME_CONTROL_HEIGHT = 34;

/**
 * How hard the task card's background pattern is blurred while an answer verdict is on screen.
 *
 * Applied as the Image's own `blurRadius`, never as an overlay -- see the note at that Image for
 * why that distinction is what finally got this right. 10px is enough to push the pattern clearly
 * out of focus behind the verdict without losing its colour, which is what separates "the card is
 * blurred" from "the card is covered".
 */
const TASK_BACKGROUND_FEEDBACK_BLUR = 10;

/**
 * One lap of the task card's own pink/green wash, in milliseconds.
 *
 * Exactly a QUARTER of the screen background's lap (owner instruction: "4 times faster"), derived
 * from that constant rather than written as a second literal -- so changing the screen's speed
 * keeps the 4:1 relationship instead of silently breaking it.
 */
const TASK_CARD_GRADIENT_DURATION_MS = SCREEN_GRADIENT_DURATION_MS / 4;

export type CSessionScreenProps = {
  // Not decided or invented by this screen -- see c-session-logic.ts's decideSessionBootstrap
  // doc comment. Optional and, in this batch, ordinarily absent: nothing upstream supplies them
  // yet, so the create path fails closed to the "not ready" screen rather than fabricating either
  // value.
  grade?: number;
  sessionMode?: CreateCSessionRequest['session_mode'];
  /** How long this run lasts, chosen by the child on c-prepare. Validated at the route boundary,
   * so this is always a real value -- `endless` is the default and is exactly the behaviour that
   * existed before the choice did. */
  challenge: ChallengeLength;
};

type Phase =
  | { kind: 'loading' }
  // `attempt` and `feedback` extend the existing `task` phase rather than adding a sibling phase,
  // because a retry stays ON this same task instance -- it is not a new task, so it does not
  // belong to a new phase. `feedback === null` renders the archetype surface (today's behaviour,
  // unchanged); `feedback !== null` renders `AnswerFeedbackPanel` INSTEAD OF the surface -- see
  // that file's own header for why that placement, not an overlay, is load-bearing. `attempt`
  // increments only on a "try again" press and is folded into the surface's remount `key` below,
  // so a wrong answer never survives visibly into the next attempt, mirroring `19d4530`'s fix for
  // the same problem across TASKS rather than across attempts on one task.
  | {
      kind: 'task';
      task: CNextTaskResponse;
      Surface: ComponentType<ArchetypeSurfaceProps>;
      attempt: number;
      feedback: { matched: boolean; scaffoldLevel: string } | null;
    }
  | { kind: 'fail-closed'; supportCode: string | null }
  | { kind: 'technical-block'; supportCode: string | null }
  | { kind: 'failure'; supportCode: string | null; copy: { title: string; detail: string } }
  | { kind: 'not-ready' }
  // A fixed-length run that reached its last task. Reachable only when `challenge` is 'challenge';
  // an endless run has no terminal phase, by definition.
  | { kind: 'run-complete'; taskCount: number; results: readonly ChallengeRunResult[] };

/** The panel's warm ground, matching the Play hub's card so a game opens into the same object the
 *  menu showed. Only the colour BEHIND the card changes per family. */
const TASK_PANEL_BACKGROUND = '#fffdf6';

/**
 * The task card's shape, as width ÷ height. Pinned so a background image has ONE ratio to be
 * authored against (2026-10-10, owner decision).
 *
 * WHY IT WAS PINNED. The card used to be `width: '90%', height: '90%'` of its canvas, so its ratio
 * was whatever the viewport happened to be: roughly 0.42–0.62 across portrait-locked phones and
 * tablets, and on WEB — where `app.json`'s `"orientation": "portrait"` does not apply — anywhere
 * from about 0.38 in a tall window to 1.25 in a short, wide one, at which point the card is wider
 * than it is tall. No single image can cover that range without being cropped differently on every
 * screen, which is precisely what you cannot design artwork against.
 *
 * WHY 0.5 SPECIFICALLY. It sits in the middle of the portrait range and within a couple of percent
 * of what phones already rendered (~0.52), so pinning it changes the familiar shape as little as
 * possible while making it predictable everywhere else.
 *
 * WHAT THIS COSTS. On a tall window the card no longer stretches to fill the height; it is centred
 * with space above and below. That is the deliberate trade — a consistent canvas is worth more here
 * than filling every pixel, because the alternative is artwork that crops unpredictably.
 *
 * `maxHeight: '90%'` still bounds it, so on a SHORT window the card shrinks (keeping this ratio)
 * rather than overflowing its canvas.
 */
const TASK_PANEL_ASPECT_RATIO = 0.5;

// The screen's own ground, BEHIND the card (2026-08-26 request): a fixed neutral, not the family
// accent -- the accent moved to the card's own border instead (`taskPanel.borderColor`, below), so
// each family is still visually distinguished, just on the card's edge rather than filling the
// whole screen.
const TASK_SCREEN_BACKGROUND = '#F4F4F6';

const FAILURE_COPY: Record<'authentication' | 'network' | 'technical', { title: string; detail: string }> = {
  authentication: { title: 'Sign-in needed', detail: 'Ask a grown-up to help you sign in again.' },
  network: { title: 'No connection', detail: 'Check the internet and try again in a moment.' },
  technical: { title: 'Something went wrong', detail: 'Try again in a little while.' },
};

export function CSessionScreen({ challenge, grade, sessionMode }: CSessionScreenProps) {
  const { getAccessToken, me } = useAuth();
  const subject = me?.principal.user_id ?? null;
  const configResult = useMemo(() => readPublicConfig(), []);
  // Null-safe by construction: createComponentCApi() with no config and no active fixture throws
  // (component-c-api.ts:145-147), and calling that inside useMemo during render would crash the
  // component tree rather than route through this screen's own failure path. The fixture check
  // needs no config at all, so it is tried before treating a missing config as fatal.
  const api = useMemo(() => {
    if (configResult.config) return createComponentCApi(configResult.config);
    if (getComponentCDevelopmentFixture()) return createComponentCApi();
    return null;
  }, [configResult.config]);
  const [phase, setPhase] = useState<Phase>({ kind: 'loading' });
  /** Tasks this run has FINISHED (matched and advanced past), not tasks served. A ref rather than
   * state because nothing renders it mid-run: reading it in advanceToNextTask must see the value
   * the previous advance wrote, and a state update scheduled asynchronously would not guarantee
   * that. It is deliberately NOT restored on resume -- see the note in challenge-length.ts on why
   * `isRunComplete` compares with `>=`. */
  const completedTasksRef = useRef(0);
  /** One row per finished game, in play order, for the completion card's list. Refs for the same
   * reason as the counter above: these are written from callbacks that must see the previous
   * write, and nothing renders them until the run ends. */
  const runResultsRef = useRef<ChallengeRunResult[]>([]);
  const currentTaskNameRef = useRef('');
  /** When the current question went on screen. The run card reports TIME rather than correctness,
   * because a C task only advances once the answer matches -- see ChallengeRunResult's header. */
  const currentTaskStartedAtRef = useRef(0);
  /** The elapsed time captured at the moment the answer was ACCEPTED, so the clock stops there
   * rather than running on through the feedback panel and the child's "Next" press. Null between
   * questions. */
  const acceptedElapsedMsRef = useRef<number | null>(null);
  const cSessionIdRef = useRef<string | null>(null);
  const mountedRef = useRef(true);
  const backgroundedRef = useRef(false);
  // One gate per mounted screen. `useRef` so the cell survives re-renders and, critically, so
  // reading it is synchronous -- a `useState` flag cannot close a same-frame double-tap race.
  const submitGateRef = useRef(createSubmitGate());
  /**
   * The next task, already requested while the child reads their feedback (FE-004, 2026-10-09).
   * Keyed by the instance it was fetched AFTER, so a stale entry can never be served for the
   * wrong task. See the pre-advance effect below for when it is filled and why only then.
   */
  const nextTaskPrefetchRef = useRef<{
    cSessionId: string;
    afterInstanceId: string;
    promise: Promise<CNextTaskResponse>;
  } | null>(null);
  // Render-only mirror of the gate, for the in-flight overlay. Never read to decide whether a
  // submission may proceed; `submitGateRef` alone owns that.
  const [submitting, setSubmitting] = useState(false);

  const goHome = useCallback(() => router.replace('/(learner)/home'), []);

  const routeFailure = useCallback((error: unknown) => {
    if (!mountedRef.current) return;
    const supportCode = error instanceof ApiClientError ? error.requestId ?? null : null;
    const kind = classifySessionFailure(error);
    if (kind === 'network') {
      recordTechnicalIssue(
        error instanceof ApiClientError && error.kind === 'timeout' ? 'timeout' : 'network',
      );
    }
    if (kind === 'technical-block') {
      setPhase({ kind: 'technical-block', supportCode });
      return;
    }
    setPhase({ kind: 'failure', supportCode, copy: FAILURE_COPY[kind] });
  }, []);

  // The half of `loadNextTask` that runs AFTER a task is in hand, regardless of whether it just
  // came off the wire or arrived pre-fetched (see the cache check in `bootstrap()` below) -- split
  // out so neither path can silently diverge on telemetry or fail-closed handling.
  const presentTask = useCallback((task: CNextTaskResponse) => {
    if (!mountedRef.current) return;
    recordTaskOffered();
    // Both fail-closed reasons (unresolvable template; resolved archetype with no registered
    // surface) route to the same phase and support code here -- planTaskSurface keeps them
    // distinguishable in its own return value so a test can prove they stay separate, even
    // though the screen has no reason to render them differently.
    const surfacePlan = planTaskSurface(task, resolveArchetypeSurface);
    if (surfacePlan.kind === 'fail-closed') {
      setPhase({ kind: 'fail-closed', supportCode: task.request_id });
      return;
    }
    recordTaskStarted();
    // The name is captured HERE, while the task is in hand. Reading it at advance time instead
    // would mean reaching for a task the screen has already moved past.
    currentTaskNameRef.current = nameForGameFamily(task.game_family_id);
    // THE CLOCK STARTS WHEN THE QUESTION IS PUT ON SCREEN, not when it was fetched: the first task
    // is pre-fetched while the prep card is still up, and timing from the request would bill the
    // child for a wait they never saw.
    currentTaskStartedAtRef.current = Date.now();
    acceptedElapsedMsRef.current = null;
    setPhase({
      kind: 'task',
      task: surfacePlan.task,
      Surface: surfacePlan.Surface,
      attempt: 0,
      feedback: null,
    });
  }, []);

  const loadNextTask = useCallback(
    async (cSessionId: string, accessToken: string) => {
      if (!api) return;
      try {
        // Normally already resolved by the pre-advance effect below, so this is a read rather
        // than a wait. A prefetch for a DIFFERENT instance is ignored (not reused), and a
        // rejected one falls through to a fresh request under the same semantics it would have
        // had if no prefetch existed.
        const parked = nextTaskPrefetchRef.current;
        nextTaskPrefetchRef.current = null;
        const task =
          parked && parked.cSessionId === cSessionId
            ? await parked.promise.catch(() => api.nextTask(cSessionId, accessToken))
            : await api.nextTask(cSessionId, accessToken);
        presentTask(task);
      } catch (error) {
        routeFailure(error);
      }
    },
    [api, presentTask, routeFailure],
  );

  const handleSubmit = useCallback(
    async (
      cSessionId: string,
      task: CNextTaskResponse,
      accessToken: string,
      values: Record<string, unknown>,
    ) => {
      if (!api) return;
      const payload = encodeActionPayload(task.valid_action_space, values);
      if (payload === null) return;
      try {
        const result = await api.submitAction(
          cSessionId,
          task.c_task_instance_id,
          { action_payload: payload },
          accessToken,
        );
        recordActionSubmitted();
        // Neither branch calls `loadNextTask` directly, even on a matched answer -- advancing is
        // always the child's own "Next" press (see answer-feedback-panel.tsx's header), never
        // automatic. `outcome` only decides what the panel SHOWS; `planSubmissionOutcome` computes
        // nothing about correctness itself, it relays `result.response_matched` and
        // `result.scaffold_level` exactly as the server sent them.
        const outcome = planSubmissionOutcome(result);
        // Recorded here rather than inside the state updater below: a `setPhase` callback can be
        // invoked more than once, and a side effect written inside one would double-count.
        //
        // A WRONG ANSWER DOES NOT STOP THE CLOCK. The child stays on this same task and tries
        // again, so the question is not over; only an accepted answer ends it, and the time then
        // covers every attempt it took.
        if (outcome.kind === 'advance') {
          acceptedElapsedMsRef.current = Date.now() - currentTaskStartedAtRef.current;
        }
        setPhase((prev) =>
          prev.kind === 'task'
            ? { ...prev, feedback: { matched: outcome.kind === 'advance', scaffoldLevel: result.scaffold_level } }
            : prev,
        );
      } catch (error) {
        // The benign duplicate: this instance already carries a terminal event, so the child's
        // earlier answer landed and was scored. Show them that outcome instead of a technical
        // failure screen -- same `feedback` field, same AnswerFeedbackPanel, same "Next" press to
        // advance, so this reuses the success path's own machinery rather than adding a parallel
        // one. `matched: true` is sound because `completed_correct` is the only wired terminal
        // reason (see isDuplicateSubmissionConflict's header for the ruling that guarantees it).
        //
        // `scaffold_level` is unavailable here -- there is no result body on an error -- so the
        // task's own server-sent `scaffold_state` is relayed rather than a value invented in this
        // file. It is not rendered on the matched branch anyway; AnswerFeedbackPanel shows the
        // support level only when `matched` is false.
        if (isDuplicateSubmissionConflict(error)) {
          // The benign duplicate is an ACCEPTED answer too (see below), so it ends the question
          // and stops the clock exactly as the success path does.
          acceptedElapsedMsRef.current = Date.now() - currentTaskStartedAtRef.current;
          setPhase((prev) =>
            prev.kind === 'task'
              ? { ...prev, feedback: { matched: true, scaffoldLevel: prev.task.scaffold_state } }
              : prev,
          );
          return;
        }
        routeFailure(error);
      }
    },
    [api, routeFailure],
  );

  /**
   * PRE-ADVANCE (FE-004, 2026-10-09). The moment a CORRECT answer is on screen, ask for the next
   * task -- while the child is still reading "Nice work!". By the time they press Next the
   * response is normally already in hand, so the next task appears instead of a loading state.
   *
   * Component B has done this since 2026-09-27 (live-session-screen.tsx's own PRE-ADVANCE effect);
   * C simply never got it, so every "Next" press paid a full round trip the child watched.
   *
   * ONLY ON A MATCHED ANSWER, and the asymmetry with B is worth stating because it runs the other
   * way. B must not pre-advance on a wrong answer because advancing CLOSES the opportunity and the
   * child may still "TRY AGAIN" on it. Here, `retryTask` stays on the same instance and makes no
   * network call at all, so there is nothing to close -- but `next_task` would still be the wrong
   * call: only `completed_correct` writes a terminal event (`task_service.py`), so after a wrong
   * answer the instance is still unterminated and `next_task` RESUMES it, returning the same task
   * we already have. That is a wasted round trip, not a hazard. Restricting to matched keeps it
   * both useful and pointless-free.
   *
   * WHY MINTING EARLY IS SAFE HERE. Component C has NO answering deadline at all: there is no
   * deadline or expiry column on any `c_task_*` table -- `timeout_no_response` is a gameplay-event
   * REASON, not a server-enforced clock. So a task minted a few seconds early costs the child
   * nothing, and there is no equivalent of B's anchoring step to get right.
   *
   * (Corrected 2026-10-10. This paragraph used to add that B's `selectOpportunity` "lights a
   * five-minute `timeout_deadline_utc` that is never reset, so every second between the fetch and
   * the child seeing the question is spent from their answering budget". That was wrong -- B
   * re-anchors the deadline at PRESENTATION via `anchor_presentation`, so prefetch time is not
   * charged to the child. The contrast with C still stands on the narrower, true ground above: B
   * has a deadline to anchor, C has none.)
   *
   * AND IF THE CHILD NEVER PLAYS IT: the minted instance carries no terminal event, so the next
   * `next_task` call RESUMES it rather than minting again (the resume-instead-of-mint path). An
   * abandoned pre-advance is picked up where it was left, not leaked and not duplicated.
   *
   * Best-effort: the rejection is parked here and handled by `loadNextTask`, which falls back to a
   * fresh request. A failed pre-advance costs nothing.
   */
  useEffect(() => {
    if (!api || phase.kind !== 'task' || phase.feedback?.matched !== true) return;
    const cSessionId = cSessionIdRef.current;
    if (!cSessionId) return;
    const afterInstanceId = phase.task.c_task_instance_id;
    if (nextTaskPrefetchRef.current?.afterInstanceId === afterInstanceId) return;

    let cancelled = false;
    void (async () => {
      const accessToken = await getAccessToken();
      // No token is not an error worth routing here: the child is looking at their verdict, and
      // `advanceToNextTask` resolves a token of its own and owns that failure.
      if (!accessToken || cancelled) return;
      const promise = api.nextTask(cSessionId, accessToken);
      // Parked, not handled here -- `loadNextTask` awaits this same promise and owns every
      // outcome. The no-op catch only stops an unhandled-rejection warning in the meantime.
      promise.catch(() => undefined);
      if (cancelled) return;
      nextTaskPrefetchRef.current = { afterInstanceId, cSessionId, promise };
    })();

    return () => {
      cancelled = true;
    };
  }, [api, getAccessToken, phase]);

  // Fired by AnswerFeedbackPanel's "Try again" -- clears the panel and bumps `attempt`, which is
  // folded into the surface's remount `key` below so the wrong answer does not survive visibly
  // into the fresh attempt. Stays on the SAME task instance; no network call, since nothing about
  // the task itself changed.
  const retryTask = useCallback(() => {
    setPhase((prev) =>
      prev.kind === 'task' ? { ...prev, feedback: null, attempt: prev.attempt + 1 } : prev,
    );
  }, []);

  // Fired by AnswerFeedbackPanel's "Next" -- the one place a matched answer actually advances the
  // session, mirroring submitFromSurface's own token/session-id handling exactly.
  const advanceToNextTask = useCallback(async () => {
    const cSessionId = cSessionIdRef.current;
    if (!cSessionId) return;
    const accessToken = await getAccessToken();
    if (!accessToken) {
      routeFailure(new ApiClientError('unauthenticated', 'No access token is available.'));
      return;
    }

    // COUNTED HERE, AND ONLY HERE. This callback fires on AnswerFeedbackPanel's "Next", which is
    // reachable only after a MATCHED answer -- the one path on which a task is actually finished.
    // Counting at submit instead would count wrong answers, and counting in loadNextTask would
    // count the task the child is about to be GIVEN rather than the one they just completed.
    const completed = completedTasksRef.current + 1;
    completedTasksRef.current = completed;
    runResultsRef.current = [
      ...runResultsRef.current,
      {
        // Falls back to timing up to this press if no acceptance was recorded, so a row always
        // carries a real duration rather than a zero that would quietly shrink the total.
        ms: acceptedElapsedMsRef.current ?? Date.now() - currentTaskStartedAtRef.current,
        name: currentTaskNameRef.current,
      },
    ];
    acceptedElapsedMsRef.current = null;

    if (isRunComplete(challenge, completed)) {
      // The run the child asked for is over, so the session is told it is over. This is the first
      // caller `completeSession` has ever had: until now a Component C session was simply left
      // open when the child walked away, because nothing in the app had a reason to end one.
      //
      // BEST EFFORT, DELIBERATELY. If the call fails the child still sees their finished run --
      // the request is bookkeeping (attendance), and a network error on it is not something to
      // put in front of a seven-year-old who just completed ten games. A session left open by a
      // failure is the same state every C session was in before this existed, and the next entry
      // resumes it exactly as it always did.
      try {
        await api?.completeSession(cSessionId, { attendance_status: 'attended' }, accessToken);
      } catch {
        // Intentionally swallowed; see above.
      }
      setPhase({ kind: 'run-complete', results: runResultsRef.current, taskCount: completed });
      return;
    }

    await loadNextTask(cSessionId, accessToken);
  }, [api, challenge, getAccessToken, loadNextTask, routeFailure]);

  // The bridge from an archetype surface's own onSubmit (raw per-key values, no session/task
  // plumbing -- see ArchetypeSurfaceProps) to handleSubmit's full signature. Reads cSessionId from
  // the ref and re-fetches a fresh access token per submission rather than closing over a stale one.
  const submitFromSurface = useCallback(
    async (values: Record<string, unknown>) => {
      const cSessionId = cSessionIdRef.current;
      if (!cSessionId || phase.kind !== 'task') return;
      // The re-entry guard, taken BEFORE the first `await`. Placing it after any await would
      // reopen the exact race it exists to close: both taps would reach the suspension point
      // before either had claimed the gate. `submitGateRef` holds a synchronous cell for the same
      // reason it is not `useState` -- see createSubmitGate's own header.
      if (!submitGateRef.current.tryEnter()) return;
      setSubmitting(true);
      try {
        const accessToken = await getAccessToken();
        if (!accessToken) {
          routeFailure(new ApiClientError('unauthenticated', 'No access token is available.'));
          return;
        }
        await handleSubmit(cSessionId, phase.task, accessToken, values);
      } finally {
        // `finally`, not the happy path: handleSubmit routes its own failures rather than
        // rethrowing, but an unauthenticated early return and any future throw must still release
        // the gate. A gate left closed is a permanently dead SUBMIT button with no error shown.
        submitGateRef.current.release();
        if (mountedRef.current) setSubmitting(false);
      }
    },
    [getAccessToken, handleSubmit, phase, routeFailure],
  );

  const bootstrap = useCallback(async () => {
    if (!api) return;
    // A prefetch started on Home's own Play press (requestPlay, adventure-charge-context.tsx) has
    // already settled by the time navigation lands here (that press awaits it before navigating),
    // so this never shows its own 'loading' phase for a request Home already made -- the blur
    // overlay on Home IS the loading state, for the entire wait. A miss (nothing cached: a deep
    // link straight to /c-session, or the prefetch itself resolved 'not ready'/failed) falls
    // through to the full bootstrap below, unchanged.
    if (subject) {
      const prefetch = takeCSessionPrefetch(subject);
      if (prefetch) {
        try {
          const result = await prefetch;
          if (result) {
            cSessionIdRef.current = result.cSessionId;
            presentTask(result.task);
            return;
          }
        } catch {
          // Falls through -- the normal bootstrap below is the real fallback, not a second attempt
          // at whatever failed here.
        }
      }
    }
    setPhase({ kind: 'loading' });
    try {
      const accessToken = await getAccessToken();
      if (!accessToken) throw new ApiClientError('unauthenticated', 'No access token is available.');
      const active = await api.getActiveSession(accessToken);
      const decision = decideSessionBootstrap(active, grade, sessionMode);
      if (decision.action === 'not-ready') {
        if (!mountedRef.current) return;
        setPhase({ kind: 'not-ready' });
        return;
      }
      if (decision.action === 'resume') {
        cSessionIdRef.current = decision.cSessionId;
        await loadNextTask(decision.cSessionId, accessToken);
        return;
      }
      const created = await api.createSession(decision.body, accessToken);
      cSessionIdRef.current = created.c_session_id;
      await loadNextTask(created.c_session_id, accessToken);
    } catch (error) {
      routeFailure(error);
    }
  }, [api, getAccessToken, grade, loadNextTask, presentTask, routeFailure, sessionMode, subject]);

  // Leaving is never conditional on the background `abandonSession` cleanup call succeeding -- a
  // child pressing X wants to leave the task NOW, and stranding them on a "Something went wrong"
  // screen because that cleanup call failed (which, under the development fixture, it always does
  // by design -- 10.0b-i/-fix) is a worse outcome than a session the server cleans up some other
  // way. The call is still attempted, for the real-backend case where it matters, but its result
  // (success or failure) never changes where this takes the child: home, always -- the same
  // destination every other exit path on this screen already uses (`goHome`), landing on the
  // "Your Session" card rather than the hero, via the SAME catch-all Home already relies on for
  // "any way of leaving Home" (learner-home-screen.tsx's own unmount effect). There is no
  // game-hub menu to return to any more -- removed on owner instruction (2026-08-27); Play
  // navigates straight into Component C and X now returns straight to home the same way.
  const leaveSession = useCallback(async () => {
    // Read the id BEFORE navigating: `goHome` starts tearing this screen down, and the ref is the
    // only place the id survives.
    const cSessionId = cSessionIdRef.current;

    // NAVIGATE FIRST, ABANDON AFTER (2026-10-10, owner-reported lag).
    //
    // This used to `await getAccessToken()` and then `await api.abandonSession(...)` before calling
    // `goHome()`, so the X button did nothing visible until the server answered. Against the remote
    // pooler that is seconds, during which a child has tapped a button and watched the screen
    // ignore them -- the exact pattern that produces repeated taps.
    //
    // Nothing about leaving depends on that call succeeding: its errors were ALREADY swallowed, so
    // the screen has always navigated whether or not the server was told. Making it fire-and-forget
    // changes when the child sees the result, not what the system does.
    //
    // THE REQUEST IS NOT CANCELLED BY UNMOUNTING. A fetch already in flight continues after the
    // component goes, so the abandon still reaches the server on the normal path; it is simply no
    // longer in front of the child. It targets one specific `cSessionId`, so a late arrival cannot
    // touch a session the child starts next.
    goHome();

    if (cSessionId && api) {
      try {
        const accessToken = await getAccessToken();
        if (accessToken) {
          await api.abandonSession(cSessionId, accessToken);
        }
      } catch {
        // Swallowed on purpose -- see the comment above this function.
      }
    }
  }, [api, getAccessToken, goHome]);

  useEffect(() => {
    mountedRef.current = true;
    if (!api) {
      // No config and no active fixture -- the same "technical" bucket an unconfigured B screen
      // routes to (live-session-screen.tsx:425-427), reached through this screen's own failure
      // path rather than a render-time throw.
      setPhase({ kind: 'failure', supportCode: null, copy: FAILURE_COPY.technical });
    } else {
      void bootstrap();
    }
    return () => {
      mountedRef.current = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [api]);

  useEffect(() => {
    const subscription = AppState.addEventListener('change', (state) => {
      if (state === 'active' && backgroundedRef.current) {
        backgroundedRef.current = false;
        recordForegrounded();
      } else if (state !== 'active' && !backgroundedRef.current) {
        backgroundedRef.current = true;
        recordBackgrounded();
      }
    });
    return () => subscription.remove();
  }, []);

  // Computed HERE, above every early return below, because `useMemo` is a Hook: Hooks must run in
  // the same order on every render, so this cannot live down beside the task render where it is
  // used. `null` outside the task phase is what skips re-picking -- the dependency array only
  // changes, and `pickBackgroundGradientColors` only re-runs, on an actual new task instance,
  // never on an unrelated re-render (a feedback panel, a retry). Component B's own gradient
  // carries the identical note for the identical reason.
  const taskAccent = phase.kind === 'task' ? accentForGameFamily(phase.task.game_family_id) : null;
  const taskInstanceId = phase.kind === 'task' ? phase.task.c_task_instance_id : null;
  const gradientColors = useMemo(
    () => (taskAccent ? pickBackgroundGradientColors(taskAccent) : (['#ffffff', '#ffffff'] as const)),
    // `taskInstanceId` is the re-pick trigger and is deliberately listed although the memo body
    // does not read it -- lint flags it, and Component B's own gradient memo carries the same
    // flagged dependency for the same reason. Removing it would leave one background for the
    // whole session; reading it inside the body would be a lie about what the value depends on.
    [taskAccent, taskInstanceId],
  );

  if (phase.kind === 'loading') {
    return (
      <ScreenShell centered>
        <ActivityIndicator color={colors.primary} size="large" />
        <AppText align="center" style={styles.muted}>
          Getting your session ready…
        </AppText>
      </ScreenShell>
    );
  }

  if (phase.kind === 'run-complete') {
    return (
      // One way off this card: Back to Home (owner request). The "Play again" control that used
      // to sit beside it is gone -- Play on the tab bar is the way into another run, and it goes
      // through the length choice rather than silently repeating the last one.
      <ChallengeCompleteScreen onExit={goHome} results={phase.results} taskCount={phase.taskCount} />
    );
  }

  if (phase.kind === 'not-ready') {
    return (
      <NeutralMessageScreen
        detail="This session isn't ready yet. Please check back soon."
        onExit={goHome}
        supportCode={null}
        title="Not ready yet"
      />
    );
  }

  if (phase.kind === 'fail-closed') {
    return <FailClosedFrame onExit={goHome} supportCode={phase.supportCode} />;
  }

  if (phase.kind === 'technical-block') {
    return <TechnicalBlockScreen onExit={goHome} supportCode={phase.supportCode} />;
  }

  if (phase.kind === 'failure') {
    return (
      <NeutralMessageScreen
        detail={phase.copy.detail}
        onExit={goHome}
        supportCode={phase.supportCode}
        title={phase.copy.title}
      />
    );
  }

  // phase.kind === 'task'. Renders whichever archetype surface resolveArchetypeSurface produced
  // for this task, per its own ArchetypeSurfaceProps contract (task + onSubmit only -- no exit
  // affordance in that contract, which is why the exit control lives in this wrapper rather than
  // being threaded into the surface itself).
  const { Surface, attempt, feedback, task } = phase;
  // Written as a truthiness check, NOT `feedback === null ? ... : ...`, on purpose:
  // c-feedback-replaces-surface.test.ts anchors on the FIRST `feedback <comparison> null` in this
  // file and then requires the ternary around it to be the Surface/AnswerFeedbackPanel branch. An
  // earlier comparison here would anchor that scan on the wrong occurrence and fail a guard whose
  // real subject -- the two never rendering together -- is untouched. Keep it this way.
  const backgroundBlurRadius = feedback ? TASK_BACKGROUND_FEEDBACK_BLUR : 0;
  // The ground behind the task panel is the accent of the family this task came from, read from
  // the shared table by `game_family_id` -- a required wire field, never a literal here, so Number
  // Path opens on its own blue and every other family on its own colour without this file naming
  // any of them. An unknown id yields a neutral, which is a background choice and not a
  // fail-closed condition; see game-family-accents.ts.
  const accent = accentForGameFamily(task.game_family_id);
  return (
    <SafeAreaView style={[styles.taskSafeArea, { backgroundColor: TASK_SCREEN_BACKGROUND }]}>
      {/* The same faded, slowly rotating wash Component B's task screen sits on -- shared
          component, so the two cannot drift (rotating-gradient-background.tsx). Two of the five
          game-type colours, re-picked per task and never including THIS task's own family accent,
          so the panel's accent border always reads against the background rather than blending
          into it. The SafeAreaView's own background stays underneath: this is a wash over it. */}
      <RotatingGradientBackground
        colors={[
          withAlpha(gradientColors[0], GRADIENT_WASH_ALPHA),
          withAlpha(gradientColors[1], GRADIENT_WASH_ALPHA),
        ]}
      />
      {/* Mirrors the Play hub's own outer shape (game-hub-screen.tsx's `mobileCanvas`): a flex:1,
          alignSelf-centred, maxWidth-500 canvas, stretched by its SafeAreaView ancestor rather than
          centred by it. The hub's SafeAreaView sets no alignItems (default 'stretch'); this one
          previously set `alignItems: 'center'` directly, which on web only shrink-wraps the child's
          CROSS axis but left the panel visibly short of full height in practice -- matching the
          hub's exact two-level shape (stretch, then centre-via-alignSelf one level in) is what the
          hub itself relies on to fill the screen, so the task canvas does the same rather than
          trying a different way to reach the same box. */}
      <View style={styles.taskCanvas}>
        {/* SESSION CHROME, ABOVE THE CARD (owner instruction, 2026-10-10).

            Exit, game-family name and difficulty level used to float absolutely INSIDE the card,
            overlapping its top corners. They are not part of the task -- they are the frame around
            it -- so they now sit in the space between the screen top and the card, which the
            pinned 1:2 ratio created. The band is `flex: 1` with its content centred, and a
            matching `flex: 1` spacer sits below the card, so the chrome lands in the MIDDLE of the
            top gap while the card itself stays centred on the screen.

            THE PILL IS CENTRED ON THE CARD'S AXIS, not between its neighbours: the two side cells
            are both `flex: 1`, so they always claim equal width no matter how wide the exit button
            or the level chip are, leaving the middle cell dead centre. Using `space-between` would
            have let the pill drift whenever the chip's text changed width ("Lv 2" vs none). */}
        <View style={styles.taskChromeBand}>
          <View style={styles.taskChromeRow}>
            <View style={[styles.taskChromeSide, styles.taskChromeSideStart]}>
              <Pressable
                accessibilityLabel="Leave session"
                accessibilityRole="button"
                hitSlop={HIT_SLOP}
                onPress={() => void leaveSession()}
                style={({ pressed }) => [styles.taskExitButton, pressed && styles.pressed]}>
                <Ionicons color={colors.textSecondary} name="close" size={22} />
              </Pressable>
            </View>
            <View pointerEvents="none" style={[styles.familyPill, { borderColor: accent }]}>
              <AppText style={[styles.familyPillText, { color: accent }]}>
                {nameForGameFamily(task.game_family_id)}
              </AppText>
            </View>
            <View style={[styles.taskChromeSide, styles.taskChromeSideEnd]}>
              {/* This task's DIFFICULTY level, straight from the server -- not the scaffold/support
                  level it once showed, and no denominator (see difficultyLevelLabel). */}
              {difficultyLevelLabel(task.difficulty_level) !== null ? (
                <View style={[styles.levelChip, { borderColor: accent }]}>
                  <AppText style={[styles.levelChipText, { color: accent }]}>
                    {difficultyLevelLabel(task.difficulty_level)}
                  </AppText>
                </View>
              ) : null}
            </View>
          </View>
        </View>
        {/* The task panel, accent-bordered on its warm ground -- the same big card Component B
            draws, and restored here on 2026-09-28 after briefly being removed. What DID change
            that day stays: `TaskPromptCard` inside each archetype surface now gives the question
            and its items their own white card within this one, so the two components nest the same
            way -- outer task panel, inner question card, answer controls on the panel's ground. */}
        <View style={[styles.taskPanel, { borderColor: accent }]}>
            {/* The card's background pattern, authored at this card's exact 1:2 ratio so it fills
                edge to edge with no cropping (see TASK_PANEL_ASPECT_RATIO).

                DRAWN AS AN ABSOLUTE CHILD, NOT VIA `overflow: 'hidden'` ON THE PANEL. The obvious
                way to clip an image to a rounded card is to hide overflow on the parent -- but
                this panel also carries `shadowColor`/`shadowOffset`/`shadowOpacity`, and on iOS a
                view with both a shadow and clipped overflow loses the shadow entirely. Giving the
                image its own `borderRadius` clips it without the parent ever clipping anything, so
                the card keeps its elevation on every platform.

                The radius is the panel's MINUS its 4pt border: `absoluteFillObject` insets to the
                padding box (inside the border), where the corner curve is tighter than the outer
                edge. Using radius.lg here would leave a hairline of background showing through the
                corners.

                `pointerEvents="none"` so it can never intercept a tap meant for the answer
                controls above it; first child, so everything else paints on top. */}
          <View pointerEvents="none" style={styles.taskPanelBackground}>
            {/* BLURRED WHILE A VERDICT IS SHOWING (owner instruction, 2026-10-10).
                
                The blur belongs to the IMAGE, not to a layer over it. Three earlier attempts put
                an expo-blur scrim above the card instead -- a band, then a frosted popup, then a
                full-area overlay -- and every one of them tinted what it covered, because
                expo-blur's web build couples its blur radius and its white backgroundColor to the
                same `intensity`. That is what kept washing the card's pink out to near-white.
                
                `blurRadius` has no such coupling: it is a property of the image itself (CSS
                `filter: blur()` on web, native on iOS and Android), so the pattern keeps its own
                colour and simply goes soft. It also works on ANDROID, where expo-blur does not
                blur at all -- so for the first time this effect is the same on every platform
                rather than silently degrading to a flat scrim.
                
                The verdict card above it therefore needs no background and no blur layer of its
                own; it is fully transparent, which is the whole point. */}
            <Image
              blurRadius={backgroundBlurRadius}
              resizeMode="cover"
              source={artwork.cTaskBackground}
              style={styles.taskPanelBackgroundImage}
            />
            {/* A PINK-AND-GREEN WASH OVER THE PATTERN, turning the other way (owner instruction,
                2026-10-10).
                
                Same component as the screen behind the card, with two deliberate differences: it
                runs at a QUARTER of that lap time (4x faster) and COUNTER-clockwise. Both exist to
                make the two layers legible as two. Two gradients turning the same way at similar
                speeds read as one layer rendering badly; opposite directions at clearly different
                periods never drift into alignment, so the card keeps its own identity against the
                screen behind it.
                
                `GRADIENT_WASH_ALPHA` is the SAME alpha the screen background uses -- the shared
                constant exists precisely so one of these layers cannot quietly get bolder than the
                other. It is a wash over the pattern, not a replacement for it: the pattern stays
                the card's texture and this only tints it. */}
            <RotatingGradientBackground
              clockwise={false}
              colors={[
                withAlpha(colors.primary, GRADIENT_WASH_ALPHA),
                withAlpha(colors.accentGreen, GRADIENT_WASH_ALPHA),
              ]}
              durationMs={TASK_CARD_GRADIENT_DURATION_MS}
            />
          </View>
            {/* Fixed shares of the card's own height, not of whatever's left over: 7% above the
                question, 5% below SUBMIT. The middle wrapper is `flex: 1, justifyContent:
                'flex-end'` so the surface's content -- title, tokens, keypad, SUBMIT -- is pinned
                against the bottom spacer rather than top-aligned with a leftover gap drifting in
                after it; any slack the content doesn't use collects above it instead, since the
                bottom gap is the one pinned to an exact percentage right now. Distributing that
                middle space is a separate, later step. */}
            {/* pointerEvents="none" on BOTH spacers (2026-09-28). These are empty layout boxes
                with a percentage height and nothing in them -- but they are real, hit-testable
                elements, and the bottom one is the LAST sibling, so it paints over anything the
                middle area overflows. When a surface grew taller than the middle area (the task
                prompt card did it), the bottom spacer landed directly on top of SUBMIT and
                swallowed every press: the button was enabled, visible, `pointerEvents: auto`, and
                completely untappable, with no error anywhere because the submit path is silent by
                construction. A spacer has no business receiving a touch under any circumstances. */}
            <View pointerEvents="none" style={styles.taskContentSpacerTop} />
            <View style={styles.taskContentMiddle}>
              {/* The `key` is load-bearing, not cosmetic. Every archetype surface holds the child's
                in-progress answer in its own local state (ordered-value-sequence's `entryValues`
                and `order`, and whatever 10b...10h add), and none of that state is derived from the
                task prop. Without a key, React reconciles a new task into the SAME component
                instance -- same type, same position -- so the previous question's already-entered
                answer survives into the next question and can be submitted against it without ever
                being re-entered. Keying on the task instance id makes every new task a new
                instance, which discards that state as a consequence of mounting rather than by any
                explicit reset.

                `c_task_instance_id` is the registry's own per-instance identifier and is a required
                non-null string on CNextTaskResponse. It is deliberately not combined with
                `task_index`: a composite would encode a distrust of the contract without detecting
                its violation, quietly papering over a backend that had issued two tasks under one
                instance id instead of letting that surface as the defect it would be.

                It IS combined with `attempt` (added for retry): a wrong answer may be resubmitted
                on this same instance id without limit, and without `attempt` in the key, a
                "try again" would reconcile into the SAME component instance and the wrong answer
                would still be sitting there, filled in, for the child to resubmit unchanged. That
                is the identical defect this key was first added to prevent (`19d4530`), one level
                down -- across attempts on one task, not across tasks. */}
              {feedback === null ? (
                <Surface
                  key={`${task.c_task_instance_id}:${attempt}`}
                  onSubmit={submitFromSurface}
                  task={task}
                />
              ) : (
                <AnswerFeedbackPanel
                  matched={feedback.matched}
                  onNext={() => void advanceToNextTask()}
                  onTryAgain={retryTask}
                  scaffoldLevel={feedback.scaffoldLevel}
                />
              )}
            </View>
            <View pointerEvents="none" style={styles.taskContentSpacerBottom} />
            {/* In-flight indicator. Two jobs, both required by the same defect:
                  1. It TELLS the child the answer is being processed, so an unresponsive-looking
                     SUBMIT does not read as "nothing happened, press it again".
                  2. It absorbs taps. Covering the card's whole content area means no archetype's
                     own SUBMIT can be pressed while a request is out, without this file reaching
                     into eight separate surfaces to disable eight separate buttons -- every
                     archetype gets the behaviour from one place, and a ninth would inherit it.
                This is the visible half of the fix; `submitGateRef` is the half that actually
                guarantees single submission, and it would still hold if this overlay were
                removed. Deliberately no text: the wait is normally sub-second, and wording shown
                to a child on every single answer is a pedagogical question this does not open
                (ESCALATIONS.md section 4's own routing). */}
            {submitting ? (
              <View accessibilityLabel="Checking your answer" style={styles.submittingOverlay}>
                <ActivityIndicator color={accent} size="large" />
              </View>
            ) : null}
        </View>
        {/* Balances the chrome band above: equal `flex: 1` on both sides of the card keeps the
            card itself centred on the screen while the band occupies -- and centres its contents
            within -- the whole gap above it. `pointerEvents="none"` because it is an empty layout
            box that would otherwise be hit-testable over the card's shadow. */}
        <View pointerEvents="none" style={styles.taskChromeBalance} />
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  familyPill: {
    alignItems: 'center',
    alignSelf: 'center',
    // Same ground and border as `levelChip` (owner instruction, 2026-10-10). It used to be a
    // translucent tint of the family accent with no border, which read as a different KIND of
    // object from the level chip beside it; the two are peers, so they now share one treatment and
    // differ only in their text.
    backgroundColor: colors.surface1,
    borderRadius: radius.pill,
    borderWidth: 1.5,
    justifyContent: 'center',
    minHeight: CHROME_CONTROL_HEIGHT,
    paddingHorizontal: spacing.smPlus,
    paddingVertical: spacing.xs,
  },
  familyPillText: {
    fontFamily: typography.fonts.bold,
    fontSize: typography.fontSize.sm,
    letterSpacing: typography.letterSpacing.label,
  },
  levelChip: {
    alignItems: 'center',
    backgroundColor: colors.surface1,
    borderRadius: radius.pill,
    borderWidth: 1.5,
    justifyContent: 'center',
    minHeight: CHROME_CONTROL_HEIGHT,
    minWidth: TOUCH_TARGET_MIN_SIZE,
    paddingHorizontal: spacing.sm,
    paddingVertical: spacing.xs,
  },
  levelChipText: {
    fontFamily: typography.fonts.bold,
    fontSize: typography.fontSize.sm,
    letterSpacing: typography.letterSpacing.label,
    textAlign: 'center',
  },
  muted: { color: colors.textSecondary },
  pressed: { opacity: 0.85 },
  taskExitButton: {
    alignItems: 'center',
    backgroundColor: colors.surface1,
    borderColor: colors.border,
    borderRadius: radius.pill,
    borderWidth: 1.5,
    // Matches the pills beside it rather than filling TOUCH_TARGET_MIN_SIZE. The tappable area is
    // still 50pt via HIT_SLOP -- see CHROME_CONTROL_HEIGHT.
    height: CHROME_CONTROL_HEIGHT,
    justifyContent: 'center',
    width: CHROME_CONTROL_HEIGHT,
  },
  taskCanvas: {
    alignItems: 'center',
    alignSelf: 'center',
    flex: 1,
    justifyContent: 'center',
    maxWidth: 500,
    width: '100%',
  },
  // Fixed percentages of the card's own height (not of leftover space): 7% between the card's top
  // and the question, 5% between SUBMIT and the card's bottom.
  taskContentSpacerBottom: { height: '5%' },
  // Covers the whole panel, including its own SUBMIT row, so no archetype's button is reachable
  // while a submission is out. Translucent rather than opaque: the child keeps sight of the
  // question they just answered, which matters more here than a clean scrim.
  submittingOverlay: {
    alignItems: 'center',
    backgroundColor: 'rgba(255,255,255,0.55)',
    borderRadius: radius.lg,
    bottom: 0,
    justifyContent: 'center',
    left: 0,
    position: 'absolute',
    right: 0,
    top: 0,
  },
  taskContentSpacerTop: { height: '7%' },
  // Fills whatever height is left between the two spacers. The surface's own root now stretches to
  // this height and spaces its children `space-between` (ordered-value-sequence-surface.tsx's
  // `container`), so the question sits right after the 7% top spacer, SUBMIT sits right before the
  // 5% bottom spacer, and any unused slack shows up as extra white space between them instead of
  // pushing either one off its fixed gap.
  taskContentMiddle: { flex: 1 },
  // The card's border and shadow now match learner-home-screen.tsx's own hero card exactly
  // (2026-08-26 request): borderWidth 4, elevation 5, shadowOffset {0,4}, shadowOpacity 0.18,
  // shadowRadius 7 -- learner-home-screen.tsx:418's own `hero` style, values copied rather than
  // imported since that style is private to its own file. `borderColor` is applied inline from the
  // task's own game family (was `colors.surface1` -- a fixed white border -- until this request
  // moved the family's accent from the SCREEN's background, now `TASK_SCREEN_BACKGROUND`, onto the
  // card's own edge instead), so nothing about a specific family is written down here.
  //
  // Sized to 90% of the canvas on both axes and centred by the canvas's own `alignItems` /
  // `justifyContent`, rather than `flex: 1`, so the card reads as a card sitting on the screen's
  // neutral ground, distinguished by its own accent-coloured border -- instead of filling the
  // screen edge to edge.
  taskChromeBalance: { flex: 1 },
  taskChromeBand: {
    alignItems: 'center',
    flex: 1,
    justifyContent: 'center',
    // The card is 90% of the canvas; the band matches so exit and level sit on the card's own
    // left/right edges rather than the viewport's.
    maxWidth: '90%',
    // Guarantees the chrome a usable strip even on a short window, where the gap above the card
    // would otherwise collapse toward nothing and crowd the controls against the screen edge.
    minHeight: TOUCH_TARGET_MIN_SIZE,
    width: '90%',
  },
  taskChromeRow: {
    alignItems: 'center',
    flexDirection: 'row',
    width: '100%',
  },
  // Both sides flex equally, so the pill between them is centred on the card's axis regardless of
  // how wide the exit button or the level chip happen to be.
  taskChromeSide: { flex: 1 },
  taskChromeSideEnd: { alignItems: 'flex-end' },
  taskChromeSideStart: { alignItems: 'flex-start' },
  taskPanel: {
    // Fixed shape, not a share of the viewport -- see TASK_PANEL_ASPECT_RATIO. Width still leads
    // (90% of the <=500pt canvas); height follows the ratio, and maxHeight clamps the pair on a
    // short window so the card shrinks instead of overflowing.
    aspectRatio: TASK_PANEL_ASPECT_RATIO,
    backgroundColor: TASK_PANEL_BACKGROUND,
    borderRadius: radius.lg,
    borderWidth: 4,
    elevation: 5,
    maxHeight: '90%',
    // The panel's half of TASK_CONTENT_INSET; the surfaces supply the rest.
    padding: TASK_PANEL_PADDING,
    position: 'relative',
    shadowColor: colors.foreground,
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.18,
    shadowRadius: 7,
    width: '90%',
  },
  taskPanelBackground: {
    ...StyleSheet.absoluteFillObject,
    // radius.lg (20) minus the panel's 4pt borderWidth: absoluteFill insets to the padding box,
    // where the corner curve is tighter than the panel's outer edge. See the note at the <Image>.
    // `overflow: 'hidden'` is safe HERE -- this wrapper carries no shadow, unlike the panel.
    borderRadius: radius.lg - 4,
    overflow: 'hidden',
  },
  taskPanelBackgroundImage: { height: '100%', width: '100%' },
  taskSafeArea: { flex: 1 },
});
