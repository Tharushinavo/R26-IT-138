import React, { useCallback, useEffect, useState } from 'react';
import {
  StyleSheet,
  Text,
  View,
  ScrollView,
  RefreshControl,
  TouchableOpacity,
} from 'react-native';
import { useNavigation } from '@react-navigation/native';
import PrimaryButton from '../components/PrimaryButton';
import Card from '../components/Card';
import { useLanguage } from '../i18n/LanguageContext';
import { useAuth } from '../context/AuthContext';
import { colors as lightColors, radius, spacing, typography, useAppTheme } from '../theme';
import { api, type CognitiveProfile } from '../api/client';

export default function StudentDashboard({ route }: any) {
  const { t } = useLanguage();
  const { user } = useAuth();
  const navigation = useNavigation<any>();
  const { colors } = useAppTheme();
  const styles = createStyles(colors);
  const { studentId } = route.params;
  const name = user?.full_name || '';
  const [profile, setProfile] = useState<CognitiveProfile | null>(null);
  const [refreshing, setRefreshing] = useState(false);

  const load = useCallback(async () => {
    console.log('[dashboard] latest profile fetch start', { studentId });
    try {
      const p = await api.getLatestProfile(studentId);
      console.log('[dashboard] latest profile fetch success', {
        requestedStudentId: studentId,
        storedStudentId: p.student_id,
        totalQuestions: p.features.total_questions,
      });
      setProfile(p);
    } catch (e: any) {
      console.log('[dashboard] latest profile fetch empty', { studentId, message: e?.message });
      setProfile(null);
    }
  }, [studentId]);

  useEffect(() => { load(); }, [load]);

  async function onRefresh() {
    setRefreshing(true);
    await load();
    setRefreshing(false);
  }

  const levelLabel = (l: string) => {
    switch (l) {
      case 'high': return `🌟 ${t.levels.high}`;
      case 'medium': return `👍 ${t.levels.medium}`;
      case 'low': return `💪 ${t.levels.low}`;
      case 'Fast': return `🌟 ${t.levels.fast}`;
      case 'Moderate': return `👍 ${t.levels.moderate}`;
      case 'Slow': return `💪 ${t.levels.slow}`;
      default: return l;
    }
  };

  return (
    <View style={{ flex: 1, backgroundColor: colors.background }}>
    <ScrollView
      contentContainerStyle={styles.container}
      refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} />}
    >
      {/* Greeting */}
      <View style={styles.greeting}>
        <Text style={{ fontSize: 48 }}>👋</Text>
        <Text style={styles.greetTitle}>
          {t.dashboard.welcomeBack}{name ? `, ${name}` : ''}!
        </Text>
        <Text style={styles.greetSub}>{t.dashboard.studentCode}: {studentId.slice(0, 12)}</Text>
      </View>

      {/* Latest Profile Summary */}
      {profile && (
        <Card style={styles.profileSummary}>
          <Text style={styles.sectionTitle}>{t.dashboard.latestProfile}</Text>
          <View style={styles.dimRow}>
            <Text style={styles.dimLabel}>🧠 {t.common.memory}</Text>
            <Text style={styles.dimValue}>{levelLabel(profile.memory_level)}</Text>
          </View>
          <View style={styles.dimRow}>
            <Text style={styles.dimLabel}>🎯 {t.common.attention}</Text>
            <Text style={styles.dimValue}>{levelLabel(profile.attention_level)}</Text>
          </View>
          <View style={styles.dimRow}>
            <Text style={styles.dimLabel}>🔢 {t.common.numberSense}</Text>
            <Text style={styles.dimValue}>{levelLabel(profile.number_sense_level)}</Text>
          </View>
          <View style={styles.dimRow}>
            <Text style={styles.dimLabel}>⚡ {t.common.speed}</Text>
            <Text style={styles.dimValue}>{levelLabel(profile.processing_speed_level)}</Text>
          </View>
          {profile.confidence_score != null && (
            <Text style={styles.confidence}>
              {t.common.confidence}: {Math.round(profile.confidence_score * 100)}%
            </Text>
          )}
        </Card>
      )}

      {!profile && (
        <Card style={styles.emptyCard}>
          <Text style={{ fontSize: 48, textAlign: 'center' }}>🤔</Text>
          <Text style={styles.emptyText}>
            {t.dashboard.noProfileYet}
          </Text>
        </Card>
      )}

      {/* Actions */}
      <View style={styles.actions}>
        <PrimaryButton
          title={t.dashboard.startActivity}
          onPress={() => navigation.navigate('StudentActivity', { studentId })}
        />
        <PrimaryButton
          title={t.dashboard.viewProfileResult}
          onPress={() => navigation.navigate('StudentProfile', { studentId })}
          variant="ghost"
        />
        <PrimaryButton
          title={t.dashboard.profileHistory}
          onPress={() => navigation.navigate('StudentHistory', { studentId })}
          variant="ghost"
        />
      </View>

    </ScrollView>
    </View>
  );
}

const createStyles = (colors: typeof lightColors) => StyleSheet.create({
  container: {
    padding: spacing.lg,
    paddingTop: spacing.md,
    paddingBottom: spacing.xxl,
    gap: spacing.md,
  },
  greeting: {
    alignItems: 'center',
    marginBottom: spacing.sm,
  },
  greetTitle: {
    ...typography.title,
    color: colors.textWarm,
    marginTop: spacing.sm,
  },
  greetSub: {
    ...typography.caption,
    color: colors.textMuted,
    marginTop: spacing.xs,
  },
  profileSummary: {
    gap: spacing.sm,
  },
  sectionTitle: {
    ...typography.subtitle,
    color: colors.textWarm,
    marginBottom: spacing.xs,
  },
  dimRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: 6,
    borderBottomWidth: 1,
    borderBottomColor: colors.border,
  },
  dimLabel: {
    ...typography.body,
    color: colors.text,
  },
  dimValue: {
    ...typography.caption,
    color: colors.textWarm,
  },
  confidence: {
    ...typography.caption,
    color: colors.textMuted,
    textAlign: 'right',
    marginTop: spacing.xs,
  },
  emptyCard: {
    alignItems: 'center',
    gap: spacing.md,
    paddingVertical: spacing.xl,
  },
  emptyText: {
    ...typography.body,
    color: colors.textMuted,
    textAlign: 'center',
    maxWidth: 280,
  },
  actions: {
    gap: spacing.md,
    marginTop: spacing.sm,
  },
});
