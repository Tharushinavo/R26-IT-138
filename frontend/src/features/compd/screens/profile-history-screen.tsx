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
import { useLanguage } from '@/src/features/compd/i18n/language-context';
import { radius, spacing, typography, useAppTheme } from '@/src/features/compd/theme';
import type { CognitiveProfile } from '@/src/features/compd/compd-legacy-client';
import { useCompdApi } from '@/src/features/compd/use-compd-api';

type Props = CompdScreenProps;


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

const levelToScore = (l: string): number => {
  switch (l) {
    case 'high': case 'Fast': return 100;
    case 'medium': case 'Moderate': return 60;
    case 'low': case 'Slow': return 30;
    default: return 50;
  }
};

function calcBrainPower(p: CognitiveProfile): number {
  return Math.round(
    (levelToScore(p.memory_level) + levelToScore(p.attention_level) +
     levelToScore(p.number_sense_level) + levelToScore(p.processing_speed_level)) / 4,
  );
}

const kidEmoji = (l: string): string => {
  switch (l) {
    case 'high': case 'Fast': return '🌟';
    case 'medium': case 'Moderate': return '🌿';
    case 'low': case 'Slow': return '🌱';
    default: return '🌿';
  }
};

// How many past profiles the page asks for; the contract allows 1-100.
const HISTORY_LIMIT = 20;

export default function ProfileHistoryScreen({ navigation }: Props) {
  const { lang, t } = useLanguage();
  const { call } = useCompdApi();
  const { colors } = useAppTheme();
  const styles = createStyles(colors);
  // compD's teacher view (its own teacher login) is not part of the learner app; teachers come
  // through MathMingo's own teacher side in a later phase (plan v5 Phase 7).
  const [profiles, setProfiles] = useState<CognitiveProfile[]>([]);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      // Newest first, with each recommendation written in the language the child has chosen now.
      const history = await call((api, accessToken) => api.listProfiles(HISTORY_LIMIT, lang, accessToken));
      setProfiles(history.items);
    } catch {
      setProfiles([]);
    } finally {
      setLoading(false);
    }
  }, [call, lang]);

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
          {t.history.completeActivities}
        </Text>
        <PrimaryButton
          title={t.history.startActivity}
          onPress={() => navigation.navigate('MathActivity')}
        />
      </View>
    );
  }

  // Find personal best
  const brainPowers = profiles.map(calcBrainPower);
  const bestIndex = brainPowers.indexOf(Math.max(...brainPowers));

  const LevelChip = ({ level }: { level: string }) => (
    <View style={[styles.chip, { backgroundColor: levelBg(level, colors), borderColor: levelColor(level, colors) + '60' }]}>
      <Text style={[styles.chipText, { color: levelColor(level, colors) }]}>
        {kidEmoji(level)} {levelWord(level, t)}
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

      {/* ── Timeline Cards ── */}
      {profiles.map((p, idx) => {
        const isBest = idx === bestIndex;
        const bp = brainPowers[idx];
        return (
          <TimelineCard
            key={`timeline-${idx}`}
            profile={p}
            index={idx}
            isBest={isBest}
            brainPower={bp}
            t={t}
            LevelChip={LevelChip}
          />
        );
      })}

      {/* ── Kid-Friendly Legend ── */}
      <Card style={styles.legendCard}>
        <Text style={styles.legendTitle}>{t.history.legend}</Text>
        <View style={styles.legendGrid}>
          <View style={[styles.legendItem, { backgroundColor: colors.successBg, borderColor: colors.success + '50' }]}>
            <Text style={{ fontSize: 18 }}>🌟</Text>
            <View>
              <Text style={[styles.legendLevel, { color: colors.success }]}>{t.history.legendHigh}</Text>
              <Text style={styles.legendSub}>{t.history.legendHighSub}</Text>
            </View>
          </View>
          <View style={[styles.legendItem, { backgroundColor: colors.skyBlueSoft, borderColor: colors.primary + '50' }]}>
            <Text style={{ fontSize: 18 }}>🌿</Text>
            <View>
              <Text style={[styles.legendLevel, { color: colors.primary }]}>{t.history.legendMedium}</Text>
              <Text style={styles.legendSub}>{t.history.legendMediumSub}</Text>
            </View>
          </View>
          <View style={[styles.legendItem, { backgroundColor: colors.warningBg, borderColor: colors.warning + '50' }]}>
            <Text style={{ fontSize: 18 }}>🌱</Text>
            <View>
              <Text style={[styles.legendLevel, { color: colors.warning }]}>{t.history.legendLow}</Text>
              <Text style={styles.legendSub}>{t.history.legendLowSub}</Text>
            </View>
          </View>
        </View>
      </Card>
      <PrimaryButton
        title={t.history.backToDashboard}
        variant="ghost"
        onPress={() => navigation.goBack()}
      />
    </ScrollView>
    </View>
  );
}

