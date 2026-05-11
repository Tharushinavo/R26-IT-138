import React, { useCallback, useEffect, useState } from 'react';
import {
  ActivityIndicator,
  Alert,
  RefreshControl,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from 'react-native';
import type { NativeStackScreenProps } from '@react-navigation/native-stack';
import type { RootStackParamList } from '../../App';
import Card from '../components/Card';
import PrimaryButton from '../components/PrimaryButton';
import { api, type Question, type QuestionInput } from '../api/client';
import { colors as lightColors, radius, spacing, typography, useAppTheme } from '../theme';

type Props = NativeStackScreenProps<RootStackParamList, 'CognitiveQuestions'>;
type Difficulty = QuestionInput['difficulty'];

const DIFFICULTIES: Difficulty[] = ['Easy', 'Medium', 'Hard'];

const emptyForm = {
  question_code: '',
  topic: 'Addition',
  difficulty: 'Easy' as Difficulty,
  question_text: '',
  correct_answer: '',
  optionsText: '',
};

export default function CognitiveQuestionsScreen({ route, navigation }: Props) {
  const { teacherId } = route.params;
  const { colors } = useAppTheme();
  const styles = createStyles(colors);
  const [questions, setQuestions] = useState<Question[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [form, setForm] = useState(emptyForm);

  const load = useCallback(async (showSpinner = true) => {
    if (showSpinner) setLoading(true);
    try {
      const data = await api.getQuestions(undefined, undefined, 100);
      setQuestions(data);
    } catch {
      setQuestions([]);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  function resetForm() {
    setEditingId(null);
    setForm(emptyForm);
  }

  function editQuestion(question: Question) {
    setEditingId(question.id);
    setForm({
      question_code: question.question_code || '',
      topic: question.topic,
      difficulty: question.difficulty,
      question_text: question.question_text,
      correct_answer: question.correct_answer,
      optionsText: question.options?.join(', ') || '',
    });
  }

  function payloadFromForm(): QuestionInput {
    const options = form.optionsText
      .split(',')
      .map(option => option.trim())
      .filter(Boolean);
    if (form.correct_answer.trim() && !options.includes(form.correct_answer.trim())) {
      options.push(form.correct_answer.trim());
    }
    return {
      question_code: form.question_code.trim() || undefined,
      topic: form.topic.trim(),
      difficulty: form.difficulty,
      question_text: form.question_text.trim(),
      correct_answer: form.correct_answer.trim(),
      options: options.length ? options.slice(0, 4) : undefined,
    };
  }

  async function saveQuestion() {
    const payload = payloadFromForm();
    if (!payload.topic || !payload.question_text || !payload.correct_answer) {
      Alert.alert('Missing details', 'Topic, question text, and correct answer are required.');
      return;
    }
    setSaving(true);
    try {
      if (editingId) {
        const updated = await api.updateQuestion(editingId, payload);
        setQuestions(prev => prev.map(q => (q.id === editingId ? updated : q)));
      } else {
        const created = await api.createQuestion(payload);
        setQuestions(prev => [created, ...prev]);
      }
      resetForm();
    } catch (e: any) {
      Alert.alert('Could not save question', e?.message || 'Please check Supabase and try again.');
    } finally {
      setSaving(false);
    }
  }

  function confirmDelete(question: Question) {
    Alert.alert(
      'Delete question',
      'This removes the question from Supabase.',
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Delete',
          style: 'destructive',
          onPress: async () => {
            try {
              await api.deleteQuestion(question.id);
              setQuestions(prev => prev.filter(q => q.id !== question.id));
              if (editingId === question.id) resetForm();
            } catch (e: any) {
              Alert.alert('Could not delete question', e?.message || 'Please try again.');
            }
          },
        },
      ],
    );
  }



  if (loading) {
    return (
      <View style={[styles.center, { backgroundColor: colors.background }]}>
        <ActivityIndicator size="large" color={colors.primary} />
        <Text style={styles.loadingText}>Loading cognitive questions...</Text>
      </View>
    );
  }

  return (
    <View style={{ flex: 1, backgroundColor: colors.background }}>
    <ScrollView
      contentContainerStyle={styles.container}
      refreshControl={<RefreshControl refreshing={refreshing} onRefresh={() => { setRefreshing(true); load(false); }} />}
    >
      <View style={styles.header}>
        <Text style={styles.kicker}>Teacher {teacherId.slice(0, 8)}</Text>
        <Text style={styles.title}>Cognitive Questions</Text>
        <Text style={styles.subtitle}>Create, edit, delete, and AI-generate the question bank used by students.</Text>
      </View>

      <Card style={styles.formCard}>
        <View style={styles.formHeader}>
          <Text style={styles.sectionTitle}>{editingId ? 'Edit question' : 'Create question'}</Text>
          {editingId && (
            <TouchableOpacity onPress={resetForm} activeOpacity={0.75}>
              <Text style={styles.linkText}>New</Text>
            </TouchableOpacity>
          )}
        </View>

        <Field label="Question code">
          <TextInput
            value={form.question_code}
            onChangeText={value => setForm(prev => ({ ...prev, question_code: value }))}
            placeholder="Optional, e.g. ADD-021"
            placeholderTextColor={colors.textMuted}
            style={styles.input}
          />
        </Field>
        <Field label="Topic">
          <TextInput
            value={form.topic}
            onChangeText={value => setForm(prev => ({ ...prev, topic: value }))}
            placeholder="Addition"
            placeholderTextColor={colors.textMuted}
            style={styles.input}
          />
        </Field>
        <Text style={styles.label}>Difficulty</Text>
        <View style={styles.segmentRow}>
          {DIFFICULTIES.map(item => (
            <SegmentButton
              key={item}
              label={item}
              active={form.difficulty === item}
              onPress={() => setForm(prev => ({ ...prev, difficulty: item }))}
            />
          ))}
        </View>
        <Field label="Question text">
          <TextInput
            value={form.question_text}
            onChangeText={value => setForm(prev => ({ ...prev, question_text: value }))}
            placeholder="2 + 3 = ?"
            placeholderTextColor={colors.textMuted}
            style={[styles.input, styles.multiline]}
            multiline
          />
        </Field>
        <Field label="Correct answer">
          <TextInput
            value={form.correct_answer}
            onChangeText={value => setForm(prev => ({ ...prev, correct_answer: value }))}
            placeholder="5"
            placeholderTextColor={colors.textMuted}
            style={styles.input}
          />
        </Field>
        <Field label="Options">
          <TextInput
            value={form.optionsText}
            onChangeText={value => setForm(prev => ({ ...prev, optionsText: value }))}
            placeholder="4, 5, 6, 7"
            placeholderTextColor={colors.textMuted}
            style={styles.input}
          />
        </Field>
        <PrimaryButton
          title={editingId ? 'Save Changes' : 'Create Question'}
          onPress={saveQuestion}
          loading={saving}
        />
      </Card>

      {/* AI Generate — navigates to dedicated screen */}
      <Card style={[styles.formCard, { alignItems: 'center', gap: spacing.md }]}>
        <Text style={{ fontSize: 36 }}>✨</Text>
        <Text style={styles.sectionTitle}>Generate with AI</Text>
        <Text style={[styles.helperText, { textAlign: 'center' }]}>
          Let AI create questions for you. Choose a type, difficulty, and the AI does the rest!
        </Text>
        <PrimaryButton
          title="✨ Generate Questions"
          onPress={() => navigation.navigate('AIGenerate', { teacherId })}
          variant="coral"
        />
      </Card>

      <View style={styles.listHeader}>
        <Text style={styles.sectionTitle}>Question bank</Text>
        <Text style={styles.countText}>{questions.length} questions</Text>
      </View>

      {questions.map(question => (
        <Card key={question.id} style={styles.questionCard}>
          <View style={styles.questionHeader}>
            <View style={styles.questionTitleBlock}>
              <Text style={styles.questionTopic}>{question.topic}</Text>
              <Text style={styles.questionCode}>{question.question_code || question.id.slice(0, 10)}</Text>
            </View>
            <View style={styles.difficultyBadge}>
              <Text style={styles.difficultyText}>{question.difficulty}</Text>
            </View>
          </View>
          <Text style={styles.questionText}>{question.question_text}</Text>
          <Text style={styles.answerText}>Answer: {question.correct_answer}</Text>
          {!!question.options?.length && (
            <View style={styles.optionRow}>
              {question.options.map(option => (
                <View key={option} style={styles.optionChip}>
                  <Text style={styles.optionChipText}>{option}</Text>
                </View>
              ))}
            </View>
          )}
          <View style={styles.cardActions}>
            <TouchableOpacity style={styles.editButton} onPress={() => editQuestion(question)} activeOpacity={0.75}>
              <Text style={styles.editText}>Edit</Text>
            </TouchableOpacity>
            <TouchableOpacity style={styles.deleteButton} onPress={() => confirmDelete(question)} activeOpacity={0.75}>
              <Text style={styles.deleteText}>Delete</Text>
            </TouchableOpacity>
          </View>
        </Card>
      ))}
    </ScrollView>
    </View>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  const { colors } = useAppTheme();
  const styles = createStyles(colors);
  return (
    <View style={styles.field}>
      <Text style={styles.label}>{label}</Text>
      {children}
    </View>
  );
}

function SegmentButton({ label, active, onPress }: { label: string; active: boolean; onPress: () => void }) {
  const { colors } = useAppTheme();
  const styles = createStyles(colors);
  return (
    <TouchableOpacity
      style={[styles.segmentButton, active && styles.segmentButtonActive]}
      onPress={onPress}
      activeOpacity={0.75}
    >
      <Text style={[styles.segmentText, active && styles.segmentTextActive]}>{label}</Text>
    </TouchableOpacity>
  );
}

const createStyles = (colors: typeof lightColors) => StyleSheet.create({
  center: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    padding: spacing.xl,
    gap: spacing.md,
  },
  loadingText: {
    ...typography.subtitle,
    color: colors.textMuted,
  },
  container: {
    padding: spacing.lg,
    paddingTop: spacing.md,
    paddingBottom: spacing.xxl,
    gap: spacing.md,
  },
  header: {
    gap: spacing.xs,
  },
  kicker: {
    ...typography.caption,
    color: colors.primaryDark,
    textTransform: 'uppercase',
  },
  title: {
    ...typography.title,
    color: colors.textWarm,
  },
  subtitle: {
    ...typography.body,
    color: colors.textMuted,
  },
  formCard: {
    gap: spacing.sm,
  },
  formHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  sectionTitle: {
    ...typography.subtitle,
    color: colors.textWarm,
  },
  helperText: {
    ...typography.caption,
    color: colors.textMuted,
    lineHeight: 18,
  },
  field: {
    gap: spacing.xs,
  },
  label: {
    ...typography.caption,
    color: colors.textWarm,
  },
  input: {
    backgroundColor: colors.surfaceSoft,
    borderRadius: radius.md,
    borderWidth: 1,
    borderColor: colors.border,
    color: colors.text,
    fontSize: 15,
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm,
  },
  multiline: {
    minHeight: 78,
    textAlignVertical: 'top',
  },
  segmentRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: spacing.sm,
  },
  segmentButton: {
    paddingVertical: spacing.sm,
    paddingHorizontal: spacing.md,
    borderRadius: radius.pill,
    backgroundColor: colors.surface,
    borderWidth: 1.5,
    borderColor: colors.border,
  },
  segmentButtonActive: {
    backgroundColor: colors.primary,
    borderColor: colors.primary,
  },
  segmentText: {
    ...typography.caption,
    color: colors.textWarm,
    textTransform: 'capitalize',
  },
  segmentTextActive: {
    color: colors.textInverse,
  },
  listHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  countText: {
    ...typography.caption,
    color: colors.textMuted,
  },
  questionCard: {
    gap: spacing.sm,
  },
  questionHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: spacing.md,
  },
  questionTitleBlock: {
    flex: 1,
  },
  questionTopic: {
    ...typography.subtitle,
    color: colors.textWarm,
  },
  questionCode: {
    ...typography.small,
    color: colors.textMuted,
    marginTop: 2,
  },
  difficultyBadge: {
    borderRadius: radius.pill,
    backgroundColor: colors.skyBlueSoft,
    paddingHorizontal: spacing.sm,
    paddingVertical: 5,
  },
  difficultyText: {
    ...typography.small,
    color: colors.primaryDark,
  },
  questionText: {
    ...typography.body,
    color: colors.text,
    lineHeight: 22,
  },
  answerText: {
    ...typography.caption,
    color: colors.success,
  },
  optionRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: spacing.sm,
  },
  optionChip: {
    backgroundColor: colors.surfaceSoft,
    borderRadius: radius.pill,
    paddingHorizontal: spacing.sm,
    paddingVertical: 5,
    borderWidth: 1,
    borderColor: colors.border,
  },
  optionChipText: {
    ...typography.small,
    color: colors.textWarm,
  },
  cardActions: {
    flexDirection: 'row',
    gap: spacing.sm,
  },
  editButton: {
    flex: 1,
    alignItems: 'center',
    paddingVertical: spacing.sm,
    borderRadius: radius.pill,
    backgroundColor: colors.primary,
  },
  editText: {
    ...typography.caption,
    color: colors.textInverse,
  },
  deleteButton: {
    flex: 1,
    alignItems: 'center',
    paddingVertical: spacing.sm,
    borderRadius: radius.pill,
    backgroundColor: colors.surface,
    borderWidth: 1.5,
    borderColor: colors.coral,
  },
  deleteText: {
    ...typography.caption,
    color: colors.coral,
  },
  linkText: {
    ...typography.caption,
    color: colors.primaryDark,
  },
});
