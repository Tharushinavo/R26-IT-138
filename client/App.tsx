import React from 'react';
import { StatusBar } from 'expo-status-bar';
import { NavigationContainer } from '@react-navigation/native';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import { SafeAreaProvider } from 'react-native-safe-area-context';

import { LanguageProvider, useLanguage } from './src/i18n/LanguageContext';
import LogoScreen from './src/screens/LogoScreen';
import SplashScreen from './src/screens/SplashScreen';
import LanguageSelectScreen from './src/screens/LanguageSelectScreen';
import LoginScreen from './src/screens/LoginScreen';
import SignUpScreen from './src/screens/SignUpScreen';
import WelcomeScreen from './src/screens/WelcomeScreen';
import StudentDashboard from './src/screens/StudentDashboard';
import MathActivityScreen from './src/screens/MathActivityScreen';
import ProfileResultScreen from './src/screens/ProfileResultScreen';
import ProfileHistoryScreen from './src/screens/ProfileHistoryScreen';
import TeacherDashboard from './src/screens/TeacherDashboard';
import { colors } from './src/theme';

export type RootStackParamList = {
  Logo: undefined;
  Splash: undefined;
  LanguageSelect: undefined;
  Login: undefined;
  SignUp: undefined;
  Welcome: undefined;
  StudentDashboard: { studentId: string; role?: string };
  MathActivity: { studentId: string };
  ProfileResult: { studentId: string; sessionId?: string };
  ProfileHistory: { studentId: string };
  TeacherDashboard: { teacherId: string };
};

const Stack = createNativeStackNavigator<RootStackParamList>();

function AppNavigator() {
  const { t } = useLanguage();
  return (
    <NavigationContainer>
      <StatusBar style="dark" />
      <Stack.Navigator
        initialRouteName="Logo"
        screenOptions={{
          headerStyle: { backgroundColor: colors.surfaceSoft },
          headerTintColor: colors.textWarm,
          headerTitleStyle: { fontWeight: '800' },
          contentStyle: { backgroundColor: colors.background },
        }}
      >
        <Stack.Screen name="Logo" component={LogoScreen} options={{ headerShown: false }} />
        <Stack.Screen name="Splash" component={SplashScreen} options={{ headerShown: false }} />
        <Stack.Screen name="LanguageSelect" component={LanguageSelectScreen} options={{ headerShown: false }} />
        <Stack.Screen name="Login" component={LoginScreen} options={{ title: t.nav.signIn, headerBackVisible: false }} />
        <Stack.Screen name="SignUp" component={SignUpScreen} options={{ title: t.nav.signUp, headerBackVisible: false }} />
        <Stack.Screen name="Welcome" component={WelcomeScreen} options={{ headerShown: false }} />
        <Stack.Screen name="StudentDashboard" component={StudentDashboard} options={{ title: t.nav.mathsMate, headerBackVisible: false }} />
        <Stack.Screen name="MathActivity" component={MathActivityScreen} options={{ title: t.nav.mathActivity }} />
        <Stack.Screen name="ProfileResult" component={ProfileResultScreen} options={{ title: t.nav.cognitiveProfile }} />
        <Stack.Screen name="ProfileHistory" component={ProfileHistoryScreen} options={{ title: t.nav.profileHistory }} />
        <Stack.Screen name="TeacherDashboard" component={TeacherDashboard} options={{ title: t.nav.teacherDashboard, headerBackVisible: false }} />
      </Stack.Navigator>
    </NavigationContainer>
  );
}

export default function App() {
  return (
    <SafeAreaProvider>
      <LanguageProvider>
        <AppNavigator />
      </LanguageProvider>
    </SafeAreaProvider>
  );
}
