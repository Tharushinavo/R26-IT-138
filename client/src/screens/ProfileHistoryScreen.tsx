import React, { useCallback, useEffect, useState } from 'react';
import {
  ActivityIndicator,
  RefreshControl,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from 'react-native';
import type { NativeStackScreenProps } from '@react-navigation/native-stack';
import type { RootStackParamList } from '../../App';
import Card from '../components/Card';
import PrimaryButton from '../components/PrimaryButton';
import ProfileControls from '../components/ProfileControls';
import { useLanguage } from '../i18n/LanguageContext';
import { useAuth } from '../context/AuthContext';
import { radius, spacing, typography, useAppTheme } from '../theme';
import { api, type CognitiveProfile } from '../api/client';

type Props = NativeStackScreenProps<RootStackParamList, 'ProfileHistory'>;

const levelEmoji = (l: string) => {
  switch (l) {
    case 'high': case 'Fast': return '🌟';
    case 'medium': case 'Moderate': return '👍';
    case 'low': case 'Slow': return '💪';
    default: return '–';
  }
};

const levelColor = (l: string, colors: ReturnType<typeof useAppTheme>['colors']) => {
  switch (l) {
    case 'high': case 'Fast': return colors.success;
    case 'medium': case 'Moderate': return colors.primary;
    case 'low': case 'Slow': return colors.warning;
    default: return colors.textMuted;
  }
};

export default function ProfileHistoryScreen({ route, navigation }: Props) {
  const { t } = useLanguage();
  const { role, user } = useAuth();
  const { colors } = useAppTheme();
  const styles = createStyles(colors);
  const { studentId } = route.params;
  const isTeacherView = role === 'teacher' || role === 'admin';
  const [profiles, setProfiles] = useState<CognitiveProfile[]>([]);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    console.log('[profile] history fetch start', { studentId });
    try {
      const data = await api.getProfileHistory(studentId);
      console.log('[profile] history fetch success', { studentId, count: data.length });
      setProfiles(data);
    } catch (e: any) {
      console.log('[profile] history fetch failed', { studentId, message: e?.message });
      setProfiles([]);
    } finally {
      setLoading(false);
    }
  }, [studentId]);

  useEffect(() => { load(); }, [load]);

  if (loading) {
    return (
      <View style={[styles.center, { backgroundColor: colors.background }]}>
        <ActivityIndicator size="large" color={colors.primary} />
        <Text style={styles.loadingText}>{t.history.loadingHistory}</Text>
      </View>
    );
  }

  if (profiles.length === 0) {
    return (
      <View style={[styles.center, { backgroundColor: colors.background }]}>
        <Text style={{ fontSize: 56 }}>📊</Text>
        <Text style={styles.emptyTitle}>{t.history.noHistoryYet}</Text>
        <Text style={styles.emptySubtitle}>
          {isTeacherView
            ? 'No profile history is available for this student yet.'
            : t.history.completeActivities}
        </Text>
        {isTeacherView ? (
          <PrimaryButton
            title="Back to Teacher Dashboard"
            onPress={() => navigation.navigate('TeacherDashboard', { teacherId: user?.id || '' })}
          />
        ) : (
          <PrimaryButton
            title={t.history.startActivity}
            onPress={() => navigation.navigate('MathActivity', { studentId })}
          />
        )}
      </View>
    );
  }

  return (
    <View style={{ flex: 1, backgroundColor: colors.background }}>
    <ScrollView
      contentContainerStyle={styles.container}
      refreshControl={<RefreshControl refreshing={loading} onRefresh={load} />}
    >
      <ProfileControls />

      <Text style={styles.heading}>{t.history.profileHistory}</Text>
      <Text style={styles.subheading}>
        {t.history.profilesRecorded
          .replace('{count}', String(profiles.length))
          .replace('{s}', profiles.length === 1 ? '' : 's')}
      </Text>

      {/* History Table */}
      <Card style={styles.tableCard}>
        {/* Header Row */}
        <View style={styles.tableHeader}>
          <Text style={[styles.headerCell, { flex: 1.5 }]}>{t.common.date}</Text>
          <Text style={styles.headerCell}>🧠</Text>
          <Text style={styles.headerCell}>🎯</Text>
          <Text style={styles.headerCell}>🔢</Text>
          <Text style={styles.headerCell}>⚡</Text>
        </View>

        {/* Data Rows */}
        {profiles.map((p, idx) => {
          const date = new Date(p.generated_at);
          const dateStr = `${date.getMonth() + 1}/${date.getDate()}`;
          return (
            <View
              key={idx}
              style={[styles.tableRow, idx % 2 === 0 && styles.tableRowAlt]}
            >
              <Text style={[styles.cell, { flex: 1.5 }]}>{dateStr}</Text>
              <Text style={[styles.cell, { color: levelColor(p.memory_level, colors) }]}>
                {levelEmoji(p.memory_level)}
              </Text>
              <Text style={[styles.cell, { color: levelColor(p.attention_level, colors) }]}>
                {levelEmoji(p.attention_level)}
              </Text>
              <Text style={[styles.cell, { color: levelColor(p.number_sense_level, colors) }]}>
                {levelEmoji(p.number_sense_level)}
              </Text>
              <Text style={[styles.cell, { color: levelColor(p.processing_speed_level, colors) }]}>
                {levelEmoji(p.processing_speed_level)}
              </Text>
            </View>
          );
        })}
      </Card>

      {/* Legend */}
      <Card style={styles.legendCard}>
        <Text style={styles.legendTitle}>{t.history.legend}</Text>
        <View style={styles.legendRow}>
          <Text style={styles.legendItem}>{t.history.legendHigh}</Text>
          <Text style={styles.legendItem}>{t.history.legendMedium}</Text>
          <Text style={styles.legendItem}>{t.history.legendLow}</Text>
        </View>
      </Card>

      {/* Detailed List */}
      {profiles.map((p, idx) => (
        <Card key={`detail-${idx}`} style={styles.detailCard}>
          <Text style={styles.detailDate}>
            {new Date(p.generated_at).toLocaleDateString()} –{' '}
            {new Date(p.generated_at).toLocaleTimeString()}
          </Text>
          <View style={styles.detailRow}>
            <Text style={styles.detailLabel}>{t.common.memory}</Text>
            <Text style={[styles.detailValue, { color: levelColor(p.memory_level, colors) }]}>
              {levelEmoji(p.memory_level)} {p.memory_level}
            </Text>
          </View>
          <View style={styles.detailRow}>
            <Text style={styles.detailLabel}>{t.common.attention}</Text>
            <Text style={[styles.detailValue, { color: levelColor(p.attention_level, colors) }]}>
              {levelEmoji(p.attention_level)} {p.attention_level}
            </Text>
          </View>
          <View style={styles.detailRow}>
            <Text style={styles.detailLabel}>{t.common.numberSense}</Text>
            <Text style={[styles.detailValue, { color: levelColor(p.number_sense_level, colors) }]}>
              {levelEmoji(p.number_sense_level)} {p.number_sense_level}
            </Text>
          </View>
          <View style={styles.detailRow}>
            <Text style={styles.detailLabel}>{t.common.speed}</Text>
            <Text style={[styles.detailValue, { color: levelColor(p.processing_speed_level, colors) }]}>
              {levelEmoji(p.processing_speed_level)} {p.processing_speed_level}
            </Text>
          </View>
          <Text style={styles.detailAccuracy}>
            {t.common.accuracy}: {Math.round(p.features.accuracy * 100)}% | {t.common.questions}: {p.features.total_questions}
          </Text>
        </Card>
      ))}

      <PrimaryButton
        title={isTeacherView ? 'Back to Teacher Dashboard' : t.history.backToDashboard}
        variant="ghost"
        onPress={() => navigation.goBack()}
      />
    </ScrollView>
    </View>
  );
}

