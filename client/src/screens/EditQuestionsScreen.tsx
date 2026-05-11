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

type Props = NativeStackScreenProps<RootStackParamList, 'EditQuestions'>;
type Difficulty = QuestionInput['difficulty'];

const DIFFICULTIES: Difficulty[] = ['Easy', 'Medium', 'Hard'];

export default function EditQuestionsScreen({ navigation }: Props) {
  const { colors } = useAppTheme();
  const styles = createStyles(colors);

  const [questions, setQuestions] = useState<Question[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  // Inline editing
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editForm, setEditForm] = useState({
    question_text: '',
    correct_answer: '',
    optionsText: '',
    difficulty: 'Easy' as Difficulty,
  });
  const [saving, setSaving] = useState(false);

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

  function startEdit(q: Question) {
    setEditingId(q.id);
    setEditForm({
      question_text: q.question_text,
      correct_answer: q.correct_answer,
      optionsText: q.options?.join(', ') || '',
      difficulty: q.difficulty,
    });
  }

  function cancelEdit() {
    setEditingId(null);
  }

  async function saveEdit(questionId: string) {
    const options = editForm.optionsText
      .split(',')
      .map(o => o.trim())
      .filter(Boolean);
    if (editForm.correct_answer.trim() && !options.includes(editForm.correct_answer.trim())) {
      options.push(editForm.correct_answer.trim());
    }

    const patch: Partial<QuestionInput> = {
      question_text: editForm.question_text.trim(),
      correct_answer: editForm.correct_answer.trim(),
      difficulty: editForm.difficulty,
      options: options.length ? options.slice(0, 4) : undefined,
    };

    setSaving(true);
    try {
      const updated = await api.updateQuestion(questionId, patch);
      setQuestions(prev => prev.map(q => (q.id === questionId ? updated : q)));
      setEditingId(null);
    } catch (e: any) {
      Alert.alert('Could not save', e?.message || 'Please try again.');
    } finally {
      setSaving(false);
    }
  }

  function confirmDelete(question: Question) {
    Alert.alert(
      'Delete question',
      `Are you sure you want to delete "${question.question_text.slice(0, 40)}…"?`,
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Delete',
          style: 'destructive',
          onPress: async () => {
            try {
              await api.deleteQuestion(question.id);
              setQuestions(prev => prev.filter(q => q.id !== question.id));
              if (editingId === question.id) setEditingId(null);
            } catch (e: any) {
              Alert.alert('Could not delete', e?.message || 'Please try again.');
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
        <Text style={styles.loadingText}>Loading questions…</Text>
      </View>
    );
  }

  return (
    <View style={{ flex: 1, backgroundColor: colors.background }}>
      <ScrollView
        contentContainerStyle={styles.container}
        refreshControl={
          <RefreshControl refreshing={refreshing} onRefresh={() => { setRefreshing(true); load(false); }} />
        }
      >
        {/* Header */}
        <View style={styles.header}>
          <Text style={{ fontSize: 42, textAlign: 'center' }}>📝</Text>
          <Text style={styles.title}>Edit Questions</Text>
          <Text style={styles.subtitle}>
            Browse, edit, and delete questions in the question bank.
          </Text>
          <View style={styles.countBadge}>
            <Text style={styles.countText}>{questions.length} questions</Text>
          </View>
        </View>

        {questions.length === 0 && (
          <Card style={{ alignItems: 'center', gap: spacing.md, paddingVertical: spacing.xl }}>
            <Text style={{ fontSize: 48 }}>📭</Text>
            <Text style={styles.emptyTitle}>No questions yet</Text>
            <Text style={styles.emptySubtitle}>
              Create questions manually or generate with AI first.
            </Text>
            <PrimaryButton
              title="← Back"
              onPress={() => navigation.goBack()}
              variant="ghost"
            />
          </Card>
        )}

        {questions.map(question => {
          const isEditing = editingId === question.id;
          return (
            <Card key={question.id} style={styles.questionCard}>
              {/* Header */}
              <View style={styles.questionHeader}>
                <View style={styles.questionTitleBlock}>
                  <Text style={styles.questionTopic}>{question.topic}</Text>
                  <Text style={styles.questionCode}>
                    {question.question_code || question.id.slice(0, 10)}
                  </Text>
                </View>
                <View style={styles.difficultyBadge}>
                  <Text style={styles.difficultyText}>{question.difficulty}</Text>
                </View>
              </View>

              {isEditing ? (
                /* ── Inline Edit Mode ── */
                <View style={{ gap: spacing.sm }}>
                  <Text style={styles.label}>Question</Text>
                  <TextInput
                    value={editForm.question_text}
                    onChangeText={v => setEditForm(prev => ({ ...prev, question_text: v }))}
                    style={[styles.input, styles.multiline]}
                    multiline
                  />
                  <Text style={styles.label}>Correct Answer</Text>
                  <TextInput
                    value={editForm.correct_answer}
                    onChangeText={v => setEditForm(prev => ({ ...prev, correct_answer: v }))}
                    style={styles.input}
                  />
                  <Text style={styles.label}>Options (comma-separated)</Text>
                  <TextInput
                    value={editForm.optionsText}
                    onChangeText={v => setEditForm(prev => ({ ...prev, optionsText: v }))}
                    style={styles.input}
                    placeholder="4, 5, 6, 7"
                    placeholderTextColor={colors.textMuted}
                  />
                  <Text style={styles.label}>Difficulty</Text>
                  <View style={styles.chipRow}>
                    {DIFFICULTIES.map(d => (
                      <TouchableOpacity
                        key={d}
                        style={[styles.chip, editForm.difficulty === d && styles.chipActive]}
                        onPress={() => setEditForm(prev => ({ ...prev, difficulty: d }))}
                        activeOpacity={0.75}
                      >
                        <Text style={[styles.chipText, editForm.difficulty === d && styles.chipTextActive]}>
                          {d}
                        </Text>
                      </TouchableOpacity>
                    ))}
                  </View>
                  <View style={styles.cardActions}>
                    <TouchableOpacity style={styles.cancelButton} onPress={cancelEdit} activeOpacity={0.75}>
                      <Text style={styles.cancelText}>Cancel</Text>
                    </TouchableOpacity>
                    <TouchableOpacity
                      style={[styles.saveButton, saving && { opacity: 0.5 }]}
                      onPress={saving ? undefined : () => saveEdit(question.id)}
                      activeOpacity={0.75}
                    >
                      {saving ? (
                        <ActivityIndicator size="small" color={colors.textInverse} />
                      ) : (
                        <Text style={styles.saveText}>Save Changes</Text>
                      )}
                    </TouchableOpacity>
                  </View>
                </View>
              ) : (
                /* ── View Mode ── */
                <>
                  <Text style={styles.questionText}>{question.question_text}</Text>
                  <Text style={styles.answerText}>Answer: {question.correct_answer}</Text>
                  {!!question.options?.length && (
                    <View style={styles.optionRow}>
                      {question.options.map(opt => (
                        <View
                          key={opt}
                          style={[
                            styles.optionChip,
                            opt === question.correct_answer && styles.optionChipCorrect,
                          ]}
                        >
                          <Text
                            style={[
                              styles.optionChipText,
                              opt === question.correct_answer && styles.optionChipTextCorrect,
                            ]}
                          >
                            {opt}
                          </Text>
                        </View>
                      ))}
                    </View>
                  )}
                  <View style={styles.cardActions}>
                    <TouchableOpacity style={styles.editButton} onPress={() => startEdit(question)} activeOpacity={0.75}>
                      <Text style={styles.editText}>✏️ Edit</Text>
                    </TouchableOpacity>
                    <TouchableOpacity style={styles.deleteButton} onPress={() => confirmDelete(question)} activeOpacity={0.75}>
                      <Text style={styles.deleteText}>🗑️ Delete</Text>
                    </TouchableOpacity>
                  </View>
                </>
              )}
            </Card>
          );
        })}
      </ScrollView>
    </View>
  );
}

const createStyles = (colors: typeof lightColors) => StyleSheet.create({
  center: {
    flex: 1, alignItems: 'center', justifyContent: 'center',
    padding: spacing.xl, gap: spacing.md,
  },
  loadingText: { ...typography.subtitle, color: colors.textMuted },
  container: {
    padding: spacing.lg, paddingTop: spacing.md,
    paddingBottom: spacing.xxl + 20, gap: spacing.md,
  },
  header: {
    alignItems: 'center', gap: spacing.xs, marginBottom: spacing.sm,
  },
  title: {
    ...typography.title, color: colors.textWarm, textAlign: 'center',
  },
  subtitle: {
    ...typography.body, color: colors.textMuted, textAlign: 'center',
    maxWidth: 320, lineHeight: 22,
  },
  countBadge: {
    backgroundColor: colors.skyBlueSoft,
    paddingHorizontal: spacing.lg, paddingVertical: spacing.sm,
    borderRadius: radius.pill, marginTop: spacing.xs,
  },
  countText: { ...typography.caption, color: colors.primaryDark },
  emptyTitle: { ...typography.subtitle, color: colors.textWarm },
  emptySubtitle: { ...typography.body, color: colors.textMuted, textAlign: 'center' },

  // Question cards
  questionCard: { gap: spacing.sm },
  questionHeader: {
    flexDirection: 'row', alignItems: 'center',
    justifyContent: 'space-between', gap: spacing.md,
  },
  questionTitleBlock: { flex: 1 },
  questionTopic: { ...typography.subtitle, color: colors.textWarm },
  questionCode: { ...typography.small, color: colors.textMuted, marginTop: 2 },
  difficultyBadge: {
    borderRadius: radius.pill, backgroundColor: colors.skyBlueSoft,
    paddingHorizontal: spacing.sm, paddingVertical: 5,
  },
  difficultyText: { ...typography.small, color: colors.primaryDark },
  questionText: { ...typography.body, color: colors.text, lineHeight: 22 },
  answerText: { ...typography.caption, color: colors.success },
  optionRow: { flexDirection: 'row', flexWrap: 'wrap', gap: spacing.sm },
  optionChip: {
    backgroundColor: colors.surfaceSoft, borderRadius: radius.pill,
    paddingHorizontal: spacing.sm, paddingVertical: 5,
    borderWidth: 1, borderColor: colors.border,
  },
  optionChipCorrect: {
    backgroundColor: colors.successBg, borderColor: colors.success,
  },
  optionChipText: { ...typography.small, color: colors.textWarm },
  optionChipTextCorrect: { color: colors.success, fontWeight: '800' },

  // Edit form
  label: { ...typography.caption, color: colors.textWarm, marginBottom: 2 },
  input: {
    backgroundColor: colors.surfaceSoft, borderRadius: radius.md,
    borderWidth: 1, borderColor: colors.border,
    color: colors.text, fontSize: 15,
    paddingHorizontal: spacing.md, paddingVertical: spacing.sm,
  },
  multiline: { minHeight: 80, textAlignVertical: 'top' },
  chipRow: { flexDirection: 'row', gap: spacing.sm },
  chip: {
    paddingVertical: spacing.sm, paddingHorizontal: spacing.lg,
    borderRadius: radius.pill, backgroundColor: colors.surface,
    borderWidth: 1.5, borderColor: colors.border,
  },
  chipActive: { backgroundColor: colors.primary, borderColor: colors.primary },
  chipText: { ...typography.caption, color: colors.textWarm },
  chipTextActive: { color: colors.textInverse },

  // Actions
  cardActions: { flexDirection: 'row', gap: spacing.sm },
  editButton: {
    flex: 1, alignItems: 'center', paddingVertical: spacing.sm,
    borderRadius: radius.pill, backgroundColor: colors.primary,
  },
  editText: { ...typography.caption, color: colors.textInverse },
  deleteButton: {
    flex: 1, alignItems: 'center', paddingVertical: spacing.sm,
    borderRadius: radius.pill, backgroundColor: colors.surface,
    borderWidth: 1.5, borderColor: colors.coral,
  },
  deleteText: { ...typography.caption, color: colors.coral },
  cancelButton: {
    flex: 1, alignItems: 'center', paddingVertical: spacing.sm,
    borderRadius: radius.pill, backgroundColor: colors.surface,
    borderWidth: 1.5, borderColor: colors.border,
  },
  cancelText: { ...typography.caption, color: colors.textMuted },
  saveButton: {
    flex: 1, alignItems: 'center', paddingVertical: spacing.sm,
    borderRadius: radius.pill, backgroundColor: colors.success,
  },
  saveText: { ...typography.caption, color: colors.textInverse, fontWeight: '800' },
});
