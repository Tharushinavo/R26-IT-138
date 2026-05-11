import React, { useCallback, useEffect, useMemo, useState } from 'react';
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
import { useLanguage } from '../i18n/LanguageContext';
import { useAuth } from '../context/AuthContext';
import { colors as lightColors, radius, spacing, typography, useAppTheme } from '../theme';
import { api, type StudentPerformance, type StudentSummary, type TeacherDashboardStats } from '../api/client';

type Props = NativeStackScreenProps<RootStackParamList, 'TeacherDashboard'>;
type Filter = 'all' | 'support' | 'missing';

const EMPTY_PERFORMANCE: StudentPerformance = {
  total_questions: 0,
  completed_sessions: 0,
  accuracy: 0,
  avg_response_time_sec: 0,
  avg_attempts: 1,
  retry_rate: 0,
  hint_rate: 0,
  topics: [],
};

const levelLabel = (level: string) => {
  switch (level) {
    case 'high': return 'High';
    case 'medium': return 'Medium';
    case 'low': return 'Needs Work';
    case 'Fast': return 'Fast';
    case 'Moderate': return 'Moderate';
    case 'Slow': return 'Slow';
    default: return level || 'None';
  }
};

const levelColor = (level: string, colors: typeof lightColors) => {
  switch (level) {
    case 'high':
    case 'Fast':
      return colors.success;
    case 'low':
    case 'Slow':
      return colors.warning;
    case 'medium':
    case 'Moderate':
      return colors.primary;
    default:
      return colors.textMuted;
  }
};

const performanceOf = (student: StudentSummary): StudentPerformance =>
  student.performance ?? EMPTY_PERFORMANCE;

const needsSupport = (student: StudentSummary) => {
  const p = student.latest_profile;
  const perf = performanceOf(student);
  return (
    p?.memory_level === 'low' ||
    p?.attention_level === 'low' ||
    p?.number_sense_level === 'low' ||
    p?.processing_speed_level === 'Slow' ||
    (perf.total_questions >= 5 && perf.accuracy < 0.6)
  );
};

const weakestArea = (
  p: StudentSummary['latest_profile'],
  labels: { memory: string; attention: string; numberSense: string; speed: string },
): string => {
  if (!p) return 'No profile';
  const dims = [
    { label: labels.memory, level: p.memory_level },
    { label: labels.attention, level: p.attention_level },
    { label: labels.numberSense, level: p.number_sense_level },
    { label: labels.speed, level: p.processing_speed_level },
  ];
  const weak = dims.filter(d => d.level === 'low' || d.level === 'Slow');
  return weak.length ? weak.map(d => d.label).join(', ') : 'None';
};

const pct = (value: number) => `${Math.round(value * 100)}%`;

const shortDate = (value?: string) => {
  if (!value) return 'No activity';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return 'No activity';
  return date.toLocaleDateString();
};

const fallbackStats = (students: StudentSummary[]): TeacherDashboardStats => {
  const totalQuestions = students.reduce((sum, s) => sum + performanceOf(s).total_questions, 0);
  const weightedAccuracy = students.reduce(
    (sum, s) => sum + performanceOf(s).accuracy * performanceOf(s).total_questions,
    0,
  );
  const weightedTime = students.reduce(
    (sum, s) => sum + performanceOf(s).avg_response_time_sec * performanceOf(s).total_questions,
    0,
  );
  return {
    total_students: students.length,
    students_with_profiles: students.filter(s => !!s.latest_profile).length,
    total_interactions: students.reduce((sum, s) => sum + s.total_interactions, 0),
    average_accuracy: totalQuestions ? weightedAccuracy / totalQuestions : 0,
    average_response_time_sec: totalQuestions ? weightedTime / totalQuestions : 0,
    needs_support_count: students.filter(needsSupport).length,
  };
};

