import { StyleSheet, Text, type TextProps } from 'react-native';

import { colors, typography } from '@/src/theme/tokens';

type AppTextVariant = 'body' | 'subtitle' | 'title';

const variantStyles = StyleSheet.create({
  body: {
    fontFamily: typography.fonts.body,
    fontSize: typography.fontSize.body,
    lineHeight: typography.lineHeight.body,
  },
  subtitle: {
    fontFamily: typography.fonts.display,
    fontSize: typography.fontSize.subtitle,
    lineHeight: typography.lineHeight.subtitle,
  },
  title: {
    fontFamily: typography.fonts.display,
    fontSize: typography.fontSize.title,
    lineHeight: typography.lineHeight.title,
  },
});

type AppTextProps = TextProps & {
  align?: 'auto' | 'left' | 'right' | 'center' | 'justify';
  variant?: AppTextVariant;
};

export function AppText({ align = 'auto', style, variant = 'body', ...props }: AppTextProps) {
  return (
    <Text
      {...props}
      style={[
        styles.base,
        variantStyles[variant],
        { color: colors.textPrimary, textAlign: align },
        style,
      ]}
    />
  );
}

const styles = StyleSheet.create({
  base: {
    maxWidth: 560,
  },
});
