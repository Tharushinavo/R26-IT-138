import React, { useCallback, useEffect, useRef, useState } from 'react';
import {
  ActivityIndicator,
  Animated,
  RefreshControl,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from 'react-native';
import type { CompdScreenProps } from '@/src/features/compd/navigation';
import Card from '@/src/features/compd/components/card';
import PrimaryButton from '@/src/features/compd/components/primary-button';
import ProfileControls from '@/src/features/compd/components/profile-controls';
import BrainPowerCircle from '@/src/features/compd/components/brain-power-circle';
import StarRating from '@/src/features/compd/components/star-rating';
import { useLanguage } from '@/src/features/compd/i18n/language-context';
import { radius, spacing, typography, useAppTheme } from '@/src/features/compd/theme';
import type { CognitiveProfile } from '@/src/features/compd/compd-legacy-client';
import { useCompdApi } from '@/src/features/compd/use-compd-api';
import { ApiClientError } from '@/src/api/errors';

type Props = CompdScreenProps;

// ── Kid-friendly level helpers ──

type DimLevel = 'low' | 'medium' | 'high' | 'Slow' | 'Moderate' | 'Fast';

function kidLabel(level: DimLevel): { emoji: string; label: string; message: string } {
  switch (level) {
    case 'high':
    case 'Fast':
      return { emoji: '🌟', label: 'Superstar', message: "You're amazing at this!" };
    case 'medium':
    case 'Moderate':
      return { emoji: '🌿', label: 'Blooming', message: 'Growing stronger every day!' };
    case 'low':
    case 'Slow':
      return { emoji: '🌱', label: 'Growing', message: "Keep practising — you've got this!" };
    default:
      return { emoji: '🌿', label: 'Blooming', message: 'Growing stronger every day!' };
  }
}

function levelColor(level: DimLevel, colors: any): string {
  switch (level) {
    case 'high':
    case 'Fast':
      return colors.success;
    case 'medium':
    case 'Moderate':
      return colors.primary;
    case 'low':
    case 'Slow':
      return colors.warning;
    default:
      return colors.primary;
  }
}

function levelBgColor(level: DimLevel, colors: any): string {
  switch (level) {
    case 'high':
    case 'Fast':
      return colors.successBg;
    case 'medium':
    case 'Moderate':
      return colors.skyBlueSoft;
    case 'low':
    case 'Slow':
      return colors.warningBg;
    default:
      return colors.skyBlueSoft;
  }
}

function levelBarWidth(level: DimLevel): string {
  switch (level) {
    case 'high':
    case 'Fast':
      return '100%';
    case 'medium':
    case 'Moderate':
      return '60%';
    case 'low':
    case 'Slow':
      return '30%';
    default:
      return '60%';
  }
}

export default function ProfileResultScreen({ route, navigation }: Props) {
  const { lang, t } = useLanguage();
  const { call } = useCompdApi();
  const { colors } = useAppTheme();
  const styles = createStyles(colors);
  const { sessionId } = route.params;
  // compD's teacher view (its own teacher login) is not part of the learner app; teachers come
  // through MathMingo's own teacher side in a later phase (plan v5 Phase 7).

  const DIM_META = {
    memory_level: {
      title: t.profileResult.memoryTitle,
      blurb: t.profileResult.memoryBlurb,
      emoji: '🧠',
      dimColor: colors.purple,
      gradient: ['#E8DAFF', '#F3ECFF'],
    },
    attention_level: {
      title: t.profileResult.attentionTitle,
      blurb: t.profileResult.attentionBlurb,
      emoji: '🎯',
      dimColor: colors.pink,
      gradient: ['#FFE0F0', '#FFF0F7'],
    },
    number_sense_level: {
      title: t.profileResult.numberSenseTitle,
      blurb: t.profileResult.numberSenseBlurb,
      emoji: '🔢',
      dimColor: colors.primary,
      gradient: ['#D6ECFF', '#EAF4FF'],
    },
    processing_speed_level: {
      title: t.profileResult.speedTitle,
      blurb: t.profileResult.speedBlurb,
      emoji: '⚡',
      dimColor: colors.teal,
      gradient: ['#D1FAE5', '#ECFDF5'],
    },
  };

  const [profile, setProfile] = useState<CognitiveProfile | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Arriving from a finished quiz carries that run's `sessionId`, so the page shows exactly that
  // profile; opened from compD's home it shows the latest. Re-read when the language changes: the
  // server writes the recommendation in the language it is asked for.
  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      if (sessionId) {
        const response = await call((api, accessToken) => api.getSessionProfile(sessionId, lang, accessToken));
        setProfile(response.profile);
      } else {
        const latest = await call((api, accessToken) => api.getLatestProfile(lang, accessToken));
        setProfile(latest.profile);
      }
    } catch (e: unknown) {
      setProfile(null);
      // A session that is not (or not yet) this learner's reads as "no profile", like none at all.
      const notFound = e instanceof ApiClientError && e.status === 404;
      if (!notFound) {
        setError(lang === 'si' ? 'පැතිකඩ පූරණය කළ නොහැකි විය. නැවත උත්සාහ කරන්න.' : 'We could not load your profile. Pull down to try again.');
      }
    } finally {
      setLoading(false);
    }
  }, [call, lang, sessionId]);

  useEffect(() => { load(); }, [load]);

  if (loading) {
    return (
      <View style={[styles.center, { backgroundColor: colors.background }]}>
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
      <View style={[styles.center, { backgroundColor: colors.background }]}>
        <Text style={{ fontSize: 64, marginBottom: spacing.md }}>🤔</Text>
        <Text style={styles.emptyTitle}>{t.profileResult.noProfileYet}</Text>
        <Text style={styles.emptySubtitle}>
          {error ?? t.profileResult.playActivity}
        </Text>
        <PrimaryButton
          title={t.profileResult.startActivity}
          onPress={() => navigation.replace('MathActivity')}
        />
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

      {/* ── Brain Power Score Circle ── */}
      <View style={styles.powerSection}>
        <BrainPowerCircle
          memory={profile.memory_level}
          attention={profile.attention_level}
          numberSense={profile.number_sense_level}
          speed={profile.processing_speed_level}
          size={170}
          delay={200}
        />
      </View>

      {/* ── Header Card ── */}
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
            {Math.round(profile.features.accuracy * 100)}% {t.common.correctness}
          </Text>
        </View>
      </Card>

      {/* ── Dimension Cards with Stars ── */}
      {(
        ['memory_level', 'attention_level', 'number_sense_level', 'processing_speed_level'] as const
      ).map((dim, idx) => {
        const meta = DIM_META[dim];
        const levelValue = profile[dim] as DimLevel;
        const kid = kidLabel(levelValue);
        const dimLevelColor = levelColor(levelValue, colors);
        const dimLevelBg = levelBgColor(levelValue, colors);

        return (
          <AnimatedDimensionCard
            key={dim}
            index={idx}
            title={meta.title}
            emoji={meta.emoji}
            blurb={meta.blurb}
            dimColor={meta.dimColor}
            level={levelValue}
            levelLabel={kid.label}
            levelEmoji={kid.emoji}
            levelMessage={kid.message}
            levelColor={dimLevelColor}
            levelBg={dimLevelBg}
            barWidth={levelBarWidth(levelValue)}
          />
        );
      })}

      {/* ── Recommendation Card ── */}
      {profile.recommendation && (
        <Card style={styles.recommendCard}>
          <View style={styles.recommendHeader}>
            <Text style={{ fontSize: 32 }}>👩‍🏫</Text>
            <Text style={styles.recommendTitle}>{t.profileResult.recommendedSupport}</Text>
          </View>
          <View style={styles.speechBubble}>
            <Text style={styles.recommendText}>{profile.recommendation}</Text>
            <View style={styles.speechTriangle} />
          </View>
        </Card>
      )}

      {/* ── Stats Card ── */}
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
          onPress={() => navigation.replace('MathActivity')}
        />

        {/* ── Start Learning Path CTA ── */}
        {/* Goes to MathMingo's own Home, which is the real learning path (compD showed a picture). */}
        <View style={styles.learningPathCTA}>
          <View style={styles.learningPathInner}>
            <View style={styles.learningPathIcon}>
              <Text style={{ fontSize: 28 }}>📚</Text>
            </View>
            <View style={{ flex: 1 }}>
              <Text style={styles.learningPathTitle}>{t.learningPath.startLearningPath}</Text>
              <Text style={styles.learningPathSub}>
                {t.learningPath.heroTitle.replace('\n', ' ')}
              </Text>
            </View>
          </View>
          <PrimaryButton
            title={t.learningPath.continueAdventure + ' ›'}
            onPress={() => navigation.navigate('LearningPath')}
          />
        </View>

        <PrimaryButton
          title={t.profileResult.viewHistory}
          onPress={() => navigation.navigate('ProfileHistory')}
          variant="ghost"
        />
        <PrimaryButton
          title={t.profileResult.backToDashboard}
          variant="ghost"
          onPress={() => navigation.goBack()}
        />
      </View>
    </ScrollView>
    </View>
  );
}

