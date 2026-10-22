import { Ionicons } from '@expo/vector-icons';
import * as Crypto from 'expo-crypto';
import * as Haptics from 'expo-haptics';
import { router } from 'expo-router';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { ActivityIndicator, Pressable, ScrollView, StyleSheet, View } from 'react-native';
import Animated, { ZoomIn } from 'react-native-reanimated';
import { SafeAreaView } from 'react-native-safe-area-context';

import type {
  PendingCompleteOpportunityCommand,
  PendingRequestAssistCommand,
  PendingSubmitResponseCommand,
} from '@/src/api/contracts';
import { FrostedScrim } from '@/src/components/frosted-scrim';
import { createComponentBApi } from '@/src/api/component-b-api';
import { ApiClientError } from '@/src/api/errors';
import type {
  AttemptResponse,
  OpportunityAdvanceResponse,
  OpportunityPresentationResponse,
} from '@/src/api/generated/openapi-types';
import { useAuth } from '@/src/auth/auth-context';
import { takeBSessionPrefetch } from '@/src/features/session/b-session-prefetch-cache';
import { AppText } from '@/src/components/app-text';
import { useAdventureCharge } from '@/src/features/navigation/adventure-charge-context';
import { readPublicConfig } from '@/src/config/env';
import {
  canAdvance,
  canRequestHint,
  clampCompleted,
  classifyAttemptOutcome,
  classifyFailure,
  failureRequestId,
  hintStateFor,
  initialAnswerState,
  isAnswerSurfaceDisabled,
  isDeadlinePassed,
  markHintsUnavailable,
  outcomeView,
  planPresentation,
  recordHint,
  decideAdvance,
  decidePendingAssist,
  decidePendingReplay,
  HINTS_UNAVAILABLE_COPY,
  type AttemptOutcome,
  type HintState,
  type SessionFailure,
  type SessionPlan,
  type SessionProgress,
} from '@/src/features/session/live-session-logic';
import {
  clearActiveSessionId,
  clearPendingCommand,
  loadPendingCommand,
  savePendingCommand,
} from '@/src/features/session/session-command-store';
import { skillBarChanges, type SkillBarChange } from '@/src/features/session/session-mastery-change';
import { captureMasterySnapshot, readMasterySnapshot } from '@/src/features/session/session-mastery-snapshot';
import { SessionResultsScreen } from '@/src/features/session/session-results-screen';
import {
  accentForSkill,
  pickBackgroundGradientColors,
  pillColorsForSkill,
} from '@/src/features/session/session-skill-accents';
import { PromptVisual } from '@/src/features/session/prompt-visuals/prompt-visual';
import { resolvePromptVisual } from '@/src/features/session/prompt-visuals/registry';
import { encodeSubmittedValue } from '@/src/features/session/renderers/encode';
import { ChoiceGrid } from '@/src/features/session/renderers/choice-grid';
import { CountSelection } from '@/src/features/session/renderers/count-selection';
import { FreeEntry } from '@/src/features/session/renderers/free-entry';
import type { AnswerState } from '@/src/features/session/renderers/types';
import {
  GRADIENT_WASH_ALPHA,
  RotatingGradientBackground,
  withAlpha,
} from '@/src/features/session/rotating-gradient-background';
import { createSubmitGate } from '@/src/utils/submit-gate';
import { colors, radius, spacing, typography } from '@/src/theme/tokens';

// FE-3b: select the question, render it, accept an answer, submit it, show the outcome.
//
// Deliberately absent, each owned by a later batch: the countdown UI (FE-3c), hints (FE-3d),
// advancing to the next question (FE-3e) and results (FE-3f). After an attempt is recorded the
// child sees the outcome and the existing "Back to home" affordance. There is no next-question
// button here on purpose — inventing one would front-run FE-3e's completion call.

type RenderPlan = Extract<SessionPlan, { kind: 'render' }>;

type Phase =
  | { kind: 'loading' }
  | { kind: 'question'; plan: RenderPlan }
  // Reached when the server reports the session bound is met. FE-3f owns the real results screen;
  // this batch only needs to arrive here cleanly and stop, rather than dead-ending on a blank
  // question surface.
  | { kind: 'completed'; progress: SessionProgress }
  | { kind: 'unrenderable'; requestId: string }
  | { kind: 'failure'; failure: SessionFailure; requestId: string | null };

const EXIT_HIT_SLOP = { bottom: 8, left: 8, right: 8, top: 8 };

const TASK_PANEL_BORDER_WIDTH = 4;
// The footer's real target gap is now the live-measured pill-bottom-to-prompt-card-top distance
// (`measuredTopGap`, computed from onLayout in the render body — see its own comment), not a
// static token: the pill's rendered height depends on font metrics this file does not control, so
// only an actual measurement can match it exactly, as requested. This is only the fallback used
// for the one frame before that measurement exists, kept close to the old (pre-measurement) value
// so there is no visible jump once the real measurement lands.
const TASK_FOOTER_BOTTOM_GAP = (spacing.smPlus + TASK_PANEL_BORDER_WIDTH) * 2;

// Appends an alpha channel to a plain 7-char `#rrggbb` colour (every colour
// `pickBackgroundGradientColors` can return is exactly this shape). `alphaHex` is a 2-digit hex
// byte, e.g. `'33'` for ~20% opacity — this is what keeps the background gradient "faded" rather
// than the game-type colours appearing at full saturation behind the card.
const failureCopy: Record<SessionFailure, { title: string; detail: string }> = {
  authentication: { title: 'Sign-in needed', detail: 'Ask a grown-up to help you sign in again.' },
  conflict: { title: 'One moment', detail: "Something changed — let's take another look." },
  network: { title: 'No connection', detail: 'Check the internet and try again in a moment.' },
  technical: { title: 'Something went wrong', detail: 'Try again in a little while.' },
};

/**
 * Presentation-acknowledgement retry budget (A2, widened 2026-10-10).
 *
 * FOUR attempts over ~6s, not two over 0.4s. The original budget assumed the thing being recovered
 * from was a dropped packet. It is not: the failure actually observed was the API being
 * unavailable for several seconds (a container restart), which a 400ms ladder cannot outlive.
 *
 * Why this matters more than it looks. If the acknowledgement never lands, `presented_at_utc` stays
 * null and the deadline the SERVER judges against remains the fail-safe written at selection --
 * and since Home now warms the question well before the child opens it, that fail-safe can already
 * be minutes old. The child then answers a question they have only just seen and is told "Time's
 * up". That exact sequence was observed on 2026-10-09.
 *
 * Still bounded, and still safe to retry: the call is idempotent (first acknowledgement wins, later
 * ones return the same deadline), so no retry can extend or reset an established deadline. The
 * backoff grows so a genuinely dead network costs four requests, not a stream of them.
 */
const PRESENTATION_ACK_ATTEMPTS = 4;
const PRESENTATION_ACK_RETRY_DELAYS_MS = [400, 1500, 4000];

