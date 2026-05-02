import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  Alert,
  Animated,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from 'react-native';
import type { NativeStackScreenProps } from '@react-navigation/native-stack';
import type { RootStackParamList } from '../../App';
import PrimaryButton from '../components/PrimaryButton';
import Card from '../components/Card';
import AnimalMascot from '../components/AnimalMascot';
import CelebrationOverlay from '../components/CelebrationOverlay';
import { useLanguage } from '../i18n/LanguageContext';
import { colors, radius, spacing, typography } from '../theme';
import { api, type InteractionEvent } from '../api/client';
import { pickQuestions, type BankQuestion } from '../data/questionBank';
import { playSound, unloadAllSounds } from '../utils/sounds';
import { animalForTopic, randomCelebrationAnimal, type AnimalId } from '../assets/animalImages';

type Props = NativeStackScreenProps<RootStackParamList, 'MathActivity'>;

const TOTAL_QUESTIONS = 10;

const DIFFICULTY_DOTS: Record<string, number> = {
  'Easy': 1,
  'Medium': 2,
  'Hard': 3,
};

export default function MathActivityScreen({ route, navigation }: Props) {
  const { t, lang } = useLanguage();
  const { studentId } = route.params;
  const sessionId = useMemo(
    () => `ses_${Date.now()}_${Math.floor(Math.random() * 10000)}`,
    [],
  );

  const [bankQuestions, setBankQuestions] = useState<BankQuestion[]>([]);
  const [index, setIndex] = useState(0);
  const [selected, setSelected] = useState<string | null>(null);
  const [attempts, setAttempts] = useState(0);
  const [clickCount, setClickCount] = useState(0);
  const [hintUsed, setHintUsed] = useState(false);
  const [showHint, setShowHint] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [events, setEvents] = useState<InteractionEvent[]>([]);
  const [feedback, setFeedback] = useState<'correct' | 'wrong' | null>(null);
  const [loadingQuestions, setLoadingQuestions] = useState(true);
  const [showCelebration, setShowCelebration] = useState(false);
  const [celebrationAnimal, setCelebrationAnimal] = useState<AnimalId>(5);

  const questionStartRef = useRef<number>(Date.now());
  const sessionStartRef = useRef<number>(Date.now());
  const lastActionRef = useRef<number>(Date.now());

  // Animated values for question entrance
  const slideAnim = useRef(new Animated.Value(0)).current;
  const scaleAnim = useRef(new Animated.Value(1)).current;

  // Load questions: try backend first, fall back to local question bank
  useEffect(() => {
    (async () => {
      try {
        const q = await api.getQuestions();
        if (q && q.length >= TOTAL_QUESTIONS) {
          const shuffled = q.sort(() => Math.random() - 0.5).slice(0, TOTAL_QUESTIONS);
          // Map API questions to BankQuestion shape
          const mapped: BankQuestion[] = shuffled.map((apiQ) => {
            const topic = (apiQ.topic as BankQuestion['topic']) || 'Addition';
            return {
              id: apiQ.id,
              set: 1 as const,
              topic,
              difficulty: apiQ.difficulty,
              question_text: apiQ.question_text,
              question_text_si: apiQ.question_text,
              correct_answer: apiQ.correct_answer,
              options: apiQ.options ?? [apiQ.correct_answer],
              mascot: animalForTopic(topic),
            };
          });
          setBankQuestions(mapped);
        } else {
          throw new Error('Not enough questions');
        }
      } catch {
        // Use local 60-question bank with randomization
        setBankQuestions(pickQuestions(TOTAL_QUESTIONS));
      }
      setLoadingQuestions(false);
    })();
    return () => { unloadAllSounds(); };
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
    questionStartRef.current = Date.now();
    lastActionRef.current = Date.now();
    setSelected(null);
    setAttempts(0);
    setClickCount(0);
    setHintUsed(false);
    setShowHint(false);
    setFeedback(null);
    setShowCelebration(false);
    animateEntrance();
    if (index > 0) playSound('nextQuestion');
  }, [index, animateEntrance]);

  function trackAction() {
    lastActionRef.current = Date.now();
    setClickCount((c) => c + 1);
  }

  function handleSelect(option: string) {
    if (feedback) return;
    trackAction();
    playSound('tap');
    setSelected(option);
  }

  function handleHint() {
    if (showHint) return;
    trackAction();
    playSound('hint');
    setShowHint(true);
    setHintUsed(true);
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

  async function handleSubmit() {
    if (selected === null || !current) return;
    trackAction();

    const isCorrect = selected === current.correct_answer;
    const nextAttempts = attempts + 1;
    setAttempts(nextAttempts);

    // Allow second attempt on wrong answer
    if (!isCorrect && nextAttempts < 2) {
      setFeedback('wrong');
      playSound('wrong');
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
    }
    setFeedback(isCorrect ? 'correct' : 'wrong');

    const now = Date.now();
    const responseTimeSec = (now - questionStartRef.current) / 1000;
    const sessionTimeSec = (now - sessionStartRef.current) / 1000;
    const timeBetweenActions = clickCount > 1
      ? (now - questionStartRef.current) / (clickCount * 1000)
      : responseTimeSec;

    const errorType = classifyError(isCorrect, selected, current.correct_answer, current.topic);

    const event: InteractionEvent = {
      student_id: studentId,
      session_id: sessionId,
      question_id: current.id,
      topic: current.topic,
      difficulty: current.difficulty,
      response_time_sec: Math.round(responseTimeSec * 10) / 10,
      attempts: nextAttempts,
      is_correct: isCorrect,
      hint_used: hintUsed,
      click_count: clickCount,
      session_time_sec: Math.round(sessionTimeSec * 10) / 10,
      time_between_actions: Math.round(timeBetweenActions * 10) / 10,
      error_type: errorType,
      expected_answer: current.correct_answer,
      given_answer: selected,
    };

    const nextEvents = [...events, event];
    setEvents(nextEvents);

    if (index + 1 < bankQuestions.length) {
      setTimeout(() => setIndex(index + 1), isCorrect ? 1400 : 800);
      return;
    }

    // Last question — send data and navigate to profile
    setSubmitting(true);
    playSound('complete');
    try {
      await api.logInteractions(nextEvents).catch(() => undefined);
      await api.generateProfile({
        student_id: studentId,
        session_id: sessionId,
        events: nextEvents,
      });
      setTimeout(() => {
        navigation.replace('ProfileResult', { studentId, sessionId });
      }, 1800);
    } catch (e: any) {
      Alert.alert(
        t.activity.couldNotReachServer,
        e?.message ?? t.activity.checkConnection,
      );
      setSubmitting(false);
      setFeedback(null);
    }
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
      {/* Celebration overlay */}
      <CelebrationOverlay visible={showCelebration} animal={celebrationAnimal} />

      {/* Timer display */}
      <TimerDisplay startTime={sessionStartRef.current} />

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
              backgroundColor: feedback === 'correct' ? colors.successBg : colors.dangerBg,
              borderColor: feedback === 'correct' ? colors.success : colors.danger,
            },
          ]}
        >
          <Text style={styles.feedbackText}>
            {feedback === 'correct' ? t.activity.greatJob : t.activity.tryAgain}
          </Text>
        </Animated.View>
      )}

      {/* Question Card — animated entrance */}
      <Animated.View style={{ flex: 1, transform: [{ translateY: slideAnim }, { scale: scaleAnim }] }}>
        <Card style={styles.questionCard}>
          {/* Topic + Difficulty + Animal Mascot */}
          <View style={styles.qHeader}>
            <View style={styles.qTypeRow}>
              <Text style={styles.qType}>{current.topic}</Text>
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
                  disabled={!!feedback}
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
              <Text style={styles.hintText}>💡 {hintFor(current.topic)}</Text>
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
          title={showHint ? t.activity.hintShown : t.activity.hint}
          onPress={handleHint}
          variant="ghost"
          disabled={showHint || !!feedback}
          style={{ flex: 1 }}
        />
        <PrimaryButton
          title={index + 1 === bankQuestions.length ? t.common.finish : t.common.submit}
          onPress={handleSubmit}
          disabled={selected === null || !!feedback}
          loading={submitting}
          style={{ flex: 1 }}
        />
      </View>
    </View>
  );
}