// ── Animated Dimension Card ──

function AnimatedDimensionCard({
  index,
  title,
  emoji,
  blurb,
  dimColor,
  level,
  levelLabel,
  levelEmoji,
  levelMessage,
  levelColor: lColor,
  levelBg,
  barWidth,
}: {
  index: number;
  title: string;
  emoji: string;
  blurb: string;
  dimColor: string;
  level: DimLevel;
  levelLabel: string;
  levelEmoji: string;
  levelMessage: string;
  levelColor: string;
  levelBg: string;
  barWidth: string;
}) {
  const { colors } = useAppTheme();
  const styles = createStyles(colors);
  const slideAnim = useRef(new Animated.Value(50)).current;
  const fadeAnim = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    const delay = 600 + index * 150;
    setTimeout(() => {
      Animated.parallel([
        Animated.spring(slideAnim, {
          toValue: 0,
          friction: 6,
          tension: 60,
          useNativeDriver: true,
        }),
        Animated.timing(fadeAnim, {
          toValue: 1,
          duration: 400,
          useNativeDriver: true,
        }),
      ]).start();
    }, delay);
  }, [index, slideAnim, fadeAnim]);

  return (
    <Animated.View
      style={{
        transform: [{ translateY: slideAnim }],
        opacity: fadeAnim,
      }}
    >
      <Card style={[styles.dimCard, { borderLeftWidth: 4, borderLeftColor: dimColor }]}>
        {/* Header row */}
        <View style={styles.dimHeader}>
          <View style={[styles.dimIconCircle, { backgroundColor: levelBg }]}>
            <Text style={{ fontSize: 28 }}>{emoji}</Text>
          </View>
          <View style={{ flex: 1 }}>
            <Text style={[typography.subtitle, { color: colors.textWarm }]}>{title}</Text>
            <Text style={[typography.caption, { color: colors.textMuted, marginTop: 2 }]}>{blurb}</Text>
          </View>
          {/* Star Rating */}
          <StarRating level={level} starSize={18} delay={800 + index * 150} />
        </View>

        {/* Progress bar */}
        <View style={styles.levelRow}>
          <View style={styles.levelBarBg}>
            <View
              style={[
                styles.levelBarFill,
                { backgroundColor: lColor, width: barWidth as any },
              ]}
            />
          </View>
        </View>

        {/* Kid-friendly label + message */}
        <View style={styles.kidLabelRow}>
          <View style={[styles.levelBadge, { backgroundColor: levelBg }]}>
            <Text style={[styles.levelBadgeText, { color: lColor }]}>
              {levelEmoji} {levelLabel}
            </Text>
          </View>
          <Text style={[styles.levelMessage, { color: colors.textMuted }]}>
            {levelMessage}
          </Text>
        </View>
      </Card>
    </Animated.View>
  );
}

