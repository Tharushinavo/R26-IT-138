import React from 'react';
import { StyleSheet, Platform } from 'react-native';
import { StatusBar } from 'expo-status-bar';
import { NavigationContainer } from '@react-navigation/native';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';
import { SafeAreaProvider } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';

import { LanguageProvider, useLanguage } from './src/i18n/LanguageContext';
import { AuthProvider } from './src/context/AuthContext';
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
import TeacherHomeScreen from './src/screens/TeacherHomeScreen';
import TeacherDashboard from './src/screens/TeacherDashboard';
import CognitiveQuestionsScreen from './src/screens/CognitiveQuestionsScreen';
import SettingsScreen from './src/screens/SettingsScreen';
import { ThemeProvider, lightColors, spacing, useAppTheme } from './src/theme';

// ── Type definitions ────────────────────────────────────────────────────

export type RootStackParamList = {
  Logo: undefined;
  Splash: undefined;
  LanguageSelect: undefined;
  Login: undefined;
  SignUp: undefined;
  Welcome: undefined;
  StudentTabs: { studentId: string; role?: string };
  TeacherTabs: { teacherId: string };
  // These are pushed on top of the tab navigators
  MathActivity: { studentId: string; sessionId?: string; quizState?: any };
  ProfileResult: { studentId: string; sessionId?: string };
  ProfileHistory: { studentId: string };
  TeacherDashboard: { teacherId: string };
  CognitiveQuestions: { teacherId: string };
};

export type StudentTabParamList = {
  StudentHome: { studentId: string };
  StudentActivity: { studentId: string };
  StudentProfile: { studentId: string };
  StudentHistory: { studentId: string };
  StudentSettings: undefined;
};

type TeacherTabParamList = {
  TeacherHome: { teacherId: string };
  TeacherStudents: { teacherId: string };
  TeacherQuestions: { teacherId: string };
  TeacherSettings: undefined;
};

// ── Navigators ──────────────────────────────────────────────────────────

const Stack = createNativeStackNavigator<RootStackParamList>();
const StudentTab = createBottomTabNavigator<StudentTabParamList>();
const TeacherTab = createBottomTabNavigator<TeacherTabParamList>();

// ── Tab icon helper (Ionicons) ──────────────────────────────────────────

type IoniconsName = React.ComponentProps<typeof Ionicons>['name'];

function TabIcon({ name, focused, color }: { name: IoniconsName; focused: boolean; color: string }) {
  return <Ionicons name={name} size={22} color={color} />;
}

// ── Student Bottom Tabs ─────────────────────────────────────────────────

