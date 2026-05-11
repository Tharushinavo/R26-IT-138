import React, { useState } from 'react';
import {
  Alert,
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
import { api, type QuestionInput } from '../api/client';
import { radius, spacing, typography, useAppTheme } from '../theme';

type Props = NativeStackScreenProps<RootStackParamList, 'ManualCreateQuestion'>;
type Difficulty = QuestionInput['difficulty'];

const DIFFICULTIES: Difficulty[] = ['Easy', 'Medium', 'Hard'];
const QUESTION_TYPES = [
  'Addition',
  'Subtraction',
  'Counting',
  'Number Recognition',
  'Number Comparison',
];

export default function ManualCreateScreen({ navigation }: Props) {
  const { colors } = useAppTheme();
  const styles = createStyles(colors);

  const [topic, setTopic] = useState('Addition');
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const [difficulty, setDifficulty] = useState<Difficulty>('Easy');
  const [questionCode, setQuestionCode] = useState('');
  const [questionText, setQuestionText] = useState('');
  const [correctAnswer, setCorrectAnswer] = useState('');
  const [optionsText, setOptionsText] = useState('');
  const [saving, setSaving] = useState(false);

  async function handleCreate() {
    if (!questionText.trim() || !correctAnswer.trim()) {
      Alert.alert('Missing details', 'Question text and correct answer are required.');
      return;
    }

    const options = optionsText
      .split(',')
      .map(o => o.trim())
      .filter(Boolean);
    if (correctAnswer.trim() && !options.includes(correctAnswer.trim())) {
      options.push(correctAnswer.trim());
    }

    const payload: QuestionInput = {
      question_code: questionCode.trim() || undefined,
      topic: topic.trim(),
      difficulty,
      question_text: questionText.trim(),
      correct_answer: correctAnswer.trim(),
      options: options.length ? options.slice(0, 4) : undefined,
    };

    setSaving(true);
    try {
      await api.createQuestion(payload);
      Alert.alert('✅ Created', 'Question has been added to the question bank.', [
        { text: 'Create Another', onPress: resetForm },
        { text: 'Back to Questions', onPress: () => navigation.goBack() },
      ]);
    } catch (e: any) {
      Alert.alert('Could not save', e?.message || 'Please check Supabase and try again.');
    } finally {
      setSaving(false);
    }
  }

  function resetForm() {
    setQuestionCode('');
    setQuestionText('');
    setCorrectAnswer('');
    setOptionsText('');
  }

  return (
    <View style={{ flex: 1, backgroundColor: colors.background }}>
      <ScrollView contentContainerStyle={styles.container} keyboardShouldPersistTaps="handled">
        {/* Header */}
        <View style={styles.header}>
          <Text style={{ fontSize: 42, textAlign: 'center' }}>✏️</Text>
          <Text style={styles.title}>Create Question</Text>
          <Text style={styles.subtitle}>
            Manually create a new math question for the student question bank.
          </Text>
        </View>

        <Card style={styles.formCard}>
          {/* Question Type Dropdown */}
          <Text style={styles.label}>Question Type</Text>
          <TouchableOpacity
            style={styles.dropdown}
            onPress={() => setDropdownOpen(!dropdownOpen)}
            activeOpacity={0.8}
          >
            <Text style={styles.dropdownText}>{topic}</Text>
            <Text style={styles.dropdownArrow}>{dropdownOpen ? '▲' : '▼'}</Text>
          </TouchableOpacity>
          {dropdownOpen && (
            <View style={styles.dropdownList}>
              {QUESTION_TYPES.map(t => (
                <TouchableOpacity
                  key={t}
                  style={[styles.dropdownItem, t === topic && styles.dropdownItemActive]}
                  onPress={() => { setTopic(t); setDropdownOpen(false); }}
                  activeOpacity={0.75}
                >
                  <Text style={[styles.dropdownItemText, t === topic && styles.dropdownItemTextActive]}>
                    {t}
                  </Text>
                </TouchableOpacity>
              ))}
            </View>
          )}

          {/* Difficulty */}
          <Text style={[styles.label, { marginTop: spacing.md }]}>Difficulty</Text>
          <View style={styles.chipRow}>
            {DIFFICULTIES.map(d => (
              <TouchableOpacity
                key={d}
                style={[styles.chip, difficulty === d && styles.chipActive]}
                onPress={() => setDifficulty(d)}
                activeOpacity={0.75}
              >
                <Text style={[styles.chipText, difficulty === d && styles.chipTextActive]}>
                  {d}
                </Text>
              </TouchableOpacity>
            ))}
          </View>

          {/* Question Code */}
          <Text style={[styles.label, { marginTop: spacing.md }]}>Question Code</Text>
          <TextInput
            value={questionCode}
            onChangeText={setQuestionCode}
            placeholder="Optional, e.g. ADD-021"
            placeholderTextColor={colors.textMuted}
            style={styles.input}
          />

          {/* Question Text */}
          <Text style={[styles.label, { marginTop: spacing.md }]}>Question Text</Text>
          <TextInput
            value={questionText}
            onChangeText={setQuestionText}
            placeholder="e.g. 2 + 3 = ?"
            placeholderTextColor={colors.textMuted}
            style={[styles.input, styles.multiline]}
            multiline
          />

          {/* Correct Answer */}
          <Text style={[styles.label, { marginTop: spacing.md }]}>Correct Answer</Text>
          <TextInput
            value={correctAnswer}
            onChangeText={setCorrectAnswer}
            placeholder="e.g. 5"
            placeholderTextColor={colors.textMuted}
            style={styles.input}
          />

          {/* Options */}
          <Text style={[styles.label, { marginTop: spacing.md }]}>Answer Options</Text>
          <TextInput
            value={optionsText}
            onChangeText={setOptionsText}
            placeholder="Separate with commas, e.g. 4, 5, 6, 7"
            placeholderTextColor={colors.textMuted}
            style={styles.input}
          />
          <Text style={styles.helperText}>
            The correct answer is automatically included if not listed.
          </Text>

          {/* Submit */}
          <PrimaryButton
            title="Create Question"
            onPress={handleCreate}
            loading={saving}
            style={{ marginTop: spacing.md }}
          />
        </Card>
      </ScrollView>
    </View>
  );
}

const createStyles = (colors: ReturnType<typeof useAppTheme>['colors']) =>
  StyleSheet.create({
    container: {
      padding: spacing.lg,
      paddingTop: spacing.md,
      paddingBottom: spacing.xxl + 20,
      gap: spacing.md,
    },
    header: {
      alignItems: 'center',
      gap: spacing.xs,
      marginBottom: spacing.sm,
    },
    title: {
      ...typography.title,
      color: colors.textWarm,
      textAlign: 'center',
    },
    subtitle: {
      ...typography.body,
      color: colors.textMuted,
      textAlign: 'center',
      maxWidth: 320,
      lineHeight: 22,
    },
    formCard: { gap: spacing.sm },
    label: {
      ...typography.caption,
      color: colors.textWarm,
      marginBottom: 2,
    },
    helperText: {
      ...typography.small,
      color: colors.textMuted,
      marginTop: 2,
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
      minHeight: 80,
      textAlignVertical: 'top',
    },
    dropdown: {
      flexDirection: 'row',
      alignItems: 'center',
      justifyContent: 'space-between',
      backgroundColor: colors.surfaceSoft,
      borderRadius: radius.md,
      borderWidth: 1,
      borderColor: colors.border,
      paddingHorizontal: spacing.md,
      paddingVertical: 14,
    },
    dropdownText: {
      ...typography.body,
      color: colors.text,
    },
    dropdownArrow: {
      fontSize: 12,
      color: colors.textMuted,
    },
    dropdownList: {
      backgroundColor: colors.surface,
      borderRadius: radius.md,
      borderWidth: 1,
      borderColor: colors.border,
      overflow: 'hidden',
    },
    dropdownItem: {
      paddingHorizontal: spacing.md,
      paddingVertical: 12,
      borderBottomWidth: 1,
      borderBottomColor: colors.borderLight,
    },
    dropdownItemActive: {
      backgroundColor: colors.skyBlueSoft,
    },
    dropdownItemText: {
      ...typography.body,
      color: colors.text,
    },
    dropdownItemTextActive: {
      color: colors.primaryDark,
      fontWeight: '700',
    },
    chipRow: {
      flexDirection: 'row',
      gap: spacing.sm,
    },
    chip: {
      paddingVertical: spacing.sm,
      paddingHorizontal: spacing.lg,
      borderRadius: radius.pill,
      backgroundColor: colors.surface,
      borderWidth: 1.5,
      borderColor: colors.border,
    },
    chipActive: {
      backgroundColor: colors.primary,
      borderColor: colors.primary,
    },
    chipText: {
      ...typography.caption,
      color: colors.textWarm,
    },
    chipTextActive: {
      color: colors.textInverse,
    },
  });
