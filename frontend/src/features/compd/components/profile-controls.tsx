import React from 'react';
import { StyleSheet, View } from 'react-native';
import LanguageToggle from '@/src/features/compd/components/language-toggle';
import { spacing } from '@/src/features/compd/theme';

// compD's ThemeToggle is not carried over: inside MathMingo compD is light only (plan v5 Q6).
export default function ProfileControls() {
  return (
    <View style={styles.container}>
      <LanguageToggle />
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    gap: spacing.xs,
  },
});
