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

const levelWord = (l: string, t: any) => {
  switch (l) {
    case 'high': return t.levels.levelHigh;
    case 'medium': return t.levels.levelMedium;
    case 'low': return t.levels.levelLow;
    case 'Fast': return t.levels.levelFast;
    case 'Moderate': return t.levels.levelModerate;
    case 'Slow': return t.levels.levelSlow;
    default: return l.toUpperCase();
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

const levelBg = (l: string, colors: ReturnType<typeof useAppTheme>['colors']) => {
  switch (l) {
    case 'high': case 'Fast': return colors.successBg;
    case 'medium': case 'Moderate': return colors.skyBlueSoft;
    case 'low': case 'Slow': return colors.warningBg;
    default: return colors.surfaceSoft;
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

  const LevelChip = ({ level }: { level: string }) => (
    <View style={[styles.chip, { backgroundColor: levelBg(level, colors), borderColor: levelColor(level, colors) + '60' }]}>
      <Text style={[styles.chipText, { color: levelColor(level, colors) }]}>
        {levelWord(level, t)}
      </Text>
    </View>
  );

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

      {/* ── History Table ── */}
      <Card style={styles.tableCard}>
        {/* Header Row */}
        <View style={styles.tableHeader}>
          <Text style={[styles.headerCell, styles.dateCol]}>{t.common.date}</Text>
          <Text style={[styles.headerCell, styles.dimCol]}>{t.history.columnMemory}</Text>
          <Text style={[styles.headerCell, styles.dimCol]}>{t.history.columnAttention}</Text>
          <Text style={[styles.headerCell, styles.dimCol]}>{t.history.columnNumberSense}</Text>
          <Text style={[styles.headerCell, styles.dimCol]}>{t.history.columnSpeed}</Text>
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
              <Text style={[styles.dateCell]}>{dateStr}</Text>
              <View style={styles.dimCell}>
                <Text style={[styles.cellWord, { color: levelColor(p.memory_level, colors) }]}>
                  {levelWord(p.memory_level, t)}
                </Text>
              </View>
              <View style={styles.dimCell}>
                <Text style={[styles.cellWord, { color: levelColor(p.attention_level, colors) }]}>
                  {levelWord(p.attention_level, t)}
                </Text>
              </View>
              <View style={styles.dimCell}>
                <Text style={[styles.cellWord, { color: levelColor(p.number_sense_level, colors) }]}>
                  {levelWord(p.number_sense_level, t)}
                </Text>
              </View>
              <View style={styles.dimCell}>
                <Text style={[styles.cellWord, { color: levelColor(p.processing_speed_level, colors) }]}>
                  {levelWord(p.processing_speed_level, t)}
                </Text>
              </View>
            </View>
          );
        })}
      </Card>

      {/* ── Legend ── */}
      <Card style={styles.legendCard}>
        <Text style={styles.legendTitle}>{t.history.legend}</Text>
        <View style={styles.legendGrid}>
          {/* High */}
          <View style={[styles.legendItem, { backgroundColor: colors.successBg, borderColor: colors.success + '50' }]}>
            <View style={[styles.legendDot, { backgroundColor: colors.success }]} />
            <View>
              <Text style={[styles.legendLevel, { color: colors.success }]}>{t.history.legendHigh}</Text>
              <Text style={styles.legendSub}>{t.history.legendHighSub}</Text>
            </View>
          </View>
          {/* Medium */}
          <View style={[styles.legendItem, { backgroundColor: colors.skyBlueSoft, borderColor: colors.primary + '50' }]}>
            <View style={[styles.legendDot, { backgroundColor: colors.primary }]} />
            <View>
              <Text style={[styles.legendLevel, { color: colors.primary }]}>{t.history.legendMedium}</Text>
              <Text style={styles.legendSub}>{t.history.legendMediumSub}</Text>
            </View>
          </View>
          {/* Low */}
          <View style={[styles.legendItem, { backgroundColor: colors.warningBg, borderColor: colors.warning + '50' }]}>
            <View style={[styles.legendDot, { backgroundColor: colors.warning }]} />
            <View>
              <Text style={[styles.legendLevel, { color: colors.warning }]}>{t.history.legendLow}</Text>
              <Text style={styles.legendSub}>{t.history.legendLowSub}</Text>
            </View>
          </View>
        </View>
      </Card>

      {/* ── Detailed List ── */}
      {profiles.map((p, idx) => (
        <Card key={`detail-${idx}`} style={styles.detailCard}>
          <Text style={styles.detailDate}>
            {new Date(p.generated_at).toLocaleDateString()} –{' '}
            {new Date(p.generated_at).toLocaleTimeString()}
          </Text>
          <View style={styles.chipRow}>
            <View style={styles.chipGroup}>
              <Text style={styles.chipLabel}>{t.common.memory}</Text>
              <LevelChip level={p.memory_level} />
            </View>
            <View style={styles.chipGroup}>
              <Text style={styles.chipLabel}>{t.common.attention}</Text>
              <LevelChip level={p.attention_level} />
            </View>
            <View style={styles.chipGroup}>
              <Text style={styles.chipLabel}>{t.common.numberSense}</Text>
              <LevelChip level={p.number_sense_level} />
            </View>
            <View style={styles.chipGroup}>
              <Text style={styles.chipLabel}>{t.common.speed}</Text>
              <LevelChip level={p.processing_speed_level} />
            </View>
          </View>
          <Text style={styles.detailAccuracy}>
            {t.common.correctness}: {Math.round(p.features.accuracy * 100)}% | {t.common.questions}: {p.features.total_questions}
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
  subheading: { ...typography.body, color: colors.textMuted, marginBottom: spacing.xs },

  // Table
  tableCard: { padding: 0, overflow: 'hidden' },
  tableHeader: {
    flexDirection: 'row',
    backgroundColor: colors.skyBlue,
    paddingVertical: 10,
    paddingHorizontal: spacing.sm,
  },
  headerCell: {
    ...typography.small,
    fontWeight: '700',
    color: colors.deepBlue,
    textAlign: 'center',
    textTransform: 'uppercase',
    letterSpacing: 0.4,
  },
  dateCol: { flex: 1.2 },
  dimCol: { flex: 1.4 },
  tableRow: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 9,
    paddingHorizontal: spacing.sm,
    borderBottomWidth: 1,
    borderBottomColor: colors.border,
  },
  tableRowAlt: { backgroundColor: colors.skyBlueSoft },
  dateCell: {
    flex: 1.2,
    ...typography.caption,
    color: colors.textMuted,
    textAlign: 'center',
    fontWeight: '600',
  },
  dimCell: { flex: 1.4, alignItems: 'center' },
  cellWord: {
    fontSize: 10,
    fontWeight: '800',
    letterSpacing: 0.6,
    textAlign: 'center',
  },

  // Legend
  legendCard: { gap: spacing.md },
  legendTitle: { ...typography.subtitle, color: colors.textWarm, marginBottom: spacing.xs },
  legendGrid: { gap: spacing.sm },
  legendItem: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.sm,
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm,
    borderRadius: radius.lg,
    borderWidth: 1,
  },
  legendDot: { width: 12, height: 12, borderRadius: 6 },
  legendLevel: { ...typography.caption, fontWeight: '800' },
  legendSub: { ...typography.small, color: colors.textMuted },

  // Detail Cards
  detailCard: { gap: spacing.sm },
  detailDate: { ...typography.caption, color: colors.primaryDark, fontWeight: '700' },
  chipRow: { flexDirection: 'row', flexWrap: 'wrap', gap: spacing.sm },
  chipGroup: { alignItems: 'center', gap: 4, minWidth: 70 },
  chipLabel: { ...typography.small, color: colors.textMuted, textTransform: 'uppercase', fontSize: 9, letterSpacing: 0.5 },
  chip: {
    paddingHorizontal: spacing.sm,
    paddingVertical: 4,
    borderRadius: radius.pill,
    borderWidth: 1,
  },
  chipText: { fontWeight: '800', fontSize: 10, letterSpacing: 0.6 },
  detailAccuracy: { ...typography.small, color: colors.textMuted, marginTop: 4 },
});
