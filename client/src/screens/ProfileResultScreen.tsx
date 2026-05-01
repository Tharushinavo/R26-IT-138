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
import LanguageToggle from '../components/LanguageToggle';
import { useLanguage } from '../i18n/LanguageContext';
import { colors, radius, spacing, typography } from '../theme';
import { api, type CognitiveProfile, type Level, type SpeedLevel } from '../api/client';

type Props = NativeStackScreenProps<RootStackParamList, 'ProfileResult'>;

const DIM_STYLE = {
  memory_level: { emoji: '🧠', color: colors.purple, bgColor: '#EDE9FE' },
  attention_level: { emoji: '🎯', color: colors.pink, bgColor: '#FCE7F3' },
  number_sense_level: { emoji: '🔢', color: colors.primary, bgColor: '#DBEAFE' },
  processing_speed_level: { emoji: '⚡', color: colors.teal, bgColor: '#D1FAE5' },
};

const LEVEL_STYLE: Record<string, { color: string; bgColor: string; emoji: string; width: string }> = {
  high: { color: colors.success, bgColor: colors.successBg, emoji: '🌟', width: '100%' },
  medium: { color: colors.primary, bgColor: '#DBEAFE', emoji: '👍', width: '60%' },
  low: { color: colors.warning, bgColor: colors.warningBg, emoji: '💪', width: '30%' },
  Fast: { color: colors.success, bgColor: colors.successBg, emoji: '🌟', width: '100%' },
  Moderate: { color: colors.primary, bgColor: '#DBEAFE', emoji: '👍', width: '60%' },
  Slow: { color: colors.warning, bgColor: colors.warningBg, emoji: '💪', width: '30%' },
};

