import React from 'react';
import { StyleSheet, Text, TouchableOpacity, View } from 'react-native';
import { radius, spacing, typography, useAppTheme } from '../theme';

export default function ThemeToggle() {
  const { colors, isDark, mode, setThemeMode } = useAppTheme();
  const styles = createStyles(colors, isDark);

  return (
    <View style={styles.container}>
      <TouchableOpacity
        style={[styles.btn, mode === 'light' && styles.active]}
        onPress={() => setThemeMode('light')}
        activeOpacity={0.7}
      >
        <Text style={[styles.text, mode === 'light' && styles.activeText]}>Light</Text>
      </TouchableOpacity>
      <TouchableOpacity
        style={[styles.btn, mode === 'dark' && styles.active]}
        onPress={() => setThemeMode('dark')}
        activeOpacity={0.7}
      >
        <Text style={[styles.text, mode === 'dark' && styles.activeText]}>Dark</Text>
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
