/*
 * CelebrationOverlay — shows confetti particles, star bursts, bouncing
 * "Great Job!" text, and a bouncing animal mascot when the student
 * answers correctly or completes the activity.
 * Uses pure RN Animated API (no extra deps).
 */
import React, { useEffect, useRef } from 'react';
import { Animated, Image, StyleSheet, Text, useWindowDimensions, View } from 'react-native';
import { ANIMAL_IMAGES, type AnimalId } from '@/src/features/compd/assets/animal-images';

// Inside MathMingo the learner pages sit in a canvas at most 500 wide (app/(learner)/_layout.tsx),
// so confetti is spread across that, not across a wide browser window.
const CANVAS_MAX_WIDTH = 500;

const CONFETTI_COLORS = [
  '#FFD93D', '#E06E52', '#91D159', '#71A0FB',
  '#AE7FFA', '#F472B6', '#2DD4BF', '#FB923C',
  '#FF6B8A', '#5BCCF6', '#FFA63D', '#7EE08A',
];
const CONFETTI_COUNT = 28;
const STAR_BURST_COUNT = 8;

interface Props {
  /** Show the celebration */
  visible: boolean;
  /** Animal ID (1-18) shown bouncing in the centre */
  animal?: AnimalId;
  /** Animal image size in px */
  size?: number;
}

// ── Confetti piece (rectangle, circle, or triangle shape) ──
function ConfettiPiece({ delay, color, shape }: { delay: number; color: string; shape: 'rect' | 'circle' | 'triangle' }) {
  const { width, height } = useWindowDimensions();
  const fall = useRef(new Animated.Value(-40)).current;
  const x = useRef(Math.random() * Math.min(width, CANVAS_MAX_WIDTH)).current;
  const rotate = useRef(new Animated.Value(0)).current;
  const sway = useRef(new Animated.Value(0)).current;
  const size = 8 + Math.random() * 10;

  useEffect(() => {
    Animated.parallel([
      Animated.timing(fall, {
        toValue: height + 40,
        duration: 1800 + Math.random() * 800,
        delay,
        useNativeDriver: true,
      }),
      Animated.timing(rotate, {
        toValue: 360 * (Math.random() > 0.5 ? 1 : -1),
        duration: 1800,
        delay,
        useNativeDriver: true,
      }),
      // Side-to-side swaying motion
      Animated.sequence([
        Animated.timing(sway, {
          toValue: (Math.random() > 0.5 ? 1 : -1) * (20 + Math.random() * 30),
          duration: 800 + Math.random() * 400,
          delay,
          useNativeDriver: true,
        }),
        Animated.timing(sway, {
          toValue: (Math.random() > 0.5 ? -1 : 1) * (15 + Math.random() * 25),
          duration: 600 + Math.random() * 400,
          useNativeDriver: true,
        }),
      ]),
    ]).start();
  }, []);

  const shapeStyle =
    shape === 'circle'
      ? { borderRadius: size / 2 }
      : shape === 'triangle'
      ? {
          width: 0,
          height: 0,
          borderLeftWidth: size / 2,
          borderRightWidth: size / 2,
          borderBottomWidth: size * 1.2,
          borderLeftColor: 'transparent',
          borderRightColor: 'transparent',
          borderBottomColor: color,
          backgroundColor: 'transparent',
        }
      : {};

  return (
    <Animated.View
      style={{
        position: 'absolute',
        left: x,
        width: shape === 'triangle' ? 0 : size,
        height: shape === 'triangle' ? 0 : size * 1.6,
        borderRadius: shape === 'circle' ? size / 2 : size / 4,
        backgroundColor: shape === 'triangle' ? 'transparent' : color,
        ...shapeStyle,
        transform: [
          { translateY: fall },
          { translateX: sway },
          {
            rotate: rotate.interpolate({
              inputRange: [0, 360],
              outputRange: ['0deg', '360deg'],
            }),
          },
        ],
      }}
    />
  );
}

