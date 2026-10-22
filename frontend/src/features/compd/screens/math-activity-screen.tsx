import React, { useCallback, useEffect, useRef, useState } from 'react';
import {
  Animated,
  AppState,
  BackHandler,
  ScrollView,
  StyleSheet,
  Text,
  TouchableOpacity,
  Vibration,
  View,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import * as Crypto from 'expo-crypto';
import { useFocusEffect } from 'expo-router';
import PrimaryButton from '@/src/features/compd/components/primary-button';
import Card from '@/src/features/compd/components/card';
import LeaveQuizPopup from '@/src/features/compd/components/leave-quiz-popup';
import AnimalMascot from '@/src/features/compd/components/animal-mascot';
import CelebrationOverlay from '@/src/features/compd/components/celebration-overlay';
import { useLanguage } from '@/src/features/compd/i18n/language-context';
import { colors as lightColors, radius, spacing, typography, useAppTheme } from '@/src/features/compd/theme';
import type { DProfileCreateRequest } from '@/src/features/compd/api/compd-types';
import type { InteractionEvent } from '@/src/features/compd/compd-legacy-client';
import type { CompdScreenProps } from '@/src/features/compd/navigation';
import { useCompdApi } from '@/src/features/compd/use-compd-api';
import { setCompdQuizRunning } from '@/src/features/compd/compd-quiz-running';
import { pickQuestions, type BankQuestion } from '@/src/features/compd/data/question-bank';
import { playSound, unloadAllSounds } from '@/src/features/compd/utils/sounds';
import { generateMathHint } from '@/src/features/compd/utils/local-hint';
import { randomCelebrationAnimal, type AnimalId } from '@/src/features/compd/assets/animal-images';

type QuizGateMode = 'start' | 'active' | 'resume';

const TOTAL_QUESTIONS = 10;
const QUESTION_TIMER_SECONDS = 60;
const TIME_WARNING_SECONDS = 60;  // Show "time running out" alert at 1:00
const AUTO_SKIP_SECONDS = 120;    // Auto-skip question at 2:00

const DIFFICULTY_DOTS: Record<string, number> = {
  'Easy': 1,
  'Medium': 2,
  'Hard': 3,
};

export default function MathActivityScreen({ navigation }: CompdScreenProps) {
  const { t, lang } = useLanguage();
  const { colors } = useAppTheme();
  const styles = createStyles(colors);
  const { call } = useCompdApi();
  // One UUID per quiz RUN, renewed in startQuiz. compD used to derive it once per screen mount, so
  // a retaken quiz reused the first run's id and its answers were never stored (backlog B1).
  const [sessionId, setSessionId] = useState(() => Crypto.randomUUID());
  // The final submission, kept byte-for-byte so "Try again" re-sends exactly the same body -- the
  // server treats a repeat for the same session as the same profile (contract: idempotent).
  const pendingSubmitRef = useRef<{ sessionId: string; body: DProfileCreateRequest } | null>(null);
  const [submitFailed, setSubmitFailed] = useState(false);
  const [confirmLeave, setConfirmLeave] = useState(false);
  const pausedForLeaveRef = useRef(false);
  // Android's hardware back opens the same popup as the X; the listener is registered once, so it
  // calls the latest `openLeaveConfirm` through this ref.
  const openLeaveRef = useRef<() => void>(() => setConfirmLeave(true));

  const [quizGate, setQuizGate] = useState<QuizGateMode>('start');
  const [bankQuestions, setBankQuestions] = useState<BankQuestion[]>([]);
  const [index, setIndex] = useState(0);
  const [selected, setSelected] = useState<string | null>(null);
  const [attempts, setAttempts] = useState(0);
  const [clickCount, setClickCount] = useState(0);
  const [hintUsed, setHintUsed] = useState(false);
  const [showHint, setShowHint] = useState(false);
  const [hintText, setHintText] = useState('');
  const [loadingHint, setLoadingHint] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [events, setEvents] = useState<InteractionEvent[]>([]);
  const [feedback, setFeedback] = useState<'correct' | 'wrong' | 'skipped' | null>(null);
  const [loadingQuestions, setLoadingQuestions] = useState(false);
  const [showCelebration, setShowCelebration] = useState(false);
  const [celebrationAnimal, setCelebrationAnimal] = useState<AnimalId>(5);
  const [isPaused, setIsPaused] = useState(false);
  const [streak, setStreak] = useState(0);
  const [showFloatingStar, setShowFloatingStar] = useState(false);
  const [sessionPausedMs, setSessionPausedMs] = useState(0);
  const [questionPausedMs, setQuestionPausedMs] = useState(0);

  const questionStartRef = useRef<number>(Date.now());
  const sessionStartRef = useRef<number>(Date.now());
  const lastActionRef = useRef<number>(Date.now());
  const pauseStartedAtRef = useRef<number | null>(null);
  const indexRef = useRef(0);
  const submittingRef = useRef(false);
  const quizGateRef = useRef<QuizGateMode>('start');

  // Animated values for question entrance
  const slideAnim = useRef(new Animated.Value(0)).current;
  const scaleAnim = useRef(new Animated.Value(1)).current;
  const feedbackScale = useRef(new Animated.Value(0)).current;
  const floatingStarY = useRef(new Animated.Value(0)).current;
  const floatingStarOpacity = useRef(new Animated.Value(0)).current;

  useEffect(() => { indexRef.current = index; }, [index]);
  useEffect(() => { submittingRef.current = submitting; }, [submitting]);
  useEffect(() => { quizGateRef.current = quizGate; }, [quizGate]);
  // The tab bar hides only while questions are on screen (compd-quiz-running.ts).
  useEffect(() => {
    setCompdQuizRunning(quizGate === 'active');
    return () => setCompdQuizRunning(false);
  }, [quizGate]);

  useEffect(() => {
    return () => { unloadAllSounds(); };
  }, []);


  // Handle mobile back button — navigate to Home tab instead of closing app
  useFocusEffect(
    useCallback(() => {
      const onBackPress = () => {
        if (submittingRef.current) return true;
        if (quizGateRef.current === 'active') openLeaveRef.current();
        else navigation.navigate('StudentHome');
        return true;
      };
      const subscription = BackHandler.addEventListener('hardwareBackPress', onBackPress);
      return () => subscription.remove();
    }, [navigation])
  );

  // Pause quiz when user navigates away from Activity tab
  useFocusEffect(
    useCallback(() => {
      // On focus: if quiz was active and is now in resume mode, stay in resume
      return () => {
        // On blur: pause the quiz if it was active
        if (quizGateRef.current !== 'active' || submittingRef.current) return;
        const now = Date.now();
        if (!pauseStartedAtRef.current) {
          pauseStartedAtRef.current = now;
          setIsPaused(true);
        }
        setQuizGate('resume');
      };
    }, []),
  );

  // Pause quiz when app goes to background
  useEffect(() => {
    const subscription = AppState.addEventListener('change', (nextAppState) => {
      if (nextAppState !== 'active' && quizGateRef.current === 'active' && !submittingRef.current) {
        const now = Date.now();
        if (!pauseStartedAtRef.current) {
          pauseStartedAtRef.current = now;
          setIsPaused(true);
        }
        setQuizGate('resume');
      }
    });
    return () => subscription.remove();
  }, []);

  // ── Start Quiz handler ──
  const startQuiz = useCallback(() => {
    const questions = pickQuestions(TOTAL_QUESTIONS);
    const now = Date.now();
    setSessionId(Crypto.randomUUID());
    pendingSubmitRef.current = null;
    setSubmitFailed(false);
    setConfirmLeave(false);
    setBankQuestions(questions);
    setIndex(0);
    setSelected(null);
    setAttempts(0);
    setClickCount(0);
    setHintUsed(false);
    setShowHint(false);
    setHintText('');
    setLoadingHint(false);
    setSubmitting(false);
    setEvents([]);
    setFeedback(null);
    setShowCelebration(false);
    setIsPaused(false);
    setSessionPausedMs(0);
    setQuestionPausedMs(0);
    questionStartRef.current = now;
    sessionStartRef.current = now;
    lastActionRef.current = now;
    pauseStartedAtRef.current = null;
    setQuizGate('active');
    setLoadingQuestions(false);
  }, []);

  // ── Resume Quiz handler ──
  const resumeQuiz = useCallback(() => {
    const now = Date.now();
    const startedAt = pauseStartedAtRef.current;
    if (startedAt) {
      const pauseMs = now - startedAt;
      setSessionPausedMs((v) => v + pauseMs);
      setQuestionPausedMs((v) => v + pauseMs);
    }
    pauseStartedAtRef.current = null;
    lastActionRef.current = now;
    setIsPaused(false);
    // A leave popup left open when the app went to the background must not come back over a
    // running quiz, nor make "Keep playing" pause it (its own pause was just resumed here).
    setConfirmLeave(false);
    pausedForLeaveRef.current = false;
    setQuizGate('active');
    playSound('tap');
  }, []);

  const current = bankQuestions[index];

  // Animate question entrance
  const animateEntrance = useCallback(() => {
    slideAnim.setValue(60);
    scaleAnim.setValue(0.9);
    Animated.parallel([
      Animated.spring(slideAnim, { toValue: 0, friction: 6, tension: 80, useNativeDriver: true }),
      Animated.spring(scaleAnim, { toValue: 1, friction: 5, tension: 100, useNativeDriver: true }),
    ]).start();
  }, [slideAnim, scaleAnim]);

  // Reset state when question changes
  useEffect(() => {
    if (quizGateRef.current !== 'active') return;
    questionStartRef.current = Date.now();
    lastActionRef.current = Date.now();
    setSelected(null);
    setAttempts(0);
    setClickCount(0);
    setHintUsed(false);
    setShowHint(false);
    setHintText('');
    setLoadingHint(false);
    setFeedback(null);
    setShowCelebration(false);
    setQuestionPausedMs(0);
    setIsPaused(false);
    pauseStartedAtRef.current = null;
    animateEntrance();
    if (index > 0) playSound('nextQuestion');
  }, [index, animateEntrance]);

  function trackAction() {
    if (isPaused) return;
    lastActionRef.current = Date.now();
    setClickCount((c) => c + 1);
  }

  function handleSelect(option: string) {
    if (feedback || isPaused) return;
    trackAction();
    playSound('tap');
    setSelected(option);
  }

  async function handleHint() {
    if (showHint || isPaused || !current) return;
    trackAction();
    playSound('hint');
    setLoadingHint(true);
    setHintUsed(true);

    try {
      const hint = await generateMathHint(
        lang === 'si' ? current.question_text_si : current.question_text,
        current.topic,
        lang
      );
      setHintText(hint.text.replace(/^💡\s*/, ''));
      setShowHint(true);
    } catch {
      // Fallback to static hint if API fails
      setHintText(hintFor(current.topic).replace(/^💡\s*/, ''));
      setShowHint(true);
    } finally {
      setLoadingHint(false);
    }
  }

  function togglePause() {
    if (feedback || submitting) return;
    const now = Date.now();
    if (isPaused) {
      const startedAt = pauseStartedAtRef.current;
      if (startedAt) {
        const pauseMs = now - startedAt;
        setSessionPausedMs((value) => value + pauseMs);
        setQuestionPausedMs((value) => value + pauseMs);
      }
      pauseStartedAtRef.current = null;
      lastActionRef.current = now;
      setIsPaused(false);
      playSound('tap');
      return;
    }
    pauseStartedAtRef.current = now;
    setIsPaused(true);
    playSound('tap');
  }

  function classifyError(isCorrect: boolean, given: string, expected: string, topic: string): InteractionEvent['error_type'] {
    if (isCorrect) return 'none';
    const givenNum = parseFloat(given);
    const expectedNum = parseFloat(expected);
    if (!isNaN(givenNum) && !isNaN(expectedNum)) {
      const diff = Math.abs(givenNum - expectedNum);
      if (diff <= 2) return 'careless';
      if (topic === 'Number Comparison') return 'conceptual';
      return 'calculation';
    }
    return 'unknown';
  }

  function buildEvent(
    isCorrect: boolean,
    _givenAnswer: string,
    nextAttempts: number,
    nextClickCount: number,
    errorType: InteractionEvent['error_type'],
  ): InteractionEvent {
    const now = Date.now();
    const currentPauseMs = isPaused && pauseStartedAtRef.current
      ? now - pauseStartedAtRef.current
      : 0;
    const activeQuestionMs = Math.max(
      0,
      now - questionStartRef.current - questionPausedMs - currentPauseMs,
    );
    const activeSessionMs = Math.max(
      0,
      now - sessionStartRef.current - sessionPausedMs - currentPauseMs,
    );
    const responseTimeSec = activeQuestionMs / 1000;
    const sessionTimeSec = activeSessionMs / 1000;
    const timeBetweenActions = nextClickCount > 1
      ? activeQuestionMs / (nextClickCount * 1000)
      : responseTimeSec;

    return {
      question_id: current.id,
      topic: current.topic,
      difficulty: current.difficulty,
      response_time_sec: Math.round(responseTimeSec * 10) / 10,
      attempts: nextAttempts,
      response_matched: isCorrect,
      assist_used: hintUsed,
      click_count: nextClickCount,
      session_time_sec: Math.round(sessionTimeSec * 10) / 10,
      time_between_actions: Math.round(timeBetweenActions * 10) / 10,
      error_type: errorType,
    };
  }

  async function finishQuestion(event: InteractionEvent, delayMs: number) {
    const nextEvents = [...events, event];
    setEvents(nextEvents);

    if (index + 1 < bankQuestions.length) {
      setTimeout(() => setIndex(index + 1), delayMs);
      return;
    }

    // Last question: send the run and show its profile.
    setSubmitting(true);
    playSound('complete');
    pendingSubmitRef.current = { sessionId, body: { language: lang, events: nextEvents } };
    await submitProfile();
  }

  async function submitProfile() {
    const pending = pendingSubmitRef.current;
    if (!pending) return;
    setSubmitFailed(false);
    setSubmitting(true);
    try {
      await call((api, accessToken) => api.createSessionProfile(pending.sessionId, pending.body, accessToken));
      pendingSubmitRef.current = null;
      setTimeout(() => {
        // `replace`: Back from the result must not return to a finished quiz.
        navigation.replace('ProfileResult', { sessionId: pending.sessionId });
        setQuizGate('start');
      }, 1800);
    } catch {
      // In-screen card with Try again (Alert does not show on web). The run stays pending, so the
      // child's answers are not lost and cannot be counted twice.
      setSubmitting(false);
      setSubmitFailed(true);
    }
  }

  // Pauses the run behind the popup, so the question timer does not keep counting.
  function openLeaveConfirm() {
    if (!isPaused && !feedback && !submitting) {
      togglePause();
      pausedForLeaveRef.current = true;
    }
    setConfirmLeave(true);
  }
  useEffect(() => {
    openLeaveRef.current = openLeaveConfirm;
  });

  function keepPlaying() {
    setConfirmLeave(false);
    if (pausedForLeaveRef.current) {
      pausedForLeaveRef.current = false;
      togglePause();
    }
  }

  async function handleSubmit() {
    if (pendingSubmitRef.current || selected === null || !current || isPaused) return;
    const nextClickCount = clickCount + 1;
    trackAction();

    const isCorrect = selected === current.correct_answer;
    const nextAttempts = attempts + 1;
    setAttempts(nextAttempts);

    // Allow second attempt on wrong answer
    if (!isCorrect && nextAttempts < 2) {
      setFeedback('wrong');
      playSound('wrong');
      Vibration.vibrate(300);
      setTimeout(() => {
        setFeedback(null);
        setSelected(null);
      }, 1200);
      return;
    }

    if (isCorrect) {
      playSound('correct');
      setCelebrationAnimal(randomCelebrationAnimal());
      setShowCelebration(true);
      setStreak(s => s + 1);
      // Floating star animation
      setShowFloatingStar(true);
      floatingStarY.setValue(0);
      floatingStarOpacity.setValue(1);
      Animated.parallel([
        Animated.timing(floatingStarY, { toValue: -80, duration: 1000, useNativeDriver: true }),
        Animated.timing(floatingStarOpacity, { toValue: 0, duration: 1000, useNativeDriver: true }),
      ]).start(() => setShowFloatingStar(false));
    } else {
      playSound('wrong');
      Vibration.vibrate(300);
      setStreak(0);
    }
    setFeedback(isCorrect ? 'correct' : 'wrong');
    // Animate feedback banner entrance
    feedbackScale.setValue(0.5);
    Animated.spring(feedbackScale, { toValue: 1, friction: 4, tension: 150, useNativeDriver: true }).start();

    const errorType = classifyError(isCorrect, selected, current.correct_answer, current.topic);
    const event = buildEvent(isCorrect, selected, nextAttempts, nextClickCount, errorType);
    await finishQuestion(event, isCorrect ? 1400 : 800);
  }

  async function handleSkip() {
    if (pendingSubmitRef.current || !current || feedback || submitting || isPaused) return;
    const nextClickCount = clickCount + 1;
    trackAction();
    playSound('tap');
    setFeedback('skipped');
    const event = buildEvent(false, 'Skipped', Math.max(attempts, 1), nextClickCount, 'unknown');
    await finishQuestion(event, 500);
  }

  // ── Quiz Gate: Start / Resume screens ──
  if (quizGate === 'start' || quizGate === 'resume') {
    return (
      // No back row here (owner request, 2026-10-21): compD's yellow fills the whole page.
      <View style={{ backgroundColor: colors.background, flex: 1 }}>
        <QuizGateView
          mode={quizGate}
          questionIndex={index + 1}
          totalQuestions={bankQuestions.length || TOTAL_QUESTIONS}
          onPress={quizGate === 'start' ? startQuiz : resumeQuiz}
        />
      </View>
    );
  }

  if (loadingQuestions) {
    return (
      <View style={styles.center}>
        <AnimalMascot animal={5} size={120} />
        <Text style={styles.loadingText}>{t.activity.loadingQuestions}</Text>
      </View>
    );
  }

  if (!current) return null;

  const progress = (index + 1) / bankQuestions.length;
  const questionText = lang === 'si' ? current.question_text_si : current.question_text;

  return (
    <View style={styles.container}>
      <ScrollView style={styles.container} contentContainerStyle={styles.scrollContent}>
        {/* An X, not "Back" (owner request, 2026-10-21), styled like Component C's exit button. It
            opens the leave popup; Android's hardware back opens the same popup. */}
        {!submitting && !pendingSubmitRef.current ? (
          <TouchableOpacity
            accessibilityLabel={lang === 'si' ? 'ක්‍රියාකාරකමෙන් ඉවත් වන්න' : 'Leave the quiz'}
            accessibilityRole="button"
            activeOpacity={0.75}
            hitSlop={8}
            onPress={openLeaveConfirm}
            style={styles.exitButton}>
            <Ionicons color={colors.textMuted} name="close" size={22} />
          </TouchableOpacity>
        ) : null}

        {submitFailed ? (
          <Card style={styles.noticeCard}>
            <Text style={styles.noticeTitle}>{t.activity.couldNotReachServer}</Text>
            <Text style={styles.noticeBody}>{t.activity.checkConnection}</Text>
            <PrimaryButton title={lang === 'si' ? 'නැවත උත්සාහ කරන්න' : 'Try again'} onPress={submitProfile} />
          </Card>
        ) : null}

        {/* Celebration overlay */}
        <CelebrationOverlay visible={showCelebration} animal={celebrationAnimal} />

        {/* Timer display */}
        <KidTimerBar
          startTime={questionStartRef.current}
          pausedMs={questionPausedMs}
          isPaused={isPaused}
          pauseStartedAt={pauseStartedAtRef.current}
          mascot={current.mascot}
          onTogglePause={togglePause}
          onSkip={handleSkip}
          onAutoSkip={handleSkip}
          disableSkip={!!feedback || submitting}
        />

        {/* Streak counter */}
        {streak >= 2 && (
          <View style={styles.streakBanner}>
            <Text style={styles.streakText}>🔥 {streak} in a row!</Text>
          </View>
        )}

        {/* Progress */}
        <View style={styles.progressWrap}>
          <View style={styles.progressBar}>
            <Animated.View style={[styles.progressFill, { width: `${progress * 100}%` }]} />
          </View>
          <Text style={styles.progressLabel}>
            {index + 1} / {bankQuestions.length}
          </Text>
        </View>

        {/* Floating Star Reward */}
        {showFloatingStar && (
          <Animated.View
            style={[
              styles.floatingStar,
              { transform: [{ translateY: floatingStarY }], opacity: floatingStarOpacity },
            ]}
          >
            <Text style={{ fontSize: 32 }}>⭐</Text>
          </Animated.View>
        )}

        {/* Feedback Banner — animated entrance */}
        {feedback && (
          <Animated.View
            style={[
              styles.feedbackBanner,
              {
                backgroundColor: feedback === 'correct' ? colors.successBg : feedback === 'skipped' ? colors.skyBlueSoft : colors.dangerBg,
                borderColor: feedback === 'correct' ? colors.success : feedback === 'skipped' ? colors.primary : colors.danger,
                transform: [{ scale: feedbackScale }],
              },
            ]}
          >
            <Text style={styles.feedbackText}>
              {feedback === 'correct'
                ? (streak >= 3 ? `🔥 ${t.activity.greatJob} (${streak}x streak!)` : t.activity.greatJob)
                : feedback === 'skipped' ? '⏭️ Skipped!' : t.activity.tryAgain}
            </Text>
          </Animated.View>
        )}

        {isPaused && (
          <View style={styles.pausedBanner}>
            <Text style={styles.pausedText}>Timer paused</Text>
          </View>
        )}

        {/* Question Card — animated entrance */}
        <Animated.View style={{ flex: 1, transform: [{ translateY: slideAnim }, { scale: scaleAnim }] }}>
          <Card style={styles.questionCard}>
            {/* Topic + Difficulty + Animal Mascot */}
            <View style={styles.qHeader}>
              <View style={styles.qTypeRow}>
                <Text style={styles.qType}>{getTranslatedTopic(current.topic, t)}</Text>
                <View style={styles.difficultyDots}>
                  {Array.from({ length: 3 }).map((_, i) => (
                    <View
                      key={i}
                      style={[
                        styles.dot,
                        {
                          backgroundColor:
                            i < (DIFFICULTY_DOTS[current.difficulty] ?? 1)
                              ? colors.primary
                              : colors.border,
                        },
                      ]}
                    />
                  ))}
                </View>
              </View>
              <AnimalMascot
                animal={current.mascot}
                size={72}
                celebrating={feedback === 'correct'}
              />
            </View>

            <Text style={styles.prompt}>{questionText}</Text>

            <View style={styles.options}>
              {current.options.map((opt, optIdx) => {
                const isSelected = selected === opt;
                const optionColors = [colors.coral, colors.green, colors.blue, colors.purple];
                const bgColor = optionColors[optIdx % optionColors.length];
                const optionLetters = ['A', 'B', 'C', 'D'];
                return (
                  <TouchableOpacity
                    key={`${opt}-${optIdx}`}
                    activeOpacity={0.7}
                    onPress={() => handleSelect(opt)}
                    disabled={!!feedback || isPaused}
                    style={[
                      styles.option,
                      isSelected && [styles.optionSelected, { borderColor: bgColor, backgroundColor: bgColor }],
                    ]}
                  >
                    <View style={styles.optionInner}>
                      <View style={[styles.optionBadge, { backgroundColor: isSelected ? 'rgba(255,255,255,0.3)' : bgColor + '30' }]}>
                        <Text style={[styles.optionBadgeText, { color: isSelected ? '#FFF' : bgColor }]}>
                          {optionLetters[optIdx]}
                        </Text>
                      </View>
                      <Text
                        style={[
                          styles.optionText,
                          isSelected && styles.optionTextSelected,
                        ]}
                      >
                        {opt}
                      </Text>
                    </View>
                  </TouchableOpacity>
                );
              })}
            </View>

            {showHint && (
              <View style={styles.hintBox}>
                <Text style={styles.hintText}>💡 {hintText}</Text>
              </View>
            )}
          </Card>
        </Animated.View>

        {/* Attempt counter */}
        <View style={styles.metaRow}>
          <Text style={styles.metaText}>{t.activity.attempts}: {attempts}</Text>
          <Text style={styles.metaText}>{t.activity.clicks}: {clickCount}</Text>
        </View>

        {/* Action Buttons */}
        <View style={styles.actions}>
          <PrimaryButton
            title={loadingHint ? 'Loading...' : showHint ? t.activity.hintShown : t.activity.hint}
            onPress={handleHint}
            variant="ghost"
            disabled={showHint || loadingHint || !!feedback || isPaused}
            loading={loadingHint}
            style={{ flex: 1 }}
          />
          <PrimaryButton
            title={index + 1 === bankQuestions.length ? t.common.finish : t.common.submit}
            onPress={handleSubmit}
            disabled={selected === null || !!feedback || isPaused}
            loading={submitting}
            style={{ flex: 1 }}
          />
        </View>
      </ScrollView>
      {confirmLeave ? (
        <LeaveQuizPopup lang={lang} onKeepPlaying={keepPlaying} onLeave={() => navigation.replace('StudentHome')} />
      ) : null}
    </View>
  );
}


function QuizGateView({
  mode,
  questionIndex,
  totalQuestions,
  onPress,
}: {
  mode: 'start' | 'resume';
  questionIndex: number;
  totalQuestions: number;
  onPress: () => void;
}) {
  const { lang } = useLanguage();
  const { colors } = useAppTheme();
  const styles = createStyles(colors);
  const floatAnim = useRef(new Animated.Value(0)).current;
  const haloAnim = useRef(new Animated.Value(0)).current;
  const isResume = mode === 'resume';

  useEffect(() => {
    const floatLoop = Animated.loop(
      Animated.sequence([
        Animated.timing(floatAnim, { toValue: 1, duration: 1100, useNativeDriver: true }),
        Animated.timing(floatAnim, { toValue: 0, duration: 1100, useNativeDriver: true }),
      ]),
    );
    const haloLoop = Animated.loop(
      Animated.sequence([
        Animated.timing(haloAnim, { toValue: 1, duration: 900, useNativeDriver: true }),
        Animated.timing(haloAnim, { toValue: 0, duration: 900, useNativeDriver: true }),
      ]),
    );
    floatLoop.start();
    haloLoop.start();
    return () => { floatLoop.stop(); haloLoop.stop(); };
  }, [floatAnim, haloAnim]);

  const copy = lang === 'si'
    ? {
        title: isResume ? 'ප්‍රශ්නාවලිය නවතා ඇත' : 'ප්‍රශ්නාවලියට සූදානම්ද?',
        subtitle: isResume
          ? 'ඔබ නැවත පැමිණෙන තුරු timer එක නවතා තබා ඇත.'
          : 'ඔබ සූදානම් වූ විට ප්‍රශ්නාවලිය ආරම්භ කරන්න.',
        detail: isResume ? `ප්‍රශ්නය ${questionIndex} / ${totalQuestions}` : `ප්‍රශ්න ${totalQuestions}`,
        button: isResume ? 'ප්‍රශ්නාවලිය නැවත ආරම්භ කරන්න' : 'ප්‍රශ්නාවලිය ආරම්භ කරන්න',
      }
    : {
        title: isResume ? 'Quiz Paused' : 'Ready for a Quiz?',
        subtitle: isResume
          ? 'The timer is paused until you come back.'
          : 'Tap Start Quiz when you are ready.',
        detail: isResume ? `Question ${questionIndex} / ${totalQuestions}` : `${totalQuestions} questions`,
        button: isResume ? 'Resume Quiz' : 'Start Quiz',
      };

  const translateY = floatAnim.interpolate({ inputRange: [0, 1], outputRange: [0, -14] });
  const haloScale = haloAnim.interpolate({ inputRange: [0, 1], outputRange: [0.92, 1.08] });
  const haloOpacity = haloAnim.interpolate({ inputRange: [0, 1], outputRange: [0.35, 0.65] });

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.gateContent}>
      <View style={styles.gateHero}>
        <Animated.View style={[styles.gateHalo, { opacity: haloOpacity, transform: [{ scale: haloScale }] }]} />
        <View style={[styles.gateBubble, styles.gateBubbleTop]}><Text style={styles.gateBubbleText}>1</Text></View>
        <View style={[styles.gateBubble, styles.gateBubbleRight]}><Text style={styles.gateBubbleText}>+</Text></View>
        <View style={[styles.gateBubble, styles.gateBubbleBottom]}><Text style={styles.gateBubbleText}>2</Text></View>
        <View style={[styles.gateBubble, styles.gateBubbleLeft]}><Text style={styles.gateBubbleText}>=</Text></View>
        <Animated.View style={[styles.gateMascot, { transform: [{ translateY }] }]}>
          <AnimalMascot animal={isResume ? 18 : 5} size={150} />
        </Animated.View>
      </View>
      <Text style={styles.gateTitle}>{copy.title}</Text>
      <Text style={styles.gateSubtitle}>{copy.subtitle}</Text>
      <View style={styles.gatePill}><Text style={styles.gatePillText}>{copy.detail}</Text></View>
      <View style={styles.gateAction}>
        <PrimaryButton title={copy.button} onPress={onPress} />
      </View>
    </ScrollView>
  );
}

