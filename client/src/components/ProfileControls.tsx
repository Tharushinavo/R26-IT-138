import React from 'react';
import { StyleSheet, View } from 'react-native';
import LanguageToggle from './LanguageToggle';
import ThemeToggle from './ThemeToggle';
import { spacing } from '../theme';

export default function ProfileControls() {
  return (
    <View style={styles.container}>
      <LanguageToggle />
      <ThemeToggle />
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    gap: spacing.xs,
  },
});
