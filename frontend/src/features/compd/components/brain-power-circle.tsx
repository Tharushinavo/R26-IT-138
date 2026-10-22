/**
 * BrainPowerCircle — Animated circular progress indicator
 * showing overall "Brain Power" percentage score.
 *
 * Calculates score from all 4 cognitive dimensions.
 * Animates from 0→target with counting number and colour transition.
 */
import React, { useEffect, useRef } from 'react';
import { Animated, StyleSheet, Text, View } from 'react-native';
import { useAppTheme } from '@/src/features/compd/theme';

type DimensionLevel = 'low' | 'medium' | 'high' | 'Slow' | 'Moderate' | 'Fast';

interface Props {
  memory: DimensionLevel;
  attention: DimensionLevel;
  numberSense: DimensionLevel;
  speed: DimensionLevel;
  /** Size of the circle */
  size?: number;
  /** Animation delay (ms) */
  delay?: number;
}

function levelToScore(level: DimensionLevel): number {
  switch (level) {
    case 'high':
    case 'Fast':
      return 100;
    case 'medium':
    case 'Moderate':
      return 60;
    case 'low':
    case 'Slow':
      return 30;
    default:
      return 50;
  }
}

function getScoreEmoji(score: number): string {
  if (score >= 85) return '🏆';
  if (score >= 65) return '🌟';
  if (score >= 45) return '🌿';
  return '🌱';
}

function getScoreLabel(score: number): string {
  if (score >= 85) return 'Champion!';
  if (score >= 65) return 'Superstar!';
  if (score >= 45) return 'Blooming!';
  return 'Growing!';
}

export default function BrainPowerCircle({
  memory,
  attention,
  numberSense,
  speed,
  size = 160,
  delay = 0,
}: Props) {
  const { colors } = useAppTheme();
  const totalScore = Math.round(
    (levelToScore(memory) + levelToScore(attention) + levelToScore(numberSense) + levelToScore(speed)) / 4,
  );

  const animValue = useRef(new Animated.Value(0)).current;
  const scaleAnim = useRef(new Animated.Value(0.6)).current;
  const glowAnim = useRef(new Animated.Value(0)).current;
  const [displayNum, setDisplayNum] = React.useState(0);

  useEffect(() => {
    const timer = setTimeout(() => {
      // Scale in entrance
      Animated.spring(scaleAnim, {
        toValue: 1,
        friction: 5,
        tension: 60,
        useNativeDriver: true,
      }).start();

      // Count up animation
      Animated.timing(animValue, {
        toValue: totalScore,
        duration: 1500,
        useNativeDriver: false,
      }).start();

      // Glow loop
      Animated.loop(
        Animated.sequence([
          Animated.timing(glowAnim, {
            toValue: 1,
            duration: 1500,
            useNativeDriver: true,
          }),
          Animated.timing(glowAnim, {
            toValue: 0,
            duration: 1500,
            useNativeDriver: true,
          }),
        ]),
      ).start();
    }, delay);

    return () => clearTimeout(timer);
  }, [totalScore, delay, animValue, scaleAnim, glowAnim]);

  // Track animated value for display
  useEffect(() => {
    const listener = animValue.addListener(({ value }) => {
      setDisplayNum(Math.round(value));
    });
    return () => animValue.removeListener(listener);
  }, [animValue]);

  const scoreColor =
    totalScore >= 85
      ? colors.success
      : totalScore >= 65
      ? colors.primary
      : totalScore >= 45
      ? colors.warmYellow
      : colors.warning;

  const scoreColorLight =
    totalScore >= 85
      ? colors.successBg
      : totalScore >= 65
      ? colors.skyBlueSoft
      : totalScore >= 45
      ? colors.warmYellowSoft
      : colors.warningBg;

  const borderThickness = size * 0.06;
  const innerSize = size - borderThickness * 4;

  const glowOpacity = glowAnim.interpolate({
    inputRange: [0, 1],
    outputRange: [0.3, 0.7],
  });

  return (
    <Animated.View
      style={[
        styles.container,
        {
          width: size,
          height: size,
          transform: [{ scale: scaleAnim }],
        },
      ]}
    >
      {/* Outer glow ring */}
      <Animated.View
        style={[
          styles.outerGlow,
          {
            width: size,
            height: size,
            borderRadius: size / 2,
            borderWidth: borderThickness,
            borderColor: scoreColor,
            opacity: glowOpacity,
          },
        ]}
      />

      {/* Progress track background */}
      <View
        style={[
          styles.trackBg,
          {
            width: size - borderThickness * 2,
            height: size - borderThickness * 2,
            borderRadius: (size - borderThickness * 2) / 2,
            borderWidth: borderThickness,
            borderColor: scoreColorLight,
          },
        ]}
      />

      {/* Progress ring (simulated with border segments) */}
      <View
        style={[
          styles.progressRing,
          {
            width: size - borderThickness * 2,
            height: size - borderThickness * 2,
            borderRadius: (size - borderThickness * 2) / 2,
            borderWidth: borderThickness + 1,
            borderTopColor: totalScore > 25 ? scoreColor : 'transparent',
            borderRightColor: totalScore > 50 ? scoreColor : 'transparent',
            borderBottomColor: totalScore > 75 ? scoreColor : 'transparent',
            borderLeftColor: totalScore > 0 ? scoreColor : 'transparent',
          },
        ]}
      />

      {/* Inner circle with content */}
      <View
        style={[
          styles.innerCircle,
          {
            width: innerSize,
            height: innerSize,
            borderRadius: innerSize / 2,
            backgroundColor: colors.surface,
            shadowColor: scoreColor,
          },
        ]}
      >
        <Text style={[styles.emoji, { fontSize: size * 0.16 }]}>
          {getScoreEmoji(totalScore)}
        </Text>
        <Text
          style={[
            styles.scoreNumber,
            { color: scoreColor, fontSize: size * 0.2 },
          ]}
        >
          {displayNum}%
        </Text>
        <Text
          style={[
            styles.scoreLabel,
            { color: colors.textMuted, fontSize: size * 0.065 },
          ]}
        >
          {getScoreLabel(totalScore)}
        </Text>
        <Text
          style={[
            styles.brainPowerText,
            { color: colors.textWarm, fontSize: size * 0.055 },
          ]}
        >
          BRAIN POWER
        </Text>
      </View>
    </Animated.View>
  );
}

const styles = StyleSheet.create({
  container: {
    alignItems: 'center',
    justifyContent: 'center',
    alignSelf: 'center',
  },
  outerGlow: {
    position: 'absolute',
  },
  trackBg: {
    position: 'absolute',
  },
  progressRing: {
    position: 'absolute',
    transform: [{ rotate: '-45deg' }],
  },
  innerCircle: {
    alignItems: 'center',
    justifyContent: 'center',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.25,
    shadowRadius: 16,
    elevation: 6,
    gap: 2,
  },
  emoji: {
    textAlign: 'center',
  },
  scoreNumber: {
    fontWeight: '900',
    letterSpacing: -1,
  },
  scoreLabel: {
    fontWeight: '700',
    letterSpacing: 0.5,
  },
  brainPowerText: {
    fontWeight: '800',
    letterSpacing: 1.5,
    textTransform: 'uppercase',
    marginTop: 2,
  },
});
