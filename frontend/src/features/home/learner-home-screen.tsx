import { useCallback, useEffect, useMemo, useRef, useState } from 'react';

import { Ionicons } from '@expo/vector-icons';
import { Image } from 'expo-image';
import { router } from 'expo-router';
import {
  Animated,
  InteractionManager,
  Platform,
  Pressable,
  type ScrollView,
  StyleSheet,
  useWindowDimensions,
  View,
} from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { artwork } from '@/src/utils/artwork';
import { createComponentBApi } from '@/src/api/component-b-api';
import { useAuth } from '@/src/auth/auth-context';
import { AppText } from '@/src/components/app-text';
import { readPublicConfig } from '@/src/config/env';
import {
  readHomeSessionState,
  writeHomeSessionState,
} from '@/src/features/home/home-session-state-cache';
import {
  combineHomeSessionState,
  derivePathNodeStates,
  pathNodeLabel,
  type HomeSessionState,
  type PathNodeState,
} from '@/src/features/home/session-progress';
import {
  LearnerHeaderBar,
  LEARNER_HEADER_HEIGHT,
  LEARNER_HEADER_HEIGHT_COMPACT,
} from '@/src/features/navigation/learner-header-bar';
import { prefetchBSessionBootstrap } from '@/src/features/session/b-session-prefetch';
import {
  peekBSessionPrefetch,
  putBSessionPrefetch,
} from '@/src/features/session/b-session-prefetch-cache';
import { colors, radius, spacing, typography } from '@/src/theme/tokens';
import { firstNameOf } from '@/src/utils/display-name';

const heroArtwork = artwork.heroSection;
const learningPathArtwork = artwork.learningPath;
const heroAspectRatio = 1672 / 941;
const heroBorderWidth = 4;
/** Fraction of the hero's scrollable distance past which a settled gesture snaps to the path instead of back to the hero. */
const heroSnapThreshold = 0.3;

/**
 * Module-scoped, not persisted: resets on app relaunch (new JS runtime), stays
 * true across navigations within the same app session once the learner scrolls
 * past the hero once.
 */
let heroDismissedThisAppSession = false;

// Node POSITIONS ONLY — where the artwork's path markers sit, and the colour each one is painted.
// These are facts about the illustration, not about the session, and their count is a property of
// the artwork rather than a session length: `PATH_NODE_POSITIONS.length` is passed to
// `derivePathNodeStates` as the number of positions available to draw into, and the number of nodes
// actually drawn comes from the server's `opportunities_total_bound`. No session length is assumed
// or hardcoded here.
//
// What used to be here — a skill-label table plus per-node skill ids and lesson-status subtitles — is
// gone. The server has no path, no ordering and no per-skill progress, so those labels asserted a
// structure the backend does not have. See session-progress.ts for the reframe. (The exact removed
// strings are deliberately not quoted anywhere in this file: home-session-progress.test.ts greps for
// them bluntly, and a guard with exemptions is a guard nobody trusts.)
const PATH_NODE_POSITIONS = [
  { color: colors.primary, left: '5%', top: '14%' },
  { color: colors.accentBlue, left: '20%', top: '27.5%' },
  { color: colors.accentGreen, left: '9%', top: '41%' },
  { color: '#ffb51f', left: '19%', top: '54.5%' },
  { color: '#9a64df', left: '20%', top: '68%' },
] as const;

// `current` reads differently depending on whether a session is already running: mid-session it is
// the question the child left off at, on a fresh path it is where they begin. Same node, same play
// control, different truth.
const nodeSubtitles: Record<PathNodeState, string> = {
  current: 'Up next',
  done: 'Answered',
  pending: 'Not started',
};
const FRESH_START_SUBTITLE = 'Start here';

