import React, { useEffect, useMemo, useRef, useState } from 'react';
import {
  Alert,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from 'react-native';
import type { NativeStackScreenProps } from '@react-navigation/native-stack';
import type { RootStackParamList } from '../../App';
import PrimaryButton from '../components/PrimaryButton';
import Card from '../components/Card';
import { useLanguage } from '../i18n/LanguageContext';
import { colors, radius, spacing, typography } from '../theme';
import { api, type InteractionEvent, type Question } from '../api/client';

type Props = NativeStackScreenProps<RootStackParamList, 'MathActivity'>;

const TOTAL_QUESTIONS = 10;

const TOPIC_EMOJI: Record<string, string> = {
  'Counting': '🔢',
  'Number Recognition': '🔍',
  'Number Comparison': '⚖️',
  'Addition': '➕',
  'Subtraction': '➖',
  'Multiplication': '✖️',
  'Division': '➗',
};

const DIFFICULTY_DOTS: Record<string, number> = {
  'Easy': 1,
  'Medium': 2,
  'Hard': 3,
};

export default function MathActivityScreen({ route, navigation }: Props) {
  const { t } = useLanguage();
  const { studentId } = route.params;
  const sessionId = useMemo(
    () => `ses_${Date.now()}_${Math.floor(Math.random() * 10000)}`,
    [],
  );

  const [questions, setQuestions] = useState<Question[]>([]);
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

  const questionStartRef = useRef<number>(Date.now());
  const sessionStartRef = useRef<number>(Date.now());
  const lastActionRef = useRef<number>(Date.now());

  // Load questions from backend (falls back to seed data)
  useEffect(() => {
    (async () => {
      try {
        const q = await api.getQuestions();
        // Shuffle and pick TOTAL_QUESTIONS
        const shuffled = q.sort(() => Math.random() - 0.5).slice(0, TOTAL_QUESTIONS);
        setQuestions(shuffled);
      } catch {
        // Fallback: generate simple questions locally
        setQuestions(generateFallbackQuestions(TOTAL_QUESTIONS));
      }
      setLoadingQuestions(false);
    })();
  }, []);

  const current = questions[index];

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
  }, [index]);

  function trackAction() {
    lastActionRef.current = Date.now();
    setClickCount((c) => c + 1);
  }

  function handleSelect(option: string) {
    if (feedback) return;
    trackAction();
    setSelected(option);
  }

  function handleHint() {
    if (showHint) return;
    trackAction();
    setShowHint(true);
    setHintUsed(true);
  }

  function classifyError(isCorrect: boolean, given: string, expected: string, q: Question): InteractionEvent['error_type'] {
    if (isCorrect) return 'none';
    const givenNum = parseFloat(given);
    const expectedNum = parseFloat(expected);
    if (!isNaN(givenNum) && !isNaN(expectedNum)) {
      const diff = Math.abs(givenNum - expectedNum);
      if (diff <= 2) return 'careless';
      if (q.topic === 'Number Comparison') return 'conceptual';
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
      setTimeout(() => {
        setFeedback(null);
        setSelected(null);
      }, 1200);
      return;
    }

    setFeedback(isCorrect ? 'correct' : 'wrong');

    const now = Date.now();
    const responseTimeSec = (now - questionStartRef.current) / 1000;
    const sessionTimeSec = (now - sessionStartRef.current) / 1000;
    const timeBetweenActions = clickCount > 1
      ? (now - questionStartRef.current) / (clickCount * 1000)
      : responseTimeSec;

    const errorType = classifyError(isCorrect, selected, current.correct_answer, current);

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

    if (index + 1 < questions.length) {
      setTimeout(() => setIndex(index + 1), 800);
      return;
    }

    // Last question — send data and navigate to profile
    setSubmitting(true);
    try {
      await api.logInteractions(nextEvents).catch(() => undefined);
      await api.generateProfile({
        student_id: studentId,
        session_id: sessionId,
        events: nextEvents,
      });
      navigation.replace('ProfileResult', { studentId, sessionId });
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
        <Text style={{ fontSize: 48 }}>📚</Text>
        <Text style={styles.loadingText}>{t.activity.loadingQuestions}</Text>
      </View>
    );
  }

  if (!current) return null;

  const progress = (index + 1) / questions.length;
  const options = current.options ?? [current.correct_answer];

  return (
    <View style={styles.container}>
      {/* Timer display */}
      <TimerDisplay startTime={sessionStartRef.current} />

      {/* Progress */}
      <View style={styles.progressWrap}>
        <View style={styles.progressBar}>
          <View style={[styles.progressFill, { width: `${progress * 100}%` }]} />
        </View>
        <Text style={styles.progressLabel}>
          {index + 1} / {questions.length}
        </Text>
      </View>

      {/* Feedback Banner */}
      {feedback && (
        <View
          style={[
            styles.feedbackBanner,
            { backgroundColor: feedback === 'correct' ? colors.successBg : colors.dangerBg },
          ]}
        >
          <Text style={styles.feedbackText}>
            {feedback === 'correct' ? t.activity.greatJob : t.activity.tryAgain}
          </Text>
        </View>
      )}

      {/* Question Card */}
      <Card style={styles.questionCard}>
        <View style={styles.qTypeRow}>
          <Text style={styles.qTypeEmoji}>{TOPIC_EMOJI[current.topic] ?? '🤔'}</Text>
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

        <Text style={styles.prompt}>{current.question_text}</Text>

        <View style={styles.options}>
          {options.map((opt, optIdx) => {
            const isSelected = selected === opt;
            const optionColors = [colors.primary, colors.purple, colors.teal, colors.orange];
            const bgColor = optionColors[optIdx % optionColors.length];
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
                <Text
                  style={[
                    styles.optionText,
                    isSelected && styles.optionTextSelected,
                  ]}
                >
                  {opt}
                </Text>
              </TouchableOpacity>
            );
          })}
        </View>

        {showHint && (
          <View style={styles.hintBox}>
            <Text style={styles.hintText}>💡 {hintFor(current)}</Text>
          </View>
        )}
      </Card>

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
          title={index + 1 === questions.length ? `${t.common.finish} 🎉` : t.common.submit}
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

