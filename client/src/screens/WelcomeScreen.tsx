import React from 'react';
import { StyleSheet, Text, View } from 'react-native';
import type { NativeStackScreenProps } from '@react-navigation/native-stack';
import type { RootStackParamList } from '../../App';
import PrimaryButton from '../components/PrimaryButton';
import { useLanguage } from '../i18n/LanguageContext';
import { colors as lightColors, spacing, typography, radius, useAppTheme } from '../theme';

type Props = NativeStackScreenProps<RootStackParamList, 'Welcome'>;

export default function WelcomeScreen({ navigation }: Props) {
  const { t } = useLanguage();
  const { colors } = useAppTheme();
  const styles = createStyles(colors);
  return (
    <View style={styles.container}>
      <View style={styles.hero}>
        <View style={styles.mascotCircle}>
          <Text style={styles.mascotEmoji}>🧠</Text>
        </View>
        <Text style={styles.title}>{t.welcome.title}</Text>
        <Text style={styles.subtitle}>{t.welcome.subtitle}</Text>
      </View>

      <View style={styles.pillRow}>
        <View style={[styles.pill, { backgroundColor: '#EDE9FE' }]}>
          <Text style={styles.pillText}>{t.welcome.pillMemory}</Text>
        </View>
        <View style={[styles.pill, { backgroundColor: '#FCE7F3' }]}>
          <Text style={styles.pillText}>{t.welcome.pillAttention}</Text>
        </View>
        <View style={[styles.pill, { backgroundColor: '#DBEAFE' }]}>
          <Text style={styles.pillText}>{t.welcome.pillNumberSense}</Text>
        </View>
        <View style={[styles.pill, { backgroundColor: '#D1FAE5' }]}>
          <Text style={styles.pillText}>{t.welcome.pillSpeed}</Text>
        </View>
      </View>

      <View style={styles.infoBox}>
        <Text style={styles.infoText}>{t.welcome.info}</Text>
      </View>

      <View style={styles.buttons}>
        <PrimaryButton
          title={t.welcome.getStarted}
          onPress={() => navigation.navigate('Login')}
        />
      </View>
    </View>
  );
}

const createStyles = (colors: typeof lightColors) => StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.background,
    padding: spacing.lg,
    justifyContent: 'center',
  },
  hero: {
    alignItems: 'center',
    marginBottom: spacing.lg,
  },
  mascotCircle: {
    width: 100,
    height: 100,
    borderRadius: 50,
    backgroundColor: colors.skyBlueSoft,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: spacing.md,
    borderWidth: 3,
    borderColor: colors.primaryLight,
  },
  mascotEmoji: { fontSize: 52 },
  title: {
    ...typography.titleXL,
    color: colors.textWarm,
    textAlign: 'center',
    marginBottom: spacing.xs,
  },
  subtitle: {
    ...typography.body,
    color: colors.textMuted,
    textAlign: 'center',
    lineHeight: 24,
  },
  pillRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    justifyContent: 'center',
    gap: spacing.sm,
    marginBottom: spacing.lg,
  },
  pill: {
    paddingHorizontal: 14,
    paddingVertical: 8,
    borderRadius: radius.pill,
  },
  pillText: {
    ...typography.caption,
    color: colors.text,
  },
  infoBox: {
    backgroundColor: colors.surface,
    borderRadius: radius.lg,
    padding: spacing.lg,
    marginBottom: spacing.xl,
    borderWidth: 1,
    borderColor: colors.border,
  },
  infoText: {
    ...typography.body,
    color: colors.textMuted,
    textAlign: 'center',
    lineHeight: 24,
  },
  buttons: {
    gap: spacing.md,
  },
});