function KidTimerBar({
  startTime,
  pausedMs,
  isPaused,
  pauseStartedAt,
  mascot,
  onTogglePause,
  onSkip,
  onAutoSkip,
  disableSkip,
}: {
  startTime: number;
  pausedMs: number;
  isPaused: boolean;
  pauseStartedAt: number | null;
  mascot: AnimalId;
  onTogglePause: () => void;
  onSkip: () => void;
  onAutoSkip: () => void;
  disableSkip: boolean;
}) {
  const { colors } = useAppTheme();
  const timerStyles = createTimerStyles(colors);
  const [elapsed, setElapsed] = useState(0);
  const warnedRef = useRef(false);
  const autoSkippedRef = useRef(false);
  const [showWarning, setShowWarning] = useState(false);

  useEffect(() => {
    // Reset refs when question changes (startTime changes)
    warnedRef.current = false;
    autoSkippedRef.current = false;
    setShowWarning(false);
  }, [startTime]);

  useEffect(() => {
    const calculateElapsed = () => {
      const now = Date.now();
      const currentPauseMs = isPaused && pauseStartedAt ? now - pauseStartedAt : 0;
      const activeMs = Math.max(0, now - startTime - pausedMs - currentPauseMs);
      const secs = Math.floor(activeMs / 1000);
      setElapsed(secs);

      // 1:00 warning
      if (secs >= TIME_WARNING_SECONDS && !warnedRef.current && !disableSkip) {
        warnedRef.current = true;
        playSound('alarm');
        Vibration.vibrate(500);
        setShowWarning(true);
      }

      // 2:00 auto-skip
      if (secs >= AUTO_SKIP_SECONDS && !autoSkippedRef.current && !disableSkip) {
        autoSkippedRef.current = true;
        onAutoSkip();
        setElapsed(AUTO_SKIP_SECONDS); // Cap at 2:00
        return; // Stop timer updates after auto-skip
      }
    };
    calculateElapsed();
    const interval = setInterval(calculateElapsed, 1000);
    return () => clearInterval(interval);
  }, [isPaused, pauseStartedAt, pausedMs, startTime, disableSkip, onAutoSkip]);

  const displayElapsed = Math.min(elapsed, AUTO_SKIP_SECONDS); // Cap display at 2:00
  const mins = Math.floor(displayElapsed / 60);
  const secs = displayElapsed % 60;
  const progress = Math.min(displayElapsed / QUESTION_TIMER_SECONDS, 1);
  const markerLeft = `${Math.min(92, Math.max(4, progress * 92))}%`;

  return (
    <View style={timerStyles.shell}>
      {showWarning ? (
        <Text accessibilityLiveRegion="polite" style={timerStyles.warning}>
          ⏰ Time is running out! The question will be skipped at 2:00.
        </Text>
      ) : null}
      <View style={timerStyles.timerRow}>
        <View style={timerStyles.track}>
          <View
            style={[
              timerStyles.fill,
              {
                width: `${Math.max(8, progress * 100)}%` as any,
                backgroundColor: progress > 0.82 ? colors.coral : colors.warmYellow,
              },
            ]}
          />
          <View style={[timerStyles.mascotMarker, { left: markerLeft as any }]}>
            <AnimalMascot animal={mascot} size={34} />
          </View>
        </View>
        <View style={timerStyles.timeBubble}>
          <Text style={timerStyles.text}>
            {mins}:{secs.toString().padStart(2, '0')}
          </Text>
        </View>
      </View>
      <View style={timerStyles.buttonRow}>
        <TouchableOpacity style={timerStyles.pauseButton} onPress={onTogglePause} activeOpacity={0.75}>
          <Text style={timerStyles.pauseButtonText}>{isPaused ? 'Resume' : 'Pause'}</Text>
        </TouchableOpacity>
        <TouchableOpacity
          style={[timerStyles.skipButton, disableSkip && timerStyles.disabledButton]}
          onPress={disableSkip ? undefined : onSkip}
          activeOpacity={0.75}
          disabled={disableSkip}
        >
          <Text style={timerStyles.skipButtonText}>Skip</Text>
        </TouchableOpacity>
      </View>
    </View>
  );
}

