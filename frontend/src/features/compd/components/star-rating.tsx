/**
 * StarRating — Animated 1-3 star display for cognitive dimension levels.
 * Stars appear sequentially with spring+glow animations.
 *
 * Low = 1 star, Medium = 2 stars, High = 3 stars.
 */
import React, { useEffect, useRef } from 'react';
import { Animated, StyleSheet, Text, View } from 'react-native';

type DimensionLevel = 'low' | 'medium' | 'high' | 'Slow' | 'Moderate' | 'Fast';

interface Props {
  level: DimensionLevel;
  /** Optional size multiplier */
  starSize?: number;
  /** Delay before animation starts (ms) */
  delay?: number;
}

function levelToStars(level: DimensionLevel): number {
  switch (level) {
    case 'high':
    case 'Fast':
      return 3;
    case 'medium':
    case 'Moderate':
      return 2;
    case 'low':
    case 'Slow':
      return 1;
    default:
      return 2;
  }
}

export default function StarRating({ level, starSize = 24, delay = 0 }: Props) {
  const totalStars = 3;
  const filledStars = levelToStars(level);

  // Create animation values for each star
  const starAnims = useRef(
    Array.from({ length: totalStars }, () => ({
      scale: new Animated.Value(0),
      glow: new Animated.Value(0),
    })),
  ).current;

  useEffect(() => {
    // Sequentially animate stars
    starAnims.forEach((anim, i) => {
      if (i < filledStars) {
        setTimeout(
          () => {
            Animated.sequence([
              // Pop in with spring
              Animated.spring(anim.scale, {
                toValue: 1.3,
                friction: 3,
                tension: 200,
                useNativeDriver: true,
              }),
              // Settle to normal
              Animated.spring(anim.scale, {
                toValue: 1,
                friction: 5,
                tension: 80,
                useNativeDriver: true,
              }),
            ]).start();

            // Start glow pulse after pop-in
            setTimeout(() => {
              Animated.loop(
                Animated.sequence([
                  Animated.timing(anim.glow, {
                    toValue: 1,
                    duration: 1000 + i * 200,
                    useNativeDriver: true,
                  }),
                  Animated.timing(anim.glow, {
                    toValue: 0,
                    duration: 1000 + i * 200,
                    useNativeDriver: true,
                  }),
                ]),
              ).start();
            }, 400);
          },
          delay + i * 200,
        );
      } else {
        // Empty stars fade in gently
        setTimeout(
          () => {
            Animated.timing(anim.scale, {
              toValue: 1,
              duration: 400,
              useNativeDriver: true,
            }).start();
          },
          delay + i * 200,
        );
      }
    });
  }, [filledStars, delay, starAnims]);

  return (
    <View style={styles.container}>
      {starAnims.map((anim, i) => {
        const isFilled = i < filledStars;
        const glowOpacity = anim.glow.interpolate({
          inputRange: [0, 1],
          outputRange: [0.6, 1],
        });

        return (
          <Animated.View
            key={i}
            style={[
              styles.starWrap,
              {
                transform: [{ scale: anim.scale }],
                opacity: isFilled ? glowOpacity : 0.25,
              },
            ]}
          >
            <Text
              style={[
                styles.star,
                {
                  fontSize: starSize,
                  textShadowColor: isFilled ? 'rgba(255, 180, 0, 0.6)' : 'transparent',
                  textShadowOffset: { width: 0, height: 0 },
                  textShadowRadius: isFilled ? 8 : 0,
                },
              ]}
            >
              ⭐
            </Text>
          </Animated.View>
        );
      })}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
  },
  starWrap: {
    alignItems: 'center',
    justifyContent: 'center',
  },
  star: {
    textAlign: 'center',
  },
});
