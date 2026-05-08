/*
 * CelebrationOverlay — shows confetti particles + bouncing animal
 * when the student answers correctly or completes the activity.
 * Uses pure RN Animated API (no extra deps).
 */
import React, { useEffect, useRef } from 'react';
import { Animated, Dimensions, Image, StyleSheet, View } from 'react-native';
import { ANIMAL_IMAGES, type AnimalId } from '../assets/animalImages';

const { width: SCREEN_W, height: SCREEN_H } = Dimensions.get('window');

const CONFETTI_COLORS = ['#FFD93D', '#E06E52', '#91D159', '#71A0FB', '#AE7FFA', '#F472B6', '#2DD4BF', '#FB923C'];
const CONFETTI_COUNT = 18;

interface Props {
  /** Show the celebration */
  visible: boolean;
  /** Animal ID (1-18) shown bouncing in the centre */
  animal?: AnimalId;
  /** Animal image size in px */
  size?: number;
}

function ConfettiPiece({ delay, color }: { delay: number; color: string }) {
  const fall = useRef(new Animated.Value(-40)).current;
  const x = useRef(Math.random() * SCREEN_W).current;
  const rotate = useRef(new Animated.Value(0)).current;
  const size = 8 + Math.random() * 10;

  useEffect(() => {
    Animated.parallel([
      Animated.timing(fall, {
        toValue: SCREEN_H + 40,
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
    ]).start();
  }, []);

  return (
    <Animated.View
      style={{
        position: 'absolute',
        left: x,
        width: size,
        height: size * 1.6,
        borderRadius: size / 4,
        backgroundColor: color,
        transform: [
          { translateY: fall },
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

export default function CelebrationOverlay({ visible, animal = 5, size = 160 }: Props) {
  const scale = useRef(new Animated.Value(0)).current;
  const bounce = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    if (!visible) {
      scale.setValue(0);
      bounce.setValue(0);
      return;
    }

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

  return (
    <View style={StyleSheet.absoluteFill} pointerEvents="none">
      {/* Confetti */}
      {Array.from({ length: CONFETTI_COUNT }).map((_, i) => (
        <ConfettiPiece
          key={i}
          delay={i * 60}
          color={CONFETTI_COLORS[i % CONFETTI_COLORS.length]}
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
