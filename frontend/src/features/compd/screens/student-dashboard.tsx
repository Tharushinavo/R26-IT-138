import React, { useCallback, useEffect, useRef, useState } from 'react';
import {
  Animated,
  StyleSheet,
  Text,
  View,
  ScrollView,
  RefreshControl,
} from 'react-native';
import PrimaryButton from '@/src/features/compd/components/primary-button';
import Card from '@/src/features/compd/components/card';
import BrainPowerCircle from '@/src/features/compd/components/brain-power-circle';
import AnimalMascot from '@/src/features/compd/components/animal-mascot';
import { useLanguage } from '@/src/features/compd/i18n/language-context';
import { useAuth } from '@/src/features/compd/compd-auth';
import { colors as lightColors, radius, spacing, typography, useAppTheme } from '@/src/features/compd/theme';
import type { CognitiveProfile } from '@/src/features/compd/compd-legacy-client';
import type { CompdScreenProps } from '@/src/features/compd/navigation';
import { useCompdApi } from '@/src/features/compd/use-compd-api';

export default function StudentDashboard({ navigation }: CompdScreenProps) {
  const { lang, t } = useLanguage();
  const { user } = useAuth();
  const { call } = useCompdApi();
  const { colors, isDark } = useAppTheme();
  const styles = createStyles(colors);
  const name = user?.full_name || '';
  const [profile, setProfile] = useState<CognitiveProfile | null>(null);
  const [refreshing, setRefreshing] = useState(false);

  // Animations
  const greetScale = useRef(new Animated.Value(0.7)).current;
  const greetOpacity = useRef(new Animated.Value(0)).current;
  const cardSlide = useRef(new Animated.Value(40)).current;
  const cardFade = useRef(new Animated.Value(0)).current;
  const ctaScale = useRef(new Animated.Value(0.9)).current;
  const ctaPulse = useRef(new Animated.Value(1)).current;
  const mascotBounce = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    // Greeting entrance
    Animated.parallel([
      Animated.spring(greetScale, { toValue: 1, friction: 5, tension: 60, useNativeDriver: true }),
      Animated.timing(greetOpacity, { toValue: 1, duration: 500, useNativeDriver: true }),
    ]).start();

    const timers: ReturnType<typeof setTimeout>[] = [];
    // Card entrance (delayed)
    timers.push(setTimeout(() => {
      Animated.parallel([
        Animated.spring(cardSlide, { toValue: 0, friction: 6, tension: 50, useNativeDriver: true }),
        Animated.timing(cardFade, { toValue: 1, duration: 400, useNativeDriver: true }),
      ]).start();
    }, 300));

    // CTA button entrance
    timers.push(setTimeout(() => {
      Animated.spring(ctaScale, { toValue: 1, friction: 5, tension: 80, useNativeDriver: true }).start();
    }, 500));

    // CTA pulse loop
    const pulse = Animated.loop(
      Animated.sequence([
        Animated.timing(ctaPulse, { toValue: 1.03, duration: 1200, useNativeDriver: true }),
        Animated.timing(ctaPulse, { toValue: 1, duration: 1200, useNativeDriver: true }),
      ]),
    );
    pulse.start();

    // Mascot bounce loop
    const bounce = Animated.loop(
      Animated.sequence([
        Animated.timing(mascotBounce, { toValue: -8, duration: 800, useNativeDriver: true }),
        Animated.timing(mascotBounce, { toValue: 0, duration: 800, useNativeDriver: true }),
      ]),
    );
    bounce.start();

    return () => {
      timers.forEach(clearTimeout);
      pulse.stop();
      bounce.stop();
    };
  }, [cardFade, cardSlide, ctaPulse, ctaScale, greetOpacity, greetScale, mascotBounce]);

  // `{ profile: null }` is "no profile yet" (contract); a failed read also shows the empty card,
  // as compD always did, rather than an error on the child's home page.
  const load = useCallback(async () => {
    try {
      const latest = await call((api, accessToken) => api.getLatestProfile(lang, accessToken));
      setProfile(latest.profile);
    } catch {
      setProfile(null);
    }
  }, [call, lang]);

  useEffect(() => { load(); }, [load]);

  async function onRefresh() {
    setRefreshing(true);
    await load();
    setRefreshing(false);
  }

  // Motivational quotes (rotate based on time)
  const quotes = [
    t.gamification.quoteOfDay,
    t.gamification.keepGoing,
    t.gamification.firstStep,
  ];
  const quoteIndex = Math.floor(Date.now() / (1000 * 60 * 60)) % quotes.length;

  return (
    <View style={{ flex: 1, backgroundColor: colors.background }}>
    <ScrollView
      contentContainerStyle={styles.container}
      refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} />}
    >
      {/* ── Greeting with Mascot ── */}
      <Animated.View
        style={[
          styles.greeting,
          {
            transform: [{ scale: greetScale }],
            opacity: greetOpacity,
          },
        ]}
      >
        <Animated.View style={{ transform: [{ translateY: mascotBounce }] }}>
          <AnimalMascot animal={5} size={80} still />
        </Animated.View>
        <View style={styles.speechBubble}>
          <Text style={styles.greetTitle}>
            {t.dashboard.welcomeBack}{name ? `, ${name}` : ''}! 👋
          </Text>
          <View style={styles.speechTriangle} />
        </View>
      </Animated.View>

      {/* ── Motivational Quote Card ── */}
      <Card style={styles.quoteCard}>
        <Text style={styles.quoteEmoji}>💭</Text>
        <Text style={styles.quoteText}>{quotes[quoteIndex]}</Text>
      </Card>

      {/* ── Latest Profile with Brain Radar ── */}
      {profile && (
        <Animated.View
          style={{
            transform: [{ translateY: cardSlide }],
            opacity: cardFade,
          }}
        >
          <Card style={styles.profileSummary}>
            <Text style={styles.sectionTitle}>{t.dashboard.latestProfile}</Text>

            {/* Mini Brain Power Circle */}
            <BrainPowerCircle
              memory={profile.memory_level}
              attention={profile.attention_level}
              numberSense={profile.number_sense_level}
              speed={profile.processing_speed_level}
              size={250}
              delay={600}
            />
          </Card>
        </Animated.View>
      )}

      {!profile && (
        <Card style={styles.emptyCard}>
          <Text style={{ fontSize: 48, textAlign: 'center' }}>🤔</Text>
          <Text style={styles.emptyText}>
            {t.dashboard.noProfileYet}
          </Text>
        </Card>
      )}

      {/* ── Start Adventure CTA ── */}
      <Animated.View
        style={[
          styles.adventureCard,
          {
            transform: [{ scale: Animated.multiply(ctaScale, ctaPulse) }],
            backgroundColor: isDark ? colors.surfaceSoft : '#FFF8E7',
          },
        ]}
      >
        <View style={styles.adventureInner}>
          <AnimalMascot animal={7} size={64} />
          <View style={styles.adventureText}>
            <Text style={styles.adventureTitle}>{t.gamification.startAdventure}</Text>
            <Text style={styles.adventureSub}>{t.gamification.readyToPlay}</Text>
          </View>
        </View>
        <PrimaryButton
          title={t.dashboard.startActivity}
          onPress={() => navigation.navigate('StudentActivity')}
        />
      </Animated.View>

      {/* ── Quick Actions ── */}
      <View style={styles.actions}>
        <PrimaryButton
          title={t.dashboard.viewProfileResult}
          onPress={() => navigation.navigate('StudentProfile')}
          variant="ghost"
        />
        <PrimaryButton
          title={t.dashboard.profileHistory}
          onPress={() => navigation.navigate('StudentHistory')}
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
    paddingBottom: spacing.xxl + 20,
    gap: spacing.md,
  },
  // Greeting
  greeting: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.md,
    marginBottom: spacing.xs,
  },
  speechBubble: {
    flex: 1,
    backgroundColor: colors.surface,
    borderRadius: radius.xl,
    padding: spacing.md,
    borderWidth: 2,
    borderColor: colors.border,
    position: 'relative',
    shadowColor: colors.shadow,
    shadowOffset: { width: 0, height: 3 },
    shadowOpacity: 0.3,
    shadowRadius: 6,
    elevation: 3,
  },
  speechTriangle: {
    position: 'absolute',
    left: -10,
    top: 18,
    width: 0,
    height: 0,
    borderTopWidth: 8,
    borderBottomWidth: 8,
    borderRightWidth: 10,
    borderTopColor: 'transparent',
    borderBottomColor: 'transparent',
    borderRightColor: colors.surface,
  },
  greetTitle: {
    ...typography.subtitle,
    color: colors.textWarm,
  },
  greetSub: {
    ...typography.caption,
    color: colors.textMuted,
    marginTop: spacing.xs,
  },
  // Quote
  quoteCard: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.md,
    backgroundColor: colors.warmYellowSoft,
    borderColor: colors.warmYellow + '50',
    paddingVertical: spacing.md,
  },
  quoteEmoji: { fontSize: 28 },
  quoteText: {
    ...typography.body,
    color: colors.textWarm,
    flex: 1,
    fontStyle: 'italic',
    lineHeight: 22,
  },
  // Profile summary
  profileSummary: {
    gap: spacing.md,
    alignItems: 'center',
  },
  sectionTitle: {
    ...typography.subtitle,
    color: colors.textWarm,
    alignSelf: 'flex-start',
  },
  levelGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: spacing.sm,
    justifyContent: 'center',
    width: '100%',
  },
  levelItem: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.xs,
    backgroundColor: colors.surfaceSoft,
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm,
    borderRadius: radius.pill,
    borderWidth: 1,
    borderColor: colors.border + '60',
  },
  levelEmoji: { fontSize: 16 },
  levelText: {
    ...typography.caption,
    color: colors.textWarm,
    fontSize: 11,
  },
  // Empty
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
  // Adventure CTA
  adventureCard: {
    borderRadius: radius.xl,
    padding: spacing.lg,
    gap: spacing.md,
    borderWidth: 2,
    borderColor: colors.warmYellow,
    shadowColor: 'rgba(255, 180, 0, 0.3)',
    shadowOffset: { width: 0, height: 6 },
    shadowOpacity: 0.8,
    shadowRadius: 12,
    elevation: 6,
  },
  adventureInner: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.md,
  },
  adventureText: {
    flex: 1,
    gap: 4,
  },
  adventureTitle: {
    ...typography.subtitle,
    color: colors.textWarm,
    fontSize: 18,
    fontWeight: '800',
  },
  adventureSub: {
    ...typography.body,
    color: colors.textMuted,
    fontSize: 13,
    lineHeight: 20,
  },
  // Actions
  actions: {
    gap: spacing.md,
  },
});