/** Shared learner landing page; Component B owns the lesson path and preparation entry points. */
export function LearnerHomeScreen() {
  const { height, width } = useWindowDimensions();
  const insets = useSafeAreaInsets();
  const compact = height < 760;
  const { getAccessToken, me, profileName } = useAuth();
  // The authenticated Supabase subject: keys the Home->prep prefetch handoff.
  const subject = me?.principal.user_id ?? null;
  // The personal-name fallback that used to sit at the end of this chain is gone: it was a real
  // person's name, so a child whose profile had not loaded yet was greeted as someone else.
  // 'Math Explorer' is the same neutral placeholder the prep screen uses. (The removed name is not
  // quoted here — a grep guard enforces its absence.)
  const displayName = firstNameOf(me?.learnerProfile?.name.trim() || profileName || 'Math Explorer');
  const configResult = useMemo(() => readPublicConfig(), []);
  const api = useMemo(
    () => (configResult.config ? createComponentBApi(configResult.config) : null),
    [configResult.config],
  );
  // SEEDED FROM THE LAST RESOLVED STATE, not from the neutral one. Home unmounts on every
  // navigation, so starting at not-in-progress meant each return repainted "Ready to Play" /
  // question 1 "Start here" until two sequential reads finished, then snapped to the real panel.
  // See home-session-state-cache.ts for the full account. A learner with nothing cached (cold
  // start, or a different account) still begins at the neutral state exactly as before.
  const [sessionState, setSessionState] = useState<HomeSessionState>(
    () => readHomeSessionState(subject) ?? { kind: 'not-in-progress' },
  );
  const mountedRef = useRef(true);

  /**
   * One place where a server-confirmed state is both remembered and rendered, so the two can never
   * drift. The cache write is NOT guarded by `mountedRef`: the server's answer is just as true if
   * the child navigated away mid-read, and remembering it is what makes the NEXT return instant.
   * Only the React state update is guarded, because setting state on an unmounted screen is the
   * thing that is actually invalid.
   */
  const applyResolvedSessionState = useCallback(
    (next: HomeSessionState) => {
      writeHomeSessionState(subject, next);
      if (!mountedRef.current) return;
      setSessionState(next);
    },
    [subject],
  );

  // Two best-effort reads. Neither may block the screen: any failure degrades to not-in-progress,
  // which is self-correcting because POST /b/sessions returns an existing session anyway (see
  // combineHomeSessionState). The home screen must never show a child an error where their path was.
  useEffect(() => {
    mountedRef.current = true;
    const load = async () => {
      if (!api) return;
      try {
        const accessToken = await getAccessToken();
        if (!accessToken) return;
        const { session } = await api.getActiveSession(accessToken);
        if (!session || session.state !== 'active') {
          // A DEFINITIVE "nothing in progress" -- the server answered, there is just no active
          // session. This branch used to `return` and leave the state alone, which was harmless
          // only because the state always started neutral. With a seeded cache it is load-bearing:
          // without it, a session the child just FINISHED would keep rendering as in-progress for
          // the rest of the app session. Remember what the server said, including when it says no.
          applyResolvedSessionState({ kind: 'not-in-progress' });
          return;
        }
        const summary = await api.getSessionSummary(session.session_id, accessToken);
        applyResolvedSessionState(combineHomeSessionState(session, summary));
      } catch {
        // Deliberately silent, and deliberately NOT cached: a failed read is not an answer, so the
        // last state the server did confirm stays on screen rather than being replaced by a
        // neutral panel the server never asserted.
      }
    };
    void load();
    return () => {
      mountedRef.current = false;
    };
  }, [api, applyResolvedSessionState, getAccessToken]);

  // Once this screen has been visited and left AT ALL — the Play tab (LearnerTabBar's Play button,
  // which this screen has no other hook into and which now goes straight into a Component C
  // session, no game-hub menu in between), the hero button, a scroll-dismiss, anything — a later
  // return should open straight at the session card, never back at the hero. `openBLearning` and
  // handleGestureSettle's snap branch already set the same module flag for their own specific paths
  // (and keep doing so, since dismissTriggeredRef and showContinuationFade still need to react
  // within THIS mount); this cleanup-only effect is the catch-all that covers every OTHER way of
  // leaving (including Component C's own X button, c-session-screen.tsx's `leaveSession`), so no
  // future exit path can reintroduce "hero shows again after all" as a gap.
  useEffect(() => {
    return () => {
      heroDismissedThisAppSession = true;
    };
  }, []);

  const inProgress = sessionState.kind === 'in-progress';
  const nodeStates = derivePathNodeStates(sessionState, PATH_NODE_POSITIONS.length);
  // Always through preparation -- both the hero button and the "Your Session" card's own
  // current-question control, on owner instruction (2026-08-27).
  //
  // The prep screen no longer only checks readiness: as of 2026-09-27 both entry points also kick
  // off a background prefetch here (start-or-resume the session, then select the first question)
  // and hand the result to the session screen, so the child sees ONE loading surface -- the prep
  // screen's own artwork -- instead of it and then "Getting your question ready...". The previous
  // version of this comment claimed the prep screen already did this; it never did.
  //
  // Best-effort throughout: a rejected promise is caught by the consumer, which falls through to
  // the existing unprefetched path.
  //
  // IDEMPOTENT. It peeks before it puts, so the warm-up effect below and a later button press
  // share ONE in-flight bootstrap instead of the press discarding a prefetch that is already
  // most of the way done -- which is the entire point of warming it early.
  const startBSessionPrefetch = useCallback(() => {
    if (!subject) return;
    if (peekBSessionPrefetch(subject)) return;
    putBSessionPrefetch(subject, prefetchBSessionBootstrap(subject, getAccessToken));
  }, [getAccessToken, subject]);

  /**
   * WARM COMPONENT B WHILE HOME IS OPEN (owner instruction, 2026-10-10).
   *
   * Starts the session and selects the first question as soon as Home has settled, so pressing the
   * hero button or the path's play control lands on a bootstrap that is already finished rather
   * than starting one. That removes roughly a session-start plus a question-selection round trip
   * from the press -- the bulk of the wait the preparation screen exists to cover.
   *
   * THIS REVERSES THE EARLIER RULE, deliberately, and the reason the rule existed has been
   * retracted. The audit originally said B must not be preloaded merely because Home opened,
   * because `selectOpportunity` was believed to light the question's five-minute answer clock.
   * It does not: `anchor_presentation` sets `timeout_deadline_utc = now + timeout` on the FIRST
   * acknowledgement, which `live-session-screen.tsx` sends when the question renders. Time spent
   * on Home, or on the preparation screen, is not charged to the child.
   *
   * WHAT IT DOES COST, stated because it is not nothing. A learner who opens Home and never plays
   * leaves a session and one open opportunity behind, and `sessions_since_practice` -- which feeds
   * the `spacing_due` selection feature -- counts distinct sessions. The cost is BOUNDED to one:
   * `POST /b/sessions` returns any existing starting-or-active session rather than minting a
   * second (`b_session_lifecycle.py`), so repeated visits reuse it. It is the session that child
   * would have used anyway, created earlier.
   *
   * `runAfterInteractions` so the bootstrap cannot compete with Home's own first frame; the point
   * is to spend idle time, not the time the child is waiting to see the screen.
   */
  useEffect(() => {
    if (!subject) return;
    const task = InteractionManager.runAfterInteractions(() => startBSessionPrefetch());
    return () => task.cancel();
  }, [startBSessionPrefetch, subject]);
  const openBLearning = () => {
    // Treated the same as scrolling past the hero (see handleGestureSettle's own dismiss branch):
    // once the child has used the hero's own call-to-action, a later return to this screen should
    // open straight at the session card rather than showing the hero again from the top.
    heroDismissedThisAppSession = true;
    startBSessionPrefetch();
    router.push('/(learner)/prepare');
  };
  // The path's play control. Named for the resume case it was written for, but it now also serves
  // the not-in-progress one, where node 1 starts a fresh session -- both go through preparation,
  // which resolves resume-or-start for itself, so this needs no branch of its own. The early
  // return that used to sit here made the control inert in exactly the case it was added for.
  const openCurrentQuestion = () => {
    heroDismissedThisAppSession = true;
    startBSessionPrefetch();
    router.push('/(learner)/prepare');
  };
  const scrollRef = useRef<ScrollView>(null);
  const dismissTriggeredRef = useRef(heroDismissedThisAppSession);
  const snapInFlightRef = useRef(false);
  // Whether THIS mount opens past the hero, straight at the session/path card — true once the hero
  // has been "used" once in this app session (scrolled past, the CTA pressed, a path node pressed,
  // or simply leaving this screen at all: see the catch-all cleanup effect above). Read once via
  // `useRef`, not `useState`, so a later change to the module flag (from a scroll on THIS mount)
  // cannot retroactively move where THIS mount started.
  //
  // OWNER RULING, 2026-09-28: when this is true the hero is not rendered AT ALL, and the screen
  // does not scroll. The hero is a first-run welcome -- it belongs to a fresh app start or a fresh
  // login, not to every return from Profile or Play.
  //
  // This reverses an earlier decision, deliberately. `scrollEnabled={false}` used to be set here
  // and was removed as a bug, because on its own it locked the child out of scrolling back up to a
  // hero that was still rendered above them. NOT RENDERING the hero is a different thing from
  // hiding it behind a disabled scroll: with it gone the path panel is the entire content, and the
  // panel is already sized to exactly fit the viewport (`pathViewportHeight` below), so nothing is
  // off-screen and there is nothing to scroll to. The old failure mode cannot recur, because there
  // is no longer anything above the fold to be locked away from.
  //
  // It also removes work rather than adding it: no imperative `scrollToEnd`, and no `layoutReady`
  // delay to hide the frame before it lands (both below are now skipped entirely in this case).
  const startScrolledToPath = useRef(heroDismissedThisAppSession).current;
  const showHero = !startScrolledToPath;
  const [showContinuationFade, setShowContinuationFade] = useState(
    () => !heroDismissedThisAppSession,
  );
  const scrollY = useRef(new Animated.Value(0)).current;
  const introOpacity = scrollY.interpolate({
    extrapolate: 'clamp',
    inputRange: [0, 150],
    outputRange: [1, 0],
  });
  const introLift = scrollY.interpolate({
    extrapolate: 'clamp',
    inputRange: [0, 150],
    outputRange: [0, -36],
  });
  const continuationFadeOpacity = scrollY.interpolate({
    extrapolate: 'clamp',
    inputRange: [0, 10],
    outputRange: [1, 0],
  });
  // The tab bar AND both safe-area insets belong to the learner LAYOUT now, not to this screen
  // (app/(learner)/_layout.tsx hoisted them out so they stop unmounting on every navigation), so
  // this screen is handed a box that already excludes all three.
  //
  // This figure is only ever a FALLBACK, used for the single frame before the ScrollView has
  // measured itself -- `pathViewportHeight` prefers the measured height the moment it arrives, and
  // `layoutReady` keeps that frame off screen either way. It is deliberately an estimate that errs
  // large rather than a second copy of the layout's arithmetic, which would be one more number to
  // drift out of step with the chrome it describes.
  const usableHeight = height - insets.top - insets.bottom;
  const fixedHeaderHeight = compact ? LEARNER_HEADER_HEIGHT_COMPACT : LEARNER_HEADER_HEIGHT;
  const [measuredViewportHeight, setMeasuredViewportHeight] = useState(0);
  // The "buttons glitch on returning to home" report: this screen fully remounts every time it's
  // navigated back to (goHome/goToGameHub elsewhere use router.replace, and expo-router mounts a
  // fresh instance rather than reusing one). On that fresh mount, `measuredViewportHeight` starts
  // at 0 for one frame, so `pathPanelWidth` (below) is computed from a rough fallback estimate
  // instead of the ScrollView's real measured height — the path-stage buttons render once at that
  // wrong position/size, then visibly snap to the correct one the instant `onLayout` reports the
  // real height. `layoutReady` hides the ScrollView (via opacity, not by skipping layout — it
  // still needs to be measured) until that first real `onLayout` has landed, so the correction
  // happens off-screen instead of as a visible jump.
  const [layoutReady, setLayoutReady] = useState(false);
  const pathViewportHeight =
    measuredViewportHeight || Math.max(0, usableHeight - fixedHeaderHeight);
  // The header already supplies the visible gap above the panel (its own
  // paddingBottom), so the panel only needs a matching paddingBottom of its
  // own to keep the gap below it equal — no separate paddingTop here.
  const dashboardBottomPadding = compact ? 3 : spacing.md;
  const pathPanelWidth = Math.min(
    Math.min(width, 500) - spacing.md,
    Math.max(0, pathViewportHeight - dashboardBottomPadding) * (941 / 1672),
  );

  const handleScroll = Animated.event(
    [{ nativeEvent: { contentOffset: { y: scrollY } } }],
    { useNativeDriver: Platform.OS !== 'web' },
  );

  /**
   * Runs only once the learner's gesture has fully settled (drag released with
   * no momentum, or momentum has finished) — never while the scroll is still
   * actively moving, so it never fights the finger or native inertia. Whatever
   * fraction of the hero was scrolled past, this snaps to whichever of the two
   * end states (hero visible, or learning path pinned) it was closer to.
   */
  const handleGestureSettle = (nativeEvent: {
    contentOffset: { y: number };
    contentSize: { height: number };
    layoutMeasurement: { height: number };
  }) => {
    if (dismissTriggeredRef.current || snapInFlightRef.current) return;
    const maxOffset = Math.max(0, nativeEvent.contentSize.height - nativeEvent.layoutMeasurement.height);
    const offsetY = nativeEvent.contentOffset.y;
    if (maxOffset <= 0 || offsetY <= 0 || offsetY >= maxOffset) return;

    snapInFlightRef.current = true;
    const snapToPath = offsetY >= maxOffset * heroSnapThreshold;
    if (snapToPath) {
      dismissTriggeredRef.current = true;
      heroDismissedThisAppSession = true;
      setShowContinuationFade(false);
      scrollRef.current?.scrollTo({ y: maxOffset, animated: true });
      // Deliberately NOT `setScrollEnabled(false)` (that state no longer exists — see
      // `startScrolledToPath`'s own comment): scrolling stays available for the rest of this
      // mount, so the child can freely scroll back up to see the hero again. Only the one-time
      // auto-snap-to-nearest-end decision above is single-shot (`dismissTriggeredRef`), not the
      // ability to scroll at all.
    } else {
      scrollRef.current?.scrollTo({ y: 0, animated: true });
    }
    setTimeout(() => {
      snapInFlightRef.current = false;
    }, 400);
  };

  const pathPanelContent = (
    <View
      style={[
        styles.dashboardSection,
        { minHeight: pathViewportHeight, paddingBottom: dashboardBottomPadding },
      ]}>
      <View style={[styles.pathPanel, { width: pathPanelWidth }]}>
          <Image
            // The artwork is unchanged; only its description is, since it no longer stands for five
            // lessons — nothing in the backend has lessons.
            accessibilityLabel="A winding path leading to a treasure chest"
            contentFit="cover"
            source={learningPathArtwork}
            style={styles.learningPathArtwork}
          />
          <View style={styles.pathHeading}>
            <Ionicons color={colors.accentGreen} name="map" size={compact ? 22.5 : 27} />
            <AppText style={[styles.pathHeadingText, compact && styles.pathHeadingTextCompact]}>
              {inProgress ? 'Your Session' : 'Ready to Play'}
            </AppText>
          </View>
          {nodeStates.map((nodeState, index) => {
            const node = PATH_NODE_POSITIONS[index];
            const isCurrent = nodeState === 'current';
            const stageContent = (
              <>
              <View
                style={[
                  styles.pathStageNumber,
                  { backgroundColor: node.color },
                  isCurrent && styles.pathStageNumberActive,
                ]}>
                <AppText style={[styles.pathStageNumberText, compact && styles.pathStageNumberTextCompact]}>
                  {index + 1}
                </AppText>
              </View>
              <View style={[styles.pathStageCard, isCurrent && styles.pathStageCardActive]}>
                <View style={styles.pathStageCopy}>
                  <AppText style={[styles.pathStageTitle, compact && styles.pathStageTitleCompact]}>
                    {`Question ${index + 1}`}
                  </AppText>
                  <View style={styles.pathStageProgress}>
                    {/* A star marks a question actually answered. It used to appear on every
                        not-current node, i.e. on questions that had not happened yet. */}
                    {nodeState === 'done' && (
                      <Ionicons color="#ffb51f" name="star" size={compact ? 11.5 : 13.8} />
                    )}
                    <AppText
                      style={[
                        styles.pathStageSubtitle,
                        compact && styles.pathStageSubtitleCompact,
                        isCurrent && styles.pathStageSubtitleActive,
                        isCurrent && compact && styles.pathStageSubtitleActiveCompact,
                        isCurrent && { color: node.color },
                      ]}>
                      {isCurrent && !inProgress ? FRESH_START_SUBTITLE : nodeSubtitles[nodeState]}
                    </AppText>
                  </View>
                </View>
                <Ionicons
                  color={isCurrent ? colors.primary : node.color}
                  name={
                    isCurrent ? 'play' : nodeState === 'done' ? 'checkmark-circle' : 'ellipse-outline'
                  }
                  size={isCurrent ? (compact ? 22.4 : 27.2) : compact ? 17.6 : 20.8}
                />
              </View>
              </>
            );

            if (isCurrent) {
              return (
                <Pressable
                  accessibilityHint={
                    inProgress ? 'Opens your current question' : 'Opens session preparation'
                  }
                  accessibilityLabel={pathNodeLabel(index, nodeState)}
                  accessibilityRole="button"
                  key={index}
                  onPress={openCurrentQuestion}
                  style={({ pressed }) => [
                    styles.pathStage,
                    { left: node.left, top: node.top },
                    pressed && styles.pathStagePressed,
                  ]}>
                  {stageContent}
                </Pressable>
              );
            }

            return (
              <View
                accessibilityLabel={pathNodeLabel(index, nodeState)}
                accessible
                key={index}
                style={[styles.pathStage, { left: node.left, top: node.top }]}>
                {stageContent}
              </View>
            );
          })}
      </View>
    </View>
  );

  return (
    <View style={styles.safeArea}>
      <View style={styles.mobileCanvas}>
        <LearnerHeaderBar compact={compact} displayName={displayName} showBattery />

        <Animated.ScrollView
          bounces
          contentContainerStyle={styles.scrollContent}
          // No `onContentSizeChange` and no imperative `scrollToEnd` any more. Both existed only to
          // jump PAST a rendered hero on a return visit, along with the guard ref that kept the
          // jump one-shot and the 50ms delay that hid the frame before it landed. The hero is
          // simply not rendered on those mounts now, so there is nothing to jump past: the path
          // panel is the whole content and it opens where it belongs.
          onLayout={(event) => {
            setMeasuredViewportHeight(event.nativeEvent.layout.height);
            // `layoutReady` still earns its keep: the panel's stage buttons are sized from this
            // measured height, and until the first real `onLayout` lands they would render once at
            // the fallback estimate and visibly snap. This hides that correction, nothing more.
            setLayoutReady(true);
          }}
          onMomentumScrollEnd={(event) => handleGestureSettle(event.nativeEvent)}
          onScroll={handleScroll}
          onScrollEndDrag={(event) => {
            // iOS only: when a drag ends with no fling, no deceleration follows,
            // so onMomentumScrollEnd never fires — settle immediately in that
            // case. Android always fires onMomentumScrollEnd on its own.
            if (Platform.OS !== 'ios') return;
            const velocity = event.nativeEvent.velocity;
            const speed = velocity ? Math.hypot(velocity.x, velocity.y) : 0;
            if (speed < 0.05) handleGestureSettle(event.nativeEvent);
          }}
          ref={scrollRef}
          scrollEnabled={showHero}
          scrollEventThrottle={16}
          showsVerticalScrollIndicator={false}
          style={[styles.scrollView, !layoutReady && styles.scrollViewHidden]}>
          {showHero ? (
            <Animated.View
              style={[
                styles.heroSection,
                compact && styles.sectionCompact,
                { opacity: introOpacity, transform: [{ translateY: introLift }] },
              ]}>
              <View style={styles.hero}>
                <Image
                  accessibilityLabel="MathMingo adventure landscape"
                  contentFit="cover"
                  source={heroArtwork}
                  style={styles.heroArtwork}
                />
                <View style={styles.heroCopy}>
                  <AppText style={[styles.heroTitle, compact && styles.heroTitleCompact]}>
                    Let&apos;s make math
                  </AppText>
                  <View style={styles.heroAdventureLine}>
                    <AppText style={[styles.heroTitle, styles.heroAdventureLead, compact && styles.heroTitleCompact]}>
                      an
                    </AppText>
                    <AppText style={[styles.heroAdventure, compact && styles.heroAdventureCompact]}>
                      adventure!
                    </AppText>
                  </View>
                </View>
                <Pressable
                  accessibilityHint="Opens session preparation"
                  accessibilityRole="button"
                  onPress={openBLearning}
                  style={({ pressed }) => [
                    styles.heroButton,
                    compact && styles.heroButtonCompact,
                    pressed && styles.buttonPressed,
                  ]}>
                  <AppText style={[styles.heroButtonText, compact && styles.heroButtonTextCompact]}>
                    {inProgress ? 'Resume Adventure' : 'Start Adventure'}
                  </AppText>
                  <Ionicons color={colors.primaryForeground} name="chevron-forward" size={compact ? 18.6 : 22.32} />
                </Pressable>
              </View>
            </Animated.View>
          ) : null}

          {pathPanelContent}
        </Animated.ScrollView>

        {showContinuationFade && (
          <Animated.View
            style={[
              styles.scrollContinuationFade,
              { bottom: 0, opacity: continuationFadeOpacity },
            ]}
          >
            <View style={styles.scrollContinuationFade1} />
            <View style={styles.scrollContinuationFade2} />
            <View style={styles.scrollContinuationFade3} />
            <View style={styles.scrollContinuationFade4} />
            <View style={styles.scrollContinuationFade5} />
            <View style={styles.scrollContinuationFade6} />
            <View style={styles.scrollContinuationFade7} />
          </Animated.View>
        )}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  buttonPressed: { borderBottomWidth: 0, transform: [{ translateY: 3 }] },
  dashboardSection: { alignItems: 'center', justifyContent: 'center', paddingHorizontal: spacing.sm, paddingTop: 0, width: '100%' },
  dots: { flexDirection: 'row', gap: 2, marginTop: 2 },
  hero: { aspectRatio: heroAspectRatio, backgroundColor: colors.secondarySoft, borderColor: colors.surface1, borderRadius: radius.lg, borderWidth: heroBorderWidth, elevation: 5, overflow: 'hidden', padding: spacing.smPlus, position: 'relative', shadowColor: colors.foreground, shadowOffset: { width: 0, height: 4 }, shadowOpacity: 0.18, shadowRadius: 7, width: '100%' },
  heroArtwork: { bottom: -heroBorderWidth, left: -heroBorderWidth, position: 'absolute', right: -heroBorderWidth, top: -heroBorderWidth },
  heroAdventure: { color: '#FEC632', fontFamily: typography.fonts.display, fontSize: 34.32, lineHeight: 39.6 },
  heroAdventureCompact: { fontSize: 29.04, lineHeight: 35.2 },
  heroAdventureLead: { marginRight: 5 },
  heroAdventureLine: { alignItems: 'baseline', flexDirection: 'row' },
  heroButton: { alignItems: 'center', backgroundColor: colors.primary, borderColor: colors.surface1, borderRadius: 14.88, borderWidth: 2, bottom: spacing.smPlus, elevation: 4, flexDirection: 'row', gap: 4.96, justifyContent: 'center', left: spacing.smPlus, minHeight: 49.6, paddingHorizontal: 14.88, position: 'absolute', shadowColor: colors.primaryShadow, shadowOffset: { width: 0, height: 3 }, shadowOpacity: 0.35, shadowRadius: 4, zIndex: 2 },
  heroButtonCompact: { bottom: spacing.sm, left: spacing.sm, minHeight: 44.64, paddingHorizontal: 12.4 },
  heroButtonText: { color: colors.primaryForeground, fontFamily: typography.fonts.bold, fontSize: 13.64, lineHeight: 22.32, textAlign: 'center' },
  heroButtonTextCompact: { fontSize: 12.4, lineHeight: 19.84 },
  heroCopy: { gap: 2, maxWidth: '62%', zIndex: 2 },
  heroSection: { paddingBottom: 5, paddingHorizontal: spacing.sm },
  heroTitle: { fontFamily: typography.fonts.display, fontSize: 23.94, lineHeight: 27.72 },
  heroTitleCompact: { fontSize: 20.16, lineHeight: 24.36 },
  inactiveDot: { backgroundColor: colors.surface3, borderRadius: radius.pill, height: 4, width: 4 },
  learningPathArtwork: { ...StyleSheet.absoluteFillObject, height: '100%', width: '100%' },
  missionCopy: { flex: 1, gap: 2 },
  missionLabel: { fontFamily: typography.fonts.bold, fontSize: 9, lineHeight: 12 },
  missionLabelCompact: { fontSize: 7, lineHeight: 9 },
  missionPanel: { flex: 0.37 },
  missionRow: { alignItems: 'center', backgroundColor: '#fff9df', borderColor: '#f6e9aa', borderRadius: radius.sm, borderWidth: 1, flex: 1, flexDirection: 'row', gap: 3, minHeight: 0, paddingHorizontal: 5 },
  missionRowCompact: { paddingHorizontal: 3 },
  missionTrack: { backgroundColor: colors.surface3, borderRadius: radius.pill, height: 4 },
  missionValue: { color: colors.textSecondary, fontSize: 8 },
  mobileCanvas: { alignSelf: 'center', backgroundColor: colors.background, flex: 1, maxWidth: 500, width: '100%' },
  panel: { backgroundColor: colors.surface1, borderBottomColor: colors.borderStrong, borderBottomWidth: 2, borderColor: colors.border, borderRadius: radius.md, borderWidth: 1, gap: 4, minHeight: 0, padding: 6 },
  panelHeading: { alignItems: 'center', flexDirection: 'row', gap: 3, minHeight: 18 },
  panelTitle: { flex: 1, fontFamily: typography.fonts.display, fontSize: 11, lineHeight: 14 },
  panelTitleCompact: { fontSize: 9, lineHeight: 11 },
  pathHeading: { alignItems: 'center', flexDirection: 'row', gap: 4, left: '6%', position: 'absolute', top: '3%' },
  pathHeadingText: { fontFamily: typography.fonts.heavy, fontSize: 18, lineHeight: 22.5 },
  pathHeadingTextCompact: { fontSize: 15, lineHeight: 18 },
  pathPanel: { alignSelf: 'center', aspectRatio: 941 / 1672, borderColor: colors.surface1, borderRadius: radius.lg, borderWidth: 3, elevation: 4, maxWidth: '100%', overflow: 'hidden', position: 'relative', shadowColor: colors.foreground, shadowOffset: { width: 0, height: 3 }, shadowOpacity: 0.14, shadowRadius: 6 },
  pathStage: { alignItems: 'center', flexDirection: 'row', height: '11.5%', position: 'absolute', right: '3%' },
  pathStageCard: { alignItems: 'center', backgroundColor: 'rgba(255,255,255,0.96)', borderColor: colors.border, borderRadius: radius.md, borderWidth: 1, elevation: 2, flex: 1, flexDirection: 'row', height: '78%', justifyContent: 'space-between', marginLeft: -8, paddingLeft: 12, paddingRight: 7, shadowColor: colors.foreground, shadowOffset: { width: 0, height: 2 }, shadowOpacity: 0.1, shadowRadius: 3 },
  pathStageCardActive: { borderColor: colors.primarySoft },
  pathStageCopy: { flex: 1, gap: 4, justifyContent: 'center' },
  pathStageNumber: { alignItems: 'center', aspectRatio: 1, borderColor: colors.surface1, borderRadius: radius.pill, borderWidth: 3, elevation: 4, height: '80%', justifyContent: 'center', shadowColor: colors.foreground, shadowOffset: { width: 0, height: 3 }, shadowOpacity: 0.18, shadowRadius: 4, zIndex: 2 },
  pathStageNumberActive: { borderColor: colors.accentYellow },
  pathStageNumberText: { color: colors.primaryForeground, fontFamily: typography.fonts.display, fontSize: 18, lineHeight: 22 },
  pathStageNumberTextCompact: { fontSize: 15, lineHeight: 18 },
  pathStageProgress: { alignItems: 'center', flexDirection: 'row', gap: 2 },
  pathStagePressed: { opacity: 0.86, transform: [{ scale: 0.985 }] },
  pathStageSubtitle: { color: colors.textSecondary, fontFamily: typography.fonts.body, fontSize: 9.2, lineHeight: 11.5 },
  pathStageSubtitleActive: { color: colors.primary, fontSize: 13.8, lineHeight: 16.5 },
  pathStageSubtitleActiveCompact: { fontSize: 11.5, lineHeight: 13.8 },
  pathStageSubtitleCompact: { fontSize: 8.05, lineHeight: 10.35 },
  pathStageTitle: { fontFamily: typography.fonts.heavy, fontSize: 15, lineHeight: 18 },
  pathStageTitleCompact: { fontSize: 12, lineHeight: 15 },
  progressPanel: { flex: 0.63 },
  safeArea: { backgroundColor: colors.background, flex: 1 },
  scrollContent: {},
  scrollContinuationFade: { height: 27, left: spacing.sm, pointerEvents: 'none', position: 'absolute', right: spacing.sm, zIndex: 9 },
  scrollContinuationFade1: { backgroundColor: 'rgba(244,244,246,0.06)', flex: 1 },
  scrollContinuationFade2: { backgroundColor: 'rgba(244,244,246,0.14)', flex: 1 },
  scrollContinuationFade3: { backgroundColor: 'rgba(244,244,246,0.24)', flex: 1 },
  scrollContinuationFade4: { backgroundColor: 'rgba(244,244,246,0.36)', flex: 1 },
  scrollContinuationFade5: { backgroundColor: 'rgba(244,244,246,0.5)', flex: 1 },
  scrollContinuationFade6: { backgroundColor: 'rgba(244,244,246,0.66)', flex: 1 },
  scrollContinuationFade7: { backgroundColor: 'rgba(244,244,246,0.82)', flex: 1 },
  scrollView: { flex: 1 },
  // Opacity, not `display: 'none'`: it must still lay out and fire `onLayout`/`onContentSizeChange`
  // while hidden, or `layoutReady` would never flip to true — see the state's own comment.
  scrollViewHidden: { opacity: 0 },
  sectionCompact: { paddingBottom: 3 },
  sideColumn: { flex: 0.94, gap: 6, minHeight: 0 },
  stageArtwork: { alignItems: 'center', aspectRatio: 1, borderRadius: radius.pill, justifyContent: 'center', width: 30 },
  stageArtworkCompact: { width: 24 },
  stageCard: { alignItems: 'center', borderRadius: radius.sm, flex: 1, flexDirection: 'row', gap: 4, minHeight: 0, paddingHorizontal: 4 },
  stageCopy: { flex: 1 },
  stageDescription: { color: colors.textSecondary, fontSize: 7, lineHeight: 9 },
  stageDescriptionCompact: { fontSize: 6, lineHeight: 7 },
  stageList: { flex: 1, gap: 3, minHeight: 0 },
  stageTitle: { fontFamily: typography.fonts.bold, fontSize: 9, lineHeight: 11 },
  stageTitleCompact: { fontSize: 7, lineHeight: 9 },
  statCard: { alignItems: 'center', backgroundColor: colors.surface1, borderBottomColor: colors.borderStrong, borderBottomWidth: 2, borderColor: colors.border, borderRadius: radius.sm, borderWidth: 1, justifyContent: 'center', minWidth: 38, paddingHorizontal: 3, paddingVertical: 2 },
  statCardCompact: { minWidth: 32, paddingHorizontal: 2, paddingVertical: 1 },
  statLabel: { color: colors.textSecondary, fontSize: 6, lineHeight: 8 },
  statLabelCompact: { fontSize: 5, lineHeight: 6 },
  stats: { alignSelf: 'stretch', flexDirection: 'row', gap: 3 },
  statValue: { fontFamily: typography.fonts.bold, fontSize: 10, lineHeight: 12 },
  statValueCompact: { fontSize: 8, lineHeight: 9 },
});
