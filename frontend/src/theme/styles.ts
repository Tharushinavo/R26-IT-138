import { StyleSheet, type TextStyle, type ViewStyle } from 'react-native';

import type { AppTheme } from '@/src/theme/theme';

/** Shared React Native styles created from the active light or dark theme. */
export function createGlobalStyles(theme: AppTheme) {
  const { colors, typography: type, radius: rad, spacing: sp, layout: lay } = theme;

  return StyleSheet.create({
    displayTitle: {
      color: colors.textPrimary,
      fontFamily: type.fonts.display,
      fontSize: type.fontSize.title,
      letterSpacing: -0.16,
      lineHeight: type.lineHeight.title,
    } as TextStyle,
    subtitle: {
      color: colors.textPrimary,
      fontFamily: type.fonts.display,
      fontSize: type.fontSize.subtitle,
      lineHeight: type.lineHeight.subtitle,
    } as TextStyle,
    bodyText: {
      color: colors.textPrimary,
      fontFamily: type.fonts.body,
      fontSize: type.fontSize.body,
      lineHeight: type.lineHeight.body,
    } as TextStyle,
    mutedText: { color: colors.textSecondary } as TextStyle,
    label: {
      color: colors.textPrimary,
      fontFamily: type.fonts.bold,
      fontSize: type.fontSize.sm,
    } as TextStyle,
    eyebrow: {
      color: colors.textSecondary,
      fontFamily: type.fonts.bold,
      fontSize: 13,
      letterSpacing: type.letterSpacing.label,
      textTransform: 'uppercase',
    } as TextStyle,
    primaryButton: {
      alignItems: 'center',
      backgroundColor: colors.primary,
      borderBottomColor: colors.primaryShadow,
      borderBottomWidth: 4,
      borderRadius: rad.md,
      flexDirection: 'row',
      gap: sp[2],
      justifyContent: 'center',
      minHeight: lay.buttonHeight,
      paddingHorizontal: sp[6],
      paddingVertical: sp[3],
    } as ViewStyle,
    primaryButtonText: {
      color: colors.textOnPrimary,
      fontFamily: type.fonts.bold,
      fontSize: 15,
      letterSpacing: type.letterSpacing.button,
      textTransform: 'uppercase',
    } as TextStyle,
    secondaryButton: {
      alignItems: 'center',
      backgroundColor: colors.surface1,
      borderBottomColor: colors.borderStrong,
      borderBottomWidth: 4,
      borderColor: colors.border,
      borderRadius: rad.md,
      borderWidth: 2,
      flexDirection: 'row',
      gap: sp[2],
      justifyContent: 'center',
      minHeight: 56,
      paddingHorizontal: sp[6],
      paddingVertical: sp[3],
    } as ViewStyle,
    card: {
      backgroundColor: colors.card,
      borderBottomColor: colors.borderStrong,
      borderBottomWidth: 4,
      borderColor: colors.border,
      borderRadius: rad.md,
      borderWidth: 2,
      padding: sp[4],
    } as ViewStyle,
    featureCard: {
      backgroundColor: colors.primarySoft,
      borderBottomColor: colors.primaryShadow,
      borderBottomWidth: 4,
      borderColor: colors.primaryShadow,
      borderRadius: rad.lg,
      borderWidth: 2,
      padding: sp[6],
    } as ViewStyle,
    input: {
      backgroundColor: colors.inputBackground,
      borderColor: colors.inputBorder,
      borderRadius: rad.md,
      borderWidth: 2,
      color: colors.textPrimary,
      fontFamily: type.fonts.body,
      fontSize: type.fontSize.body,
      minHeight: 56,
      paddingHorizontal: sp[4],
      paddingVertical: sp[3],
      width: '100%',
    } as TextStyle,
    progressTrack: {
      backgroundColor: colors.surface3,
      borderRadius: rad.pill,
      height: 16,
      overflow: 'hidden',
      width: '100%',
    } as ViewStyle,
    progressFill: {
      backgroundColor: colors.primary,
      borderRadius: rad.pill,
      height: '100%',
    } as ViewStyle,
  });
}

export type GlobalStyles = ReturnType<typeof createGlobalStyles>;