// ── Animated Timeline Card ──
function TimelineCard({
  profile,
  index,
  isBest,
  brainPower,
  t,
  LevelChip,
}: {
  profile: CognitiveProfile;
  index: number;
  isBest: boolean;
  brainPower: number;
  t: any;
  LevelChip: React.FC<{ level: string }>;
}) {
  const { colors } = useAppTheme();
  const styles = createStyles(colors);
  const slideAnim = useRef(new Animated.Value(30)).current;
  const fadeAnim = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    setTimeout(() => {
      Animated.parallel([
        Animated.spring(slideAnim, { toValue: 0, friction: 7, tension: 50, useNativeDriver: true }),
        Animated.timing(fadeAnim, { toValue: 1, duration: 350, useNativeDriver: true }),
      ]).start();
    }, 200 + index * 100);
  }, [index, slideAnim, fadeAnim]);

  const date = new Date(profile.generated_at);

  return (
    <Animated.View
      style={{
        transform: [{ translateY: slideAnim }],
        opacity: fadeAnim,
      }}
    >
      <Card
        style={[
          styles.detailCard,
          isBest && {
            borderColor: colors.warmYellow,
            borderWidth: 2,
            shadowColor: 'rgba(255, 180, 0, 0.4)',
            shadowOffset: { width: 0, height: 4 },
            shadowOpacity: 1,
            shadowRadius: 12,
            elevation: 6,
          },
        ]}
      >
        {/* Personal Best Ribbon */}
        {isBest && (
          <View style={styles.bestRibbon}>
            <Text style={styles.bestRibbonText}>{t.gamification.personalBest} 🏆</Text>
          </View>
        )}

        {/* Date + Brain Power */}
        <View style={styles.detailHeader}>
          <View>
            <Text style={styles.detailDate}>
              {date.toLocaleDateString()} – {date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
            </Text>
          </View>
          <View style={[styles.bpBadge, { backgroundColor: brainPower >= 65 ? colors.successBg : brainPower >= 45 ? colors.skyBlueSoft : colors.warningBg }]}>
            <Text style={[styles.bpText, { color: brainPower >= 65 ? colors.success : brainPower >= 45 ? colors.primary : colors.warning }]}>
              🧠 {brainPower}%
            </Text>
          </View>
        </View>

        {/* Level Chips */}
        <View style={styles.chipRow}>
          <View style={styles.chipGroup}>
            <Text style={styles.chipLabel}>{t.common.memory}</Text>
            <LevelChip level={profile.memory_level} />
          </View>
          <View style={styles.chipGroup}>
            <Text style={styles.chipLabel}>{t.common.attention}</Text>
            <LevelChip level={profile.attention_level} />
          </View>
          <View style={styles.chipGroup}>
            <Text style={styles.chipLabel}>{t.common.numberSense}</Text>
            <LevelChip level={profile.number_sense_level} />
          </View>
          <View style={styles.chipGroup}>
            <Text style={styles.chipLabel}>{t.common.speed}</Text>
            <LevelChip level={profile.processing_speed_level} />
          </View>
        </View>
        <Text style={styles.detailAccuracy}>
          {t.common.correctness}: {Math.round(profile.features.accuracy * 100)}% | {t.common.questions}: {profile.features.total_questions}
        </Text>
      </Card>
    </Animated.View>
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

  // Trend Card
  trendCard: { gap: spacing.md },
  trendTitle: {
    ...typography.subtitle,
    color: colors.textWarm,
    fontSize: 18,
  },
  trendGrid: { gap: spacing.md },
  trendRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.sm,
  },
  trendEmoji: { fontSize: 18, width: 24, textAlign: 'center' },
  trendLabel: {
    ...typography.caption,
    color: colors.textWarm,
    fontWeight: '700',
    width: 65,
    fontSize: 10,
  },
  trendBars: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'flex-end',
    gap: 3,
    height: 40,
    backgroundColor: colors.surfaceSoft,
    borderRadius: radius.sm,
    padding: 2,
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
  legendLevel: { ...typography.caption, fontWeight: '800' },
  legendSub: { ...typography.small, color: colors.textMuted },

  // Detail Cards
  detailCard: { gap: spacing.sm, position: 'relative', overflow: 'visible' },
  bestRibbon: {
    position: 'absolute',
    top: -10,
    right: spacing.md,
    backgroundColor: colors.warmYellow,
    paddingHorizontal: spacing.md,
    paddingVertical: 4,
    borderRadius: radius.pill,
    shadowColor: 'rgba(255, 180, 0, 0.5)',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 1,
    shadowRadius: 4,
    elevation: 3,
    zIndex: 10,
  },
  bestRibbonText: {
    fontSize: 11,
    fontWeight: '900',
    color: '#5D3E00',
    letterSpacing: 0.5,
  },
  detailHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  detailDate: { ...typography.caption, color: colors.primaryDark, fontWeight: '700' },
  bpBadge: {
    paddingHorizontal: spacing.md,
    paddingVertical: 4,
    borderRadius: radius.pill,
  },
  bpText: {
    fontSize: 12,
    fontWeight: '800',
  },
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