function hintFor(q: Question): string {
  const t = q.topic.toLowerCase();
  if (t.includes('addition')) return 'Try counting up from the bigger number.';
  if (t.includes('subtraction')) return 'Think: what do I add to the small number to get the big one?';
  if (t.includes('multiplication')) return 'Break it into smaller groups you already know.';
  if (t.includes('comparison')) return 'Compare the first digits first.';
  if (t.includes('counting')) return 'Count carefully, one by one.';
  if (t.includes('recognition')) return 'Look at the shape of each number carefully.';
  return 'Take a breath and read the question again.';
}

function generateFallbackQuestions(count: number): Question[] {
  const questions: Question[] = [];
  for (let i = 0; i < count; i++) {
    const a = Math.floor(Math.random() * 15) + 1;
    const b = Math.floor(Math.random() * 15) + 1;
    const answer = a + b;
    const opts = new Set<string>([String(answer)]);
    while (opts.size < 4) {
      opts.add(String(answer + Math.floor(Math.random() * 7) - 3));
    }
    questions.push({
      id: `fallback_${i}`,
      topic: 'Addition',
      difficulty: answer > 20 ? 'Medium' : 'Easy',
      question_text: `${a} + ${b} = ?`,
      correct_answer: String(answer),
      options: Array.from(opts).sort(() => Math.random() - 0.5),
    });
  }
  return questions;
}

const styles = StyleSheet.create({
  container: { flex: 1, padding: spacing.lg, gap: spacing.sm },
  center: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    gap: spacing.md,
  },
  loadingText: {
    ...typography.subtitle,
    color: colors.textMuted,
  },
  progressWrap: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.md,
  },
  progressBar: {
    flex: 1,
    height: 12,
    backgroundColor: colors.skyBlueSoft,
    borderRadius: radius.pill,
    overflow: 'hidden',
  },
  progressFill: {
    height: '100%',
    backgroundColor: colors.primary,
    borderRadius: radius.pill,
  },
  progressLabel: {
    ...typography.subtitle,
    color: colors.textWarm,
  },
  feedbackBanner: {
    paddingVertical: spacing.sm,
    paddingHorizontal: spacing.md,
    borderRadius: radius.md,
    alignItems: 'center',
  },
  feedbackText: {
    ...typography.subtitle,
    color: colors.text,
  },
  questionCard: { gap: spacing.md, flex: 1 },
  qTypeRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.sm,
  },
  qTypeEmoji: { fontSize: 20 },
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
    fontSize: 32,
    fontWeight: '800',
    color: colors.textWarm,
    textAlign: 'center',
    paddingVertical: spacing.md,
  },
  options: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: spacing.md,
    justifyContent: 'center',
  },
  option: {
    minWidth: '44%',
    paddingVertical: spacing.lg,
    borderRadius: radius.xl,
    backgroundColor: colors.skyBlueSoft,
    borderWidth: 2.5,
    borderColor: colors.border,
    alignItems: 'center',
  },
  optionSelected: {
    borderWidth: 2.5,
  },
  optionText: {
    fontSize: 24,
    fontWeight: '800',
    color: colors.textWarm,
  },
  optionTextSelected: { color: colors.textInverse },
  hintBox: {
    backgroundColor: colors.warningBg,
    padding: spacing.md,
    borderRadius: radius.md,
    borderWidth: 1,
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