function StudentTabNavigator({ route }: any) {
  const { t } = useLanguage();
  const { colors } = useAppTheme();
  const { studentId } = route.params as { studentId: string };
  const tabStyles = createTabStyles(colors);

  return (
    <StudentTab.Navigator
      screenOptions={{
        headerStyle: { backgroundColor: colors.surface, height: 100, elevation: 8, shadowOpacity: 0.15 },
        headerTintColor: colors.textWarm,
        headerTitleStyle: { fontWeight: '800', fontSize: 20 },
        headerTitleAlign: 'center',
        tabBarStyle: tabStyles.tabBar,
        tabBarActiveTintColor: colors.textWarm,
        tabBarInactiveTintColor: colors.textMuted,
        tabBarLabelStyle: tabStyles.tabLabel,
      }}
    >
      <StudentTab.Screen
        name="StudentHome"
        component={StudentDashboard as React.ComponentType<any>}
        initialParams={{ studentId }}
        options={{
          title: t.tabs.home,
          headerTitle: t.nav.mathsMate,
          tabBarIcon: ({ focused, color }) => <TabIcon name={focused ? 'home' : 'home-outline'} focused={focused} color={color} />,
        }}
      />
      <StudentTab.Screen
        name="StudentActivity"
        component={MathActivityScreen as React.ComponentType<any>}
        initialParams={{ studentId }}
        options={{
          title: t.tabs.activity,
          headerTitle: t.nav.mathActivity,
          tabBarIcon: ({ focused, color }) => <TabIcon name={focused ? 'game-controller' : 'game-controller-outline'} focused={focused} color={color} />,
        }}
      />
      <StudentTab.Screen
        name="StudentProfile"
        component={ProfileResultScreen as React.ComponentType<any>}
        initialParams={{ studentId }}
        options={{
          title: t.tabs.profile,
          headerTitle: t.nav.cognitiveProfile,
          tabBarIcon: ({ focused, color }) => <TabIcon name={focused ? 'person-circle' : 'person-circle-outline'} focused={focused} color={color} />,
        }}
      />
      <StudentTab.Screen
        name="StudentHistory"
        component={ProfileHistoryScreen as React.ComponentType<any>}
        initialParams={{ studentId }}
        options={{
          title: t.tabs.history,
          headerTitle: t.nav.profileHistory,
          tabBarIcon: ({ focused, color }) => <TabIcon name={focused ? 'bar-chart' : 'bar-chart-outline'} focused={focused} color={color} />,
        }}
      />
      <StudentTab.Screen
        name="StudentSettings"
        component={SettingsScreen}
        options={{
          title: t.tabs.settings,
          headerTitle: t.tabs.settings,
          tabBarIcon: ({ focused, color }) => <TabIcon name={focused ? 'settings' : 'settings-outline'} focused={focused} color={color} />,
        }}
      />
    </StudentTab.Navigator>
  );
}

// ── Teacher Bottom Tabs ─────────────────────────────────────────────────

function TeacherTabNavigator({ route }: any) {
  const { t } = useLanguage();
  const { colors } = useAppTheme();
  const { teacherId } = route.params as { teacherId: string };
  const tabStyles = createTabStyles(colors);

  return (
    <TeacherTab.Navigator
      screenOptions={{
        headerStyle: { backgroundColor: colors.surface, height: 100, elevation: 8, shadowOpacity: 0.15 },
        headerTintColor: colors.textWarm,
        headerTitleStyle: { fontWeight: '800', fontSize: 20 },
        headerTitleAlign: 'center',
        tabBarStyle: tabStyles.tabBar,
        tabBarActiveTintColor: colors.textWarm,
        tabBarInactiveTintColor: colors.textMuted,
        tabBarLabelStyle: tabStyles.tabLabel,
      }}
    >
      <TeacherTab.Screen
        name="TeacherHome"
        component={TeacherHomeScreen as React.ComponentType<any>}
        initialParams={{ teacherId }}
        options={{
          title: t.tabs.home,
          headerTitle: t.nav.teacherHome,
          tabBarIcon: ({ focused, color }) => <TabIcon name={focused ? 'home' : 'home-outline'} focused={focused} color={color} />,
        }}
      />
      <TeacherTab.Screen
        name="TeacherStudents"
        component={TeacherDashboard as React.ComponentType<any>}
        initialParams={{ teacherId }}
        options={{
          title: t.tabs.students,
          headerTitle: t.nav.teacherDashboard,
          tabBarIcon: ({ focused, color }) => <TabIcon name={focused ? 'people' : 'people-outline'} focused={focused} color={color} />,
        }}
      />
      <TeacherTab.Screen
        name="TeacherQuestions"
        component={CognitiveQuestionsScreen as React.ComponentType<any>}
        initialParams={{ teacherId }}
        options={{
          title: t.tabs.questions,
          headerTitle: t.nav.cognitiveQuestions,
          tabBarIcon: ({ focused, color }) => <TabIcon name={focused ? 'document-text' : 'document-text-outline'} focused={focused} color={color} />,
        }}
      />
      <TeacherTab.Screen
        name="TeacherSettings"
        component={SettingsScreen}
        options={{
          title: t.tabs.settings,
          headerTitle: t.tabs.settings,
          tabBarIcon: ({ focused, color }) => <TabIcon name={focused ? 'settings' : 'settings-outline'} focused={focused} color={color} />,
        }}
      />
    </TeacherTab.Navigator>
  );
}

