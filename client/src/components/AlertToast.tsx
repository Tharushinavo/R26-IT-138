import React, { useEffect, useRef } from 'react';
import {
  Animated,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from 'react-native';
import { lightColors, radius, spacing, typography } from '../theme';

export type AlertType = 'success' | 'error';

interface AlertToastProps {
  visible: boolean;
  type: AlertType;
  title: string;
  message?: string;
  duration?: number;
  onDismiss: () => void;
}

const ALERT_CONFIG: Record<AlertType, { emoji: string; bg: string; border: string; accent: string }> = {
  success: {
    emoji: '🎉',
    bg: lightColors.successBg,
    border: lightColors.success,
    accent: '#059669',
  },
  error: {
    emoji: '😟',
    bg: lightColors.dangerBg,
    border: lightColors.danger,
    accent: '#DC2626',
  },
};

export default function AlertToast({
  visible,
  type,
  title,
  message,
  duration = 3500,
  onDismiss,
}: AlertToastProps) {
  const translateY = useRef(new Animated.Value(-120)).current;
  const opacity = useRef(new Animated.Value(0)).current;
  const scale = useRef(new Animated.Value(0.85)).current;
  const bounceEmoji = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    if (visible) {
      // Slide in + bounce
      Animated.parallel([
        Animated.spring(translateY, {
          toValue: 0,
          friction: 6,
          tension: 80,
          useNativeDriver: true,
        }),
        Animated.timing(opacity, {
          toValue: 1,
          duration: 250,
          useNativeDriver: true,
        }),
        Animated.spring(scale, {
          toValue: 1,
          friction: 5,
          tension: 100,
          useNativeDriver: true,
        }),
      ]).start();

      // Emoji bounce loop
      Animated.loop(
        Animated.sequence([
          Animated.timing(bounceEmoji, { toValue: -8, duration: 350, useNativeDriver: true }),
          Animated.timing(bounceEmoji, { toValue: 0, duration: 350, useNativeDriver: true }),
        ]),
      ).start();

      // Auto-dismiss
      const timer = setTimeout(() => {
        dismiss();
      }, duration);
      return () => clearTimeout(timer);
    } else {
      translateY.setValue(-120);
      opacity.setValue(0);
      scale.setValue(0.85);
      bounceEmoji.setValue(0);
    }
  }, [visible]);

  const dismiss = () => {
    Animated.parallel([
      Animated.timing(translateY, {
        toValue: -120,
        duration: 250,
        useNativeDriver: true,
      }),
      Animated.timing(opacity, {
        toValue: 0,
        duration: 200,
        useNativeDriver: true,
      }),
    ]).start(() => onDismiss());
  };

  if (!visible) return null;

  const config = ALERT_CONFIG[type];

  return (
    <Animated.View
      style={[
        styles.wrapper,
        {
          transform: [{ translateY }, { scale }],
          opacity,
        },
      ]}
    >
      <TouchableOpacity
        activeOpacity={0.9}
        onPress={dismiss}
        style={[
          styles.container,
          {
            backgroundColor: config.bg,
            borderColor: config.border,
          },
        ]}
      >
        <Animated.Text
          style={[styles.emoji, { transform: [{ translateY: bounceEmoji }] }]}
        >
          {config.emoji}
        </Animated.Text>
        <View style={styles.textWrap}>
          <Text style={[styles.title, { color: config.accent }]}>{title}</Text>
          {message ? (
            <Text style={[styles.message, { color: config.accent }]}>{message}</Text>
          ) : null}
        </View>
        <Text style={[styles.close, { color: config.accent }]}>✕</Text>
      </TouchableOpacity>
    </Animated.View>
  );
}

const styles = StyleSheet.create({
  wrapper: {
    position: 'absolute',
    top: 50,
    left: 16,
    right: 16,
    zIndex: 9999,
    elevation: 20,
  },
  container: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 14,
    paddingHorizontal: spacing.md,
    borderRadius: radius.xl,
    borderWidth: 2,
    gap: spacing.sm,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.15,
    shadowRadius: 8,
    elevation: 12,
  },
  emoji: {
    fontSize: 32,
  },
  textWrap: {
    flex: 1,
    gap: 2,
  },
  title: {
    ...typography.subtitle,
    fontSize: 15,
  },
  message: {
    ...typography.caption,
    opacity: 0.85,
  },
  close: {
    fontSize: 18,
    fontWeight: '700',
    opacity: 0.5,
    paddingLeft: spacing.sm,
  },
});
