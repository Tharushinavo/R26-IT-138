import React from 'react';
import { StyleSheet, Text, TouchableOpacity, View } from 'react-native';
import type { NativeStackScreenProps } from '@react-navigation/native-stack';
import type { RootStackParamList } from '../../App';
import PrimaryButton from '../components/PrimaryButton';
import { useLanguage } from '../i18n/LanguageContext';
import type { Language } from '../i18n/translations';
import { colors, radius, spacing, typography, shadow } from '../theme';

type Props = NativeStackScreenProps<RootStackParamList, 'LanguageSelect'>;

export default function LanguageSelectScreen({ navigation }: Props) {
  const { lang, setLanguage, t } = useLanguage();

  return (
    <View style={styles.container}>
      {/* Decorative blobs */}
      <View style={styles.blob1} />
      <View style={styles.blob2} />

      {/* Mascot header */}
      <View style={styles.header}>
        <View style={styles.mascotCircle}>
          <Text style={{ fontSize: 44 }}>🦒</Text>
        </View>
        <Text style={styles.title}>{t.langSelect.title}</Text>
        <Text style={styles.subtitle}>{t.langSelect.subtitle}</Text>
      </View>

      {/* Language Options */}
      <View style={styles.options}>
        <LanguageOption
          flag="🇬🇧"
          animal="🐑"
          name={t.langSelect.english}
          nativeName={t.langSelect.englishNative}
          bgColor="#E8F4FF"
          accentColor={colors.blue}
          selected={lang === 'en'}
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
          onPress={() => setLanguage('si')}
        />
      </View>

      {/* Preview speech bubble */}
      <View style={styles.previewBubble}>
        <View style={styles.bubbleTail} />
        <Text style={styles.previewText}>
          {lang === 'en'
            ? '🎮 Play fun math activities and discover how your brain learns best!'
            : '🎮 විනෝදජනක ගණිත ක්‍රියාකාරකම් කරමින් ඔබේ මොළය වඩාත් හොඳින් ඉගෙන ගන්නේ කෙසේදැයි සොයා ගන්න!'}
        </Text>
      </View>

      {/* Progress dots */}
      <View style={styles.dotsRow}>
        <View style={styles.dot} />
        <View style={styles.dotActive} />
        <View style={styles.dot} />
      </View>

      {/* Continue */}
      <View style={styles.cta}>
        <PrimaryButton
          title={`${t.langSelect.confirm}  →`}
          onPress={() => navigation.replace('Login')}
        />
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
  onPress,
}: {
  flag: string;
  animal: string;
  name: string;
  nativeName: string;
  bgColor: string;
  accentColor: string;
  selected: boolean;
  onPress: () => void;
}) {
  return (
    <TouchableOpacity
      activeOpacity={0.7}
      onPress={onPress}
      style={[
        styles.langCard,
        { backgroundColor: selected ? bgColor : colors.surface },
        selected && { borderColor: accentColor },
      ]}
    >
      <View style={[styles.langAnimal, { borderColor: selected ? accentColor : colors.border }]}>
        <Text style={{ fontSize: 30 }}>{animal}</Text>
      </View>
      <View style={styles.langTextWrap}>
        <Text style={[styles.langName, selected && { color: accentColor }]}>
          {name}
        </Text>
        <Text style={styles.langNative}>{flag} {nativeName}</Text>
      </View>
      <View style={[styles.radio, selected && { borderColor: accentColor }]}>
        {selected && <View style={[styles.radioDot, { backgroundColor: accentColor }]} />}
      </View>
    </TouchableOpacity>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.background,
    padding: spacing.lg,
    paddingTop: 60,
    justifyContent: 'center',
  },
  blob1: {
    position: 'absolute',
    width: 180,
    height: 180,
    borderRadius: 90,
    backgroundColor: 'rgba(255, 217, 61, 0.15)',
    top: -30,
    left: -40,
  },
  blob2: {
    position: 'absolute',
    width: 140,
    height: 140,
    borderRadius: 70,
    backgroundColor: 'rgba(174, 127, 250, 0.10)',
    bottom: 60,
    right: -30,
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
    borderColor: '#FFE082',
    shadowColor: 'rgba(255, 180, 0, 0.3)',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 1,
    shadowRadius: 8,
    elevation: 4,
  },
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
