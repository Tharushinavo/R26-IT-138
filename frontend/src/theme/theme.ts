import type { TextStyle, ViewStyle } from 'react-native';

/** The single, fixed MathMingo color palette. */
export const colors = {
  background: '#f4f4f6',
  foreground: '#2f3136',
  surface1: '#ffffff',
  surface2: '#eaebee',
  surface3: '#dcdfe4',
  card: '#ffffff',
  cardForeground: '#2f3136',
  primary: '#ff6b68',
  primaryHover: '#f05653',
  primaryShadow: '#d94340',
  primarySoft: '#ffe5e4',
  primaryForeground: '#ffffff',
  secondary: '#b3e0fc',
  secondaryShadow: '#85c2ea',
  secondarySoft: '#eaf5fe',
  secondaryForeground: '#1a4360',
  accentYellow: '#f2cd38',
  accentGreen: '#7bd3aa',
  accentBlue: '#3ca6f8',
  accentRed: '#f0504d',
  accentWingPink: '#ffb7c5',
  success: '#7bd3aa',
  warning: '#f2cd38',
  danger: '#f0504d',
  dangerSoft: '#fde8e8',
  dangerForeground: '#ffffff',
  textPrimary: '#2f3136',
  textSecondary: '#686d76',
  textMuted: '#9398a1',
  textDisabled: '#c1c5cc',
  textOnPrimary: '#ffffff',
  border: '#e2e4e8',
  borderStrong: '#cdcfd5',
  inputBackground: '#ffffff',
  inputBorder: '#e2e4e8',
  focusRing: '#3ca6f8',
  streak: '#f2cd38',
  xp: '#3ca6f8',
  correct: '#7bd3aa',
  incorrect: '#f0504d',
} as const;

export const typography = {
  fonts: {
    display: 'Nunito_800ExtraBold',
    heavy: 'Nunito_900Black',
    bold: 'Nunito_700Bold',
    body: 'Nunito_600SemiBold',
  },
  fontSize: { xs: 12, sm: 14, body: 16, lg: 18, subtitle: 24, title: 40 },
  lineHeight: { xs: 16, sm: 21, body: 24, lg: 27, subtitle: 31, title: 46 },
  fontWeight: {
    regular: '600' as TextStyle['fontWeight'],
    bold: '700' as TextStyle['fontWeight'],
    extraBold: '800' as TextStyle['fontWeight'],
  },
  letterSpacing: { label: 0.7, button: 0.4 },
};

export const spacing = {
  1: 4,
  2: 8,
  3: 12,
  4: 16,
  5: 20,
  6: 24,
  8: 32,
  10: 40,
  12: 48,
  16: 64,
  xs: 4,
  sm: 8,
  smPlus: 12,
  md: 16,
  mdPlus: 20,
  lg: 24,
  xl: 32,
  xxl: 48,
  xxxl: 64,
};

export const radius = { sm: 8, md: 12, lg: 20, xl: 28, pill: 9999 };

export const layout = {
  screenPadding: 16,
  contentMaxWidth: 640,
  touchTargetMinimum: 44,
  buttonHeight: 60,
};

export const shadows = {
  elevated: {
    shadowColor: '#000000',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.1,
    shadowRadius: 16,
    elevation: 4,
  } as ViewStyle,
};

export const motion = {
  duration: { fast: 80, normal: 200, slow: 350 },
  springConfig: { damping: 15, stiffness: 150, mass: 1 },
};

export type ThemeColors = typeof colors;

export interface AppTheme {
  colors: ThemeColors;
  spacing: typeof spacing;
  radius: typeof radius;
  typography: typeof typography;
  layout: typeof layout;
  shadows: typeof shadows;
  motion: typeof motion;
}

export const appTheme: AppTheme = {
  colors,
  spacing,
  radius,
  typography,
  layout,
  shadows,
  motion,
};