function StatBox({ emoji, label, value }: { emoji: string; label: string; value: string }) {
  const { colors } = useAppTheme();
  const styles = createStyles(colors);
  const scaleAnim = useRef(new Animated.Value(0.8)).current;

  useEffect(() => {
    Animated.spring(scaleAnim, {
      toValue: 1,
      friction: 5,
      tension: 80,
      delay: 400,
      useNativeDriver: true,
    }).start();
  }, [scaleAnim]);

  return (
    <Animated.View style={[styles.statBox, { transform: [{ scale: scaleAnim }] }]}>
      <Text style={{ fontSize: 22 }}>{emoji}</Text>
      <Text style={styles.statValue}>{value}</Text>
      <Text style={styles.statLabel}>{label}</Text>
    </Animated.View>
  );
}

function pct(v: number) {
  return `${Math.round(v * 100)}%`;
}

const createStyles = (colors: ReturnType<typeof useAppTheme>['colors']) => StyleSheet.create({
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

  // Power section
  powerSection: {
    alignItems: 'center',
    paddingVertical: spacing.md,
  },

  // Header
  headerCard: {
    gap: spacing.sm,
    alignItems: 'center',
    paddingVertical: spacing.xl,
    backgroundColor: colors.surface,
    borderRadius: radius.xl,
    shadowColor: colors.primaryDark,
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.1,
    shadowRadius: 12,
    elevation: 4,
  },
  heading: { ...typography.title, fontSize: 26, color: colors.textWarm, textAlign: 'center' },
  headingSub: { ...typography.body, color: colors.textMuted, textAlign: 'center' },
  accuracyBadge: {
    backgroundColor: colors.successBg,
    paddingHorizontal: spacing.lg, paddingVertical: spacing.sm,
    borderRadius: radius.pill, marginTop: spacing.md,
    borderWidth: 1, borderColor: colors.success + '40',
  },
  accuracyText: { ...typography.subtitle, color: colors.success, fontSize: 18 },

  // Dimension cards
  dimCard: {
    gap: spacing.md,
    paddingVertical: spacing.lg,
    borderRadius: radius.lg,
    borderWidth: 1,
    borderColor: colors.border + '50',
  },
  dimHeader: { flexDirection: 'row', alignItems: 'center', gap: spacing.md },
  dimIconCircle: {
    width: 56, height: 56, borderRadius: 28,
    alignItems: 'center', justifyContent: 'center',
    shadowColor: '#000', shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.05, shadowRadius: 4, elevation: 2,
  },
  levelRow: { gap: spacing.sm },
  levelBarBg: {
    height: 14,
    backgroundColor: colors.skyBlueSoft,
    borderRadius: radius.pill,
    overflow: 'hidden',
  },
  levelBarFill: { height: '100%', borderRadius: radius.pill },
  kidLabelRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.md,
  },
  levelBadge: {
    paddingHorizontal: spacing.md,
    paddingVertical: 8,
    borderRadius: radius.pill,
    borderWidth: 1,
    borderColor: 'rgba(0,0,0,0.05)',
  },
  levelBadgeText: { fontWeight: '800', fontSize: 12, letterSpacing: 0.8 },
  levelMessage: {
    ...typography.caption,
    fontSize: 11,
    fontStyle: 'italic',
    flex: 1,
  },

  // Recommend
  recommendCard: {
    gap: spacing.md,
    backgroundColor: colors.skyBlueSoft,
    borderColor: colors.primary + '30',
    borderWidth: 1,
  },
  recommendHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.sm,
  },
  recommendTitle: { ...typography.subtitle, color: colors.primaryDark, fontSize: 18 },
  speechBubble: {
    backgroundColor: colors.surface,
    padding: spacing.md,
    borderRadius: radius.lg,
    borderWidth: 1,
    borderColor: colors.border,
    position: 'relative',
  },
  speechTriangle: {
    position: 'absolute',
    top: -8,
    left: 40,
    width: 0,
    height: 0,
    borderLeftWidth: 8,
    borderRightWidth: 8,
    borderBottomWidth: 8,
    borderLeftColor: 'transparent',
    borderRightColor: 'transparent',
    borderBottomColor: colors.surface,
  },
  recommendText: { ...typography.body, color: colors.text, lineHeight: 26 },

  // Stats
  statsCard: { gap: spacing.md, backgroundColor: colors.surfaceSoft },
  statsTitle: { ...typography.title, color: colors.textWarm, fontSize: 20 },
  statsGrid: { flexDirection: 'row', flexWrap: 'wrap', gap: spacing.md },
  statBox: {
    width: '47%', backgroundColor: colors.surface, borderRadius: radius.lg,
    padding: spacing.md, alignItems: 'center', gap: 6,
    shadowColor: '#000', shadowOffset: { width: 0, height: 1 }, shadowOpacity: 0.05, shadowRadius: 3, elevation: 1,
  },
  statValue: { ...typography.title, fontSize: 22, color: colors.primaryDark },
  statLabel: { ...typography.caption, color: colors.textMuted, textTransform: 'uppercase', fontSize: 10, letterSpacing: 0.5 },
  modelInfo: { ...typography.small, color: colors.textMuted, textAlign: 'center', marginTop: spacing.sm },
  actionGroup: { gap: spacing.md, marginTop: spacing.sm },

  // Learning Path CTA
  learningPathCTA: {
    backgroundColor: colors.surfaceSoft,
    borderRadius: radius.xl,
    padding: spacing.md,
    gap: spacing.md,
    borderWidth: 2,
    borderColor: colors.warmYellow,
    shadowColor: colors.warmYellow,
    shadowOffset: { width: 0, height: 3 },
    shadowOpacity: 0.2,
    shadowRadius: 6,
    elevation: 3,
  },
  learningPathInner: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.md,
  },
  learningPathIcon: {
    width: 48,
    height: 48,
    borderRadius: 24,
    backgroundColor: colors.surface,
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 1.5,
    borderColor: colors.warmYellow,
  },
  learningPathTitle: {
    ...typography.subtitle,
    color: colors.textWarm,
    fontSize: 16,
  },
  learningPathSub: {
    ...typography.caption,
    color: colors.textMuted,
    marginTop: 2,
  },
});