export default function TeacherDashboard({ route, navigation }: Props) {
  const { t } = useLanguage();
  const { user } = useAuth();
  const { colors } = useAppTheme();
  const styles = createStyles(colors);
  const { teacherId } = route.params;
  const [students, setStudents] = useState<StudentSummary[]>([]);
  const [stats, setStats] = useState<TeacherDashboardStats | null>(null);
  const [filter, setFilter] = useState<Filter>('all');
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const load = useCallback(async (showSpinner = true) => {
    if (showSpinner) setLoading(true);
    try {
      const data = await api.getTeacherDashboard();
      setStudents(data.students);
      setStats(data.stats);
    } catch {
      try {
        const rows = await api.getStudentsList();
        setStudents(rows);
        setStats(fallbackStats(rows));
      } catch {
        setStudents([]);
        setStats(fallbackStats([]));
      }
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const visibleStudents = useMemo(() => {
    if (filter === 'support') return students.filter(needsSupport);
    if (filter === 'missing') return students.filter(s => !s.latest_profile);
    return students;
  }, [filter, students]);

  const dashboardStats = stats ?? fallbackStats(students);
  const teacherName = user?.full_name || `Teacher ${teacherId.slice(0, 6)}`;

  async function handleRefresh() {
    setRefreshing(true);
    await load(false);
  }

  if (loading) {
    return (
      <View style={[styles.center, { backgroundColor: colors.background }]}>
        <ActivityIndicator size="large" color={colors.primary} />
        <Text style={styles.loadingText}>{t.teacherDash.loadingStudents}</Text>
      </View>
    );
  }

  return (
    <View style={{ flex: 1, backgroundColor: colors.background }}>
    <ScrollView
      contentContainerStyle={styles.container}
      refreshControl={<RefreshControl refreshing={refreshing} onRefresh={handleRefresh} />}
    >
      <View style={styles.header}>
        <View>
          <Text style={styles.kicker}>Teacher workspace</Text>
          <Text style={styles.title}>{t.teacherDash.title}</Text>
          <Text style={styles.subtitle}>{teacherName}</Text>
        </View>
        <View style={styles.profileBubble}>
          <Text style={styles.profileBubbleText}>T</Text>
        </View>
      </View>

      <View style={styles.summaryGrid}>
        <SummaryTile label="Students" value={String(dashboardStats.total_students)} color={colors.primary} />
        <SummaryTile label="Profiles" value={String(dashboardStats.students_with_profiles)} color={colors.purple} />
        <SummaryTile label="Avg accuracy" value={pct(dashboardStats.average_accuracy)} color={colors.success} />
        <SummaryTile label="Need support" value={String(dashboardStats.needs_support_count)} color={colors.warning} />
      </View>

      <View style={styles.taskBand}>
        <Text style={styles.sectionTitle}>Class tasks</Text>
        <View style={styles.taskRow}>
          <TaskButton title="Review support" active={filter === 'support'} onPress={() => setFilter('support')} />
          <TaskButton title="Missing profiles" active={filter === 'missing'} onPress={() => setFilter('missing')} />
          <TaskButton title="All students" active={filter === 'all'} onPress={() => setFilter('all')} />
        </View>
      </View>

      <View style={styles.sectionHeader}>
        <View>
          <Text style={styles.sectionTitle}>Students</Text>
          <Text style={styles.sectionSubtitle}>
            {visibleStudents.length} shown of {students.length}
          </Text>
        </View>
        <Text style={styles.avgTime}>
          Avg time {dashboardStats.average_response_time_sec.toFixed(1)}s
        </Text>
      </View>

      {visibleStudents.length === 0 && (
        <Card style={styles.emptyCard}>
          <Text style={styles.emptyTitle}>No students in this view</Text>
          <Text style={styles.emptyText}>{t.teacherDash.noStudentData}</Text>
        </Card>
      )}

      {visibleStudents.map((student) => (
        <StudentCard
          key={student.student_id}
          student={student}
          labels={{
            memory: t.common.memory,
            attention: t.common.attention,
            numberSense: t.common.numberSense,
            speed: t.common.speed,
          }}
          onProfile={() => navigation.navigate('ProfileResult', { studentId: student.student_id })}
          onHistory={() => navigation.navigate('ProfileHistory', { studentId: student.student_id })}
        />
      ))}

    </ScrollView>
    </View>
  );
}

function SummaryTile({ label, value, color }: { label: string; value: string; color: string }) {
  const { colors } = useAppTheme();
  const styles = createStyles(colors);
  return (
    <View style={[styles.summaryTile, { borderTopColor: color }]}>
      <Text style={[styles.summaryValue, { color }]}>{value}</Text>
      <Text style={styles.summaryLabel}>{label}</Text>
    </View>
  );
}

function TaskButton({ title, active, onPress }: { title: string; active: boolean; onPress: () => void }) {
  const { colors } = useAppTheme();
  const styles = createStyles(colors);
  return (
    <TouchableOpacity
      activeOpacity={0.75}
      onPress={onPress}
      style={[styles.taskButton, active && styles.taskButtonActive]}
    >
      <Text style={[styles.taskButtonText, active && styles.taskButtonTextActive]}>{title}</Text>
    </TouchableOpacity>
  );
}

function StudentCard({
  student,
  labels,
  onProfile,
  onHistory,
}: {
  student: StudentSummary;
  labels: { memory: string; attention: string; numberSense: string; speed: string };
  onProfile: () => void;
  onHistory: () => void;
}) {
  const { colors } = useAppTheme();
  const styles = createStyles(colors);
  const perf = performanceOf(student);
  const support = needsSupport(student);
  const accuracyWidth = `${Math.max(5, Math.round(perf.accuracy * 100))}%`;
  const displayName = student.name || student.student_code || student.student_id.slice(0, 12);
  const topTopics = perf.topics?.slice(0, 3) ?? [];

  return (
    <Card style={[styles.studentCard, support && styles.studentCardAlert]}>
      <View style={styles.studentHeader}>
        <View style={styles.avatarCircle}>
          <Text style={styles.avatarText}>{displayName.charAt(0).toUpperCase()}</Text>
        </View>
        <View style={styles.studentTitleBlock}>
          <Text style={styles.studentName}>{displayName}</Text>
          <Text style={styles.studentMeta}>
            {student.student_code || student.student_id.slice(0, 12)}
            {student.grade ? `  Grade ${student.grade}` : ''}
          </Text>
        </View>
        <View style={[styles.statusBadge, support && styles.statusBadgeAlert]}>
          <Text style={[styles.statusText, support && styles.statusTextAlert]}>
            {support ? 'Support' : 'On track'}
          </Text>
        </View>
      </View>

      <View style={styles.accuracyBlock}>
        <View style={styles.accuracyHeader}>
          <Text style={styles.metricLabel}>Accuracy</Text>
          <Text style={styles.metricValue}>{pct(perf.accuracy)}</Text>
        </View>
        <View style={styles.accuracyTrack}>
          <View style={[styles.accuracyFill, { width: accuracyWidth as any }]} />
        </View>
      </View>

      <View style={styles.metricsRow}>
        <Metric label="Questions" value={String(perf.total_questions)} />
        <Metric label="Sessions" value={String(perf.completed_sessions)} />
        <Metric label="Avg time" value={`${perf.avg_response_time_sec.toFixed(1)}s`} />
        <Metric label="Hints" value={pct(perf.hint_rate)} />
      </View>

      {student.latest_profile ? (
        <View style={styles.profileGrid}>
          <ProfilePill label={labels.memory} level={student.latest_profile.memory_level} />
          <ProfilePill label={labels.attention} level={student.latest_profile.attention_level} />
          <ProfilePill label={labels.numberSense} level={student.latest_profile.number_sense_level} />
          <ProfilePill label={labels.speed} level={student.latest_profile.processing_speed_level} />
        </View>
      ) : (
        <Text style={styles.noProfile}>{'No profile generated yet'}</Text>
      )}

      <View style={styles.insightRow}>
        <Text style={styles.insightLabel}>Focus area</Text>
        <Text style={styles.insightValue}>{weakestArea(student.latest_profile, labels)}</Text>
      </View>

      {topTopics.length > 0 && (
        <View style={styles.topicRow}>
          {topTopics.map(topic => (
            <View key={topic.topic} style={styles.topicChip}>
              <Text style={styles.topicText}>{topic.topic} {pct(topic.accuracy)}</Text>
            </View>
          ))}
        </View>
      )}

      <Text style={styles.lastActivity}>Last activity: {shortDate(student.last_activity_date)}</Text>

      <View style={styles.cardActions}>
        <TouchableOpacity style={styles.cardButtonPrimary} onPress={onProfile} activeOpacity={0.75}>
          <Text style={styles.cardButtonPrimaryText}>View profile</Text>
        </TouchableOpacity>
        <TouchableOpacity style={styles.cardButtonGhost} onPress={onHistory} activeOpacity={0.75}>
          <Text style={styles.cardButtonGhostText}>History</Text>
        </TouchableOpacity>
      </View>
    </Card>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  const { colors } = useAppTheme();
  const styles = createStyles(colors);
  return (
    <View style={styles.metricBox}>
      <Text style={styles.metricValue}>{value}</Text>
      <Text style={styles.metricLabel}>{label}</Text>
    </View>
  );
}

function ProfilePill({ label, level }: { label: string; level: string }) {
  const { colors } = useAppTheme();
  const styles = createStyles(colors);
  const color = levelColor(level, colors);
  return (
    <View style={[styles.profilePill, { borderColor: color }]}>
      <Text style={styles.profilePillLabel}>{label}</Text>
      <Text style={[styles.profilePillValue, { color }]}>{levelLabel(level)}</Text>
    </View>
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
  loadingText: { ...typography.subtitle, color: colors.textMuted },
  container: {
    padding: spacing.lg,
    paddingTop: spacing.md,
    gap: spacing.md,
    paddingBottom: spacing.xxl,
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  kicker: {
    ...typography.caption,
    color: colors.primaryDark,
    textTransform: 'uppercase',
  },
  title: {
    ...typography.title,
    color: colors.textWarm,
    marginTop: spacing.xs,
  },
  subtitle: {
    ...typography.body,
    color: colors.textMuted,
    marginTop: spacing.xs,
  },
  profileBubble: {
    width: 56,
    height: 56,
    borderRadius: 28,
    backgroundColor: colors.skyBlue,
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 3,
    borderColor: colors.surface,
  },
  profileBubbleText: {
    fontSize: 24,
    fontWeight: '900',
    color: colors.primaryDark,
  },
  summaryGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: spacing.md,
  },
  summaryTile: {
    width: '47%',
    backgroundColor: colors.surface,
    borderRadius: radius.lg,
    padding: spacing.md,
    borderWidth: 1,
    borderColor: colors.border,
    borderTopWidth: 5,
  },
  summaryValue: {
    fontSize: 28,
    fontWeight: '900',
  },
  summaryLabel: {
    ...typography.caption,
    color: colors.textMuted,
    marginTop: 2,
  },
  taskBand: {
    backgroundColor: colors.skyBlueSoft,
    borderRadius: radius.lg,
    padding: spacing.md,
    gap: spacing.sm,
    borderWidth: 1,
    borderColor: colors.skyBlue,
  },
  taskRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: spacing.sm,
  },
  taskButton: {
    paddingVertical: spacing.sm,
    paddingHorizontal: spacing.md,
    borderRadius: radius.pill,
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.border,
  },
  taskButtonActive: {
    backgroundColor: colors.primary,
    borderColor: colors.primary,
  },
  taskButtonText: {
    ...typography.caption,
    color: colors.textWarm,
  },
  taskButtonTextActive: {
    color: colors.textInverse,
  },
  sectionHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-end',
  },
  sectionTitle: {
    ...typography.subtitle,
    color: colors.textWarm,
  },
  sectionSubtitle: {
    ...typography.caption,
    color: colors.textMuted,
    marginTop: 2,
  },
  avgTime: {
    ...typography.caption,
    color: colors.primaryDark,
  },
  emptyCard: {
    gap: spacing.sm,
  },
  emptyTitle: {
    ...typography.subtitle,
    color: colors.textWarm,
  },
  emptyText: {
    ...typography.body,
    color: colors.textMuted,
  },
  studentCard: {
    gap: spacing.md,
  },
  studentCardAlert: {
    borderColor: '#F4D06F',
  },
  studentHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.md,
  },
  avatarCircle: {
    width: 48,
    height: 48,
    borderRadius: 24,
    backgroundColor: colors.warmYellowSoft,
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 2,
    borderColor: colors.warmYellow,
  },
  avatarText: {
    fontSize: 20,
    fontWeight: '900',
    color: colors.textWarm,
  },
  studentTitleBlock: {
    flex: 1,
  },
  studentName: {
    ...typography.subtitle,
    color: colors.textWarm,
  },
  studentMeta: {
    ...typography.small,
    color: colors.textMuted,
    marginTop: 2,
  },
  statusBadge: {
    paddingHorizontal: spacing.sm,
    paddingVertical: 5,
    borderRadius: radius.pill,
    backgroundColor: colors.successBg,
  },
  statusBadgeAlert: {
    backgroundColor: colors.warningBg,
  },
  statusText: {
    ...typography.small,
    color: colors.success,
  },
  statusTextAlert: {
    color: '#9A6B00',
  },
  accuracyBlock: {
    gap: spacing.xs,
  },
  accuracyHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
  },
  accuracyTrack: {
    height: 12,
    backgroundColor: colors.skyBlueSoft,
    borderRadius: radius.pill,
    overflow: 'hidden',
  },
  accuracyFill: {
    height: '100%',
    backgroundColor: colors.green,
    borderRadius: radius.pill,
  },
  metricsRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: spacing.sm,
  },
  metricBox: {
    width: '47%',
    padding: spacing.sm,
    borderRadius: radius.md,
    backgroundColor: colors.surfaceSoft,
    borderWidth: 1,
    borderColor: colors.borderLight,
  },
  metricValue: {
    ...typography.subtitle,
    color: colors.textWarm,
  },
  metricLabel: {
    ...typography.small,
    color: colors.textMuted,
    marginTop: 2,
  },
  profileGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: spacing.sm,
  },
  profilePill: {
    width: '47%',
    borderWidth: 1.5,
    borderRadius: radius.md,
    padding: spacing.sm,
    backgroundColor: colors.surface,
  },
  profilePillLabel: {
    ...typography.small,
    color: colors.textMuted,
  },
  profilePillValue: {
    ...typography.caption,
    marginTop: 2,
  },
  noProfile: {
    ...typography.caption,
    color: colors.textMuted,
    fontStyle: 'italic',
  },
  insightRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    gap: spacing.md,
    borderTopWidth: 1,
    borderTopColor: colors.borderLight,
    paddingTop: spacing.sm,
  },
  insightLabel: {
    ...typography.caption,
    color: colors.textMuted,
  },
  insightValue: {
    ...typography.caption,
    color: colors.textWarm,
    flex: 1,
    textAlign: 'right',
  },
  topicRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: spacing.sm,
  },
  topicChip: {
    backgroundColor: '#F2EDFF',
    borderRadius: radius.pill,
    paddingHorizontal: spacing.sm,
    paddingVertical: 5,
  },
  topicText: {
    ...typography.small,
    color: colors.purple,
  },
  lastActivity: {
    ...typography.small,
    color: colors.textMuted,
  },
  cardActions: {
    flexDirection: 'row',
    gap: spacing.sm,
  },
  cardButtonPrimary: {
    flex: 1,
    alignItems: 'center',
    paddingVertical: spacing.sm,
    borderRadius: radius.pill,
    backgroundColor: colors.primary,
  },
  cardButtonPrimaryText: {
    ...typography.caption,
    color: colors.textInverse,
  },
  cardButtonGhost: {
    flex: 1,
    alignItems: 'center',
    paddingVertical: spacing.sm,
    borderRadius: radius.pill,
    backgroundColor: colors.surface,
    borderWidth: 1.5,
    borderColor: colors.border,
  },
  cardButtonGhostText: {
    ...typography.caption,
    color: colors.textWarm,
  },
});