const createStyles = (colors: ReturnType<typeof useAppTheme>['colors']) => StyleSheet.create({
  center: {
    flex: 1, alignItems: 'center', justifyContent: 'center',
    padding: spacing.xl, gap: spacing.md,
  },
  loadingText: { ...typography.subtitle, color: colors.textMuted },
  emptyTitle: { ...typography.title, color: colors.textWarm, textAlign: 'center' },
  emptySubtitle: { ...typography.body, color: colors.textMuted, textAlign: 'center', maxWidth: 280 },
  container: { padding: spacing.lg, paddingTop: spacing.md, gap: spacing.md, paddingBottom: spacing.xxl },
  heading: { ...typography.title, color: colors.textWarm },
  subheading: { ...typography.body, color: colors.textMuted, marginBottom: spacing.sm },
  tableCard: { padding: 0, overflow: 'hidden' },
  tableHeader: {
    flexDirection: 'row', backgroundColor: colors.skyBlue,
    paddingVertical: spacing.sm, paddingHorizontal: spacing.md,
  },
  headerCell: {
    flex: 1, ...typography.caption, color: colors.textWarm, textAlign: 'center',
  },
  tableRow: {
    flexDirection: 'row', paddingVertical: spacing.sm, paddingHorizontal: spacing.md,
  },
  tableRowAlt: { backgroundColor: colors.skyBlueSoft },
  cell: {
    flex: 1, ...typography.body, textAlign: 'center', color: colors.text,
  },
  legendCard: { gap: spacing.sm },
  legendTitle: { ...typography.caption, color: colors.textWarm },
  legendRow: { flexDirection: 'row', flexWrap: 'wrap', gap: spacing.md },
  legendItem: { ...typography.small, color: colors.textMuted },
  detailCard: { gap: spacing.xs },
  detailDate: { ...typography.caption, color: colors.primaryDark, marginBottom: 4 },
  detailRow: {
    flexDirection: 'row', justifyContent: 'space-between',
    paddingVertical: 4, borderBottomWidth: 1, borderBottomColor: colors.border,
  },
  detailLabel: { ...typography.body, color: colors.text },
  detailValue: { ...typography.caption },
  detailAccuracy: { ...typography.small, color: colors.textMuted, marginTop: 4, textAlign: 'right' },
});
