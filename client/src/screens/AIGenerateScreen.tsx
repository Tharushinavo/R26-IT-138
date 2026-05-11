import React, { useState } from 'react';
import {
  ActivityIndicator,
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
import { api, type QuestionDraft, type QuestionInput } from '../api/client';
import { radius, spacing, typography, useAppTheme } from '../theme';

type Props = NativeStackScreenProps<RootStackParamList, 'AIGenerate'>;
type Difficulty = 'Easy' | 'Medium' | 'Hard';

const DIFFICULTIES: Difficulty[] = ['Easy', 'Medium', 'Hard'];
const QUESTION_TYPES = [
  'Addition',
  'Subtraction',
  'Counting',
  'Number Recognition',
  'Number Comparison',
];

interface DraftItem extends QuestionDraft {
  _localId: string; // for React key & tracking
  _editing: boolean;
}

export default function AIGenerateScreen({ navigation }: Props) {
  const { colors } = useAppTheme();
  const styles = createStyles(colors);

  // --- Form state ---
  const [topic, setTopic] = useState('Addition');
  const [difficulty, setDifficulty] = useState<Difficulty>('Easy');
  const [count, setCount] = useState('5');
  const [instructions, setInstructions] = useState('');
  const [generating, setGenerating] = useState(false);
  const [dropdownOpen, setDropdownOpen] = useState(false);

  // --- Draft state ---
  const [drafts, setDrafts] = useState<DraftItem[]>([]);
  const [savingIds, setSavingIds] = useState<Set<string>>(new Set());
  const [savingAll, setSavingAll] = useState(false);

  // ────────────────── Generate ──────────────────
  async function handleGenerate() {
    setGenerating(true);
    try {
      const results = await api.generateQuestionsSimple({
        topic,
        difficulty,
        count: Math.max(1, Math.min(10, Number(count) || 5)),
        instructions: instructions.trim() || undefined,
      });
      const items: DraftItem[] = results.map((q, i) => ({
        ...q,
        _localId: `draft-${Date.now()}-${i}`,
        _editing: false,
      }));
      setDrafts(items);
    } catch (e: any) {
      const msg = e?.message || 'Something went wrong.';
      const title = msg.includes('rate limit') || msg.includes('busy')
        ? 'AI is busy'
        : msg.includes('API key')
          ? 'Configuration Issue'
          : 'Generation Failed';
      Alert.alert(title, msg);
    } finally {
      setGenerating(false);
    }
  }

  // ────────────────── Draft CRUD ──────────────────
  function updateDraft(id: string, patch: Partial<DraftItem>) {
    setDrafts(prev => prev.map(d => (d._localId === id ? { ...d, ...patch } : d)));
  }

  function removeDraft(id: string) {
    setDrafts(prev => prev.filter(d => d._localId !== id));
  }

  async function saveDraft(draft: DraftItem) {
    setSavingIds(prev => new Set(prev).add(draft._localId));
    const payload: QuestionInput = {
      topic: draft.topic,
      difficulty: draft.difficulty,
      question_text: draft.question_text,
      correct_answer: draft.correct_answer,
      options: draft.options?.length ? draft.options.slice(0, 4) : undefined,
      question_code: draft.question_code || undefined,
    };
    try {
      await api.createQuestion(payload);
      removeDraft(draft._localId);
      Alert.alert('✅ Saved', 'Question added to the question bank.');
    } catch (e: any) {
      Alert.alert('Could not save', e?.message || 'Please try again.');
    } finally {
      setSavingIds(prev => {
        const next = new Set(prev);
        next.delete(draft._localId);
        return next;
      });
    }
  }

  async function saveAllDrafts() {
    if (drafts.length === 0) return;
    setSavingAll(true);
    let saved = 0;
    for (const draft of [...drafts]) {
      const payload: QuestionInput = {
        topic: draft.topic,
        difficulty: draft.difficulty,
        question_text: draft.question_text,
        correct_answer: draft.correct_answer,
        options: draft.options?.length ? draft.options.slice(0, 4) : undefined,
        question_code: draft.question_code || undefined,
      };
      try {
        await api.createQuestion(payload);
        removeDraft(draft._localId);
        saved++;
      } catch {
        // continue with rest
      }
    }
    setSavingAll(false);
    Alert.alert('✅ Done', `${saved} question(s) saved to the question bank.`);
    if (saved > 0 && drafts.length === 0) {
      navigation.goBack();
    }
  }

  // ────────────────── UI ──────────────────
  const hasDrafts = drafts.length > 0;

  return (
    <View style={{ flex: 1, backgroundColor: colors.background }}>
      <ScrollView contentContainerStyle={styles.container} keyboardShouldPersistTaps="handled">
        {/* ── Header ── */}
        <View style={styles.header}>
          <Text style={{ fontSize: 42, textAlign: 'center' }}>✨</Text>
          <Text style={styles.title}>Create Questions with AI</Text>
          <Text style={styles.subtitle}>
            Choose a question type and difficulty, and the AI will generate questions for your students.
          </Text>
        </View>

        {/* ── Form Card ── */}
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
                  <Text
                    style={[styles.dropdownItemText, t === topic && styles.dropdownItemTextActive]}
                  >
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

          {/* Count */}
          <Text style={[styles.label, { marginTop: spacing.md }]}>How many questions?</Text>
          <View style={styles.countRow}>
            {['1', '3', '5', '10'].map(n => (
              <TouchableOpacity
                key={n}
                style={[styles.countChip, count === n && styles.chipActive]}
                onPress={() => setCount(n)}
                activeOpacity={0.75}
              >
                <Text style={[styles.chipText, count === n && styles.chipTextActive]}>{n}</Text>
              </TouchableOpacity>
            ))}
          </View>

          {/* Instructions */}
          <Text style={[styles.label, { marginTop: spacing.md }]}>Special Instructions</Text>
          <TextInput
            value={instructions}
            onChangeText={setInstructions}
            placeholder="Optional: e.g. 'Use word problems with fruits' or 'Focus on numbers under 20'"
            placeholderTextColor={colors.textMuted}
            style={[styles.input, styles.multiline]}
            multiline
          />

          {/* Generate Button */}
          <PrimaryButton
            title={generating ? 'Generating…' : '✨ Generate Questions'}
            onPress={handleGenerate}
            loading={generating}
            variant="coral"
            style={{ marginTop: spacing.md }}
          />
        </Card>

        {/* ── Generated Drafts ── */}
        {generating && (
          <Card style={styles.loadingCard}>
            <ActivityIndicator size="large" color={colors.primary} />
            <Text style={styles.loadingText}>AI is creating questions…</Text>
            <Text style={styles.loadingSubtext}>This may take a few seconds</Text>
          </Card>
        )}

        {hasDrafts && (
          <>
            <View style={styles.draftHeader}>
              <Text style={styles.draftTitle}>📝 Review Questions</Text>
              <Text style={styles.draftCount}>{drafts.length} draft(s)</Text>
            </View>
            <Text style={styles.draftHint}>
              Edit any question below, then add it to your question bank.
            </Text>

            {drafts.map((draft) => (
              <DraftCard
                key={draft._localId}
                draft={draft}
                saving={savingIds.has(draft._localId)}
                onUpdate={(patch) => updateDraft(draft._localId, patch)}
                onRemove={() => removeDraft(draft._localId)}
                onSave={() => saveDraft(draft)}
              />
            ))}

            <PrimaryButton
              title={savingAll ? 'Saving…' : `✅ Add All ${drafts.length} to Question Bank`}
              onPress={saveAllDrafts}
              loading={savingAll}
              style={{ marginTop: spacing.sm }}
            />
          </>
        )}
      </ScrollView>
    </View>
  );
}

// ── Draft Card Component ──────────────────────────────────────────────────

function DraftCard({
  draft,
  saving,
  onUpdate,
  onRemove,
  onSave,
}: {
  draft: DraftItem;
  saving: boolean;
  onUpdate: (patch: Partial<DraftItem>) => void;
  onRemove: () => void;
  onSave: () => void;
}) {
  const { colors } = useAppTheme();
  const styles = createStyles(colors);
  const [editing, setEditing] = useState(false);

  return (
    <Card style={styles.draftCard}>
      {/* Header row */}
      <View style={styles.draftCardHeader}>
        <View style={styles.draftBadgeRow}>
          <View style={styles.topicBadge}>
            <Text style={styles.topicBadgeText}>{draft.topic}</Text>
          </View>
          <View style={styles.diffBadge}>
            <Text style={styles.diffBadgeText}>{draft.difficulty}</Text>
          </View>
        </View>
        <TouchableOpacity onPress={() => setEditing(!editing)} activeOpacity={0.7}>
          <Text style={styles.editLink}>{editing ? 'Done' : '✏️ Edit'}</Text>
        </TouchableOpacity>
      </View>

      {/* Question */}
      {editing ? (
        <TextInput
          value={draft.question_text}
          onChangeText={(v) => onUpdate({ question_text: v })}
          style={[styles.input, styles.multiline]}
          multiline
        />
      ) : (
        <Text style={styles.questionText}>{draft.question_text}</Text>
      )}

      {/* Answer */}
      <View style={styles.answerRow}>
        <Text style={styles.answerLabel}>Answer:</Text>
        {editing ? (
          <TextInput
            value={draft.correct_answer}
            onChangeText={(v) => onUpdate({ correct_answer: v })}
            style={[styles.input, { flex: 1, marginLeft: spacing.sm }]}
          />
        ) : (
          <Text style={styles.answerValue}>{draft.correct_answer}</Text>
        )}
      </View>

      {/* Options */}
      {draft.options && draft.options.length > 0 && (
        <View style={styles.optionsRow}>
          {editing ? (
            <TextInput
              value={draft.options.join(', ')}
              onChangeText={(v) =>
                onUpdate({ options: v.split(',').map(s => s.trim()).filter(Boolean) })
              }
              placeholder="Options separated by commas"
              placeholderTextColor={colors.textMuted}
              style={styles.input}
            />
          ) : (
            draft.options.map((opt, idx) => (
              <View
                key={idx}
                style={[
                  styles.optionChip,
                  opt === draft.correct_answer && styles.optionChipCorrect,
                ]}
              >
                <Text
                  style={[
                    styles.optionChipText,
                    opt === draft.correct_answer && styles.optionChipTextCorrect,
                  ]}
                >
                  {opt}
                </Text>
              </View>
            ))
          )}
        </View>
      )}

      {/* Actions */}
      <View style={styles.draftActions}>
        <TouchableOpacity style={styles.removeBtn} onPress={onRemove} activeOpacity={0.75}>
          <Text style={styles.removeBtnText}>Remove</Text>
        </TouchableOpacity>
        <TouchableOpacity
          style={[styles.saveBtn, saving && { opacity: 0.5 }]}
          onPress={saving ? undefined : onSave}
          activeOpacity={0.75}
        >
          {saving ? (
            <ActivityIndicator size="small" color={colors.textInverse} />
          ) : (
            <Text style={styles.saveBtnText}>Add to Question Bank</Text>
          )}
        </TouchableOpacity>
      </View>
    </Card>
  );
}

// ── Styles ──────────────────────────────────────────────────────────────

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

    // Form
    formCard: { gap: spacing.sm },
    label: {
      ...typography.caption,
      color: colors.textWarm,
      marginBottom: 2,
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

    // Dropdown
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

    // Chips
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
    countRow: {
      flexDirection: 'row',
      gap: spacing.sm,
    },
    countChip: {
      width: 48,
      height: 48,
      borderRadius: radius.lg,
      backgroundColor: colors.surface,
      borderWidth: 1.5,
      borderColor: colors.border,
      alignItems: 'center',
      justifyContent: 'center',
    },

    // Loading
    loadingCard: {
      alignItems: 'center',
      gap: spacing.md,
      paddingVertical: spacing.xl,
    },
    loadingText: {
      ...typography.subtitle,
      color: colors.textWarm,
    },
    loadingSubtext: {
      ...typography.caption,
      color: colors.textMuted,
    },

    // Drafts
    draftHeader: {
      flexDirection: 'row',
      justifyContent: 'space-between',
      alignItems: 'center',
      marginTop: spacing.md,
    },
    draftTitle: {
      ...typography.subtitle,
      color: colors.textWarm,
    },
    draftCount: {
      ...typography.caption,
      color: colors.textMuted,
    },
    draftHint: {
      ...typography.caption,
      color: colors.textMuted,
      marginBottom: spacing.xs,
    },

    draftCard: {
      gap: spacing.sm,
    },
    draftCardHeader: {
      flexDirection: 'row',
      justifyContent: 'space-between',
      alignItems: 'center',
    },
    draftBadgeRow: {
      flexDirection: 'row',
      gap: spacing.sm,
    },
    topicBadge: {
      backgroundColor: colors.skyBlueSoft,
      paddingHorizontal: spacing.sm,
      paddingVertical: 4,
      borderRadius: radius.pill,
    },
    topicBadgeText: {
      ...typography.small,
      color: colors.primaryDark,
    },
    diffBadge: {
      backgroundColor: colors.warmYellowSoft,
      paddingHorizontal: spacing.sm,
      paddingVertical: 4,
      borderRadius: radius.pill,
    },
    diffBadgeText: {
      ...typography.small,
      color: colors.textWarm,
    },
    editLink: {
      ...typography.caption,
      color: colors.primary,
    },
    questionText: {
      ...typography.body,
      color: colors.text,
      lineHeight: 22,
    },
    answerRow: {
      flexDirection: 'row',
      alignItems: 'center',
    },
    answerLabel: {
      ...typography.caption,
      color: colors.textMuted,
    },
    answerValue: {
      ...typography.caption,
      color: colors.success,
      marginLeft: spacing.xs,
      fontWeight: '800',
    },
    optionsRow: {
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
    optionChipCorrect: {
      backgroundColor: colors.successBg,
      borderColor: colors.success,
    },
    optionChipText: {
      ...typography.small,
      color: colors.textWarm,
    },
    optionChipTextCorrect: {
      color: colors.success,
      fontWeight: '800',
    },
    draftActions: {
      flexDirection: 'row',
      gap: spacing.sm,
      marginTop: spacing.xs,
    },
    removeBtn: {
      flex: 1,
      alignItems: 'center',
      paddingVertical: spacing.sm,
      borderRadius: radius.pill,
      backgroundColor: colors.surface,
      borderWidth: 1.5,
      borderColor: colors.coral,
    },
    removeBtnText: {
      ...typography.caption,
      color: colors.coral,
    },
    saveBtn: {
      flex: 1,
      alignItems: 'center',
      paddingVertical: spacing.sm,
      borderRadius: radius.pill,
      backgroundColor: colors.success,
    },
    saveBtnText: {
      ...typography.caption,
      color: colors.textInverse,
      fontWeight: '800',
    },
  });
