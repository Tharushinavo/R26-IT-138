import React from 'react';
import {
  ActivityIndicator,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
  ViewStyle,
} from 'react-native';
import { colors, radius, typography } from '../theme';

interface Props {
  title: string;
  onPress?: () => void | Promise<void>;
  disabled?: boolean;
  loading?: boolean;
  variant?: 'primary' | 'ghost';
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
  const isGhost = variant === 'ghost';
  const isDisabled = disabled || loading;
  return (
    <TouchableOpacity
      activeOpacity={0.75}
      onPress={isDisabled ? undefined : onPress}
      disabled={isDisabled}
      style={[
        styles.base,
        isGhost ? styles.ghost : styles.primary,
        isDisabled && styles.disabled,
        style,
      ]}
    >
      {loading ? (
        <ActivityIndicator color={isGhost ? colors.primary : colors.textInverse} />
      ) : (
        <View style={styles.inner}>
          <Text style={[styles.text, isGhost ? styles.textGhost : styles.textPrimary]}>
            {title}
          </Text>
        </View>
      )}
    </TouchableOpacity>
  );
}

const styles = StyleSheet.create({
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
  disabled: { opacity: 0.5 },
  text: { ...typography.subtitle, letterSpacing: 0.3 },
  textPrimary: { color: colors.textWarm },
  textGhost: { color: colors.textWarm },
});
