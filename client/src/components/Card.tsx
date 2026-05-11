import React from 'react';
import { StyleSheet, View, ViewProps } from 'react-native';
import { radius, spacing, themedShadow, useAppTheme } from '../theme';

export default function Card({ style, children, ...rest }: ViewProps) {
  const { colors } = useAppTheme();
  const styles = createStyles(colors);
  return (
    <View style={[styles.card, style]} {...rest}>
      {children}
    </View>
  );
}

const createStyles = (colors: ReturnType<typeof useAppTheme>['colors']) => StyleSheet.create({
  card: {
    backgroundColor: colors.surface,
    borderRadius: radius.xl,
    padding: spacing.lg,
    borderWidth: 2,
    borderColor: colors.border,
    ...themedShadow(colors, 'soft'),
  },
});