// ── Star burst particle ──
function StarBurst({ delay, angle }: { delay: number; angle: number }) {
  const distance = useRef(new Animated.Value(0)).current;
  const opacity = useRef(new Animated.Value(1)).current;
  const scale = useRef(new Animated.Value(0.3)).current;

  useEffect(() => {
    Animated.parallel([
      Animated.timing(distance, {
        toValue: 100 + Math.random() * 80,
        duration: 800,
        delay,
        useNativeDriver: true,
      }),
      Animated.sequence([
        Animated.timing(scale, {
          toValue: 1.2,
          duration: 300,
          delay,
          useNativeDriver: true,
        }),
        Animated.timing(scale, {
          toValue: 0,
          duration: 500,
          useNativeDriver: true,
        }),
      ]),
      Animated.timing(opacity, {
        toValue: 0,
        duration: 900,
        delay,
        useNativeDriver: true,
      }),
    ]).start();
  }, []);

  const rad = (angle * Math.PI) / 180;

  return (
    <Animated.View
      style={{
        position: 'absolute',
        alignSelf: 'center',
        top: '35%',
        transform: [
          {
            translateX: Animated.multiply(
              distance,
              Math.cos(rad),
            ),
          },
          {
            translateY: Animated.multiply(
              distance,
              Math.sin(rad),
            ),
          },
          { scale },
        ],
        opacity,
      }}
    >
      <Text style={{ fontSize: 20 }}>⭐</Text>
    </Animated.View>
  );
}

export default function CelebrationOverlay({ visible, animal = 5, size = 160 }: Props) {
  const scale = useRef(new Animated.Value(0)).current;
  const bounce = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    if (!visible) {
      scale.setValue(0);
      bounce.setValue(0);
      return;
    }

    // Mascot entrance
    Animated.sequence([
      Animated.spring(scale, {
        toValue: 1,
        friction: 3,
        tension: 150,
        useNativeDriver: true,
      }),
      Animated.sequence([
        Animated.timing(bounce, { toValue: -20, duration: 150, useNativeDriver: true }),
        Animated.timing(bounce, { toValue: 0, duration: 150, useNativeDriver: true }),
        Animated.timing(bounce, { toValue: -14, duration: 120, useNativeDriver: true }),
        Animated.timing(bounce, { toValue: 0, duration: 120, useNativeDriver: true }),
      ]),
    ]).start();
  }, [visible]);

  if (!visible) return null;

  const shapes: ('rect' | 'circle' | 'triangle')[] = ['rect', 'circle', 'triangle'];

  return (
    <View style={StyleSheet.absoluteFill} pointerEvents="none">
      {/* Confetti with varied shapes */}
      {Array.from({ length: CONFETTI_COUNT }).map((_, i) => (
        <ConfettiPiece
          key={`confetti-${i}`}
          delay={i * 50}
          color={CONFETTI_COLORS[i % CONFETTI_COLORS.length]}
          shape={shapes[i % shapes.length]}
        />
      ))}

      {/* Star burst from center */}
      {Array.from({ length: STAR_BURST_COUNT }).map((_, i) => (
        <StarBurst
          key={`star-${i}`}
          delay={100 + i * 60}
          angle={(360 / STAR_BURST_COUNT) * i}
        />
      ))}

      {/* Centre cartoon animal mascot */}
      <Animated.View
        style={[
          styles.mascotWrap,
          {
            transform: [
              { scale },
              { translateY: bounce },
            ],
          },
        ]}
      >
        <Image
          source={ANIMAL_IMAGES[animal]}
          style={{ width: size, height: size }}
          resizeMode="contain"
        />
      </Animated.View>
    </View>
  );
}

const styles = StyleSheet.create({
  mascotWrap: {
    position: 'absolute',
    top: '30%',
    alignSelf: 'center',
  },
});
