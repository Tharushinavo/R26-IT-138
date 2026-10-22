import { Ionicons } from '@expo/vector-icons';
import * as Crypto from 'expo-crypto';
import { Image } from 'expo-image';
import { router } from 'expo-router';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  ActivityIndicator,
  Pressable,
  StyleSheet,
  useWindowDimensions,
  View,
} from 'react-native';

import type { PendingStartSessionCommand, SessionCommandResponse } from '@/src/api/contracts';
import { artwork } from '@/src/utils/artwork';
import { createComponentBApi, getComponentBDevelopmentFixture } from '@/src/api/component-b-api';
import { ApiClientError } from '@/src/api/errors';
import type { ActiveSessionResponse } from '@/src/api/generated/openapi-types';
import { useAuth } from '@/src/auth/auth-context';
import { AppText } from '@/src/components/app-text';
import { readPublicConfig } from '@/src/config/env';
import { resolveResumableSessionId } from '@/src/features/session/resumable-session';
import { prefetchBSessionBootstrap } from '@/src/features/session/b-session-prefetch';
import {
  dropBSessionPrefetch,
  peekBSessionPrefetch,
  putBSessionPrefetch,
} from '@/src/features/session/b-session-prefetch-cache';
import {
  clearPendingStartCommand,
  loadPendingStartCommand,
  saveActiveSessionId,
  savePendingStartCommand,
} from '@/src/features/session/session-command-store';
import { colors, radius, spacing, typography } from '@/src/theme/tokens';
import { firstNameOf } from '@/src/utils/display-name';

const brandArtwork = artwork.mathmingoHeader;
const heroArtwork = artwork.prepareHero;
const heroAspectRatio = 1672 / 941;
const heroBorderWidth = 4;

// No skill is named on this screen, by necessity rather than preference: `skill_id` does not
// exist until a question is selected, and selection is what starts the child's timeout clock
// (timeout_deadline_utc = now + timeout, opportunity_persistence.py). GET /b/sessions/active
// cannot report whether a question is already open, so asking for the skill here would risk
// creating one and starting that clock while the child is still reading this screen. The real
// skill is shown per question on the live session screen, where OpportunityPresentationResponse
// carries skill_id legitimately and for free.
const gradeLabels: Record<'GRADE_2' | 'GRADE_3', string> = {
  GRADE_2: 'Grade 2',
  GRADE_3: 'Grade 3',
};

// `resolveResumableSessionId` moved to resumable-session.ts so the prefetch can use it without
// importing this screen -- see that file for the require cycle it broke. Re-exported here
// because this screen's own tests import it from this path.
export { resolveResumableSessionId };

type PreparationPhase =
  | 'checking-identity'
  | 'checking-readiness'
  | 'ready'
  | 'starting-session'
  | 'active-session'
  | 'authentication-failure'
  | 'access-denied'
  | 'readiness-failure'
  | 'network-failure'
  | 'technical-failure';

type LearnerView = { displayName: string };

function createStartCommand(): PendingStartSessionCommand {
  return {
    createdAt: new Date().toISOString(),
    endpoint: '/api/v1/b/sessions',
    idempotencyKey: Crypto.randomUUID(),
    kind: 'start_session',
  };
}

function readinessCopy(phase: PreparationPhase, awaitingQuestion = false) {
  if (phase === 'checking-identity' || phase === 'checking-readiness') {
    return { title: 'Checking session', detail: 'Getting everything ready' };
  }
  // "Session ready" while the first question is still in flight was the lie behind the press-then-
  // wait: the check had passed, but the thing the child is about to need had not arrived.
  if (awaitingQuestion) {
    return { title: 'Building your question', detail: 'Almost there…' };
  }
  if (phase === 'ready' || phase === 'starting-session' || phase === 'active-session') {
    return { title: 'Session ready', detail: 'Everything looks good!' };
  }
  if (phase === 'authentication-failure') {
    return { title: 'Sign-in needed', detail: 'Ask a grown-up for help' };
  }
  if (phase === 'access-denied') {
    return { title: 'Learning pass needed', detail: 'Ask your teacher for help' };
  }
  return { title: 'Almost ready', detail: 'Try again in a moment' };
}

