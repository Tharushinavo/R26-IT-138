import React from 'react';
import {
  ActivityIndicator,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
  ViewStyle,
} from 'react-native';
import { radius, typography, useAppTheme } from '../theme';

interface Props {
  title: string;
  onPress?: () => void | Promise<void>;
  disabled?: boolean;
  loading?: boolean;
  variant?: 'primary' | 'ghost' | 'coral';
  style?: ViewStyle;
}

export default function PrimaryButton({
  title,
  onPress,
  disabled,
  loading,
  variant = 'primary',
  style,
}: Props) {
  const { colors, isDark } = useAppTheme();
  const primaryTextColor = isDark ? colors.textInverse : colors.textWarm;
  const styles = createStyles(colors, primaryTextColor);
  const isGhost = variant === 'ghost';
  const isCoral = variant === 'coral';
  const isDisabled = disabled || loading;
  
  const buttonStyle = isGhost ? styles.ghost : isCoral ? styles.coral : styles.primary;
  const textStyle = isGhost ? styles.textGhost : isCoral ? styles.textCoral : styles.textPrimary;
  
  return (
    <TouchableOpacity
      activeOpacity={0.75}
      onPress={isDisabled ? undefined : onPress}
      disabled={isDisabled}
      style={[
        styles.base,
        buttonStyle,
        isDisabled && styles.disabled,
        style,
      ]}
    >
      {loading ? (
        <ActivityIndicator color={isGhost || isCoral ? colors.primary : primaryTextColor} />
      ) : (
        <View style={styles.inner}>
          <Text style={[styles.text, textStyle]}>
            {title}
          </Text>
        </View>
      )}
    </TouchableOpacity>
  );
}

const createStyles = (colors: ReturnType<typeof useAppTheme>['colors'], primaryTextColor: string) => StyleSheet.create({
  base: {
    minHeight: 56,
    paddingHorizontal: 28,
    borderRadius: radius.pill,
    alignItems: 'center',
    justifyContent: 'center',
    shadowColor: 'rgba(255, 180, 0, 0.3)',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.8,
    shadowRadius: 8,
    elevation: 4,
  },
  inner: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  primary: {
    backgroundColor: colors.warmYellow,
  },
  ghost: {
    backgroundColor: colors.surface,
    borderWidth: 2.5,
    borderColor: colors.border,
    shadowColor: colors.shadow,
    shadowOpacity: 0.2,
    elevation: 2,
  },
  coral: {
    backgroundColor: colors.coral,
    shadowColor: 'rgba(224, 110, 82, 0.4)',
  },
  disabled: { opacity: 0.5 },
  text: { ...typography.subtitle, letterSpacing: 0.3, textAlign: 'center' },
  textPrimary: { color: primaryTextColor },
  textGhost: { color: colors.textWarm },
  textCoral: { color: colors.textInverse },
});
