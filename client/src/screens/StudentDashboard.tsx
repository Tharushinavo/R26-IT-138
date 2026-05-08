import React, { useCallback, useEffect, useState } from 'react';
import {
  StyleSheet,
  Text,
  View,
  ScrollView,
  RefreshControl,
  TouchableOpacity,
} from 'react-native';
import type { NativeStackScreenProps } from '@react-navigation/native-stack';
import type { RootStackParamList } from '../../App';
import PrimaryButton from '../components/PrimaryButton';
import Card from '../components/Card';
import LanguageToggle from '../components/LanguageToggle';
import { useLanguage } from '../i18n/LanguageContext';
import { useAuth } from '../context/AuthContext';
import { colors, radius, spacing, typography } from '../theme';
import { api, type CognitiveProfile } from '../api/client';

type Props = NativeStackScreenProps<RootStackParamList, 'StudentDashboard'>;

export default function StudentDashboard({ route, navigation }: Props) {
  const { t } = useLanguage();
  const { user, logout } = useAuth();
  const { studentId } = route.params;
  const name = user?.full_name || '';
  const [profile, setProfile] = useState<CognitiveProfile | null>(null);
  const [refreshing, setRefreshing] = useState(false);

  const load = useCallback(async () => {
    try {
      const p = await api.getLatestProfile(studentId);
      setProfile(p);
    } catch {
      setProfile(null);
    }
  }, [studentId]);

  const handleLogout = async () => {
    await logout();
    navigation.replace('Login');
  };

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
    <ScrollView
      contentContainerStyle={styles.container}
      refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} />}
    >
      {/* Language Toggle */}
      <LanguageToggle />

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
          onPress={() => navigation.navigate('MathActivity', { studentId })}
        />
        <PrimaryButton
          title={t.dashboard.viewProfileResult}
          onPress={() => navigation.navigate('ProfileResult', { studentId })}
          variant="ghost"
        />
        <PrimaryButton
          title={t.dashboard.profileHistory}
          onPress={() => navigation.navigate('ProfileHistory', { studentId })}
          variant="ghost"
        />
      </View>

      {/* Logout */}
      <TouchableOpacity style={styles.logoutRow} onPress={handleLogout} activeOpacity={0.7}>
        <Text style={styles.logoutText}>Logout</Text>
      </TouchableOpacity>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
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
  logoutRow: {
    alignItems: 'center',
    marginTop: spacing.lg,
    paddingVertical: spacing.sm,
  },
  logoutText: {
    ...typography.caption,
    color: colors.coral,
    textDecorationLine: 'underline',
  },
});