const createTimerStyles = (colors: typeof lightColors) => StyleSheet.create({
  warning: {
    ...typography.caption,
    backgroundColor: colors.warningBg,
    borderRadius: radius.md,
    color: colors.textWarm,
    overflow: 'hidden',
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.xs,
    textAlign: 'center',
  },
  shell: {
    gap: spacing.sm,
  },
  timerRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.sm,
  },
  track: {
    flex: 1,
    height: 30,
    borderRadius: radius.pill,
    backgroundColor: colors.skyBlue,
    borderWidth: 3,
    borderColor: colors.surface,
    overflow: 'visible',
    justifyContent: 'center',
  },
  fill: {
    position: 'absolute',
    left: 0,
    top: 0,
    bottom: 0,
    borderRadius: radius.pill,
  },
  mascotMarker: {
    position: 'absolute',
    top: -8,
    width: 38,
    height: 38,
    borderRadius: 19,
    backgroundColor: colors.surface,
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 2,
    borderColor: colors.warmYellow,
  },
  timeBubble: {
    minWidth: 70,
    minHeight: 38,
    borderRadius: radius.pill,
    backgroundColor: colors.surface,
    borderWidth: 2,
    borderColor: colors.warmYellow,
    alignItems: 'center',
    justifyContent: 'center',
  },
  buttonRow: {
    flexDirection: 'row',
    gap: spacing.sm,
  },
  pauseButton: {
    flex: 1,
    minHeight: 40,
    borderRadius: radius.pill,
    backgroundColor: colors.primary,
    alignItems: 'center',
    justifyContent: 'center',
  },
  pauseButtonText: {
    ...typography.caption,
    color: colors.textInverse,
  },
  skipButton: {
    flex: 1,
    minHeight: 40,
    borderRadius: radius.pill,
    backgroundColor: colors.surface,
    borderWidth: 2,
    borderColor: colors.coral,
    alignItems: 'center',
    justifyContent: 'center',
  },
  skipButtonText: {
    ...typography.caption,
    color: colors.coral,
  },
  disabledButton: {
    opacity: 0.45,
  },
  text: {
    ...typography.subtitle,
    color: colors.textWarm,
    fontVariant: ['tabular-nums'],
  },
});

