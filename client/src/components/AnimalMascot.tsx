/**
 * AnimalMascot — displays a cute 3D cartoon animal bundled from
 * client/assets/animals/. Each question gets its own animal friend
 * that idle-wiggles and bounces on correct answers.
 */
import React, { useEffect, useRef } from 'react';
import { Animated, Image, StyleSheet } from 'react-native';
import { ANIMAL_IMAGES, type AnimalId } from '../assets/animalImages';

interface Props {
  animal: AnimalId;
  size?: number;
  celebrating?: boolean;
  /** Disable idle wiggle (for static badges) */
  still?: boolean;
}

export default function AnimalMascot({ animal, size = 80, celebrating = false, still = false }: Props) {
  const wiggle = useRef(new Animated.Value(0)).current;
  const bounceY = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    if (still) return;
    const wiggleAnim = Animated.loop(
      Animated.sequence([
        Animated.timing(wiggle, { toValue: 1, duration: 700, useNativeDriver: true }),
        Animated.timing(wiggle, { toValue: -1, duration: 700, useNativeDriver: true }),
        Animated.timing(wiggle, { toValue: 0, duration: 500, useNativeDriver: true }),
      ]),
    );
    wiggleAnim.start();
    return () => wiggleAnim.stop();
  }, [still, wiggle]);

  useEffect(() => {
    if (celebrating) {
      Animated.sequence([
        Animated.timing(bounceY, { toValue: -22, duration: 160, useNativeDriver: true }),
        Animated.timing(bounceY, { toValue: 0, duration: 160, useNativeDriver: true }),
        Animated.timing(bounceY, { toValue: -14, duration: 130, useNativeDriver: true }),
        Animated.timing(bounceY, { toValue: 0, duration: 130, useNativeDriver: true }),
      ]).start();
    }
  }, [celebrating, bounceY]);

  const rotate = wiggle.interpolate({
    inputRange: [-1, 0, 1],
    outputRange: ['-6deg', '0deg', '6deg'],
  });

  return (
    <Animated.View
      style={[styles.container, { transform: [{ rotate }, { translateY: bounceY }] }]}
    >
      <Image
        source={ANIMAL_IMAGES[animal]}
        style={{ width: size, height: size }}
        resizeMode="contain"
      />
    </Animated.View>
  );
}

const styles = StyleSheet.create({
  container: {
    alignItems: 'center',
    justifyContent: 'center',
  },
});
