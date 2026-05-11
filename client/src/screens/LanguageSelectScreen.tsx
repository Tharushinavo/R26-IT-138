import React from 'react';
import { StyleSheet, Text, TouchableOpacity, View } from 'react-native';
import type { NativeStackScreenProps } from '@react-navigation/native-stack';
import type { RootStackParamList } from '../../App';
import PrimaryButton from '../components/PrimaryButton';
import { useLanguage } from '../i18n/LanguageContext';
import { colors as lightColors, radius, spacing, typography, useAppTheme } from '../theme';

type Props = NativeStackScreenProps<RootStackParamList, 'LanguageSelect'>;

export default function LanguageSelectScreen({ navigation }: Props) {
  const { lang, setLanguage, t } = useLanguage();
  const { colors, isDark } = useAppTheme();
  const styles = createStyles(colors);

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <View style={styles.mascotCircle}>
          <Text style={styles.mascot}>🐒</Text>
        </View>
        <Text style={styles.title}>{t.langSelect.title}</Text>
        <Text style={styles.subtitle}>{t.langSelect.subtitle}</Text>
      </View>

      <View style={styles.options}>
        <LanguageOption
          flag="🇬🇧"
          animal="🐑"
          name={t.langSelect.english}
          nativeName={t.langSelect.englishNative}
          bgColor="#E8F4FF"
          accentColor={colors.blue}
          selected={lang === 'en'}
          isDark={isDark}
          onPress={() => setLanguage('en')}
        />
        <LanguageOption
          flag="🇱🇰"
          animal="🐸"
          name={t.langSelect.sinhala}
          nativeName={t.langSelect.sinhalaNative}
          bgColor="#E8FFE8"
          accentColor={colors.green}
          selected={lang === 'si'}
          isDark={isDark}
          onPress={() => setLanguage('si')}
        />
      </View>

      <View style={styles.previewBubble}>
        <View style={styles.bubbleTail} />
        <Text style={styles.previewText}>🎮 {t.splash.subtitle}</Text>
      </View>

      <View style={styles.dotsRow}>
        <View style={styles.dot} />
        <View style={styles.dotActive} />
        <View style={styles.dot} />
      </View>

      <View style={styles.cta}>
        <PrimaryButton title={`${t.langSelect.confirm}  →`} onPress={() => navigation.replace('Login')} />
      </View>
    </View>
  );
}

function LanguageOption({
  flag,
  animal,
  name,
  nativeName,
  bgColor,
  accentColor,
  selected,
  isDark,
  onPress,
}: {
  flag: string;
  animal: string;
  name: string;
  nativeName: string;
  bgColor: string;
  accentColor: string;
  selected: boolean;
  isDark: boolean;
  onPress: () => void;
}) {
  const { colors } = useAppTheme();
  const styles = createStyles(colors);
  const selectedBg = isDark ? colors.surfaceSoft : bgColor;

  return (
    <TouchableOpacity
      activeOpacity={0.7}
      onPress={onPress}
      style={[
        styles.langCard,
        { backgroundColor: selected ? selectedBg : colors.surface },
        selected && { borderColor: accentColor },
      ]}
    >
      <View style={[styles.langAnimal, { borderColor: selected ? accentColor : colors.border }]}>
        <Text style={styles.langAnimalText}>{animal}</Text>
      </View>
      <View style={styles.langTextWrap}>
        <Text style={[styles.langName, selected && { color: accentColor }]}>{name}</Text>
        <Text style={styles.langNative}>{flag} {nativeName}</Text>
      </View>
      <View style={[styles.radio, selected && { borderColor: accentColor }]}>
        {selected && <View style={[styles.radioDot, { backgroundColor: accentColor }]} />}
      </View>
    </TouchableOpacity>
  );
}

const createStyles = (colors: typeof lightColors) => StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.background,
    padding: spacing.lg,
    paddingTop: 60,
    justifyContent: 'center',
  },
  header: {
    alignItems: 'center',
    marginBottom: spacing.xl,
  },
  mascotCircle: {
    width: 80,
    height: 80,
    borderRadius: 40,
    backgroundColor: colors.warmYellow,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: spacing.md,
    borderWidth: 3,
    borderColor: colors.yellow,
    shadowColor: colors.shadow,
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 1,
    shadowRadius: 8,
    elevation: 4,
  },
  mascot: { fontSize: 44 },
  title: {
    ...typography.title,
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
  options: {
    gap: spacing.md,
    marginBottom: spacing.lg,
  },
  langCard: {
    flexDirection: 'row',
    alignItems: 'center',
    borderRadius: radius.xl,
    padding: spacing.lg,
    gap: spacing.md,
    borderWidth: 3,
    borderColor: colors.border,
    shadowColor: colors.shadow,
    shadowOffset: { width: 0, height: 3 },
    shadowOpacity: 0.2,
    shadowRadius: 6,
    elevation: 3,
  },
  langAnimal: {
    width: 52,
    height: 52,
    borderRadius: 26,
    backgroundColor: colors.surface,
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 2.5,
  },
  langAnimalText: { fontSize: 30 },
  langTextWrap: { flex: 1, gap: 2 },
  langName: {
    ...typography.subtitle,
    color: colors.text,
    fontWeight: '800',
  },
  langNative: {
    ...typography.caption,
    color: colors.textMuted,
  },
  radio: {
    width: 26,
    height: 26,
    borderRadius: 13,
    borderWidth: 3,
    borderColor: colors.border,
    alignItems: 'center',
    justifyContent: 'center',
  },
  radioDot: {
    width: 14,
    height: 14,
    borderRadius: 7,
  },
  previewBubble: {
    backgroundColor: colors.surface,
    borderRadius: radius.xl,
    padding: spacing.lg,
    marginBottom: spacing.lg,
    shadowColor: colors.shadow,
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.15,
    shadowRadius: 6,
    elevation: 2,
  },
  bubbleTail: {
    position: 'absolute',
    top: -10,
    left: 40,
    width: 0,
    height: 0,
    borderLeftWidth: 10,
    borderRightWidth: 10,
    borderBottomWidth: 12,
    borderLeftColor: 'transparent',
    borderRightColor: 'transparent',
    borderBottomColor: colors.surface,
  },
  previewText: {
    ...typography.body,
    color: colors.textMuted,
    lineHeight: 24,
  },
  dotsRow: {
    flexDirection: 'row',
    gap: 8,
    justifyContent: 'center',
    marginBottom: spacing.lg,
  },
  dotActive: {
    width: 24,
    height: 8,
    borderRadius: 4,
    backgroundColor: colors.warmYellow,
  },
  dot: {
    width: 8,
    height: 8,
    borderRadius: 4,
    backgroundColor: colors.border,
  },
  cta: {
    gap: spacing.md,
  },
});
