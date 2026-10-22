// Render tests (React Native Testing Library), which the contract suite deliberately cannot do.
//
// WHY BOTH RUNNERS EXIST. `npm run test:contract` runs node:test over src/api/__tests__/*.test.ts:
// pure logic and source scans, no React, fast, and the bulk of the suite. It cannot catch a screen
// that throws while rendering -- and one did: a `const` declared below the effects that read it
// produced "Cannot access 'awaitingQuestion' before initialization" in the browser while both
// `tsc --noEmit` and all 1366 contract tests stayed green (React Compiler is enabled on this
// project and hoists derived values, which TypeScript cannot see). These tests mount the real
// components so that class of bug fails here instead of in a child's browser.
//
// The two runners are kept strictly apart by `testMatch`: Jest owns src/__render__/**, node:test
// owns src/api/__tests__/**. Neither will ever try to execute the other's files, which is why the
// render tests live in their own directory rather than beside the logic tests.

module.exports = {
  preset: 'jest-expo',
  testMatch: ['<rootDir>/src/__render__/**/*.test.tsx'],
  setupFilesAfterEnv: ['<rootDir>/src/__render__/setup.tsx'],
  // Per the Expo SDK 54 unit-testing guide (npm/Yarn variant). Everything listed ships untranspiled
  // ESM and must go through babel rather than being treated as CommonJS.
  transformIgnorePatterns: [
    'node_modules/(?!((jest-)?react-native|@react-native(-community)?)|expo(nent)?|@expo(nent)?/.*|@expo-google-fonts/.*|react-navigation|@react-navigation/.*|@unimodules/.*|unimodules|sentry-expo|native-base|react-native-svg|react-native-reanimated|react-native-gesture-handler|@testing-library/react-native)',
  ],
};
