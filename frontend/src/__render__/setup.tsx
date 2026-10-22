// Shared setup for the render tests. Everything mocked here is a NATIVE or NAVIGATION boundary --
// something that cannot run under Jest at all -- never application logic. The point of these tests
// is that the real components render; mocking the component under test would defeat them.

// RNTL 14 ships its matchers (toBeOnTheScreen, toBeEnabled, ...) built in -- the separate
// extend-expect entry point that older guides import no longer exists.

// Safe-area insets: the real provider reads them from the native module. The library ships this
// mock for exactly this purpose, so the screens get the zero-inset values they would on a device
// with no notch rather than crashing on a missing native module.
jest.mock('react-native-safe-area-context', () => {
  const inset = { bottom: 0, left: 0, right: 0, top: 0 };
  const actual = jest.requireActual('react-native-safe-area-context');
  return {
    ...actual,
    SafeAreaConsumer: ({ children }: { children: (i: typeof inset) => React.ReactNode }) => children(inset),
    SafeAreaProvider: ({ children }: { children: React.ReactNode }) => children,
    SafeAreaView: actual.SafeAreaView,
    useSafeAreaFrame: () => ({ height: 852, width: 393, x: 0, y: 0 }),
    useSafeAreaInsets: () => inset,
  };
});

// expo-blur renders a native view. A plain View keeps layout honest without the native module.
jest.mock('expo-blur', () => {
  const { View } = jest.requireActual('react-native');
  return { BlurView: View };
});

// expo-image likewise. `testID` passes through so a test can still assert artwork is present.
jest.mock('expo-image', () => {
  const { Image } = jest.requireActual('react-native');
  return { Image };
});

// Icon fonts are a native boundary (@expo/vector-icons pulls in expo-font's loader). The Proxy
// covers every icon set without listing them, and each icon renders its `name` as text so a test
// can still assert WHICH icon appeared -- mocking it to null would hide a wrong or missing icon.
jest.mock('@expo/vector-icons', () => {
  const React = jest.requireActual('react');
  const { Text } = jest.requireActual('react-native');
  const makeIconSet = (setName: string) =>
    function MockIcon({ name, ...rest }: { name?: string }) {
      return React.createElement(Text, { accessible: false, ...rest }, `${setName}:${name}`);
    };
  return new Proxy({}, { get: (_target, key: string) => makeIconSet(key) });
});

jest.mock('expo-haptics', () => ({
  notificationAsync: jest.fn(),
  NotificationFeedbackType: { Success: 'success', Warning: 'warning' },
}));

jest.mock('expo-crypto', () => ({ randomUUID: () => '00000000-0000-4000-8000-000000000000' }));

// expo-router's real implementation needs a mounted navigator. These are the only two surfaces the
// screens under test touch.
jest.mock('expo-router', () => ({
  router: { push: jest.fn(), replace: jest.fn(), back: jest.fn() },
  useLocalSearchParams: () => ({}),
  Redirect: () => null,
}));

// Silence the act() noise React 19 emits for the background effects these screens legitimately
// start (readiness checks, prefetches). Real failures still surface -- this filters one message.
const realError = console.error;
beforeAll(() => {
  console.error = (...args: unknown[]) => {
    if (typeof args[0] === 'string' && args[0].includes('not wrapped in act')) return;
    realError(...(args as Parameters<typeof console.error>));
  };
});
afterAll(() => {
  console.error = realError;
});
