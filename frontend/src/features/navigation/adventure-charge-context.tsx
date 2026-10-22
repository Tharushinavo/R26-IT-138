import { router } from 'expo-router';
import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from 'react';

import type { LearnerSkillStateItem } from '@/src/api/generated/openapi-types';
import { createComponentBApi } from '@/src/api/component-b-api';
import { useAuth } from '@/src/auth/auth-context';
import { readPublicConfig } from '@/src/config/env';
import {
  putCSessionPrefetch,
  takeCSessionPrefetch,
} from '@/src/features/c-session/c-session-prefetch-cache';
import { prefetchCSessionBootstrap } from '@/src/features/c-session/c-session-prefetch';
import { PlayPrepCard } from '@/src/features/home/play-prep-card';
import { PlayAdventurePopup } from '@/src/features/navigation/play-adventure-popup';
import {
  ADVENTURE_CHARGE_MAX_LEVEL,
  awardAdventureCharge,
  getAdventureChargeLevel,
} from '@/src/utils/adventure-charge';

const PILL_VISIBLE_MS = 2600;

/** `LearnerMembershipListItem.grade` is already fetched everywhere `me.classroomMembership` is
 * (the same live GET the header/onboarding already rely on) -- no new backend call. Component C's
 * route (`c-session.tsx`) wants the plain number `CreateCSessionRequest` itself uses. */
function numericGrade(grade: 'GRADE_2' | 'GRADE_3' | undefined): number | undefined {
  if (grade === 'GRADE_2') return 2;
  if (grade === 'GRADE_3') return 3;
  return undefined;
}

type AdventureChargeContextValue = {
  level: number;
  maxLevel: number;
  pillVisible: boolean;
  /** True from the moment Play is pressed (at full charge) until the child either presses
   * "Start Game" on the prep card or dismisses it. The provider renders the blurred prep-card
   * overlay while this is true. */
  preparingPlay: boolean;
  /** True once the background Component C prefetch has settled (success OR failure -- a failed
   * prefetch still navigates, into c-session's own bootstrap). The prep card's "Start Game"
   * button waits for this. */
  playPrepReady: boolean;
  /** Play's own press handler: opens the prep card only at maxLevel, otherwise shows the popup. */
  requestPlay: () => void;
  /** Closes the "Play Adventure" popup before its own timer does -- a tap on its backdrop. */
  dismissPill: () => void;
  /** The prep card's "Start Game" button: navigates into the prefetched Component C session. */
  startPreparedGame: () => void;
  /** The prep card's close control: drops the prep state and discards the pending prefetch. */
  dismissPlayPrep: () => void;
  /** Called once from the session screen when a Component B session genuinely completes. */
  awardForSession: (sessionId: string) => void;
};

const AdventureChargeContext = createContext<AdventureChargeContextValue | null>(null);

/** Wraps the (learner) route group so the header (which shows the gauge and the pill) and the
 * tab bar (whose Play button triggers the pill) can share one charge state without prop-drilling
 * it through every screen that renders both. */