export default function ProfileResultScreen({ route, navigation }: Props) {
  const { t } = useLanguage();
  const { studentId, sessionId } = route.params;

  const DIM_META = {
    memory_level: { title: t.profileResult.memoryTitle, blurb: t.profileResult.memoryBlurb, ...DIM_STYLE.memory_level },
    attention_level: { title: t.profileResult.attentionTitle, blurb: t.profileResult.attentionBlurb, ...DIM_STYLE.attention_level },
    number_sense_level: { title: t.profileResult.numberSenseTitle, blurb: t.profileResult.numberSenseBlurb, ...DIM_STYLE.number_sense_level },
    processing_speed_level: { title: t.profileResult.speedTitle, blurb: t.profileResult.speedBlurb, ...DIM_STYLE.processing_speed_level },
  };

  const levelLabel = (l: string) => {
    switch (l) {
      case 'high': return t.levels.levelHigh;
      case 'medium': return t.levels.levelMedium;
      case 'low': return t.levels.levelLow;
      case 'Fast': return t.levels.levelFast;
      case 'Moderate': return t.levels.levelModerate;
      case 'Slow': return t.levels.levelSlow;
      default: return l;
    }
  };
  const [profile, setProfile] = useState<CognitiveProfile | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const p = await api.getLatestProfile(studentId, sessionId);
      setProfile(p);
    } catch (e: any) {
      setError(e?.message ?? 'Could not load profile');
    } finally {
      setLoading(false);
    }
  }, [studentId, sessionId]);

  useEffect(() => { load(); }, [load]);

  if (loading) {
    return (
      <View style={styles.center}>
        <View style={styles.loadingCircle}>
          <ActivityIndicator size="large" color={colors.primary} />
        </View>
        <Text style={styles.loadingTitle}>{t.profileResult.analyzingBrain}</Text>
        <Text style={styles.loadingSubtitle}>{t.profileResult.wontTakeLong}</Text>
      </View>
    );
  }

  if (error || !profile) {
    return (
      <View style={styles.center}>
        <Text style={{ fontSize: 64, marginBottom: spacing.md }}>🤔</Text>
        <Text style={styles.emptyTitle}>{t.profileResult.noProfileYet}</Text>
        <Text style={styles.emptySubtitle}>
          {error ?? t.profileResult.playActivity}
        </Text>
        <PrimaryButton
          title={t.profileResult.startActivity}
          onPress={() => navigation.replace('MathActivity', { studentId })}
        />
      </View>
    );
  }

  return (
    <ScrollView
      contentContainerStyle={styles.container}
      refreshControl={<RefreshControl refreshing={loading} onRefresh={load} />}
    >
      <LanguageToggle />

      {/* Header Card */}
      <Card style={styles.headerCard}>
        <Text style={{ fontSize: 48, textAlign: 'center' }}>🏆</Text>
        <Text style={styles.heading}>{t.profileResult.cognitiveSkillProfile}</Text>
        <Text style={styles.headingSub}>
          {t.profileResult.basedOnQuestions
            .replace('{count}', String(profile.features.total_questions))
            .replace('{s}', profile.features.total_questions === 1 ? '' : 's')}
        </Text>
        <View style={styles.accuracyBadge}>
          <Text style={styles.accuracyText}>
            {Math.round(profile.features.accuracy * 100)}% {t.common.accuracy}
          </Text>
        </View>
        {profile.confidence_score != null && (
          <Text style={styles.confidenceText}>
            {t.common.confidence}: {Math.round(profile.confidence_score * 100)}%
          </Text>
        )}
      </Card>

      {/* Dimension Cards */}
      {(
        ['memory_level', 'attention_level', 'number_sense_level', 'processing_speed_level'] as const
      ).map((dim) => {
        const meta = DIM_META[dim];
        const levelValue = profile[dim] as string;
        return (
          <DimensionCard
            key={dim}
            title={meta.title}
            emoji={meta.emoji}
            blurb={meta.blurb}
            dimColor={meta.color}
            dimBgColor={meta.bgColor}
            level={levelValue}
            levelLabel={levelLabel(levelValue)}
          />
        );
      })}

      {/* Recommendation Card */}
      {profile.recommendation && (
        <Card style={styles.recommendCard}>
          <Text style={styles.recommendTitle}>{t.profileResult.recommendedSupport}</Text>
          <Text style={styles.recommendText}>{profile.recommendation}</Text>
        </Card>
      )}

      {/* Stats Card */}
      <Card style={styles.statsCard}>
        <Text style={styles.statsTitle}>{t.profileResult.detailedStats}</Text>
        <View style={styles.statsGrid}>
          <StatBox
            emoji="⏱️"
            label={t.profileResult.avgTime}
            value={`${Math.round(profile.features.avg_response_time_ms)}ms`}
          />
          <StatBox
            emoji="🔄"
            label={t.profileResult.retryRate}
            value={pct(profile.features.retry_rate)}
          />
          <StatBox
            emoji="💡"
            label={t.profileResult.hintRate}
            value={profile.features.hint_rate.toFixed(2)}
          />
          <StatBox
            emoji="✏️"
            label={t.profileResult.interactionsLabel}
            value={String(profile.features.total_questions)}
          />
        </View>
      </Card>

      {/* Model info */}
      {profile.model_version && (
        <Text style={styles.modelInfo}>{t.common.model}: {profile.model_version}</Text>
      )}

      {/* Actions */}
      <View style={styles.actionGroup}>
        <PrimaryButton
          title={t.profileResult.playAgain}
          onPress={() => navigation.replace('MathActivity', { studentId })}
        />
        <PrimaryButton
          title={t.profileResult.viewHistory}
          onPress={() => navigation.navigate('ProfileHistory', { studentId })}
          variant="ghost"
        />
        <PrimaryButton
          title={t.profileResult.backToDashboard}
          variant="ghost"
          onPress={() => navigation.navigate('StudentDashboard', { studentId })}
        />
      </View>
    </ScrollView>
  );
}

function DimensionCard({
  title, emoji, blurb, dimColor, dimBgColor, level, levelLabel,
}: {
  title: string; emoji: string; blurb: string;
  dimColor: string; dimBgColor: string; level: string; levelLabel: string;
}) {
  const levelConf = LEVEL_STYLE[level] ?? LEVEL_STYLE['medium'];
  return (
    <Card style={styles.dimCard}>
      <View style={styles.dimHeader}>
        <View style={[styles.dimIconCircle, { backgroundColor: dimBgColor }]}>
          <Text style={{ fontSize: 28 }}>{emoji}</Text>
        </View>
        <View style={{ flex: 1 }}>
          <Text style={[typography.subtitle, { color: colors.textWarm }]}>{title}</Text>
          <Text style={[typography.caption, { color: colors.textMuted, marginTop: 2 }]}>{blurb}</Text>
        </View>
      </View>
      <View style={styles.levelRow}>
        <View style={styles.levelBarBg}>
          <View
            style={[
              styles.levelBarFill,
              { backgroundColor: levelConf.color, width: levelConf.width as any },
            ]}
          />
        </View>
        <View style={[styles.levelBadge, { backgroundColor: levelConf.bgColor }]}>
          <Text style={[styles.levelBadgeText, { color: levelConf.color }]}>
            {levelConf.emoji} {levelLabel}
          </Text>
        </View>
      </View>
    </Card>
  );
}

