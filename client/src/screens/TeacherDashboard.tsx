import React, { useCallback, useEffect, useState } from 'react';
import {
  ActivityIndicator,
  RefreshControl,
  ScrollView,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from 'react-native';
import type { NativeStackScreenProps } from '@react-navigation/native-stack';
import type { RootStackParamList } from '../../App';
import Card from '../components/Card';
import PrimaryButton from '../components/PrimaryButton';
import LanguageToggle from '../components/LanguageToggle';
import { useLanguage } from '../i18n/LanguageContext';
import { colors, radius, spacing, typography } from '../theme';
import { api, type StudentSummary } from '../api/client';

type Props = NativeStackScreenProps<RootStackParamList, 'TeacherDashboard'>;

const levelEmoji = (l: string) => {
  switch (l) {
    case 'high': case 'Fast': return '🌟';
    case 'medium': case 'Moderate': return '👍';
    case 'low': case 'Slow': return '💪';
    default: return '–';
  }
};

const weakestArea = (p: StudentSummary['latest_profile'], labels: { memory: string; attention: string; numberSense: string; speed: string }): string => {
  if (!p) return '–';
  const dims = [
    { label: labels.memory, level: p.memory_level },
    { label: labels.attention, level: p.attention_level },
    { label: labels.numberSense, level: p.number_sense_level },
    { label: labels.speed, level: p.processing_speed_level },
  ];
  const lowDims = dims.filter(d =>
    d.level === 'low' || d.level === 'Slow'
  );
  if (lowDims.length === 0) return '–';
  return lowDims.map(d => d.label).join(', ');
};

export default function TeacherDashboard({ route, navigation }: Props) {
  const { t } = useLanguage();
  const { teacherId } = route.params;
  const [students, setStudents] = useState<StudentSummary[]>([]);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await api.getStudentsList();
      setStudents(data);
    } catch {
      setStudents([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  if (loading) {
    return (
      <View style={styles.center}>
        <ActivityIndicator size="large" color={colors.primary} />
        <Text style={styles.loadingText}>{t.teacherDash.loadingStudents}</Text>
      </View>
    );
  }

  return (
    <ScrollView
      contentContainerStyle={styles.container}
      refreshControl={<RefreshControl refreshing={loading} onRefresh={load} />}
    >
      {/* Language Toggle */}
      <LanguageToggle />

      {/* Header */}
      <View style={styles.header}>
        <Text style={{ fontSize: 40 }}>👩‍🏫</Text>
        <Text style={styles.title}>{t.teacherDash.title}</Text>
        <Text style={styles.subtitle}>
          {t.teacherDash.studentsTracked
            .replace('{count}', String(students.length))
            .replace('{s}', students.length === 1 ? '' : 's')}
        </Text>
      </View>

      {students.length === 0 && (
        <Card style={styles.emptyCard}>
          <Text style={{ fontSize: 48, textAlign: 'center' }}>📋</Text>
          <Text style={styles.emptyText}>
            {t.teacherDash.noStudentData}
          </Text>
        </Card>
      )}

      {/* Student List */}
      {students.map((s, idx) => (
        <TouchableOpacity
          key={idx}
          activeOpacity={0.7}
          onPress={() =>
            navigation.navigate('ProfileResult', { studentId: s.student_id })
          }
        >
          <Card style={styles.studentCard}>
            <View style={styles.studentHeader}>
              <View style={styles.avatarCircle}>
                <Text style={{ fontSize: 24 }}>🧒</Text>
              </View>
              <View style={{ flex: 1 }}>
                <Text style={styles.studentName}>
                  {s.name || s.student_code || s.student_id.slice(0, 12)}
                </Text>
                <Text style={styles.studentMeta}>
                  {s.total_interactions} {t.common.interactions}
                  {s.last_activity_date
                    ? ` · ${t.teacherDash.last}: ${new Date(s.last_activity_date).toLocaleDateString()}`
                    : ''}
                </Text>
              </View>
              <Text style={styles.arrow}>›</Text>
            </View>

            {s.latest_profile && (
              <View style={styles.profileRow}>
                <View style={styles.dimChip}>
                  <Text style={styles.chipText}>
                    🧠 {levelEmoji(s.latest_profile.memory_level)}
                  </Text>
                </View>
                <View style={styles.dimChip}>
                  <Text style={styles.chipText}>
                    🎯 {levelEmoji(s.latest_profile.attention_level)}
                  </Text>
                </View>
                <View style={styles.dimChip}>
                  <Text style={styles.chipText}>
                    🔢 {levelEmoji(s.latest_profile.number_sense_level)}
                  </Text>
                </View>
                <View style={styles.dimChip}>
                  <Text style={styles.chipText}>
                    ⚡ {levelEmoji(s.latest_profile.processing_speed_level)}
                  </Text>
                </View>
              </View>
            )}

            {s.latest_profile && (
              <View style={styles.weakRow}>
                <Text style={styles.weakLabel}>{t.teacherDash.weakestArea}:</Text>
                <Text style={styles.weakValue}>{weakestArea(s.latest_profile, { memory: t.common.memory, attention: t.common.attention, numberSense: t.common.numberSense, speed: t.common.speed })}</Text>
              </View>
            )}

            {!s.latest_profile && (
              <Text style={styles.noProfile}>{t.teacherDash.noProfileGenerated}</Text>
            )}
          </Card>
        </TouchableOpacity>
      ))}

      <PrimaryButton
        title={t.teacherDash.backToLogin}
        variant="ghost"
        onPress={() => navigation.popToTop()}
      />
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  center: {
    flex: 1, alignItems: 'center', justifyContent: 'center',
    padding: spacing.xl, gap: spacing.md,
  },
  loadingText: { ...typography.subtitle, color: colors.textMuted },
  container: { padding: spacing.lg, paddingTop: spacing.md, gap: spacing.md, paddingBottom: spacing.xxl },
  header: { alignItems: 'center', marginBottom: spacing.sm },
  title: { ...typography.title, color: colors.textWarm, marginTop: spacing.sm },
  subtitle: { ...typography.body, color: colors.textMuted, marginTop: spacing.xs },
  emptyCard: { alignItems: 'center', gap: spacing.md, paddingVertical: spacing.xl },
  emptyText: { ...typography.body, color: colors.textMuted, textAlign: 'center', maxWidth: 280 },
  studentCard: { gap: spacing.sm },
  studentHeader: { flexDirection: 'row', alignItems: 'center', gap: spacing.md },
  avatarCircle: {
    width: 44, height: 44, borderRadius: 22,
    backgroundColor: colors.skyBlueSoft,
    alignItems: 'center', justifyContent: 'center',
  },
  studentName: { ...typography.subtitle, color: colors.textWarm },
  studentMeta: { ...typography.small, color: colors.textMuted, marginTop: 2 },
  arrow: { fontSize: 28, color: colors.textMuted, fontWeight: '300' },
  profileRow: { flexDirection: 'row', gap: spacing.sm, flexWrap: 'wrap' },
  dimChip: {
    backgroundColor: colors.skyBlueSoft,
    paddingHorizontal: spacing.sm, paddingVertical: 4,
    borderRadius: radius.pill,
  },
  chipText: { ...typography.small, color: colors.text },
  weakRow: { flexDirection: 'row', gap: spacing.sm, alignItems: 'center' },
  weakLabel: { ...typography.caption, color: colors.textMuted },
  weakValue: { ...typography.caption, color: colors.warning },
  noProfile: { ...typography.caption, color: colors.textMuted, fontStyle: 'italic' },
});
