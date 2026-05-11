import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  Alert,
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
import { useFocusEffect } from '@react-navigation/native';
import PrimaryButton from '../components/PrimaryButton';
import Card from '../components/Card';
import AnimalMascot from '../components/AnimalMascot';
import CelebrationOverlay from '../components/CelebrationOverlay';
import { useLanguage } from '../i18n/LanguageContext';
import { colors as lightColors, radius, spacing, typography, useAppTheme } from '../theme';
import { api, type InteractionEvent } from '../api/client';
import { pickQuestions, type BankQuestion } from '../data/questionBank';
import { playSound, unloadAllSounds } from '../utils/sounds';
import { generateMathHint } from '../utils/gemini';
import { randomCelebrationAnimal, type AnimalId } from '../assets/animalImages';

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

export default function MathActivityScreen({ route, navigation }: any) {
  const { t, lang } = useLanguage();
  const { colors } = useAppTheme();
  const styles = createStyles(colors);
  const { studentId } = route.params;
  const sessionId = useMemo(() => `math_${studentId}_${Date.now()}`, [studentId]);

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

  useEffect(() => { indexRef.current = index; }, [index]);
  useEffect(() => { submittingRef.current = submitting; }, [submitting]);
  useEffect(() => { quizGateRef.current = quizGate; }, [quizGate]);

  useEffect(() => {
    return () => { unloadAllSounds(); };
  }, []);

  // Handle mobile back button — navigate to Home tab instead of closing app
  useFocusEffect(
    useCallback(() => {
      const onBackPress = () => {
        if (submittingRef.current) return true;
        try { navigation.navigate('StudentHome', { studentId }); } catch {}
        return true;
      };
      const subscription = BackHandler.addEventListener('hardwareBackPress', onBackPress);
      return () => subscription.remove();
    }, [navigation, studentId])
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
        console.log('[activity] quiz paused by navigation', {
          studentId,
          sessionId,
          questionIndex: indexRef.current + 1,
        });
      };
    }, [studentId, sessionId]),
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
        console.log('[activity] quiz paused by app background');
      }
    });
    return () => subscription.remove();
  }, []);

  // ── Start Quiz handler ──
  const startQuiz = useCallback(() => {
    const questions = pickQuestions(TOTAL_QUESTIONS);
    const now = Date.now();
    console.log('[activity] session start', { studentId, sessionId, questionCount: questions.length });
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
  }, [studentId, sessionId]);

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
    setQuizGate('active');
    playSound('tap');
    console.log('[activity] quiz resumed', {
      studentId,
      sessionId,
      questionIndex: indexRef.current + 1,
    });
  }, [studentId, sessionId]);

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
      setHintText(hint.text);
      setShowHint(true);
    } catch (error) {
      // Fallback to static hint if API fails
      setHintText(hintFor(current.topic));
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
    givenAnswer: string,
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
      student_id: studentId,
      session_id: sessionId,
      question_id: current.id,
      topic: current.topic,
      difficulty: current.difficulty,
      response_time_sec: Math.round(responseTimeSec * 10) / 10,
      attempts: nextAttempts,
      is_correct: isCorrect,
      hint_used: hintUsed,
      click_count: nextClickCount,
      session_time_sec: Math.round(sessionTimeSec * 10) / 10,
      time_between_actions: Math.round(timeBetweenActions * 10) / 10,
      error_type: errorType,
      expected_answer: current.correct_answer,
      given_answer: givenAnswer,
    };
  }

  async function finishQuestion(event: InteractionEvent, delayMs: number) {
    const nextEvents = [...events, event];
    setEvents(nextEvents);
    console.log('[activity] question completed', {
      studentId,
      sessionId,
      questionIndex: index + 1,
      totalQuestions: bankQuestions.length,
      questionId: event.question_id,
      isCorrect: event.is_correct,
      attempts: event.attempts,
      responseTimeSec: event.response_time_sec,
      eventsReady: nextEvents.length,
    });

    if (index + 1 < bankQuestions.length) {
      setTimeout(() => setIndex(index + 1), delayMs);
      return;
    }

    // Last question — send data and navigate to profile
    setSubmitting(true);
    playSound('complete');
    try {
      console.log('[activity] profile generation request', {
        studentId,
        sessionId,
        eventCount: nextEvents.length,
      });
      const profile = await api.generateProfile({
        student_id: studentId,
        session_id: sessionId,
        events: nextEvents,
      });
      console.log('[activity] profile generation success', {
        studentId,
        sessionId,
        totalQuestions: profile.features.total_questions,
        modelVersion: profile.model_version,
      });
      setTimeout(() => {
        // Navigate to Profile tab to show the result, or push to stack ProfileResult
        try {
          navigation.navigate('StudentProfile', { studentId, sessionId });
        } catch {
          navigation.navigate('ProfileResult', { studentId, sessionId });
        }
        // Reset quiz gate so next visit shows Start Quiz
        setQuizGate('start');
      }, 1800);
    } catch (e: any) {
      console.log('[activity] profile generation failed', {
        studentId,
        sessionId,
        message: e?.message,
      });
      Alert.alert(
        t.activity.couldNotReachServer,
        e?.message ?? t.activity.checkConnection,
      );
      setSubmitting(false);
      setFeedback(null);
    }
  }

  async function handleSubmit() {
    if (selected === null || !current || isPaused) return;
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
    } else {
      playSound('wrong');
      Vibration.vibrate(300);
    }
    setFeedback(isCorrect ? 'correct' : 'wrong');

    const errorType = classifyError(isCorrect, selected, current.correct_answer, current.topic);
    const event = buildEvent(isCorrect, selected, nextAttempts, nextClickCount, errorType);
    await finishQuestion(event, isCorrect ? 1400 : 800);
  }

  async function handleSkip() {
    if (!current || feedback || submitting || isPaused) return;
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
      <QuizGateView
        mode={quizGate}
        questionIndex={index + 1}
        totalQuestions={bankQuestions.length || TOTAL_QUESTIONS}
        onPress={quizGate === 'start' ? startQuiz : resumeQuiz}
      />
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
    <ScrollView style={styles.container} contentContainerStyle={styles.scrollContent}>
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

      {/* Progress */}
      <View style={styles.progressWrap}>
        <View style={styles.progressBar}>
          <View style={[styles.progressFill, { width: `${progress * 100}%` }]} />
        </View>
        <Text style={styles.progressLabel}>
          {index + 1} / {bankQuestions.length}
        </Text>
      </View>

      {/* Feedback Banner */}
      {feedback && (
        <Animated.View
          style={[
            styles.feedbackBanner,
            {
              backgroundColor: feedback === 'correct' ? colors.successBg : feedback === 'skipped' ? colors.skyBlueSoft : colors.dangerBg,
              borderColor: feedback === 'correct' ? colors.success : feedback === 'skipped' ? colors.primary : colors.danger,
            },
          ]}
        >
          <Text style={styles.feedbackText}>
            {feedback === 'correct' ? t.activity.greatJob : feedback === 'skipped' ? '⏭️ Skipped!' : t.activity.tryAgain}
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

  useEffect(() => {
    // Reset refs when question changes (startTime changes)
    warnedRef.current = false;
    autoSkippedRef.current = false;
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
        Alert.alert('⏰ Time is running out!', 'Hurry up! The question will be auto-skipped at 2:00.');
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