// Simple timer component
function TimerDisplay({ startTime }: { startTime: number }) {
  const [elapsed, setElapsed] = useState(0);
  useEffect(() => {
    const interval = setInterval(() => {
      setElapsed(Math.floor((Date.now() - startTime) / 1000));
    }, 1000);
    return () => clearInterval(interval);
  }, [startTime]);
  const mins = Math.floor(elapsed / 60);
  const secs = elapsed % 60;
  return (
    <View style={timerStyles.container}>
      <Text style={timerStyles.icon}>⏱️</Text>
      <Text style={timerStyles.text}>
        {mins}:{secs.toString().padStart(2, '0')}
      </Text>
    </View>
  );
}

const timerStyles = StyleSheet.create({
  container: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 6,
    paddingVertical: 4,
  },
  icon: { fontSize: 16 },
  text: {
    ...typography.subtitle,
    color: colors.textWarm,
    fontVariant: ['tabular-nums'],
  },
});

function hintFor(topic: string): string {
  const t = topic.toLowerCase();
  if (t.includes('addition')) return 'Try counting up from the bigger number.';
  if (t.includes('subtraction')) return 'Think: what do I add to the small number to get the big one?';
  if (t.includes('division')) return 'Try splitting into equal groups.';
  if (t.includes('comparison')) return 'Compare the first digits first.';
  if (t.includes('counting')) return 'Count carefully, one by one.';
  return 'Take a breath and read the question again.';
}

const styles = StyleSheet.create({
  container: { flex: 1, padding: spacing.lg, paddingTop: spacing.md, gap: spacing.sm },
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
});
