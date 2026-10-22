import { Stack } from 'expo-router';

export default function AuthLayout() {
  // `animation: 'none'` for WEB PARITY. React Navigation's native stack slides a new screen in
  // from the right on Android, which the web build never did -- the same navigation felt like a
  // different app on a phone. Matching web means no slide.
  return <Stack screenOptions={{ animation: 'none', headerShown: false }} />;
}