function StatBox({ emoji, label, value }: { emoji: string; label: string; value: string }) {
  return (
    <View style={styles.statBox}>
      <Text style={{ fontSize: 22 }}>{emoji}</Text>
      <Text style={styles.statValue}>{value}</Text>
      <Text style={styles.statLabel}>{label}</Text>
    </View>
  );
}

function pct(v: number) {
  return `${Math.round(v * 100)}%`;
}

const styles = StyleSheet.create({
  container: { padding: spacing.lg, paddingTop: spacing.md, gap: spacing.md, paddingBottom: spacing.xxl },
  center: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    padding: spacing.xl,
  },
  loadingCircle: {
    width: 80, height: 80, borderRadius: 40,
    backgroundColor: colors.skyBlueSoft,
    alignItems: 'center', justifyContent: 'center',
    marginBottom: spacing.lg,
  },
  loadingTitle: { ...typography.title, color: colors.textWarm, marginBottom: spacing.xs },
  loadingSubtitle: { ...typography.body, color: colors.textMuted },
  emptyTitle: { ...typography.title, color: colors.textWarm, textAlign: 'center', marginBottom: spacing.sm },
  emptySubtitle: { ...typography.body, color: colors.textMuted, textAlign: 'center', marginBottom: spacing.lg, maxWidth: 280 },
  headerCard: { gap: spacing.sm, alignItems: 'center', paddingVertical: spacing.xl },
  heading: { ...typography.title, color: colors.textWarm, textAlign: 'center' },
  headingSub: { ...typography.body, color: colors.textMuted, textAlign: 'center' },
  accuracyBadge: {
    backgroundColor: colors.successBg,
    paddingHorizontal: spacing.lg, paddingVertical: spacing.sm,
    borderRadius: radius.pill, marginTop: spacing.xs,
  },
  accuracyText: { ...typography.subtitle, color: colors.success },
  confidenceText: { ...typography.caption, color: colors.textMuted, marginTop: 4 },
  dimCard: { gap: spacing.md, paddingVertical: spacing.lg },
  dimHeader: { flexDirection: 'row', alignItems: 'center', gap: spacing.md },
  dimIconCircle: { width: 52, height: 52, borderRadius: 26, alignItems: 'center', justifyContent: 'center' },
  levelRow: { flexDirection: 'row', alignItems: 'center', gap: spacing.md },
  levelBarBg: { flex: 1, height: 10, backgroundColor: colors.skyBlueSoft, borderRadius: radius.pill, overflow: 'hidden' },
  levelBarFill: { height: '100%', borderRadius: radius.pill },
  levelBadge: { paddingHorizontal: spacing.md, paddingVertical: 6, borderRadius: radius.pill },
  levelBadgeText: { fontWeight: '800', fontSize: 11, letterSpacing: 0.8 },
  recommendCard: { gap: spacing.sm },
  recommendTitle: { ...typography.subtitle, color: colors.textWarm },
  recommendText: { ...typography.body, color: colors.text, lineHeight: 24 },
  statsCard: { gap: spacing.md },
  statsTitle: { ...typography.title, color: colors.textWarm },
  statsGrid: { flexDirection: 'row', flexWrap: 'wrap', gap: spacing.md },
  statBox: {
    width: '46%', backgroundColor: colors.skyBlueSoft, borderRadius: radius.lg,
    padding: spacing.md, alignItems: 'center', gap: 4,
  },
  statValue: { ...typography.subtitle, color: colors.textWarm },
  statLabel: { ...typography.caption, color: colors.textMuted },
  modelInfo: { ...typography.small, color: colors.textMuted, textAlign: 'center' },
  actionGroup: { gap: spacing.md, marginTop: spacing.sm },
});