// ── Main App Navigator ──────────────────────────────────────────────────

function AppNavigator() {
  const { t } = useLanguage();
  const { colors, isDark } = useAppTheme();
  return (
    <NavigationContainer>
      <StatusBar style={isDark ? 'light' : 'dark'} />
      <Stack.Navigator
        initialRouteName="Logo"
        screenOptions={{
          headerStyle: { backgroundColor: colors.surface },
          headerTintColor: colors.textWarm,
          headerTitleStyle: { fontWeight: '800', fontSize: 20 },
          headerTitleAlign: 'center',
          headerLargeTitle: false,
          contentStyle: { backgroundColor: colors.background },
        }}
      >
        {/* Onboarding / Auth (no back button possible) */}
        <Stack.Screen name="Logo" component={LogoScreen} options={{ headerShown: false }} />
        <Stack.Screen name="Splash" component={SplashScreen} options={{ headerShown: false }} />
        <Stack.Screen name="LanguageSelect" component={LanguageSelectScreen} options={{ headerShown: false }} />
        <Stack.Screen name="Login" component={LoginScreen} options={{ title: t.nav.signIn, headerBackVisible: false }} />
        <Stack.Screen name="SignUp" component={SignUpScreen} options={{ title: t.nav.signUp, headerBackVisible: false }} />
        <Stack.Screen name="Welcome" component={WelcomeScreen} options={{ headerShown: false }} />

        {/* Role-based tab containers (no back into auth) */}
        <Stack.Screen
          name="StudentTabs"
          component={StudentTabNavigator}
          options={{ headerShown: false, gestureEnabled: false }}
        />
        <Stack.Screen
          name="TeacherTabs"
          component={TeacherTabNavigator}
          options={{ headerShown: false, gestureEnabled: false }}
        />

        {/* Screens pushed ON TOP of tabs (deep links from tab screens) */}
        <Stack.Screen name="MathActivity" component={MathActivityScreen} options={{ title: t.nav.mathActivity }} />
        <Stack.Screen name="ProfileResult" component={ProfileResultScreen} options={{ title: t.nav.cognitiveProfile }} />
        <Stack.Screen name="ProfileHistory" component={ProfileHistoryScreen} options={{ title: t.nav.profileHistory }} />
        <Stack.Screen name="TeacherDashboard" component={TeacherDashboard} options={{ title: t.nav.teacherDashboard }} />
        <Stack.Screen name="CognitiveQuestions" component={CognitiveQuestionsScreen} options={{ title: t.nav.cognitiveQuestions }} />
      </Stack.Navigator>
    </NavigationContainer>
  );
}

// ── Tab bar styles ──────────────────────────────────────────────────────

const createTabStyles = (colors: typeof lightColors) => StyleSheet.create({
  tabBar: {
    position: 'absolute',
    bottom: Platform.OS === 'ios' ? 16 : 10,
    left: 16,
    right: 16,
    backgroundColor: colors.surface,
    borderRadius: 24,
    borderTopWidth: 0,
    paddingTop: 8,
    paddingBottom: 10,
    height: 64,
    elevation: 12,
    shadowColor: colors.shadow,
    shadowOffset: { width: 0, height: -4 },
    shadowOpacity: 0.8,
    shadowRadius: 12,
    borderWidth: 1,
    borderColor: colors.border,
  },
  tabLabel: {
    fontSize: 10,
    fontWeight: '700',
    marginTop: 2,
  },
});

// ── App entry ───────────────────────────────────────────────────────────

export default function App() {
  return (
    <SafeAreaProvider>
      <LanguageProvider>
        <ThemeProvider>
          <AuthProvider>
            <AppNavigator />
          </AuthProvider>
        </ThemeProvider>
      </LanguageProvider>
    </SafeAreaProvider>
  );
}