export function SessionPreparationScreen() {
  const { height } = useWindowDimensions();
  const compact = height < 760;
  const { getAccessToken, me, profileName, retryAuthorization, status } = useAuth();
  const configResult = useMemo(() => readPublicConfig(), []);
  const fixture = getComponentBDevelopmentFixture();
  const api = useMemo(
    () =>
      configResult.config || fixture
        ? createComponentBApi(configResult.config ?? undefined)
        : null,
    [configResult.config, fixture],
  );
  const [phase, setPhase] = useState<PreparationPhase>('checking-identity');
  const [learner, setLearner] = useState<LearnerView | null>(null);
  const [resumableSessionId, setResumableSessionId] = useState<string | null>(null);
  const mountedRef = useRef(true);
  const runningRef = useRef(false);
  const autoAdvancedRef = useRef(false);
  const subject = me?.principal.user_id ?? null;
  // Whether the first question is actually in hand. Reaching this screen directly -- a typed URL,
  // a relaunch, the tab bar -- brings no prefetch from Home, so this screen primes its own (see
  // the effect below) and the button says what is really happening until it lands, instead of
  // offering "Start Adventure" and then stalling on a press.
  const [questionReady, setQuestionReady] = useState(false);
  const primedRef = useRef(false);
  // Declared HERE, with the state it derives from, rather than down beside `busy` where it is
  // first used. React Compiler is enabled on this project and hoists derived values into memo
  // blocks, which can evaluate them ahead of their written position -- a declaration sitting
  // below the effects produced a "Cannot access 'awaitingQuestion' before initialization" at
  // runtime that `tsc` cannot see. Keeping it above every effect removes the ordering hazard.
  //
  // A question that has not landed yet is a real reason to be busy: the press would otherwise
  // succeed instantly and then stall on the session screen, which is the delay this removes.
  const awaitingQuestion = phase === 'ready' && !questionReady && !fixture && subject !== null;

  const navigateToSession = useCallback(async (sessionId: string) => {
    await saveActiveSessionId(subject, sessionId);
    await clearPendingStartCommand(subject);
    if (!mountedRef.current) return;
    setPhase('active-session');
    router.replace({
      pathname: '/(learner)/session/[sessionId]',
      params: { sessionId },
    });
  }, [subject]);

  const openActiveSession = useCallback(
    async (response: SessionCommandResponse) => {
      // A non-'active' state here (completed/abandoned) has nothing to resume into — this is
      // reached only from the start-a-new-session path, never from the resume path below (which
      // only ever targets a session resolveResumableSessionId already confirmed is 'active').
      if (response.state !== 'active') {
        setPhase('technical-failure');
        return;
      }
      await navigateToSession(response.session_id);
    },
    [navigateToSession],
  );

  const checkReadiness = useCallback(async () => {
    if (runningRef.current || !api) return false;
    runningRef.current = true;
    setPhase('checking-readiness');
    try {
      await api.checkReadiness();
      if (!mountedRef.current) return false;
      setPhase('ready');
      // Skip the resume check for the fixture: FE-0d made createFixtureApi.getActiveSession
      // throw by design (the fixture covers the prep screen's readiness/start path only), so
      // calling it here would just be a swallowed error masquerading as "no active session" —
      // an explicit skip keeps that distinction visible instead of hiding a real regression.
      if (!fixture) {
        const accessToken = await getAccessToken();
        if (accessToken && mountedRef.current) {
          const sessionId = await resolveResumableSessionId(api, accessToken);
          if (mountedRef.current) {
            setResumableSessionId(sessionId);
            if (sessionId) await saveActiveSessionId(subject, sessionId);
          }
        }
      }
      return true;
    } catch (error) {
      if (!mountedRef.current) return false;
      if (error instanceof ApiClientError && error.kind === 'forbidden') {
        setPhase('access-denied');
      } else if (
        error instanceof ApiClientError &&
        (error.kind === 'network' || error.kind === 'timeout')
      ) {
        setPhase('network-failure');
      } else if (error instanceof ApiClientError && error.kind === 'unauthenticated') {
        setPhase('authentication-failure');
      } else {
        setPhase('readiness-failure');
      }
      return false;
    } finally {
      runningRef.current = false;
    }
  }, [api, fixture, getAccessToken, subject]);

  const sendStartCommand = useCallback(
    async (command: PendingStartSessionCommand, accessToken: string) => {
      if (!api) return;
      setPhase('starting-session');
      try {
        const response = await api.startSession(command.idempotencyKey, accessToken);
        await openActiveSession(response);
      } catch (error) {
        if (!mountedRef.current) return;
        if (error instanceof ApiClientError && error.kind === 'unauthenticated') {
          const refreshedToken = await getAccessToken(true);
          if (refreshedToken) {
            try {
              const response = await api.startSession(command.idempotencyKey, refreshedToken);
              await openActiveSession(response);
              return;
            } catch (retryError) {
              if (retryError instanceof ApiClientError && retryError.kind === 'forbidden') {
                setPhase('access-denied');
                return;
              }
            }
          }
          setPhase('authentication-failure');
          return;
        }
        if (error instanceof ApiClientError && error.kind === 'forbidden') {
          setPhase('access-denied');
        } else if (
          error instanceof ApiClientError &&
          (error.kind === 'network' || error.kind === 'timeout')
        ) {
          setPhase('network-failure');
        } else {
          setPhase('technical-failure');
        }
      }
    },
    [api, getAccessToken, openActiveSession],
  );

  const startAdventure = useCallback(async () => {
    if (runningRef.current || !api || phase === 'access-denied') return;
    runningRef.current = true;
    try {
      if (phase !== 'ready' && phase !== 'network-failure' && phase !== 'technical-failure') {
        runningRef.current = false;
        if (phase === 'authentication-failure' && !fixture) await retryAuthorization();
        const ready = await checkReadiness();
        if (!ready) return;
        runningRef.current = true;
      }

      if (resumableSessionId) {
        await navigateToSession(resumableSessionId);
        return;
      }

      // Home's prefetch has usually already started the session and selected the question. Await
      // it rather than POSTing again: /b/sessions would return the same session anyway (it takes
      // an advisory lock and returns any starting-or-active one regardless of idempotency key),
      // but the extra round trip is time spent from the question's already-running clock. The
      // entry is only peeked here -- live-session-screen.tsx is what consumes it, so the question
      // it carries survives this navigation.
      if (subject) {
        const prefetch = peekBSessionPrefetch(subject);
        if (prefetch) {
          try {
            const result = await prefetch;
            if (!mountedRef.current) return;
            if (result) {
              await navigateToSession(result.sessionId);
              return;
            }
            // `null` means "nothing to hand off" (no token/config) -- fall through to the normal
            // start path below, which owns the resulting failure phases.
            dropBSessionPrefetch(subject);
          } catch {
            // A failed prefetch is not the child's problem: drop it and start normally, which is
            // exactly the behaviour that existed before the prefetch did.
            dropBSessionPrefetch(subject);
            if (!mountedRef.current) return;
          }
        }
      }

      let accessToken = fixture ? 'development-fixture-token' : await getAccessToken();
      if (!accessToken && !fixture) {
        setPhase('authentication-failure');
        return;
      }
      const pending = await loadPendingStartCommand(subject);
      const command = pending ?? createStartCommand();
      if (!pending) await savePendingStartCommand(subject, command);
      accessToken ??= 'development-fixture-token';
      await sendStartCommand(command, accessToken);
    } finally {
      runningRef.current = false;
    }
  }, [
    api,
    checkReadiness,
    fixture,
    getAccessToken,
    navigateToSession,
    phase,
    resumableSessionId,
    retryAuthorization,
    subject,
    sendStartCommand,
  ]);

  // Prime the question as soon as this screen knows who the learner is, and track when it lands.
  // Home already starts one on its hero/resume press; this covers every other way in. Doing it
  // here rather than only on Home is what removes the press-then-wait: by the time the button is
  // offered, the question exists.
  //
  // NOT GATED ON `phase === 'ready'` ANY MORE (FE-005, 2026-10-09). It was, which meant that on
  // every arrival WITHOUT a prefetch from Home -- a tab return, a relaunch, a deep link -- this
  // waited for `checkReadiness()` to come back before it even started: `GET /health/ready` opens a
  // database connection to run `SELECT 1`, measured at ~500ms warm and ~2.1s cold, and the session
  // bootstrap then ran after it. Nothing required that order. Readiness answers "is the
  // infrastructure up", which this screen uses only to choose a failure phase; it is not an input
  // to starting a session, and the server re-checks everything that actually matters on each call.
  // Both now run from mount, concurrently -- which is what b-session-prefetch.ts's own header
  // already claimed happened ("the preparation screen runs it in parallel on its own mount") and
  // what the `phase` gate was quietly preventing.
  //
  // Authorization is NOT weakened by starting earlier. The prefetch resolves a token or returns
  // `null`, and every request it makes is still authorized server-side -- a learner without access
  // gets a 403 and the prefetch rejects, which `startAdventure` already treats as "fall through to
  // the normal path". A readiness failure likewise fails the session start itself rather than
  // producing a session that cannot serve questions.
  //
  // `subject` is still required: without it there is no cache key, and the entry would be
  // unreachable by the consumer.
  useEffect(() => {
    if (!subject || fixture) return;
    let cancelled = false;
    if (!peekBSessionPrefetch(subject) && !primedRef.current) {
      primedRef.current = true;
      putBSessionPrefetch(subject, prefetchBSessionBootstrap(subject, getAccessToken));
    }
    const pending = peekBSessionPrefetch(subject);
    if (!pending) return;
    // SETTLED is what "ready" means here, not "succeeded". A resolved `null` means the prefetch
    // had nothing to hand off (no token, no config) and a rejection means it failed outright --
    // in both cases `startAdventure` falls through to the normal start path, which works. Treating
    // either as not-ready leaves the button stuck on "Getting ready..." forever, which is what an
    // earlier `setQuestionReady(value !== null)` here actually did.
    const settled = () => {
      if (!cancelled && mountedRef.current) setQuestionReady(true);
    };
    void pending.then(settled, settled);
    return () => {
      cancelled = true;
    };
  }, [fixture, getAccessToken, subject]);

  // AUTO-ADVANCE (owner ruling, 2026-09-27; BEHAVIOUR REAFFIRMED and this rationale CORRECTED
  // 2026-10-10). Home's hero/resume buttons start a background prefetch (b-session-prefetch.ts)
  // that has already started the session AND selected the first question by the time this screen
  // settles. A prefetched FRESH start therefore goes straight through rather than waiting on a tap.
  //
  // WHY, stated correctly: continuity. The child sees ONE loading surface -- this screen's own
  // artwork -- instead of it and then "Getting your question ready...", and one fewer tap stands
  // between them and the question they already asked for.
  //
  // WHY NOT, and this is the correction: it is NOT needed to protect the child's five-minute
  // answering budget. This comment used to say the prefetch "lit" that clock and auto-advancing
  // bounded the burn. It does not. `POST .../presented` -> `anchor_presentation` sets
  // `timeout_deadline_utc = now + timeout` on the FIRST acknowledgement, which
  // live-session-screen.tsx sends when the question renders -- so the clock starts when the child
  // can see the question, however long they spent on this screen. The backend is explicit that
  // anchoring at selection "charged the child for server and network time -- prefetch included",
  // which is why it stopped doing so. Do not re-justify auto-advance on clock grounds, and do not
  // treat a child-paced wait on THIS screen as a hazard to the answering budget.
  //
  // Deliberately NOT auto-advanced:
  //   - A resume. "Resume Adventure" is a real choice about re-entering work already in progress,
  //     so skipping the tap takes that choice away. (Its question was already presented once, so
  //     its deadline is already anchored and a second ack is a no-op either way.)
  //   - Any screen reached without a prefetch (deep link, relaunch, tab return). The child never
  //     asked to be sent straight in, so they keep the button.
  //   - Any non-'ready' phase. Every failure phase keeps its own copy and its own retry.
  useEffect(() => {
    if (phase !== 'ready' || autoAdvancedRef.current) return;
    if (!subject || resumableSessionId || fixture) return;
    // Only once the question has actually landed -- auto-advancing into a still-loading question
    // would just move the wait onto the session screen, which is the thing this removes. And only
    // for a prefetch that came from Home's own press: a child who arrived here directly never
    // asked to be sent straight in, so they keep the button.
    if (primedRef.current || !questionReady) return;
    if (!peekBSessionPrefetch(subject)) return;
    autoAdvancedRef.current = true;
    void startAdventure();
  }, [fixture, phase, questionReady, resumableSessionId, startAdventure, subject]);


  useEffect(() => {
    mountedRef.current = true;
    if (fixture) {
      // Neutral placeholder, not a person's name. This used to hardcode a real person's first name,
      // which in a fixture run means a child could be addressed as someone else.
      setLearner({ displayName: 'Math Explorer' });
      void checkReadiness();
    } else if (status === 'authorized' && me?.learnerProfile) {
      setLearner({
        displayName: me.learnerProfile.name.trim() || profileName || 'Math Explorer',
      });
      void checkReadiness();
    } else if (status === 'access-denied') {
      setPhase('access-denied');
    } else if (status !== 'checking') {
      setPhase('authentication-failure');
    }
    return () => {
      mountedRef.current = false;
    };
  }, [checkReadiness, fixture, me, profileName, status]);

  const readiness = readinessCopy(phase, awaitingQuestion);
  const busy =
    phase === 'checking-identity' ||
    phase === 'checking-readiness' ||
    phase === 'starting-session' ||
    awaitingQuestion;
  const disabled = busy || phase === 'access-denied' || phase === 'active-session';
  const displayName = firstNameOf(learner?.displayName || profileName || 'Math Explorer');
  // Only an APPROVED membership is shown; a PENDING/REJECTED one is not a classroom the learner
  // is in yet. The fixture path has no membership, so the card simply does not render there.
  const classroom = me?.classroomMembership?.state === 'APPROVED' ? me.classroomMembership : null;

  return (
    <View style={styles.safeArea}>
      <View style={styles.mobileCanvas}>
        <View style={[styles.header, compact && styles.headerCompact]}>
          <Image
            accessibilityLabel="MathMingo"
            contentFit="contain"
            source={brandArtwork}
            style={[styles.brandArtwork, compact && styles.brandArtworkCompact]}
          />
          <AppText numberOfLines={1} style={[styles.greeting, compact && styles.greetingCompact]}>
            Hi, <AppText style={[styles.greetingName, compact && styles.greetingNameCompact]}>{displayName}!</AppText>
          </AppText>
        </View>

        <View style={[styles.scrollContent, compact && styles.scrollContentCompact]}>
          <View style={styles.hero}>
            <Image
              accessibilityLabel="MathMingo beside a learning path"
              contentFit="cover"
              source={heroArtwork}
              style={styles.heroArtwork}
            />
            <View style={styles.heroCopy}>
              <AppText
                numberOfLines={1}
                style={[styles.heroTitle, compact && styles.heroTitleCompact]}>
                Get{' '}
                <AppText style={[styles.heroReady, compact && styles.heroReadyCompact]}>
                  Ready!
                </AppText>
              </AppText>
              <AppText style={[styles.heroSubtitle, compact && styles.heroSubtitleCompact]}>
                Let&apos;s start your{`\n`}
                <AppText style={[styles.heroSkill, compact && styles.heroSkillCompact]}>
                  maths
                </AppText>{' '}
                adventure
              </AppText>
            </View>
          </View>

          {/* Classroom + grade, both real fields on the learner's own approved membership
              (LearnerMembershipListItem.classroom_name / .grade) — not a lesson or skill claim,
              which this screen cannot make. Rendered only when a membership is actually loaded. */}
          {classroom ? (
            <View style={styles.lessonCard}>
              <View style={styles.lessonColumn}>
                <View style={[styles.lessonIcon, styles.skillIcon]}>
                  <Ionicons color={colors.primaryForeground} name="school" size={compact ? 24 : 28} />
                </View>
                <View>
                  <AppText style={styles.lessonLabel}>{gradeLabels[classroom.grade]}</AppText>
                  <AppText style={styles.lessonValue}>{classroom.classroom_name ?? 'Your classroom'}</AppText>
                </View>
              </View>
            </View>
          ) : null}

          <View style={[styles.preparationCard, compact && styles.preparationCardCompact]}>
            <AppText style={[styles.sectionTitle, compact && styles.sectionTitleCompact]}>
              Let&apos;s get ready!
            </AppText>
            <PreparationItem
              color={colors.accentGreen}
              compact={compact}
              detail={readiness.detail}
              icon={busy ? 'hourglass-outline' : 'checkmark'}
              loading={busy}
              title={readiness.title}
            />
            {/* KEPT, and re-verified rather than assumed. This claim was false when written: only 2
                of the 36 templates carried hint content, so ~94% of the time asking for help
                returned a neutral 409. BE-C1 ported the governed L1/L2/L3 hints from R26-IT-138 §11
                to all 36, and every one of the 108 lookups now resolves through
                `LiveEngineAdapter.get_hint` (checked against the live catalogue for this batch). The
                claim is now true, so it stays.
                A third item used to follow, promising unlimited retries at the learner's own pace. It
                was REMOVED: attempt limits are Gate-B unresolved, so the app cannot promise that.
                Nothing replaces it — the card is flex: 1 and absorbs the space rather than needing
                filler. (Its wording is not quoted here; a grep guard in
                home-session-progress.test.ts enforces its absence.) */}
            <PreparationItem
              color="#ffb000"
              compact={compact}
              detail="Get helpful hints anytime"
              icon="bulb-outline"
              title="Hints available"
            />
          </View>

          <Pressable
            accessibilityHint="Starts or resumes your prepared math session"
            accessibilityRole="button"
            accessibilityState={{ disabled }}
            disabled={disabled}
            onPress={() => void startAdventure()}
            style={({ pressed }) => [
              styles.startButton,
              disabled && styles.startButtonDisabled,
              pressed && styles.startButtonPressed,
            ]}>
            {phase === 'starting-session' || awaitingQuestion ? (
              <>
                <ActivityIndicator color={colors.primaryForeground} size="small" />
                <AppText style={styles.startButtonText}>Getting ready…</AppText>
              </>
            ) : (
              <AppText style={styles.startButtonText}>
                {resumableSessionId ? 'Resume Adventure' : 'Start Adventure'}
              </AppText>
            )}
            <Ionicons color={colors.primaryForeground} name="chevron-forward" size={26} />
          </Pressable>
        </View>

      </View>
    </View>
  );
}