function getTranslatedTopic(topic: string, translations: any): string {
  const t = topic.toLowerCase();
  const topicKey = t.includes('counting') ? 'counting' :
                   t.includes('addition') ? 'addition' :
                   t.includes('subtraction') ? 'subtraction' :
                   t.includes('multiplication') ? 'multiplication' :
                   t.includes('division') ? 'division' :
                   t.includes('comparison') ? 'comparison' :
                   t.includes('recognition') ? 'recognition' : 'counting';
  return translations.activity.topics[topicKey] || topic;
}

function hintFor(topic: string): string {
  const t = topic.toLowerCase();
  if (t.includes('addition')) return 'Try counting up from the bigger number.';
  if (t.includes('subtraction')) return 'Think: what do I add to the small number to get the big one?';
  if (t.includes('division')) return 'Try splitting into equal groups.';
  if (t.includes('comparison')) return 'Compare the first digits first.';
  if (t.includes('counting')) return 'Count carefully, one by one.';
  return 'Take a breath and read the question again.';
}

const createStyles = (colors: typeof lightColors) => StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.background },
  noticeCard: { gap: spacing.sm },
  exitButton: {
    alignItems: 'center',
    alignSelf: 'flex-start',
    backgroundColor: colors.surface,
    borderColor: colors.border,
    borderRadius: 17,
    borderWidth: 1.5,
    height: 34,
    justifyContent: 'center',
    width: 34,
  },
  noticeTitle: { ...typography.subtitle, color: colors.textWarm, textAlign: 'center' },
  noticeBody: { ...typography.body, color: colors.text, textAlign: 'center' },
  scrollContent: { padding: spacing.lg, paddingTop: spacing.md, gap: spacing.sm, paddingBottom: spacing.xxl },
  center: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    gap: spacing.md,
  },
  loadingText: {
    ...typography.subtitle,
    color: colors.textWarm,
    marginTop: spacing.md,
  },
    progressWrap: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.md,
  },
  progressBar: {
    flex: 1,
    height: 14,
    backgroundColor: colors.skyBlueSoft,
    borderRadius: radius.pill,
    overflow: 'hidden',
    borderWidth: 1.5,
    borderColor: colors.border,
  },
  progressFill: {
    height: '100%',
    backgroundColor: colors.warmYellow,
    borderRadius: radius.pill,
  },
  progressLabel: {
    ...typography.subtitle,
    color: colors.textWarm,
  },
  streakBanner: {
    backgroundColor: '#FFF3E0',
    borderRadius: radius.pill,
    borderWidth: 2,
    borderColor: '#FF9800',
    paddingVertical: spacing.sm,
    paddingHorizontal: spacing.lg,
    alignItems: 'center',
    alignSelf: 'center',
    shadowColor: '#FF9800',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.3,
    shadowRadius: 4,
    elevation: 3,
  },
  streakText: {
    ...typography.subtitle,
    color: '#E65100',
    fontSize: 16,
    fontWeight: '900',
    letterSpacing: 0.5,
  },
  floatingStar: {
    position: 'absolute',
    alignSelf: 'center',
    top: '30%',
    zIndex: 100,
  },
  feedbackBanner: {
    paddingVertical: spacing.sm,
    paddingHorizontal: spacing.md,
    borderRadius: radius.lg,
    alignItems: 'center',
    borderWidth: 2,
  },
  feedbackText: {
    ...typography.subtitle,
    color: colors.text,
    fontSize: 16,
  },
  pausedBanner: {
    backgroundColor: colors.skyBlueSoft,
    borderRadius: radius.pill,
    borderWidth: 2,
    borderColor: colors.primaryLight,
    paddingVertical: spacing.sm,
    alignItems: 'center',
  },
  pausedText: {
    ...typography.caption,
    color: colors.primaryDark,
  },
  questionCard: { gap: spacing.sm, flex: 1 },
  qHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  qTypeRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.sm,
    flex: 1,
  },
  qType: {
    ...typography.caption,
    color: colors.primaryDark,
    textTransform: 'uppercase',
    letterSpacing: 1.2,
    flex: 1,
  },
  difficultyDots: {
    flexDirection: 'row',
    gap: 4,
  },
  dot: {
    width: 8,
    height: 8,
    borderRadius: 4,
  },
  prompt: {
    fontSize: 28,
    fontWeight: '800',
    color: colors.textWarm,
    textAlign: 'center',
    paddingVertical: spacing.sm,
    lineHeight: 38,
  },
  options: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: spacing.md,
    justifyContent: 'center',
  },
  option: {
    minWidth: '44%',
    paddingVertical: spacing.md,
    paddingHorizontal: spacing.sm,
    borderRadius: radius.xl,
    backgroundColor: colors.surfaceSoft,
    borderWidth: 2.5,
    borderColor: colors.border,
    alignItems: 'center',
  },
  optionSelected: {
    borderWidth: 2.5,
  },
  optionInner: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.sm,
  },
  optionBadge: {
    width: 28,
    height: 28,
    borderRadius: 14,
    alignItems: 'center',
    justifyContent: 'center',
  },
  optionBadgeText: {
    fontSize: 14,
    fontWeight: '800',
  },
  optionText: {
    fontSize: 22,
    fontWeight: '800',
    color: colors.textWarm,
  },
  optionTextSelected: { color: colors.textInverse },
  hintBox: {
    backgroundColor: colors.warningBg,
    padding: spacing.md,
    borderRadius: radius.md,
    borderWidth: 1.5,
    borderColor: '#F4E2A1',
  },
  hintText: { ...typography.body, color: '#8A6A12' },
  metaRow: {
    flexDirection: 'row',
    justifyContent: 'space-around',
  },
  metaText: {
    ...typography.caption,
    color: colors.textMuted,
  },
  actions: { flexDirection: 'row', gap: spacing.md },
  // ── Quiz Gate styles ──
  gateContent: {
    flexGrow: 1,
    alignItems: 'center',
    justifyContent: 'center',
    padding: spacing.lg,
    paddingBottom: spacing.xxl,
    gap: spacing.md,
  },
  gateHero: {
    width: 240,
    height: 240,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: spacing.sm,
  },
  gateHalo: {
    position: 'absolute',
    width: 210,
    height: 210,
    borderRadius: 105,
    backgroundColor: colors.warmYellowSoft,
    borderWidth: 3,
    borderColor: colors.warmYellow,
  },
  gateMascot: {
    width: 170,
    height: 170,
    borderRadius: 85,
    backgroundColor: colors.surface,
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 4,
    borderColor: colors.warmYellow,
    shadowColor: colors.shadow,
    shadowOffset: { width: 0, height: 8 },
    shadowOpacity: 0.8,
    shadowRadius: 16,
    elevation: 8,
  },
  gateBubble: {
    position: 'absolute',
    width: 46,
    height: 46,
    borderRadius: 23,
    backgroundColor: colors.surface,
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 2.5,
    borderColor: colors.border,
    shadowColor: colors.shadow,
    shadowOffset: { width: 0, height: 3 },
    shadowOpacity: 0.35,
    shadowRadius: 6,
    elevation: 3,
  },
  gateBubbleTop: { top: 4, left: 98 },
  gateBubbleRight: { right: 4, top: 96 },
  gateBubbleBottom: { bottom: 2, left: 99 },
  gateBubbleLeft: { left: 4, top: 96 },
  gateBubbleText: {
    ...typography.subtitle,
    color: colors.primaryDark,
  },
  gateTitle: {
    ...typography.title,
    color: colors.textWarm,
    textAlign: 'center',
  },
  gateSubtitle: {
    ...typography.body,
    color: colors.textMuted,
    textAlign: 'center',
    lineHeight: 24,
    maxWidth: 320,
  },
  gatePill: {
    borderRadius: radius.pill,
    paddingHorizontal: spacing.lg,
    paddingVertical: spacing.sm,
    backgroundColor: colors.skyBlueSoft,
    borderWidth: 1.5,
    borderColor: colors.primaryLight,
  },
  gatePillText: {
    ...typography.caption,
    color: colors.primaryDark,
  },
  gateAction: {
    width: '100%',
    marginTop: spacing.sm,
  },
});
