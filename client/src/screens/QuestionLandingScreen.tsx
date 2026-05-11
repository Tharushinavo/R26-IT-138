import React, { useCallback, useEffect, useState } from 'react';
import {
  ScrollView,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from 'react-native';
import type { NativeStackScreenProps } from '@react-navigation/native-stack';
import type { RootStackParamList } from '../../App';
import Card from '../components/Card';
import { api } from '../api/client';
import { radius, spacing, typography, useAppTheme } from '../theme';

type Props = NativeStackScreenProps<RootStackParamList, 'CognitiveQuestions'>;

export default function QuestionLandingScreen({ route, navigation }: Props) {
  const { teacherId } = route.params;
  const { colors } = useAppTheme();
  const styles = createStyles(colors);
  const [questionCount, setQuestionCount] = useState<number | null>(null);

  const loadCount = useCallback(async () => {
    try {
      const data = await api.getQuestions(undefined, undefined, 100);
      setQuestionCount(data.length);
    } catch {
      setQuestionCount(0);
    }
  }, []);

  useEffect(() => { loadCount(); }, [loadCount]);

  // Reload count when returning from sub-screens
  useEffect(() => {
    const unsubscribe = navigation.addListener('focus', () => {
      loadCount();
    });
    return unsubscribe;
  }, [navigation, loadCount]);

  return (
    <View style={{ flex: 1, backgroundColor: colors.background }}>
      <ScrollView contentContainerStyle={styles.container}>
        {/* Header */}
        <View style={styles.header}>
          <Text style={{ fontSize: 48, textAlign: 'center' }}>📚</Text>
          <Text style={styles.title}>Question Bank</Text>
          <Text style={styles.subtitle}>
            Manage the cognitive math questions used by students in their learning activities.
          </Text>
          {questionCount !== null && (
            <View style={styles.countBadge}>
              <Text style={styles.countText}>
                {questionCount} question{questionCount !== 1 ? 's' : ''} in bank
              </Text>
            </View>
          )}
        </View>

        {/* ── Card 1: Create Manually ── */}
        <TouchableOpacity
          activeOpacity={0.85}
          onPress={() => navigation.navigate('ManualCreateQuestion', { teacherId })}
        >
          <Card style={styles.actionCard}>
            <View style={styles.cardRow}>
              <View style={[styles.iconCircle, { backgroundColor: colors.skyBlueSoft }]}>
                <Text style={{ fontSize: 28 }}>✏️</Text>
              </View>
              <View style={styles.cardContent}>
                <Text style={styles.cardTitle}>Create Manually</Text>
                <Text style={styles.cardDescription}>
                  Write your own question, set the topic, difficulty, answer, and options.
                </Text>
              </View>
              <Text style={styles.cardArrow}>›</Text>
            </View>
          </Card>
        </TouchableOpacity>

        {/* ── Card 2: Generate with AI ── */}
        <TouchableOpacity
          activeOpacity={0.85}
          onPress={() => navigation.navigate('AIGenerate', { teacherId })}
        >
          <Card style={[styles.actionCard, styles.aiCard]}>
            <View style={styles.cardRow}>
              <View style={[styles.iconCircle, { backgroundColor: '#FFF0E6' }]}>
                <Text style={{ fontSize: 28 }}>✨</Text>
              </View>
              <View style={styles.cardContent}>
                <Text style={styles.cardTitle}>Generate with AI</Text>
                <Text style={styles.cardDescription}>
                  Choose a type and difficulty — the AI creates questions for you to review.
                </Text>
              </View>
              <Text style={styles.cardArrow}>›</Text>
            </View>
          </Card>
        </TouchableOpacity>

        {/* ── Card 3: Edit Existing ── */}
        <TouchableOpacity
          activeOpacity={0.85}
          onPress={() => navigation.navigate('EditQuestions', { teacherId })}
        >
          <Card style={styles.actionCard}>
            <View style={styles.cardRow}>
              <View style={[styles.iconCircle, { backgroundColor: colors.successBg }]}>
                <Text style={{ fontSize: 28 }}>📝</Text>
              </View>
              <View style={styles.cardContent}>
                <Text style={styles.cardTitle}>Edit Existing Questions</Text>
                <Text style={styles.cardDescription}>
                  Browse, edit, or delete questions already in the question bank.
                </Text>
              </View>
              <Text style={styles.cardArrow}>›</Text>
            </View>
            {questionCount !== null && questionCount > 0 && (
              <View style={styles.cardBadge}>
                <Text style={styles.cardBadgeText}>{questionCount} questions</Text>
              </View>
            )}
          </Card>
        </TouchableOpacity>
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
    countBadge: {
      backgroundColor: colors.skyBlueSoft,
      paddingHorizontal: spacing.lg,
      paddingVertical: spacing.sm,
      borderRadius: radius.pill,
      marginTop: spacing.xs,
    },
    countText: {
      ...typography.caption,
      color: colors.primaryDark,
    },
    actionCard: {
      gap: spacing.sm,
    },
    aiCard: {
      borderColor: colors.coral,
      borderWidth: 2,
    },
    cardRow: {
      flexDirection: 'row',
      alignItems: 'center',
      gap: spacing.md,
    },
    iconCircle: {
      width: 56,
      height: 56,
      borderRadius: 28,
      alignItems: 'center',
      justifyContent: 'center',
    },
    cardContent: {
      flex: 1,
      gap: 4,
    },
    cardTitle: {
      ...typography.subtitle,
      color: colors.textWarm,
    },
    cardDescription: {
      ...typography.caption,
      color: colors.textMuted,
      lineHeight: 18,
    },
    cardArrow: {
      fontSize: 28,
      color: colors.textMuted,
      fontWeight: '300',
    },
    cardBadge: {
      alignSelf: 'flex-start',
      marginLeft: 56 + spacing.md,
      backgroundColor: colors.successBg,
      paddingHorizontal: spacing.sm,
      paddingVertical: 3,
      borderRadius: radius.pill,
    },
    cardBadgeText: {
      ...typography.small,
      color: colors.success,
    },
  });
