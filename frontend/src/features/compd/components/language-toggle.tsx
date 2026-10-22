import React from 'react';
import { StyleSheet, Text, TouchableOpacity, View } from 'react-native';
import { useLanguage } from '@/src/features/compd/i18n/language-context';
import { radius, spacing, typography, useAppTheme } from '@/src/features/compd/theme';

export default function LanguageToggle() {
  const { lang, setLanguage } = useLanguage();
  const { colors, isDark } = useAppTheme();
  const styles = createStyles(colors, isDark);
  return (
    <View style={styles.container}>
      <TouchableOpacity
        style={[styles.btn, lang === 'en' && styles.active]}
        onPress={() => setLanguage('en')}
        activeOpacity={0.7}
      >
        <Text style={[styles.text, lang === 'en' && styles.activeText]}>EN</Text>
      </TouchableOpacity>
      <TouchableOpacity
        style={[styles.btn, lang === 'si' && styles.active]}
        onPress={() => setLanguage('si')}
        activeOpacity={0.7}
      >
        <Text style={[styles.text, lang === 'si' && styles.activeText]}>සිං</Text>
      </TouchableOpacity>
    </View>
  );
}

const createStyles = (colors: ReturnType<typeof useAppTheme>['colors'], isDark: boolean) => StyleSheet.create({
  container: {
    flexDirection: 'row',
    alignSelf: 'center',
    backgroundColor: colors.surfaceSoft,
    borderRadius: radius.pill,
    padding: 3,
    gap: 2,
    borderWidth: 1.5,
    borderColor: colors.border,
    marginBottom: spacing.sm,
  },
  btn: {
    paddingHorizontal: 14,
    paddingVertical: 6,
    borderRadius: radius.pill,
  },
  active: {
    backgroundColor: colors.warmYellow,
  },
  text: {
    ...typography.caption,
    color: colors.textMuted,
  },
  activeText: {
    color: isDark ? colors.textInverse : colors.textWarm,
    fontWeight: '800',
  },
});
