// ─── Cartoon-friendly warm palette inspired by kids' math app references ───
export const colors = {
  // Core palette – warm cream/yellow base
  background: '#FFF8E7',       // warm cream (from reference)
  surface: '#FFFFFF',
  surfaceSoft: '#FFF3D6',      // soft golden card bg
  skyBlue: '#BDE3FF',
  skyBlueSoft: '#E6F4FF',

  // Primary – friendly blue
  primary: '#4DA3FF',
  primaryDark: '#2F7FDD',
  primaryLight: '#A8D4FF',
  deepBlue: '#1E4E8C',
  accent: '#7CC6FF',

  // Cartoon number colors (from wireframe reference)
  coral: '#E06E52',            // #e06e52 – number 1
  green: '#91D159',            // #91d159 – number 2
  blue: '#71A0FB',             // #71a0fb – number 3
  purple: '#AE7FFA',           // #ae7ffa – number 4

  // Fun accent colors for gamification
  pink: '#F472B6',
  orange: '#FB923C',
  teal: '#2DD4BF',
  yellow: '#FBBF24',
  warmYellow: '#FFD93D',       // warm button/accent yellow
  warmYellowSoft: '#FFF5D6',   // soft warm yellow background
  mint: '#A8E6CF',

  // Semantic
  success: '#34D399',
  successBg: '#ECFDF5',
  warning: '#FBBF24',
  warningBg: '#FFFBEB',
  danger: '#F87171',
  dangerBg: '#FEF2F2',

  // Text
  text: '#3D3D3D',            // softer dark for kids UI
  textMuted: '#8B8B8B',
  textInverse: '#FFFFFF',
  textWarm: '#6B4C1E',        // warm brown for headings

  // Borders / shadows
  border: '#F0E0C0',          // warm border
  borderLight: '#F5EDD8',
  shadow: 'rgba(180, 140, 60, 0.15)',

  // Level colors
  levelHigh: '#34D399',
  levelMedium: '#4DA3FF',
  levelLow: '#FBBF24',
};

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
  titleXL: { fontSize: 34, fontWeight: '800' as const, letterSpacing: -0.5 },
  title: { fontSize: 26, fontWeight: '800' as const, letterSpacing: -0.3 },
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
