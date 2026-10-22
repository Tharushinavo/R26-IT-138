// compD's own palette and type scale, kept so its screens look as they did. Inside MathMingo it is
// LIGHT ONLY (plan v5 Q6): the host app is light-only, so the dark palette below is unused and the
// theme no longer reads or writes device storage.

export type ThemeMode = 'light' | 'dark';

export const lightColors = {
  background: '#FFF8E7',
  surface: '#FFFFFF',
  surfaceSoft: '#FFF3D6',
  skyBlue: '#BDE3FF',
  skyBlueSoft: '#E6F4FF',

  primary: '#4DA3FF',
  primaryDark: '#2F7FDD',
  primaryLight: '#A8D4FF',
  deepBlue: '#1E4E8C',
  accent: '#7CC6FF',

  coral: '#E06E52',
  green: '#91D159',
  blue: '#71A0FB',
  purple: '#AE7FFA',

  pink: '#F472B6',
  orange: '#FB923C',
  teal: '#2DD4BF',
  yellow: '#FBBF24',
  warmYellow: '#FFD93D',
  warmYellowSoft: '#FFF5D6',
  mint: '#A8E6CF',

  success: '#34D399',
  successBg: '#ECFDF5',
  warning: '#FBBF24',
  warningBg: '#FFFBEB',
  danger: '#F87171',
  dangerBg: '#FEF2F2',

  text: '#3D3D3D',
  textMuted: '#8B8B8B',
  textInverse: '#FFFFFF',
  textWarm: '#6B4C1E',

  border: '#F0E0C0',
  borderLight: '#F5EDD8',
  shadow: 'rgba(180, 140, 60, 0.15)',

  levelHigh: '#34D399',
  levelMedium: '#4DA3FF',
  levelLow: '#FBBF24',
};

export const darkColors: typeof lightColors = {
  background: '#12172A',
  surface: '#1B2340',
  surfaceSoft: '#242D4C',
  skyBlue: '#334B78',
  skyBlueSoft: '#1F355D',

  primary: '#7CB7FF',
  primaryDark: '#A7CEFF',
  primaryLight: '#405D8E',
  deepBlue: '#C6DDFF',
  accent: '#8FD0FF',

  coral: '#FF927E',
  green: '#A8E67D',
  blue: '#8EAFFF',
  purple: '#C5A4FF',

  pink: '#F7A1D2',
  orange: '#FFB46F',
  teal: '#6EE7D8',
  yellow: '#FBD26B',
  warmYellow: '#F8D85A',
  warmYellowSoft: '#3A321E',
  mint: '#79D7B7',

  success: '#6EE7B7',
  successBg: '#173D35',
  warning: '#FBD26B',
  warningBg: '#3C321B',
  danger: '#FF9A9A',
  dangerBg: '#452527',

  text: '#F1F5FF',
  textMuted: '#B2BDD6',
  textInverse: '#111827',
  textWarm: '#FFE9A8',

  border: '#34405E',
  borderLight: '#2A3550',
  shadow: 'rgba(0, 0, 0, 0.35)',

  levelHigh: '#6EE7B7',
  levelMedium: '#7CB7FF',
  levelLow: '#FBD26B',
};

// Backward-compatible light tokens for legacy static styles.
export const colors = lightColors;

export const radius = {
  sm: 12,
  md: 18,
  lg: 24,
  xl: 32,
  pill: 999,
};

export const spacing = {
  xs: 4,
  sm: 8,
  md: 16,
  lg: 24,
  xl: 32,
  xxl: 48,
};

export const typography = {
  titleXL: { fontSize: 34, fontWeight: '800' as const, letterSpacing: 0 },
  title: { fontSize: 26, fontWeight: '800' as const, letterSpacing: 0 },
  subtitle: { fontSize: 18, fontWeight: '700' as const },
  body: { fontSize: 16, fontWeight: '500' as const },
  caption: { fontSize: 13, fontWeight: '600' as const },
  small: { fontSize: 11, fontWeight: '600' as const },
};

export const shadow = {
  card: {
    shadowColor: colors.shadow,
    shadowOffset: { width: 0, height: 6 },
    shadowOpacity: 0.8,
    shadowRadius: 12,
    elevation: 5,
  },
  soft: {
    shadowColor: colors.shadow,
    shadowOffset: { width: 0, height: 3 },
    shadowOpacity: 0.4,
    shadowRadius: 6,
    elevation: 2,
  },
};

type ThemeValue = {
  mode: ThemeMode;
  colors: typeof lightColors;
  isDark: boolean;
};

const LIGHT_THEME: ThemeValue = { mode: 'light', colors: lightColors, isDark: false };

/** compD screens call this as they always did; inside MathMingo it is always the light theme. */
export function useAppTheme(): ThemeValue {
  return LIGHT_THEME;
}

export function themedShadow(themeColors: typeof lightColors, strength: 'soft' | 'card' = 'soft') {
  return {
    shadowColor: themeColors.shadow,
    shadowOffset: { width: 0, height: strength === 'card' ? 6 : 3 },
    shadowOpacity: strength === 'card' ? 0.8 : 0.4,
    shadowRadius: strength === 'card' ? 12 : 6,
    elevation: strength === 'card' ? 5 : 2,
  };
}