function PreparationItem({
  color,
  compact = false,
  detail,
  icon,
  loading = false,
  title,
}: {
  color: string;
  compact?: boolean;
  detail: string;
  icon: React.ComponentProps<typeof Ionicons>['name'];
  loading?: boolean;
  title: string;
}) {
  return (
    <View style={[styles.preparationItem, compact && styles.preparationItemCompact]}>
      <View style={[styles.preparationIcon, compact && styles.preparationIconCompact, { backgroundColor: color }]}>
        {loading ? (
          <ActivityIndicator color={colors.primaryForeground} size="small" />
        ) : (
          <Ionicons color={colors.primaryForeground} name={icon} size={compact ? 19 : 23} />
        )}
      </View>
      <View style={styles.preparationCopy}>
        <AppText style={[styles.preparationTitle, compact && styles.preparationTitleCompact]}>{title}</AppText>
        <AppText style={[styles.preparationDetail, compact && styles.preparationDetailCompact]}>{detail}</AppText>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  brandArtwork: { aspectRatio: 1916 / 821, height: 68 },
  brandArtworkCompact: { height: 56 },
  greeting: { flexShrink: 1, fontFamily: typography.fonts.body, fontSize: 25, lineHeight: 30, textAlign: 'right' },
  greetingCompact: { fontSize: 21, lineHeight: 25 },
  greetingName: { color: '#26A5FD', fontFamily: typography.fonts.heavy, fontSize: 33.75, lineHeight: 40.5 },
  greetingNameCompact: { fontSize: 28.35, lineHeight: 33.75 },
  header: { alignItems: 'center', flexDirection: 'row', justifyContent: 'space-between', paddingBottom: spacing.md, paddingHorizontal: spacing.smPlus, paddingTop: 4 },
  headerCompact: { paddingBottom: spacing.sm },
  hero: { aspectRatio: heroAspectRatio, backgroundColor: colors.secondarySoft, borderColor: colors.surface1, borderRadius: radius.lg, borderWidth: heroBorderWidth, overflow: 'hidden', position: 'relative', width: '100%' },
  heroArtwork: { bottom: -heroBorderWidth, left: -heroBorderWidth, position: 'absolute', right: -heroBorderWidth, top: -heroBorderWidth },
  heroCopy: { left: '8%', position: 'absolute', top: '16%', width: '62%' },
  heroReady: { color: '#ffb000', fontFamily: typography.fonts.heavy, fontSize: 42 },
  heroReadyCompact: { fontSize: 33.6 },
  heroSkill: { color: colors.primary, fontFamily: typography.fonts.display, fontSize: 19.95 },
  heroSkillCompact: { fontSize: 16.8 },
  heroSubtitle: { fontFamily: typography.fonts.body, fontSize: 19, lineHeight: 22.41, marginTop: spacing.sm },
  heroSubtitleCompact: { fontSize: 16, lineHeight: 18.26, marginTop: 5 },
  heroTitle: { fontFamily: typography.fonts.display, fontSize: 40, lineHeight: 46 },
  heroTitleCompact: { fontSize: 32, lineHeight: 37 },
  lessonCard: { backgroundColor: colors.surface1, borderColor: colors.border, borderRadius: radius.lg, borderWidth: 1, elevation: 2, flexDirection: 'row', gap: spacing.md, padding: spacing.md, shadowColor: colors.foreground, shadowOffset: { width: 0, height: 2 }, shadowOpacity: 0.1, shadowRadius: 3 },
  lessonColumn: { alignItems: 'center', flex: 1, flexDirection: 'row', gap: spacing.smPlus },
  lessonIcon: { alignItems: 'center', borderRadius: radius.pill, height: 52, justifyContent: 'center', width: 52 },
  lessonLabel: { color: colors.textSecondary, fontSize: typography.fontSize.sm, lineHeight: typography.lineHeight.sm },
  lessonValue: { fontFamily: typography.fonts.bold, fontSize: typography.fontSize.lg, lineHeight: typography.lineHeight.lg },
  mobileCanvas: { alignSelf: 'center', backgroundColor: colors.background, flex: 1, maxWidth: 500, width: '100%' },
  preparationCard: { backgroundColor: colors.surface1, borderColor: colors.border, borderRadius: radius.lg, borderWidth: 1, elevation: 2, flex: 1, gap: spacing.sm, padding: spacing.md, shadowColor: colors.foreground, shadowOffset: { width: 0, height: 2 }, shadowOpacity: 0.1, shadowRadius: 3 },
  preparationCardCompact: { gap: spacing.xs, padding: spacing.smPlus },
  preparationCopy: { flex: 1, justifyContent: 'center' },
  preparationDetail: { color: colors.textSecondary, fontSize: typography.fontSize.sm, lineHeight: typography.lineHeight.sm },
  preparationDetailCompact: { fontSize: typography.fontSize.xs, lineHeight: typography.lineHeight.xs },
  preparationIcon: { alignItems: 'center', borderRadius: radius.pill, height: 44, justifyContent: 'center', width: 44 },
  preparationIconCompact: { height: 34, width: 34 },
  preparationItem: { alignItems: 'center', borderColor: colors.border, borderRadius: radius.md, borderWidth: 1, flex: 1, flexDirection: 'row', gap: spacing.smPlus, paddingHorizontal: spacing.md, paddingVertical: spacing.xs },
  preparationItemCompact: { gap: spacing.sm, paddingHorizontal: spacing.smPlus, paddingVertical: 2 },
  preparationTitle: { fontFamily: typography.fonts.bold, fontSize: typography.fontSize.body, lineHeight: typography.lineHeight.body },
  preparationTitleCompact: { fontSize: typography.fontSize.sm, lineHeight: typography.lineHeight.sm },
  safeArea: { backgroundColor: colors.background, flex: 1 },
  scrollContent: { flex: 1, gap: spacing.md, paddingBottom: spacing.lg, paddingHorizontal: spacing.sm },
  scrollContentCompact: { gap: spacing.smPlus },
  sectionTitle: { fontFamily: typography.fonts.display, fontSize: typography.fontSize.subtitle, lineHeight: typography.lineHeight.subtitle },
  sectionTitleCompact: { fontSize: typography.fontSize.lg, lineHeight: typography.lineHeight.lg },
  skillIcon: { backgroundColor: colors.primary },
  startButton: { alignItems: 'center', alignSelf: 'center', backgroundColor: colors.primary, borderColor: colors.surface1, borderRadius: 14.88, borderWidth: 2, elevation: 2, flexDirection: 'row', justifyContent: 'center', marginBottom: spacing.sm, marginTop: 'auto', minHeight: 62, paddingHorizontal: spacing.lg, shadowColor: colors.foreground, shadowOffset: { width: 0, height: 2 }, shadowOpacity: 0.1, shadowRadius: 3, width: '86%' },
  startButtonDisabled: { opacity: 0.55 },
  startButtonPressed: { opacity: 0.88, transform: [{ translateY: 2 }] },
  startButtonText: { color: colors.primaryForeground, flex: 1, fontFamily: typography.fonts.bold, fontSize: 20, lineHeight: 28, textAlign: 'center' },
});