export function AdventureChargeProvider({ children }: { children: React.ReactNode }) {
  const { getAccessToken, me } = useAuth();
  const subject = me?.principal.user_id ?? null;
  const grade = numericGrade(me?.classroomMembership?.grade);
  const [level, setLevel] = useState(0);
  const [pillVisible, setPillVisible] = useState(false);
  const [preparingPlay, setPreparingPlay] = useState(false);
  const [playPrepReady, setPlayPrepReady] = useState(false);
  // The learner's real per-skill BKT state for the prep card's bars (2026-09-21 ruling: shown as
  // bar length only). Fetched fresh on every Play press so it reflects the session just finished,
  // never cached across presses. Null until it lands or if it fails -- the card draws empty bars
  // and "Start Game" never waits on it.
  const [prepSkillStates, setPrepSkillStates] = useState<readonly LearnerSkillStateItem[] | null>(null);
  const preparedGradeRef = useRef<number | null>(null);
  const skillStatesRequestRef = useRef(0);
  const pillTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    if (!subject) {
      setLevel(0);
      return;
    }
    let cancelled = false;
    void getAdventureChargeLevel(subject).then((value) => {
      if (!cancelled) setLevel(value);
    });
    return () => {
      cancelled = true;
    };
  }, [subject]);

  useEffect(
    () => () => {
      if (pillTimerRef.current) clearTimeout(pillTimerRef.current);
    },
    [],
  );

  const awardForSession = useCallback(
    (sessionId: string) => {
      if (!subject) return;
      void awardAdventureCharge(subject, sessionId).then(setLevel);
    },
    [subject],
  );

  const requestPlay = useCallback(() => {
    if (level >= ADVENTURE_CHARGE_MAX_LEVEL) {
      // Straight into a real Component C session -- no game-hub family menu (removed on owner
      // instruction, 2026-08-27). `grade` is the learner's own, real classroom grade (never
      // invented here); no family/template is passed at all, so c-session.tsx's own adaptive
      // selection (BKT) is what picks it, exactly as Component C was built to -- the frontend was
      // never meant to choose a family. If grade is somehow unavailable (it should always be
      // present once Play is reachable at all, since that already requires an APPROVED classroom
      // membership), do nothing rather than sending the child into c-session.tsx's dead-end "not
      // ready" screen -- Home, which is where this press already happened, is still exactly right.
      if (grade === undefined) return;
      // Open the prep card and kick off the Component C prefetch behind its blurred backdrop. The
      // card owns the wait now: it runs its skill-calibration animation while the prefetch is in
      // flight and only navigates when the child presses "Start Game" (startPreparedGame below).
      // c-session.tsx never shows its own separate loading screen for this first task; see
      // c-session-prefetch-cache.ts for why calling next_task from here is safe. Best-effort
      // either way: a failed prefetch still navigates, into c-session.tsx's own normal
      // bootstrap-and-loading path, exactly as if none of this existed.
      preparedGradeRef.current = grade;
      setPlayPrepReady(false);
      setPreparingPlay(true);
      // Skill bars: best-effort and independent of the game prefetch. A stale response from a
      // dismissed-then-reopened card is dropped by the request counter, so bars never show a
      // previous press's answer. Failure of any kind (network, 404 for a learner with no B
      // history yet, invalid shape) leaves the bars empty -- that is a valid state, not an error
      // the child should see.
      setPrepSkillStates(null);
      const requestNumber = ++skillStatesRequestRef.current;
      void (async () => {
        try {
          const accessToken = await getAccessToken();
          if (!accessToken) return;
          const { config } = readPublicConfig();
          if (!config) return;
          const response = await createComponentBApi(config).getLearnerSkillStates(accessToken);
          if (skillStatesRequestRef.current === requestNumber) setPrepSkillStates(response.skill_states);
        } catch {
          // Bars stay empty.
        }
      })();
      const prefetch = prefetchCSessionBootstrap(grade, getAccessToken);
      if (subject) putCSessionPrefetch(subject, prefetch);
      void prefetch.catch(() => null).finally(() => setPlayPrepReady(true));
      return;
    }
    setPillVisible(true);
    if (pillTimerRef.current) clearTimeout(pillTimerRef.current);
    pillTimerRef.current = setTimeout(() => setPillVisible(false), PILL_VISIBLE_MS);
  }, [getAccessToken, grade, level, subject]);

  const dismissPill = useCallback(() => {
    if (pillTimerRef.current) clearTimeout(pillTimerRef.current);
    pillTimerRef.current = null;
    setPillVisible(false);
  }, []);

  const startPreparedGame = useCallback(() => {
    const preparedGrade = preparedGradeRef.current;
    if (preparedGrade === null) return;
    setPreparingPlay(false);
    setPlayPrepReady(false);
    // Into the run-length choice, NOT straight into the game. The session the background prefetch
    // created is untouched by the detour -- `c-session-prefetch-cache.ts` is a plain Map with no
    // expiry, so the prefetched first task is still waiting when the child picks a length. A child
    // who backs out of the choice leaves that session uncollected, exactly as dismissing this card
    // already does.
    router.replace({
      params: { grade: String(preparedGrade), sessionMode: 'c_only' },
      pathname: '/(learner)/c-prepare',
    });
  }, []);

  const dismissPlayPrep = useCallback(() => {
    setPreparingPlay(false);
    setPlayPrepReady(false);
    setPrepSkillStates(null);
    skillStatesRequestRef.current += 1;
    preparedGradeRef.current = null;
    // Discard the cached prefetch so a later entry re-bootstraps from scratch. Any session the
    // prefetch already created on the backend is simply resumed by c-session's own bootstrap.
    if (subject) takeCSessionPrefetch(subject);
  }, [subject]);

  const value = useMemo<AdventureChargeContextValue>(
    () => ({
      level,
      maxLevel: ADVENTURE_CHARGE_MAX_LEVEL,
      pillVisible,
      preparingPlay,
      playPrepReady,
      requestPlay,
      dismissPill,
      startPreparedGame,
      dismissPlayPrep,
      awardForSession,
    }),
    [
      awardForSession,
      dismissPill,
      dismissPlayPrep,
      level,
      pillVisible,
      playPrepReady,
      preparingPlay,
      requestPlay,
      startPreparedGame,
    ],
  );

  return (
    <AdventureChargeContext.Provider value={value}>
      {children}
      {/* The not-yet-charged prompt. Global, and a sibling of the prep card below, because its
          blur has to cover the whole page -- see play-adventure-popup.tsx. */}
      {pillVisible ? <PlayAdventurePopup onDismiss={dismissPill} /> : null}
      {preparingPlay ? (
        <PlayPrepCard
          onDismiss={dismissPlayPrep}
          onStart={startPreparedGame}
          ready={playPrepReady}
          skillStates={prepSkillStates}
        />
      ) : null}
    </AdventureChargeContext.Provider>
  );
}

export function useAdventureCharge(): AdventureChargeContextValue {
  const value = useContext(AdventureChargeContext);
  if (!value) throw new Error('useAdventureCharge must be used within an AdventureChargeProvider');
  return value;
}