export function LiveSessionScreen({ sessionId }: { sessionId: string }) {
  const { getAccessToken, me } = useAuth();
  // The authenticated Supabase subject. Keys the Home->prep prefetch handoff AND scopes every
  // local recovery record for this learner (B3) -- see session-command-store.ts.
  const subject = me?.principal.user_id ?? null;
  // The opportunity whose render has already been acknowledged, so a re-render does not re-send.
  const ackedOpportunityRef = useRef<string | null>(null);
  const { awardForSession } = useAdventureCharge();
  const configResult = useMemo(() => readPublicConfig(), []);
  const api = useMemo(
    () => (configResult.config ? createComponentBApi(configResult.config) : null),
    [configResult.config],
  );

  const [phase, setPhase] = useState<Phase>({ kind: 'loading' });
  const [answer, setAnswer] = useState<AnswerState | null>(null);
  const [outcome, setOutcome] = useState<AttemptOutcome | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [hints, setHints] = useState<HintState | null>(null);
  const [requestingHint, setRequestingHint] = useState(false);
  // Server-reported progress. Null until the first advance, because POST /opportunities does not
  // report it — showing nothing is more honest than seeding a client-side guess.
  const [progress, setProgress] = useState<SessionProgress | null>(null);
  const [advancing, setAdvancing] = useState(false);
  /** An advance already in flight (or finished) for the question on screen, so that pressing
   * "Next question" renders rather than waits. See the effect that fills it. */
  const advancePrefetchRef = useRef<{
    itemOpportunityId: string;
    command: PendingCompleteOpportunityCommand;
    promise: Promise<OpportunityAdvanceResponse>;
  } | null>(null);
  // Measured via onLayout rather than computed from static style tokens: the skill pill's
  // rendered height depends on font metrics this file does not control, so matching "the same gap"
  // the user asked for (pill-bottom-to-prompt-card-top, reused as the footer's own bottom gap)
  // exactly means measuring the real boxes, not guessing at the pill's size. All three are in the
  // same coordinate space (taskPanel-relative, pre-scroll layout position — see the JSX comments
  // where each is set) so they combine with plain arithmetic, no scroll-offset correction needed.
  const [pillBottom, setPillBottom] = useState<number | null>(null);
  const [scrollWrapperTop, setScrollWrapperTop] = useState<number | null>(null);
  const [promptCardTop, setPromptCardTop] = useState<number | null>(null);
  const mountedRef = useRef(true);
  const runningRef = useRef(false);
  /**
   * The answer-submission re-entry gate. `submitting` above is a render-only mirror of it, for the
   * button's busy indicator, and is NEVER read to decide whether a submission may proceed --
   * `setState` is asynchronous, so two taps in one frame both read the pre-update `false` and both
   * pass. Component C has held this exact gate since it shipped; B gated on the state alone, so a
   * double tap sent two requests with two FRESH idempotency keys and the server recorded a real
   * second attempt. See src/utils/submit-gate.ts for why `attempt_index == 2` is a research-data
   * defect even though the BKT observation itself is protected.
   *
   * Deliberately separate from `runningRef`, which guards `presentOpportunity` (the bootstrap).
   * Sharing one cell would make a submit in flight block a re-present, and vice versa.
   */
  const submitGateRef = useRef(createSubmitGate());
  // client_elapsed_ms is telemetry only and is never read for correctness (server timestamps are
  // authoritative). Measured from the moment the question surface becomes answerable — which is
  // also reset when the child chooses to try again — to the submit tap.
  const shownAtRef = useRef<number>(Date.now());

  /**
   * Runs an authenticated call, refreshing the token once on an `unauthenticated` failure. The
   * refresh is a retry of the *same* call with the *same* arguments — for submits that means the
   * same idempotency key and the same body, so a retry can never record a second attempt.
   */
  const withToken = useCallback(
    async <T,>(call: (accessToken: string) => Promise<T>): Promise<T> => {
      const accessToken = await getAccessToken();
      if (!accessToken) throw new ApiClientError('unauthenticated', 'No access token is available.');
      try {
        return await call(accessToken);
      } catch (error) {
        if (!(error instanceof ApiClientError) || error.kind !== 'unauthenticated') throw error;
        const refreshed = await getAccessToken(true);
        if (!refreshed) throw error;
        return await call(refreshed);
      }
    },
    [getAccessToken],
  );

  const applyAttempt = useCallback(async (attempt: AttemptResponse) => {
    // The attempt is recorded server-side; the local recovery record has done its job.
    await clearPendingCommand(subject);
    if (!mountedRef.current) return;
    const classified = classifyAttemptOutcome(attempt);
    setOutcome(classified);
    // A gentle buzz only — feedback, not judgement. Never awaited: haptics failing (no vibration
    // hardware, permission denied) must never block the outcome from showing.
    //
    // `.catch` and not bare `void`: `void` makes the call non-blocking but leaves a rejection
    // UNHANDLED, and on a device an unhandled rejection is not silent -- it raises the same
    // full-screen error overlay that a bad SecureStore key raised from this app's own storage
    // layer. The two failure modes named above are exactly the ones a cheap Android handset hits,
    // so without this the verdict screen would break on the hardware least able to buzz.
    Haptics.notificationAsync(
      classified === 'correct'
        ? Haptics.NotificationFeedbackType.Success
        : Haptics.NotificationFeedbackType.Warning,
    ).catch(() => {
      /* no vibration is a fine outcome; a crashed verdict screen is not. */
    });
  }, [subject]);

  /**
   * Mount (and post-409 resync) path.
   *
   * POST /opportunities takes no idempotency key and no body by design: it re-issues the session's
   * already-open question rather than minting a new one, which is exactly what makes it the
   * crash-recovery entry point. Calling it after a relaunch returns the same item_opportunity_id.
   */
  const presentOpportunity = useCallback(async (preloaded?: OpportunityPresentationResponse) => {
    if (!api || runningRef.current) return;
    runningRef.current = true;
    // A preloaded question is already in hand, so there is nothing to wait for and no loading
    // phase to show -- that is the entire point of Home's prefetch (b-session-prefetch.ts). Every
    // other caller (mount without a prefetch, post-409 resync, advancing to the next question)
    // still shows it, unchanged.
    if (!preloaded) setPhase({ kind: 'loading' });
    setOutcome(null);
    setSubmitting(false);
    try {
      const presentation = preloaded ?? (await withToken((token) => api.selectOpportunity(sessionId, token)));
      if (!mountedRef.current) return;
      const plan = planPresentation(presentation, presentation.request_id);
      if (plan.kind !== 'render') {
        setPhase({ kind: 'unrenderable', requestId: plan.requestId });
        return;
      }
      setAnswer(initialAnswerState(plan.spec));
      // Hint state is scoped to the opportunity, so a re-presentation of the *same* question (the
      // crash-recovery path) keeps hints the child has already been given, while a genuinely new
      // question starts from scratch. FE-3e advancing the loop in place needs no change here.
      setHints((current) => hintStateFor(current, plan.itemOpportunityId));
      setRequestingHint(false);
      shownAtRef.current = Date.now();
      setPhase({ kind: 'question', plan });

      // Offline-recovery replay. A saved submit for *this* opportunity is resent verbatim — same
      // key, same body — so the server returns the original attempt instead of recording a second
      // one. A saved submit for a different opportunity belongs to a question that has already
      // moved on, so it is discarded rather than sent.
      const decision = decidePendingReplay(await loadPendingCommand(subject), sessionId, plan.itemOpportunityId);
      if (decision.action === 'discard') {
        await clearPendingCommand(subject);
        return;
      }
      if (decision.action === 'replay') {
        await sendSubmit(decision.command);
      }
    } catch (error) {
      if (!mountedRef.current) return;
      setPhase({
        kind: 'failure',
        failure: classifyFailure(error),
        requestId: failureRequestId(error),
      });
    } finally {
      runningRef.current = false;
    }
    // sendSubmit is declared below and is stable for the same reasons `api`/`withToken` are; the
    // mutual reference is broken with a ref-free forward declaration.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [api, sessionId, withToken]);

  const sendSubmit = useCallback(
    async (command: PendingSubmitResponseCommand) => {
      if (!api) return;
      setSubmitting(true);
      try {
        const attempt = await withToken((token) =>
          api.submitResponse(
            command.sessionId,
            command.itemOpportunityId,
            command.idempotencyKey,
            command.body,
            token,
          ),
        );
        await applyAttempt(attempt);
      } catch (error) {
        if (!mountedRef.current) return;
        const failure = classifyFailure(error);
        if (failure === 'conflict') {
          // 409 means the server's view of this opportunity has moved on. Re-ask it what to show
          // and render whatever comes back — never a client-side rule about what "should" have
          // happened.
          await clearPendingCommand(subject);
          if (mountedRef.current) await presentOpportunity();
          return;
        }
        // Anything else leaves the pending command persisted on purpose: it is the record that
        // lets the next mount replay this exact key and body instead of losing the attempt.
        setPhase({ kind: 'failure', failure, requestId: failureRequestId(error) });
      } finally {
        if (mountedRef.current) setSubmitting(false);
      }
    },
    [api, applyAttempt, presentOpportunity, subject, withToken],
  );

  const submitAnswer = useCallback(async () => {
    if (phase.kind !== 'question' || !answer || submitting) return;
    const submittedValue = encodeSubmittedValue(phase.plan.spec, answer);
    // Unreachable via the button (it is disabled in exactly this case); kept because "no
    // submittable value" must never become "send something anyway".
    if (submittedValue === null) return;

    // THE RE-ENTRY GATE, taken BEFORE the first `await` and before the command is persisted.
    //
    // The `submitting` check above cannot do this job on its own: it reads React state, which is
    // updated asynchronously, so two taps dispatched in the same frame both see `false`.
    //
    // The position matters as much as the gate. It has to be above `savePendingCommand`, not
    // merely above the network call: each tap builds its own command with a FRESH
    // `Crypto.randomUUID()` key, so two taps reaching the write would have the second command
    // overwrite the first in the single pending slot while the first request was still in flight
    // -- leaving the stored replay record pointing at a key whose request never happened, and
    // losing the record for the one that did. Gating inside `sendSubmit` would not prevent that.
    if (!submitGateRef.current.tryEnter()) return;
    try {
      const command: PendingSubmitResponseCommand = {
        body: {
          client_elapsed_ms: Math.max(0, Date.now() - shownAtRef.current),
          submitted_value: submittedValue,
        },
        createdAt: new Date().toISOString(),
        endpoint: '/api/v1/b/sessions/{sessionId}/opportunities/{itemOpportunityId}/responses',
        idempotencyKey: Crypto.randomUUID(),
        itemOpportunityId: phase.plan.itemOpportunityId,
        kind: 'submit_response',
        sessionId,
      };
      // Persisted *before* the request, never after: if the response is lost, the key and the exact
      // body survive. The server fingerprints the body into the idempotency record, so a replay must
      // resend the saved body — one reconstructed later would fail the fingerprint check, and
      // client_elapsed_ms is unrecoverable after a relaunch.
      await savePendingCommand(subject, command);
      await sendSubmit(command);
    } finally {
      // `finally`, not the happy path: `sendSubmit` handles its own failures rather than
      // rethrowing, but an early return or any future throw must still release the gate or the
      // answer surface locks permanently for the rest of the question.
      submitGateRef.current.release();
    }
  }, [answer, phase, sendSubmit, sessionId, subject, submitting]);

  /**
   * Ask for the next hint. The client never requests or sends a level — the server derives it from
   * its own count of prior hint events, under the opportunity row lock, strictly L1 → L2 → L3.
   *
   * A 409 is the ordinary outcome (only 2 of 36 templates carry hint content) and is handled as a
   * normal, neutral end state rather than an error: the control closes for this opportunity and
   * the child gets forward-pointing copy. No attempt is made to work out *which* 409 it was; the
   * server maps "no content", "blank content", "checksum mismatch" and "already at L3" to one
   * indistinguishable ConflictError on purpose, so nothing can leak the answer through the error
   * path.
   *
   * Nothing here touches the answer surface. Asking for help never blocks answering, and a hint is
   * never a mastery/BKT observation, so it costs the child nothing.
   */
  const requestHint = useCallback(async () => {
    if (!api || phase.kind !== 'question' || requestingHint) return;
    const scoped = hintStateFor(hints, phase.plan.itemOpportunityId);
    if (!canRequestHint(scoped)) return;

    // Reuse a persisted key for this same opportunity if one survived. If a previous request
    // succeeded but its response was lost (network drop, app kill), a *fresh* key would make the
    // server count that first event and escalate — the child would silently never see L1, the
    // gentlest hint. Replaying the saved key returns the original level and content instead.
    const pending = decidePendingAssist(
      await loadPendingCommand(subject),
      sessionId,
      phase.plan.itemOpportunityId,
    );
    const command: PendingRequestAssistCommand =
      pending.action === 'reuse'
        ? pending.command
        : {
            createdAt: new Date().toISOString(),
            endpoint: '/api/v1/b/sessions/{sessionId}/opportunities/{itemOpportunityId}/assists',
            idempotencyKey: Crypto.randomUUID(),
            itemOpportunityId: phase.plan.itemOpportunityId,
            kind: 'request_assist',
            sessionId,
          };

    setRequestingHint(true);
    try {
      // Persisted before the request, never after — that ordering is the whole protection.
      if (pending.action !== 'reuse') await savePendingCommand(subject, command);
      const hint = await withToken((token) =>
        api.requestAssist(
          command.sessionId,
          command.itemOpportunityId,
          command.idempotencyKey,
          token,
        ),
      );
      await clearPendingCommand(subject);
      if (!mountedRef.current) return;
      setHints((current) => recordHint(hintStateFor(current, hint.item_opportunity_id), hint));
    } catch (error) {
      const failure = classifyFailure(error);
      if (failure === 'conflict') {
        // The normal case. The key has done its job; there is nothing left to replay.
        await clearPendingCommand(subject);
        if (!mountedRef.current) return;
        setHints((current) =>
          markHintsUnavailable(hintStateFor(current, command.itemOpportunityId)),
        );
        return;
      }
      // Any other failure deliberately changes no state: the key stays persisted so the next tap
      // replays it rather than escalating, and the control stays available so the child may simply
      // try again. It is not promoted to the full-screen failure phase either — losing the question
      // because a hint request failed would be a far worse outcome than not getting the hint.
    } finally {
      if (mountedRef.current) setRequestingHint(false);
    }
  }, [api, hints, phase, requestingHint, sessionId, subject, withToken]);

  /**
   * Move to the next question.
   *
   * The advance response carries the next presentation inline, so it is rendered directly — no
   * second POST /opportunities. The idempotency fingerprint is `{session_id,
   * item_opportunity_id}`, so a replay of the same key returns the original advance: no
   * double-close and no skipped question. That is why the key is persisted before the request and
   * cleared only on success — a lost response retried with a *fresh* key would risk closing an
   * opportunity twice.
   */
  const buildAdvanceCommand = useCallback(
    (itemOpportunityId: string): PendingCompleteOpportunityCommand => ({
      createdAt: new Date().toISOString(),
      endpoint: '/api/v1/b/sessions/{sessionId}/opportunities/{itemOpportunityId}/complete',
      idempotencyKey: Crypto.randomUUID(),
      itemOpportunityId,
      kind: 'complete_opportunity',
      sessionId,
    }),
    [sessionId],
  );

  /** The advance request itself, with no state handling -- so it can run either from the button or
   * ahead of it (see the prefetch effect below) and be applied at whichever moment is right. */
  const sendAdvance = useCallback(
    async (command: PendingCompleteOpportunityCommand): Promise<OpportunityAdvanceResponse> => {
      if (!api) throw new Error('advance without an API');
      // Overwrites the shared pending slot, which is correct here: any command still sitting in it
      // belongs to the question being left behind (FE-3d's assist key, for instance), and a stale
      // command must never survive into the next question.
      await savePendingCommand(subject, command);
      const response = await withToken((token) =>
        api.completeOpportunity(
          command.sessionId,
          command.itemOpportunityId,
          command.idempotencyKey,
          token,
        ),
      );
      await clearPendingCommand(subject);
      return response;
    },
    [api, subject, withToken],
  );

  const advance = useCallback(async () => {
    if (!api || phase.kind !== 'question' || advancing) return;
    // Advancing requires at least one recorded attempt (session_completion.py:321-325); the
    // control is gated on an outcome being on screen, so this is belt-and-braces.
    if (!canAdvance(outcome !== null)) return;

    const itemOpportunityId = phase.plan.itemOpportunityId;
    const prefetched =
      advancePrefetchRef.current?.itemOpportunityId === itemOpportunityId
        ? advancePrefetchRef.current
        : null;
    // The SAME command as the prefetch, never a fresh one. If the prefetch failed, retrying with
    // its original idempotency key is safe by construction -- the fingerprint is
    // {session_id, item_opportunity_id}, so a replay returns the original advance rather than
    // closing the opportunity a second time. A new key would be the double-close this whole flow
    // is careful to avoid.
    const command = prefetched?.command ?? buildAdvanceCommand(itemOpportunityId);

    setAdvancing(true);
    try {
      let response: OpportunityAdvanceResponse;
      if (prefetched) {
        try {
          response = await prefetched.promise;
        } catch {
          response = await sendAdvance(command);
        }
      } else {
        response = await sendAdvance(command);
      }
      advancePrefetchRef.current = null;
      if (!mountedRef.current) return;

      const decision = decideAdvance(response);
      if (decision.kind === 'drift') {
        // Neither a next question nor a finished session. Re-ask rather than guess.
        await presentOpportunity();
        return;
      }
      setProgress(decision.progress);
      if (decision.kind === 'completed') {
        setPhase({ kind: 'completed', progress: decision.progress });
        return;
      }
      if (decision.plan.kind !== 'render') {
        setPhase({ kind: 'unrenderable', requestId: decision.plan.requestId });
        return;
      }
      // Everything scoped to the question being left goes with it: the answer, the outcome, the
      // hints (keyed on item_opportunity_id since FE-3d, so this is a re-key rather than a manual
      // clear) and the elapsed-time reference behind client_elapsed_ms.
      setAnswer(initialAnswerState(decision.plan.spec));
      setOutcome(null);
      setHints(hintStateFor(null, decision.plan.itemOpportunityId));
      setRequestingHint(false);
      shownAtRef.current = Date.now();
      setPhase({ kind: 'question', plan: decision.plan });
    } catch (error) {
      if (!mountedRef.current) return;
      const failure = classifyFailure(error);
      if (failure === 'conflict') {
        // Almost certainly "no attempt recorded yet" or a state that has already moved on. Re-ask
        // POST /opportunities and render whatever the server returns — never a client-side rule
        // about what should have happened.
        await clearPendingCommand(subject);
        if (mountedRef.current) await presentOpportunity();
        return;
      }
      setPhase({ kind: 'failure', failure, requestId: failureRequestId(error) });
    } finally {
      if (mountedRef.current) setAdvancing(false);
    }
  }, [advancing, api, buildAdvanceCommand, outcome, phase, presentOpportunity, sendAdvance, subject]);

  // PRE-ADVANCE. The moment a verdict is on screen and the question is genuinely finished, ask the
  // server for the next one -- while the child is still reading "Nice work!". By the time they
  // press "Next question" the response is normally already in hand, so the next question appears
  // instead of a loading state.
  //
  // ONLY WHEN THE CHILD CANNOT TRY AGAIN. Advancing CLOSES the current opportunity, and an
  // incorrect answer still offers "TRY AGAIN" on the very same one (`tryAgain` below just clears
  // the outcome and lets them answer again). Pre-advancing there would close the question out from
  // under a child who is about to retry it, and the retry would be rejected by a server that has
  // already moved on. `canTryAgain` is false for exactly the terminal outcomes -- correct, and
  // timeout -- which are the only ones this fires for.
  //
  // This does not change WHICH question comes next. Selection is adaptive and server-side, and it
  // happens after the attempt is recorded either way; starting the request earlier only moves the
  // waiting, never the choosing.
  //
  // Best-effort: a rejection is held and retried by `advance` under the SAME idempotency key, so a
  // failed pre-advance costs nothing and cannot double-close.
  const primeAdvance = useCallback(() => {
    if (!api || phase.kind !== 'question' || outcome === null) return;
    const itemOpportunityId = phase.plan.itemOpportunityId;
    if (advancePrefetchRef.current?.itemOpportunityId === itemOpportunityId) return;
    const command = buildAdvanceCommand(itemOpportunityId);
    const promise = sendAdvance(command);
    // Parked, not handled here: `advance` awaits this same promise and owns every outcome. The
    // no-op catch only stops an unhandled rejection warning in the meantime.
    promise.catch(() => undefined);
    advancePrefetchRef.current = { command, itemOpportunityId, promise };
  }, [api, buildAdvanceCommand, outcome, phase, sendAdvance]);

  useEffect(() => {
    if (outcome === null || outcomeView(outcome).canTryAgain) return;
    primeAdvance();
  }, [outcome, primeAdvance]);

  /**
   * THE WRONG-ANSWER CASE, which the effect above deliberately will not cover.
   *
   * A wrong answer keeps TRY AGAIN, and TRY AGAIN needs this opportunity still OPEN -- so the
   * next question cannot be fetched in advance. That is not an API preference but a database
   * rule: `uq_b_item_opportunities_one_open_per_session` is a partial unique index allowing ONE
   * open opportunity per session, so the next question cannot exist while this one does.
   *
   * What is left is the gap between the child's finger landing on "Next question" and lifting
   * off. Starting `complete` on press-IN spends that gap on the round trip instead of on nothing.
   * It is small -- roughly 100-300ms -- but it is the only overlap available without taking TRY
   * AGAIN away, and the owner's instruction was to keep it (2026-10-10).
   *
   * Safe for TRY AGAIN: this fires only when the child reaches for Next. Press TRY AGAIN and
   * `complete` is never sent, so the opportunity stays open and the retry works untouched.
   *
   * The one edge: pressing down on Next, sliding off, then pressing TRY AGAIN. `complete` has
   * already closed the opportunity, so the retry submit gets a 409 -- which the existing conflict
   * handler turns into a re-present rather than an error. Degraded, not broken, and it costs a
   * deliberate gesture to reach.
   */
  const primeAdvanceOnIntent = useCallback(() => {
    if (outcome === null) return;
    primeAdvance();
  }, [outcome, primeAdvance]);

  const tryAgain = useCallback(() => {
    if (phase.kind !== 'question') return;
    setOutcome(null);
    setAnswer(initialAnswerState(phase.plan.spec));
    shownAtRef.current = Date.now();
  }, [phase]);

  // PRESENTATION ACKNOWLEDGEMENT (owner ruling, 2026-09-27). The answering clock starts HERE --
  // when the question is rendered -- not when it was selected. Selection now happens well before
  // the child is looking at anything (Home and /prepare both prefetch), and the governance
  // register rules that "infrastructure failure is never learner failure", so server and network
  // time must not be spent from the child's five minutes.
  //
  // Fired once per opportunity: `ackedOpportunityRef` guards a re-render, and the server itself is
  // the real guarantee -- the first acknowledgement anchors and every later one returns the same
  // deadline, so a remount or a relaunch can neither extend nor shorten what the child has.
  //
  // Best-effort and deliberately silent, but no longer single-shot (A2, 2026-10-10). A failure
  // leaves the fail-safe deadline written at SELECTION, and that is the one the server judges a
  // submission against -- so a lost acknowledgement is the one case where time spent before the
  // child saw the question can still be charged to them. The window is widest exactly where it
  // matters least to notice: a long dwell on the preparation screen.
  //
  // TWO ATTEMPTS TOTAL, then stop. The request is idempotent by construction -- the first
  // acknowledgement anchors and every later one is a no-op returning the SAME deadline
  // (`anchor_presentation` returns early once `presented_at_utc` is set) -- so a retry can never
  // extend or reset a deadline that already exists. That property is what makes retrying safe; it
  // is not a licence to retry indefinitely, and a bounded count keeps a dead network from
  // generating background traffic behind a child who is simply reading.
  //
  // Still silent: a transient failure must not put a technical error in front of a child, and
  // after both attempts fail the behaviour is exactly what it was before this retry existed.
  // `ackedOpportunityRef` is set BEFORE the first attempt, so a re-render during the retry cannot
  // start a second ladder; the unmount check before each attempt stops a navigated-away screen
  // from issuing one.
  useEffect(() => {
    if (phase.kind !== 'question' || !api) return;
    const opportunityId = phase.plan.itemOpportunityId;
    if (ackedOpportunityRef.current === opportunityId) return;
    ackedOpportunityRef.current = opportunityId;

    let cancelled = false;
    void (async () => {
      for (let attempt = 1; attempt <= PRESENTATION_ACK_ATTEMPTS; attempt += 1) {
        if (cancelled || !mountedRef.current) return;
        try {
          const ack = await withToken((token) =>
            api.acknowledgePresentation(sessionId, opportunityId, token),
          );
          if (cancelled || !mountedRef.current) return;
          // Adopt the server's anchored deadline: it is normally LATER than the one the
          // presentation carried, and it is the one the server will judge a submission against.
          setPhase((current) =>
            current.kind === 'question' && current.plan.itemOpportunityId === opportunityId
              ? { ...current, plan: { ...current.plan, timeoutDeadlineUtc: ack.server_timeout_deadline_utc } }
              : current,
          );
          return;
        } catch {
          // Fall through to the one retry, then give up and keep the selection-time deadline.
          if (attempt < PRESENTATION_ACK_ATTEMPTS) {
            const delay = PRESENTATION_ACK_RETRY_DELAYS_MS[attempt - 1] ?? 4000;
            await new Promise((resolve) => setTimeout(resolve, delay));
          }
        }
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [api, phase, sessionId, withToken]);

  useEffect(() => {
    mountedRef.current = true;
    if (!api) {
      setPhase({ kind: 'failure', failure: 'technical', requestId: null });
    } else {
      void (async () => {
        // Home's hero/resume press prefetched this session's first question and the preparation
        // screen already awaited it, so this entry is normally resolved and applies without a
        // network call or a loading phase. `take` is single-use: a later re-entry (relaunch, deep
        // link, retry) finds nothing and runs the normal path below, which re-issues the same
        // already-OPEN opportunity anyway. A prefetch that failed or handed back `null` falls
        // through to exactly the behaviour that existed before it.
        const prefetch = subject ? takeBSessionPrefetch(subject) : null;
        let preloaded: OpportunityPresentationResponse | undefined;
        if (prefetch) {
          try {
            const result = await prefetch;
            if (result && result.sessionId === sessionId) preloaded = result.presentation;
          } catch {
            // Fall through to the normal fetch.
          }
        }
        if (mountedRef.current) await presentOpportunity(preloaded);
      })();
    }
    return () => {
      mountedRef.current = false;
    };
  }, [api, subject, presentOpportunity, sessionId]);

  // Charges the adventure battery exactly once per genuinely completed Component B session --
  // `phase.kind === 'completed'` is the same real, backend-driven completion state
  // SessionResultsScreen renders from, not a client-side guess. awardForSession is idempotent per
  // sessionId, so re-renders of this same completed screen never double-award.
  useEffect(() => {
    if (phase.kind === 'completed') awardForSession(sessionId);
  }, [awardForSession, phase.kind, sessionId]);

  const goHome = useCallback(() => router.replace('/(learner)/home'), []);

  // --- RESULTS MASTERY BARS (owner decision, 2026-10-20) -------------------------------------
  //
  // This surface was deliberately non-evaluative; showing what moved reverses that, knowingly.
  // See session-mastery-snapshot.ts and buildLog2.md's entry for the decision and its two costs.
  const [masteryChanges, setMasteryChanges] = useState<readonly SkillBarChange[]>([]);

  // PHOTOGRAPH THE STARTING STATE, once, as early as the screen can. The snapshot module ignores
  // every call after the first for a session, so a remount or a crash-recovery resume cannot
  // re-baseline it to a mid-session state and erase the child's own progress from the screen.
  useEffect(() => {
    let cancelled = false;
    const capture = async () => {
      if (!api) return;
      try {
        const response = await withToken((token) => api.getLearnerSkillStates(token));
        if (!cancelled) captureMasterySnapshot(sessionId, response.skill_states);
      } catch {
        // Best effort. No snapshot simply means the results screen shows current mastery with no
        // movement, which is a supported state -- never an error in front of a child.
      }
    };
    void capture();
    return () => {
      cancelled = true;
    };
  }, [api, sessionId, withToken]);

  // Read the CURRENT state once the session is over, and compare. Deliberately not fetched earlier:
  // the whole point is the value after the last answer was scored.
  useEffect(() => {
    if (phase.kind !== 'completed') return;
    let cancelled = false;
    const compare = async () => {
      if (!api) return;
      try {
        const response = await withToken((token) => api.getLearnerSkillStates(token));
        if (cancelled) return;
        setMasteryChanges(skillBarChanges(readMasterySnapshot(sessionId), response.skill_states));
      } catch {
        // Leaving `masteryChanges` empty renders the bars at zero with no animation rather than
        // an error. The counts above them are still true.
      }
    };
    void compare();
    return () => {
      cancelled = true;
    };
  }, [api, phase.kind, sessionId, withToken]);

  /**
   * Leaving a finished session. The stored active-session id has done its job; leaving it behind
   * would let a later launch offer "Resume" and then try to resume a session the server has already
   * completed. Results are not persisted and are not deep-linkable — deliberately, since the app
   * keeps no learner-facing record of performance — so once this screen is left there is nothing to
   * return to, and the child lands on preparation and starts fresh.
   */
  const exitSession = useCallback(async () => {
    await clearActiveSessionId(subject);
    goHome();
  }, [goHome, subject]);

  // Computed here, above every early `return`, because it is a Hook (`useMemo`) — Hooks must run
  // on every render in the same order, so it cannot live down in the 'question'-only render path
  // below with the rest of that phase's derived values. `null` outside the 'question' phase (there
  // is no card, hence no accent to avoid) is deliberately what skips re-picking: the dependency
  // array only changes, and this only re-runs pickBackgroundGradientColors, on an actual new
  // question (a change in itemOpportunityId), never on an unrelated re-render of this screen.
  const currentQuestionAccent = phase.kind === 'question' ? accentForSkill(phase.plan.skillId) : null;
  const currentOpportunityId = phase.kind === 'question' ? phase.plan.itemOpportunityId : null;
  const gradientColors = useMemo(
    () =>
      currentQuestionAccent ? pickBackgroundGradientColors(currentQuestionAccent) : (['#ffffff', '#ffffff'] as const),
    [currentQuestionAccent, currentOpportunityId],
  );

  if (phase.kind === 'loading') {
    return (
      <SessionFrame>
        <View style={styles.centered}>
          <ActivityIndicator color={colors.primary} size="large" />
          <AppText align="center" style={styles.muted}>
            Getting your question ready…
          </AppText>
        </View>
      </SessionFrame>
    );
  }

  if (phase.kind === 'completed') {
    // The progress numbers come straight from the completion response — GET /summary is not called
    // (see component-b-api.ts's note on getSessionSummary). See SessionResultsScreen for why this
    // surface carries counts and nothing evaluative.
    return (
      <SessionResultsScreen
        changes={masteryChanges}
        onExit={() => void exitSession()}
        onPlayAgain={() => router.replace('/(learner)/prepare')}
        progress={phase.progress}
      />
    );
  }

  if (phase.kind === 'unrenderable' || phase.kind === 'failure') {
    // The fail-closed screen. Neutral, child-appropriate, one way forward, and a support code a
    // grown-up can quote. Never a free-text box: a text input shown against a question whose
    // answer surface could not be resolved lets a child submit something the item cannot accept
    // and then be told they were wrong.
    const copy =
      phase.kind === 'unrenderable'
        ? { title: "This one isn't ready", detail: "Let's head back and try again soon." }
        : failureCopy[phase.failure];
    const supportCode = phase.requestId;
    return (
      <SessionFrame>
        <View style={styles.centered}>
          <View style={styles.iconCircle}>
            <Ionicons color={colors.primary} name="alert-circle-outline" size={44} />
          </View>
          <AppText align="center" variant="title">
            {copy.title}
          </AppText>
          <AppText align="center" style={styles.muted}>
            {copy.detail}
          </AppText>
          {supportCode ? (
            <AppText align="center" style={styles.supportCode}>
              Support code: {supportCode}
            </AppText>
          ) : null}
          <PrimaryButton label="BACK TO HOME" onPress={goHome} />
        </View>
      </SessionFrame>
    );
  }

  const { plan } = phase;
  const encoded = answer ? encodeSubmittedValue(plan.spec, answer) : null;
  const view = outcome ? outcomeView(outcome) : null;
  // The deadline is read, and then deliberately does not gate anything (see
  // isAnswerSurfaceDisabled for the soft-lock reasoning). There is no countdown and no "time is
  // running out" warning: a ticking clock in front of a seven-year-old is an anxiety device, and
  // it would be counting down to something the client cannot enforce anyway. The child answers,
  // the server rules TIMEOUT, and the neutral outcome copy tells them.
  const answeringDisabled = isAnswerSurfaceDisabled({
    deadlinePassed: isDeadlinePassed(plan.timeoutDeadlineUtc, Date.now()),
    hasOutcome: outcome !== null,
    submitting,
  });
  // Submit is unavailable precisely when there is nothing submittable: no selection yet, a blank
  // expanded_form, an unset count. That mirrors the server's own min_length=1, so the disabled
  // state prevents a guaranteed 422 — it is not a correctness judgement about the answer. It is
  // never unavailable because time has run out; that submit is what records the TIMEOUT.
  const canSubmit = encoded !== null && !answeringDisabled;
  const hintView = hintStateFor(hints, plan.itemOpportunityId);
  // Resolved from payload keys, never from item_template_id or representation_type — see the
  // registry for why both of those would be wrong. `selectable-pool` is an answer surface rather
  // than an illustration, so it is routed into CountSelection below instead of being drawn here.
  const promptVisual = resolvePromptVisual(plan.promptPayload);
  const passiveVisual = promptVisual?.kind === 'selectable-pool' ? null : promptVisual;
  const poolSize = promptVisual?.kind === 'selectable-pool' ? promptVisual.poolSize : undefined;
  // Presentation only, read straight off the wire id — see session-skill-accents.ts. Falls back to
  // a neutral surface colour for a skill id this table has not been taught, never a reason to
  // change what question is shown.
  const accent = accentForSkill(plan.skillId);
  const pillColors = pillColorsForSkill(plan.skillId);
  // The gap the footer reproduces: pill-bottom to prompt-card-top, from the three onLayout
  // measurements above. `null` until all three have reported at least once (first paint, before
  // layout runs) — the footer falls back to TASK_FOOTER_BOTTOM_GAP for that one frame rather than
  // collapsing to zero.
  const measuredTopGap =
    pillBottom !== null && scrollWrapperTop !== null && promptCardTop !== null
      ? scrollWrapperTop + promptCardTop - pillBottom
      : null;
  const footerBottomGap = measuredTopGap ?? TASK_FOOTER_BOTTOM_GAP;
  const footerPaddingBottom = Math.max(0, footerBottomGap - TASK_PANEL_BORDER_WIDTH - spacing.md);

  return (
    <SafeAreaView style={styles.taskSafeArea}>
      {/* Faded — `withAlpha` at low opacity, not the raw saturated colours — and re-picked per
          question rather than fixed, from two of the five game-type colours the home screen's own
          path uses (see pickBackgroundGradientColors). `colors.background` stays as this
          SafeAreaView's own backgroundColor (styles.taskSafeArea) underneath, so the gradient is a
          wash over that base rather than a replacement for it. Rotates continuously — see
          RotatingGradientBackground. */}
      <RotatingGradientBackground
        colors={[
          withAlpha(gradientColors[0], GRADIENT_WASH_ALPHA),
          withAlpha(gradientColors[1], GRADIENT_WASH_ALPHA),
        ]}
      />
      <View style={styles.taskCanvas}>
        <View style={[styles.taskPanel, { borderColor: accent }]}>
          {/* Floats above the flow rather than taking a row of its own, matching c-session's own
              exit control. Leaving mid-question goes straight home without clearing the active
              session id (that is `exitSession`'s job, reached only from a genuinely finished
              session) — the server keeps the opportunity open, so returning through /prepare finds
              it resumable rather than abandoned.
              The skill pill sits on this same row rather than its own, so it reads as navigation
              chrome alongside the exit control instead of scrolling away with the question. It is
              centred on the CARD's own x-axis (`left: 0, right: 0` spans the full card width, not
              just the space left after the exit button) via absolute positioning, so it stays
              centred regardless of the exit button's width. */}
          <View style={styles.taskHeaderRow}>
            <Pressable
              accessibilityLabel="Leave session"
              accessibilityRole="button"
              hitSlop={EXIT_HIT_SLOP}
              onPress={goHome}
              style={({ pressed }) => [styles.taskExitButton, pressed && styles.pressed]}>
              <Ionicons color={colors.textSecondary} name="close" size={22} />
            </Pressable>
          </View>
          {/* The hint control's other half: X on the top-left, this on the top-right, same circle
              size (44) and same row. Only rendered while a hint can still be requested for this
              opportunity — once hints close (see canRequestHint), the informational
              `hintClosed` copy inline below is the only trace of it, not a dead button up here. */}
          {canRequestHint(hintStateFor(hints, plan.itemOpportunityId)) ? (
            <View style={styles.taskHintRow}>
              <Pressable
                accessibilityLabel={
                  hintStateFor(hints, plan.itemOpportunityId).received.length > 0
                    ? 'Another hint'
                    : 'I need a hint'
                }
                accessibilityRole="button"
                accessibilityState={{ disabled: requestingHint }}
                disabled={requestingHint}
                hitSlop={EXIT_HIT_SLOP}
                onPress={() => void requestHint()}
                style={({ pressed }) => [
                  styles.taskExitButton,
                  styles.taskHintButton,
                  pressed && !requestingHint && styles.pressed,
                ]}>
                {requestingHint ? (
                  <ActivityIndicator color={colors.accentBlue} size="small" />
                ) : (
                  <Ionicons color={colors.accentBlue} name="bulb-outline" size={22} />
                )}
              </Pressable>
            </View>
          ) : null}
          {/* `onLayout` here — not measured from static tokens — is the top half of the footer's
              gap measurement; see `measuredTopGap`, above. This row's own height already equals
              the pill's rendered height (nothing else in it adds vertical space), so
              `layout.y + layout.height` is exactly the pill's bottom edge, in taskPanel-relative
              coordinates (this row is a direct child of taskPanel). */}
          <View
            onLayout={(event) =>
              setPillBottom(event.nativeEvent.layout.y + event.nativeEvent.layout.height)
            }
            pointerEvents="none"
            style={styles.taskSkillPillRow}>
            <View style={[styles.skillPill, { backgroundColor: pillColors.soft }]}>
              <Ionicons color={pillColors.text} name="sparkles" size={16} />
              <AppText style={[styles.skillText, { color: pillColors.text }]}>
                {plan.skillLabel || 'Maths'}
              </AppText>
            </View>
          </View>
      {/* Wraps just the scrolling question/answer/hints area — not the header row above or the
          footer below — so the outcome popup's blur (an absolutely positioned sibling of the
          ScrollView, sized to fill this wrapper) only ever covers the now-stale question content,
          never the exit/hint corner buttons or the still-live advance/try-again button.
          Its own `onLayout` is the other half of `measuredTopGap`'s coordinate conversion: this
          wrapper is a normal-flow direct child of taskPanel, so its `layout.y` is exactly where
          the ScrollView's (unscrolled) content-space y=0 sits in taskPanel-relative coordinates. */}
      <View onLayout={(event) => setScrollWrapperTop(event.nativeEvent.layout.y)} style={styles.taskScrollWrapper}>
      <ScrollView
        contentContainerStyle={styles.scroll}
        keyboardShouldPersistTaps="handled"
        style={styles.taskScroll}>
        {/* Straight from the server's own numbers — never a client-side counter, and never a
            client-side bound. Absent until the first advance reports them, so the bar is skipped
            entirely rather than seeded with a guess. */}
        {progress ? <ProgressBar progress={progress} /> : null}

        {/* `onLayout` reports this card's y in the ScrollView's own content space — pre-scroll
            layout position, not the visually-scrolled position — which is exactly what
            `measuredTopGap` adds to `scrollWrapperTop` to land back in taskPanel-relative
            coordinates. */}
        {/* Doubles the gap to the progress bar above it specifically, not every gap in the scroll:
            `scroll`'s own `gap: spacing.md` already spaces every direct child uniformly, so an
            extra `spacing.md` of margin here — only when a progress bar is actually rendered above
            it — brings the total to 2x just for this one pair, leaving every other gap in the
            column untouched. */}
        <View
          onLayout={(event) => setPromptCardTop(event.nativeEvent.layout.y)}
          style={[styles.promptCard, progress && styles.promptCardAfterProgress]}>
          {/* The server's authored instruction, above the stem, for the templates whose stem is
              not a question on its own -- "Guess the next number." over a bare "2, 3, 4, __".
              Server-supplied and relayed verbatim; the app never composes one. Most templates send
              none, and those render exactly as before. Styled as the question (see `instruction`
              in the stylesheet): where one exists it IS the question, and the stem below it is the
              material -- the numbers to continue. */}
          {plan.instruction ? (
            <AppText style={styles.instruction}>{plan.instruction}</AppText>
          ) : null}
          <AppText style={styles.stem}>{plan.stem}</AppText>
          {/* FE-3g — the concrete representation the question refers to. `prompt` carries content
              keys beyond `stem`, and rendering only the stem left 7 of 14 Grade 2 templates
              unanswerable. `null` means this payload has no visual, which renders stem-only exactly
              as before. The visual presents the quantity the server sent and nothing else: no
              counting, no comparing, no checking the child. */}
          {passiveVisual ? (
            <View style={styles.visual}>
              <PromptVisual seed={plan.itemOpportunityId} spec={passiveVisual} />
            </View>
          ) : null}
        </View>

        {/* `flex: 1` inside the scroll's own flexGrow container: this block claims whatever
            vertical space is left over between the prompt card above and the hints/outcome/footer
            below, and `justifyContent: 'center'` centres the answer pad within exactly that space
            — between the question card and the submit button, as requested — rather than the pad
            sitting flush under the prompt with a large empty gap below it. When hints or an
            outcome ARE present, they still render below in normal flow; this block simply gets
            whatever room remains above them. */}
        <View style={styles.answerCenter}>
          {answer?.kind === 'choice' && plan.spec.kind === 'choice' ? (
            <ChoiceGrid
              disabled={answeringDisabled}
              onChange={setAnswer}
              spec={plan.spec}
              state={answer}
            />
          ) : null}
          {answer?.kind === 'free-entry' && plan.spec.kind === 'free-entry' ? (
            <FreeEntry
              disabled={answeringDisabled}
              onChange={setAnswer}
              spec={plan.spec}
              state={answer}
            />
          ) : null}
          {answer?.kind === 'count-selection' && plan.spec.kind === 'count-selection' ? (
            <CountSelection
              disabled={answeringDisabled}
              // Remount per question so the pool's local selection state cannot survive an advance.
              // (The surface also clears itself when the answer is reseeded, which is what "Try again"
              // does without changing the opportunity — both paths matter.)
              key={plan.itemOpportunityId}
              onChange={setAnswer}
              poolSize={poolSize}
              spec={plan.spec}
              state={answer}
            />
          ) : null}
        </View>

        {/* Hints sit below the answer surface and never gate it: the child can answer at any
            point, with or without asking for help. Only the MOST RECENT hint shows — requesting
            hint 2 replaces hint 1 on screen rather than stacking both (the earlier design kept
            every level visible at once; this is a deliberate change from that, at the user's own
            request). `hintView.received` is already ordered L1→L2→L3 (see hintStateFor), so the
            last entry is always the highest level received so far. */}
        {hintView.received.length > 0 ? (
          <View
            key={hintView.received[hintView.received.length - 1].hint_level}
            style={styles.hintCard}>
            <View style={styles.hintHeader}>
              <Ionicons color={colors.accentBlue} name="bulb" size={18} />
              <AppText style={styles.hintLevel}>
                Hint {hintView.received[hintView.received.length - 1].hint_level}
              </AppText>
            </View>
            <AppText style={styles.hintContent}>
              {hintView.received[hintView.received.length - 1].content}
            </AppText>
          </View>
        ) : null}

        {/* The request control itself now lives in the card's top-right corner (see taskHintRow,
            above); this is only the closed-door copy for once hints run out, since that message
            has nowhere else to live once the corner button disappears. */}
        {canRequestHint(hintView) ? null : (
          <AppText style={styles.hintClosed}>{HINTS_UNAVAILABLE_COPY}</AppText>
        )}

      </ScrollView>
      {/* The outcome popup: an absolutely positioned overlay (`outcomeOverlay`'s inset-0) sized to
          fill `taskScrollWrapper` exactly, since that wrapper — not `taskPanel` — is its nearest
          `position: 'relative'` ancestor. It therefore sits precisely over the stale question
          content and nowhere else: never the header row above or the footer below.
          `pointerEvents="box-none"` on the outer layers lets any tap that lands outside the popup
          itself (there is nothing to tap in the blurred question behind it anyway) fall through
          rather than swallowing input the rest of the card never offered. */}
      {view ? (
        <View pointerEvents="box-none" style={styles.outcomeOverlay}>
          <FrostedScrim intensity={40} style={styles.outcomeOverlay} />
          <View pointerEvents="box-none" style={styles.outcomePopupCenter}>
            <Animated.View
              entering={ZoomIn.duration(280).springify().damping(14)}
              // Re-keyed per opportunity: an outcome from the previous question must never appear
              // to "carry over" its entrance animation into this one.
              key={plan.itemOpportunityId}
              // Ternary, not two `&&` branches: a `timeout` outcome must land on one of the two
              // variants (matching the icon and text colour just below, which already do this),
              // never on neither — `&&` alone left `timeout` with no shadowColor override at all,
              // which fell back to the RN default (opaque black), rendering as a dark halo instead
              // of a coloured glow.
              style={[
                styles.outcomePopup,
                outcome === 'correct' ? styles.outcomeCorrect : styles.outcomeIncorrect,
              ]}>
              <View
                style={[
                  styles.outcomeIcon,
                  outcome === 'correct' ? styles.outcomeIconCorrect : styles.outcomeIconIncorrect,
                ]}>
                <Ionicons
                  color={colors.primaryForeground}
                  name={outcome === 'correct' ? 'checkmark' : 'heart-outline'}
                  size={30}
                />
              </View>
              <AppText
                align="center"
                style={[
                  styles.outcomeTitle,
                  outcome === 'correct' ? styles.outcomeTextCorrect : styles.outcomeTextIncorrect,
                ]}>
                {view.title}
              </AppText>
              {/* Empty for 'incorrect' (outcomeView) — no detail line to render there, rather than
                  an empty AppText taking up its line height for nothing. */}
              {view.detail ? (
                <AppText
                  align="center"
                  style={[
                    styles.muted,
                    outcome === 'correct' ? styles.outcomeTextCorrect : styles.outcomeTextIncorrect,
                  ]}>
                  {view.detail}
                </AppText>
              ) : null}
            </Animated.View>
          </View>
        </View>
      ) : null}
      </View>
          {/* Its own fixed box below the scrolling content, not part of it — the button's gap to
              the card's bottom edge (taskFooter's padding + the card's own border) is always
              exactly `footerBottomGap` (the measured pill-bottom-to-prompt-card-top distance),
              the same whether the question above has one line of hints or five, a choice grid or
              a pool of objects. Living inside the ScrollView would make that gap depend on how
              much content happened to be above it. */}
          <View style={[styles.taskFooter, { paddingBottom: footerPaddingBottom }]}>
            {/* Once an attempt is on record the child can always move on, including after a wrong
                answer — trying again is offered, never required. */}
            {view?.canTryAgain ? <PrimaryButton label="TRY AGAIN" onPress={tryAgain} /> : null}
            {view ? (
              <PrimaryButton
                busy={advancing}
                label="NEXT QUESTION"
                onPress={() => void advance()}
                // Starts `complete` on finger-down so the round trip overlaps the press itself.
                // For a correct or timed-out answer the pre-advance effect has already run and
                // this is a no-op; for a WRONG answer it is the only overlap available, because
                // TRY AGAIN needs the opportunity to stay open. See primeAdvanceOnIntent.
                onPressIn={primeAdvanceOnIntent}
                variant={view.canTryAgain ? 'secondary' : 'primary'}
              />
            ) : null}
            {!view ? (
              <PrimaryButton
                busy={submitting}
                disabled={!canSubmit}
                label="CHECK MY ANSWER"
                onPress={() => void submitAnswer()}
              />
            ) : null}
          </View>
        </View>
      </View>
    </SafeAreaView>
  );
}

function SessionFrame({ children }: { children: React.ReactNode }) {
  return (
    <SafeAreaView style={styles.safeArea}>
      <View style={styles.canvas}>{children}</View>
    </SafeAreaView>
  );
}

/**
 * A slow, continuous clockwise rotation of the background gradient around the screen's own centre.
 *
 * The gradient is drawn onto a square child sized to the screen's own DIAGONAL (measured via
 * onLayout, in real pixels — not a flat percentage guess): a screen-sized gradient rotated in
 * place would sweep its corners outside the visible area at 45°/135°/etc and expose whatever is
 * behind it there, and a fixed oversize like "200%" only happens to be enough in the dimension it
 * was tuned against — for a tall, narrow phone screen, 200% of the (shorter) WIDTH is well short
 * of the true diagonal, so the gradient's own edge became visible as a hard crop in two opposite
 * corners exactly where the oversized box ran out. The diagonal of a `width × height` rectangle,
 * `sqrt(width² + height²)`, is the minimal square side that still fully covers that rectangle at
 * every rotation angle — anything smaller can crop a corner at some angle, anything larger just
 * wastes more of the gradient's own colour transition on space that is never visible. Centred via
 * `(width - diagonal) / 2` / `(height - diagonal) / 2` (computed pixel offsets, not `-50%`, since
 * the child is no longer symmetric relative to the parent once sized to a measured diagonal rather
 * than a percentage of the parent's own two dimensions). `transform: rotate` always spins a view
 * around its own centre, and since this child's centre is (by construction) the same point as the
 * screen's centre, "around the screen's centre" falls out of that for free. `null` until the first
 * onLayout (nothing to size yet) renders nothing rather than a guessed box.
 */
/**
 * The bar is presentational only: it reads `SessionProgress`, already clamped by
 * `clampCompleted`, and never derives or guesses a count of its own.
 */
function ProgressBar({ progress }: { progress: SessionProgress }) {
  const completed = clampCompleted(progress);
  const fraction = progress.totalBound > 0 ? completed / progress.totalBound : 0;
  return (
    <View
      accessibilityLabel={`${completed} of ${progress.totalBound} questions done`}
      accessibilityRole="progressbar"
      style={styles.progressRow}>
      <View style={styles.progressTrack}>
        <Animated.View
          style={[styles.progressFill, { width: `${Math.round(fraction * 100)}%` }]}
        />
      </View>
      <AppText style={styles.progressText}>{`${completed}/${progress.totalBound}`}</AppText>
    </View>
  );
}

function PrimaryButton({
  busy = false,
  disabled = false,
  label,
  onPress,
  onPressIn,
  variant = 'primary',
}: {
  busy?: boolean;
  disabled?: boolean;
  label: string;
  onPress: () => void;
  /** Fired on finger-down, before release. Used to start work the press is about to need. */
  onPressIn?: () => void;
  variant?: 'primary' | 'secondary';
}) {
  const secondary = variant === 'secondary';
  return (
    <Pressable
      accessibilityRole="button"
      accessibilityState={{ disabled: disabled || busy }}
      disabled={disabled || busy}
      onPress={onPress}
      onPressIn={onPressIn}
      style={({ pressed }) => [
        styles.button,
        secondary && styles.buttonSecondary,
        (disabled || busy) && styles.buttonDisabled,
        pressed && !disabled && !busy && styles.buttonPressed,
      ]}>
      {busy ? (
        <ActivityIndicator color={secondary ? colors.primary : colors.primaryForeground} size="small" />
      ) : (
        <AppText style={[styles.buttonText, secondary && styles.buttonTextSecondary]}>{label}</AppText>
      )}
    </Pressable>
  );
}

const styles = StyleSheet.create({
  answerCenter: { flex: 1, gap: spacing.md, justifyContent: 'center' },
  // Matches c-session's own SubmitButton exactly (line-traversal-surface.tsx's `submitButton` /
  // `submitButtonDisabled` / `submitButtonText` / `pressed`, reproduced rather than imported since
  // none of the three is exported from that file — the same private-symbol situation its own
  // header comment describes for reusing value-report-surface.tsx's shapes): flat fill, no border,
  // no shadow, no press-down transform. `alignSelf: 'stretch'` and `borderRadius: radius.md` are
  // kept from B's own layout (the card's buttons fill the footer's width; C's SUBMIT does not need
  // to stretch itself since its container already sizes it), everything else in this block is C's.
  button: {
    alignItems: 'center',
    alignSelf: 'stretch',
    backgroundColor: colors.primary,
    borderRadius: radius.md,
    justifyContent: 'center',
    minHeight: 56,
    paddingHorizontal: spacing.lg,
  },
  buttonDisabled: { opacity: 0.5 },
  buttonPressed: { opacity: 0.72 },
  buttonSecondary: { backgroundColor: colors.surface1, borderColor: colors.primary, borderWidth: 2 },
  buttonTextSecondary: { color: colors.primary },
  buttonText: {
    color: colors.surface1,
    fontFamily: typography.fonts.bold,
    fontSize: typography.fontSize.lg,
  },
  canvas: { alignSelf: 'center', backgroundColor: colors.background, flex: 1, maxWidth: 500, width: '100%' },
  centered: { alignItems: 'center', flex: 1, gap: spacing.md, justifyContent: 'center', padding: spacing.lg },
  hintCard: {
    backgroundColor: colors.secondarySoft,
    borderRadius: radius.md,
    gap: spacing.xs,
    // Fixed regardless of which level is showing, so swapping from a short "Hint 1" to a longer
    // "Hint 3" (or back) doesn't visibly resize the box — `minHeight`, not `height`, so an
    // unusually long hint can still grow past it rather than being clipped.
    minHeight: 150,
    padding: spacing.smPlus,
  },
  hintClosed: { color: colors.textSecondary },
  // Both text styles in the hint card are 25% larger than their usual size: `hintLevel` off
  // `typography.fontSize.sm` (14 * 1.25 = 17.5, rounded), `hintContent` off the same body size
  // AppText's own default variant uses (16 * 1.25 = 20) — it was previously unstyled and inherited
  // that default outright, so scaling it needs an explicit style where none existed before.
  hintContent: { fontSize: 20, lineHeight: 30 },
  hintHeader: { alignItems: 'center', flexDirection: 'row', gap: spacing.xs },
  hintLevel: {
    color: colors.secondaryForeground,
    fontFamily: typography.fonts.bold,
    fontSize: 18,
    letterSpacing: typography.letterSpacing.label,
  },
  iconCircle: {
    alignItems: 'center',
    backgroundColor: colors.primarySoft,
    borderRadius: radius.xl,
    height: 88,
    justifyContent: 'center',
    width: 88,
  },
  muted: { color: colors.textSecondary },
  // Fills `taskScrollWrapper` exactly (see the JSX comment above its usage) — used both for the
  // FrostedScrim layer and for the pointer-events wrapper around it: both need the identical box.
  outcomeOverlay: { bottom: 0, left: 0, position: 'absolute', right: 0, top: 0 },
  // 50% of the scroll wrapper's own width/height, per the request — the wrapper IS the card's
  // working area (everything between the header row and the footer), so this reads as "half the
  // big card" without literally including the thin header/footer chrome in that measurement.
  // No background fill and no border: the popup sits directly on the blurred card behind it, with
  // only a soft glow (set per outcome below) marking its edge, shading outward rather than stopping
  // at a hard line or a filled box — the "fading away" look. `shadowOffset: {0, 0}` spreads the glow
  // evenly on every side instead of favouring one edge the way a drop shadow normally would.
  // `shadowOpacity` is pushed to 1 (full strength of the colour itself) rather than the usual
  // fractional value: that colour is already a pale near-white tint, so a "normal" shadow opacity
  // like 0.4-0.5 blends it into the card's own similarly pale background and the glow all but
  // disappears — it needs to be at full strength to read as a visible fade at all. `elevation`
  // (Android) cannot take a colour and falls back to a plain dark shadow there — an accepted
  // platform gap, not a separate bug to fix.
  outcomePopup: {
    alignItems: 'center',
    borderRadius: radius.lg,
    elevation: 10,
    gap: spacing.xs,
    height: '50%',
    justifyContent: 'center',
    padding: spacing.md,
    shadowOffset: { width: 0, height: 0 },
    shadowOpacity: 1,
    shadowRadius: 50,
    width: '50%',
  },
  outcomePopupCenter: { alignItems: 'center', flex: 1, justifyContent: 'center' },
  // Glow colour matches each variant's own background exactly (not the more saturated
  // success/danger tone), so the fade reads as the popup's own colour spreading outward rather
  // than a contrasting halo around it.
  outcomeCorrect: { shadowColor: '#e9f8f1' },
  outcomeIncorrect: { shadowColor: colors.secondarySoft },
  // Title/detail text tinted to each outcome's own saturated accent — #7bd3aa (colors.success) for
  // correct, matching the icon circle's own fill — now that the popup has no background of its own
  // to carry that colour instead.
  outcomeTextCorrect: { color: colors.success },
  outcomeTextIncorrect: { color: colors.accentRed },
  outcomeIcon: {
    alignItems: 'center',
    borderRadius: radius.pill,
    height: 56,
    justifyContent: 'center',
    width: 56,
  },
  outcomeIconCorrect: { backgroundColor: colors.success },
  outcomeIconIncorrect: { backgroundColor: colors.accentRed },
  outcomeTitle: {
    fontFamily: typography.fonts.display,
    fontSize: typography.fontSize.subtitle,
    lineHeight: typography.lineHeight.subtitle,
  },
  pressed: { opacity: 0.85 },
  progressFill: {
    backgroundColor: colors.primary,
    borderRadius: radius.pill,
    height: '100%',
  },
  progressRow: { alignItems: 'center', flexDirection: 'row', gap: spacing.sm },
  progressText: {
    color: colors.textSecondary,
    fontFamily: typography.fonts.bold,
    fontSize: typography.fontSize.sm,
  },
  progressTrack: {
    backgroundColor: colors.surface3,
    borderRadius: radius.pill,
    flex: 1,
    height: 14,
    overflow: 'hidden',
  },
  promptCard: {
    backgroundColor: colors.surface1,
    borderBottomColor: colors.borderStrong,
    borderBottomWidth: 3,
    borderColor: colors.border,
    borderRadius: radius.lg,
    borderWidth: 2,
    padding: spacing.md,
  },
  // Combined with `scroll`'s own `gap: spacing.md`, this doubles the visible gap between the
  // progress bar and this card specifically (see the JSX comment above its usage).
  promptCardAfterProgress: { marginTop: spacing.md },
  safeArea: { backgroundColor: colors.background, flex: 1 },
  // `flexGrow: 1` is what lets `answerCenter`'s own `flex: 1` mean something: without it the
  // content container sizes to its content's natural height and there is no leftover space for
  // `answerCenter` to claim, even when the card has plenty of room to spare.
  scroll: { flexGrow: 1, gap: spacing.md, padding: spacing.md },
  skillPill: {
    alignItems: 'center',
    alignSelf: 'center',
    backgroundColor: colors.primarySoft,
    borderRadius: radius.pill,
    flexDirection: 'row',
    gap: spacing.xs,
    paddingHorizontal: spacing.smPlus,
    paddingVertical: spacing.xs,
  },
  skillText: {
    color: colors.primaryShadow,
    fontFamily: typography.fonts.bold,
    fontSize: typography.fontSize.sm,
    letterSpacing: typography.letterSpacing.label,
  },
  // Deliberately the SAME type as `stem` below -- same family, size and line height -- because on
  // the templates that carry one, the instruction IS the question ("Guess the next number."), and
  // the stem under it is the material to work on ("2, 3, 4, __"), the way the dot grid is on
  // B-NS02. Rendering it smaller and greyer, as it first was, read as a caption and buried the
  // only sentence telling the child what to do. The single difference is the gap below it.
  instruction: {
    fontFamily: typography.fonts.display,
    fontSize: typography.fontSize.subtitle,
    lineHeight: typography.lineHeight.subtitle,
    marginBottom: spacing.sm,
    maxWidth: '100%',
  },
  stem: {
    fontFamily: typography.fonts.display,
    fontSize: typography.fontSize.subtitle,
    lineHeight: typography.lineHeight.subtitle,
    maxWidth: '100%',
  },
  supportCode: { color: colors.textMuted, fontSize: typography.fontSize.xs },
  // The question card: same shape as c-session's own task panel (game-family-accents.ts's
  // sibling), so the two components' games open into the same kind of object — a warm card on a
  // neutral ground, edged in the colour of the skill (here) or game family (there) it belongs to.
  taskCanvas: {
    alignItems: 'center',
    alignSelf: 'center',
    flex: 1,
    justifyContent: 'center',
    maxWidth: 500,
    width: '100%',
  },
  taskExitButton: {
    alignItems: 'center',
    backgroundColor: colors.surface1,
    borderColor: colors.border,
    borderRadius: radius.pill,
    borderWidth: 1,
    height: 44,
    justifyContent: 'center',
    width: 44,
  },
  taskHeaderRow: { left: spacing.smPlus, position: 'absolute', top: spacing.smPlus, zIndex: 2 },
  // Same corner treatment as taskHeaderRow, mirrored to the right: same size circle (taskExitButton),
  // same offset from the card's edge, same zIndex above the centred skill pill row.
  taskHintButton: { backgroundColor: colors.secondarySoft, borderColor: colors.secondary },
  taskHintRow: { position: 'absolute', right: spacing.smPlus, top: spacing.smPlus, zIndex: 2 },
  // Spans the card's full width (not just the space left of the exit button) so the pill centres
  // on the CARD's own x-axis. `pointerEvents="none"` on the row lets taps in its empty margins
  // pass through to whatever sits beneath rather than intercepting them — only the exit button,
  // which sits in its own row above this one (higher zIndex), is actually tappable up here.
  taskSkillPillRow: {
    alignItems: 'center',
    left: 0,
    position: 'absolute',
    right: 0,
    top: spacing.smPlus,
    zIndex: 1,
  },
  taskPanel: {
    backgroundColor: '#fffdf6',
    borderRadius: radius.lg,
    borderWidth: TASK_PANEL_BORDER_WIDTH,
    elevation: 5,
    height: '92%',
    padding: spacing.md,
    paddingTop: spacing.xxl,
    position: 'relative',
    shadowColor: colors.foreground,
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.18,
    shadowRadius: 7,
    width: '92%',
  },
  taskSafeArea: { backgroundColor: colors.background, flex: 1 },
  taskScroll: { flex: 1 },
  // `position: 'relative'` makes this the positioning root for `outcomeOverlay`'s absolute fill —
  // without it, the overlay would resolve against the next positioned ancestor up (`taskPanel`),
  // covering the header and footer too, which is exactly what this wrapper exists to prevent.
  taskScrollWrapper: { flex: 1, position: 'relative' },
  // Sits below the ScrollView as its own fixed box (see the JSX comment above it). `paddingBottom`
  // is set inline per render, from `footerPaddingBottom` — what is left over after subtracting the
  // panel's own border and bottom padding (both already sit between this box's bottom edge and the
  // card's outer edge) from `footerBottomGap`, the live-measured pill-bottom-to-prompt-card-top
  // gap (falling back to TASK_FOOTER_BOTTOM_GAP for the one frame before layout has measured
  // anything). `paddingHorizontal` matches `scroll`'s own horizontal padding so the buttons line up
  // with the question and answer surfaces above them, which sit inside BOTH the panel's padding
  // and the scroll's own.
  taskFooter: {
    gap: spacing.md,
    paddingHorizontal: spacing.md,
    paddingTop: spacing.sm,
  },
  visual: { marginTop: spacing.md },
});
