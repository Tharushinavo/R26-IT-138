/**
 * AuthContext - Global authentication state management
 * Provides user session, login, register, logout functionality
 * with automatic token persistence via AsyncStorage.
 * Includes 1-hour session expiry with kid-friendly timeout alert.
 */
import React, {
  createContext,
  useContext,
  useEffect,
  useState,
  useCallback,
  useRef,
} from 'react';
import {
  Animated,
  Image,
  Modal,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from 'react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';
import {
  api,
  getTokenExpiryMs,
  type User,
  type UserRole,
  type LoginRequest,
  type RegisterRequest,
} from '../api/client';
import { useLanguage } from '../i18n/LanguageContext';
import { ANIMAL_IMAGES } from '../assets/animalImages';
import { colors as lightColors, radius, spacing, typography, useAppTheme } from '../theme';

// Storage keys (matching api/client.ts)
const TOKEN_KEY = 'mm.authToken';
const USER_KEY = 'mm.authUser';

interface AuthState {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  role: UserRole | null;
  sessionExpired: boolean;
}

interface AuthContextType extends Omit<AuthState, 'sessionExpired'> {
  login: (credentials: LoginRequest) => Promise<User>;
  register: (data: RegisterRequest) => Promise<User>;
  logout: () => Promise<void>;
  refreshUser: () => Promise<void>;
  checkAuth: () => Promise<void>;
  updateUser: (user: User) => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [state, setState] = useState<AuthState>({
    user: null,
    isAuthenticated: false,
    isLoading: true,
    role: null,
    sessionExpired: false,
  });

  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // ── Session expiry timer ──────────────────────────────────────────────
  const clearExpiryTimer = useCallback(() => {
    if (timerRef.current) {
      clearTimeout(timerRef.current);
      timerRef.current = null;
    }
  }, []);

  const startExpiryTimer = useCallback(async () => {
    clearExpiryTimer();
    const expiryMs = await getTokenExpiryMs();
    if (!expiryMs) return;
    const msLeft = expiryMs - Date.now();
    if (msLeft <= 0) {
      // Stale persisted session. Clear it silently; the timeout modal is only
      // for a session that expires while the app is actively running.
      await api.logout();
      setState({
        user: null,
        isAuthenticated: false,
        isLoading: false,
        role: null,
        sessionExpired: false,
      });
      return;
    }
    timerRef.current = setTimeout(async () => {
      await api.logout();
      setState({
        user: null,
        isAuthenticated: false,
        isLoading: false,
        role: null,
        sessionExpired: true,
      });
    }, msLeft);
  }, [clearExpiryTimer]);

  // ── Check for existing session on mount ───────────────────────────────
  const checkAuth = useCallback(async () => {
    try {
      const [token, userJson] = await AsyncStorage.multiGet([TOKEN_KEY, USER_KEY]);

      if (token[1] && userJson[1]) {
        const expiryMs = await getTokenExpiryMs();
        const hasExpiredBeforeStartup = !expiryMs || Date.now() >= expiryMs;
        if (hasExpiredBeforeStartup) {
          console.log('[auth] stale stored session cleared on startup');
          await api.logout();
          setState({
            user: null,
            isAuthenticated: false,
            isLoading: false,
            role: null,
            sessionExpired: false,
          });
          return;
        }
        const user = JSON.parse(userJson[1]) as User;
        setState({
          user,
          isAuthenticated: true,
          isLoading: false,
          role: user.role,
          sessionExpired: false,
        });
        startExpiryTimer();
      } else {
        setState({
          user: null,
          isAuthenticated: false,
          isLoading: false,
          role: null,
          sessionExpired: false,
        });
      }
    } catch (error) {
      console.error('Auth check failed:', error);
      setState({
        user: null,
        isAuthenticated: false,
        isLoading: false,
        role: null,
        sessionExpired: false,
      });
    }
  }, [startExpiryTimer]);

  useEffect(() => {
    checkAuth();
    return () => clearExpiryTimer();
  }, [checkAuth, clearExpiryTimer]);

  // ── Auth actions ──────────────────────────────────────────────────────
  const login = useCallback(
    async (credentials: LoginRequest): Promise<User> => {
      const res = await api.login(credentials);
      setState({
        user: res.user,
        isAuthenticated: true,
        isLoading: false,
        role: res.user.role,
        sessionExpired: false,
      });
      startExpiryTimer();
      return res.user;
    },
    [startExpiryTimer],
  );

  const register = useCallback(
    async (data: RegisterRequest): Promise<User> => {
      const res = await api.register(data);
      setState({
        user: res.user,
        isAuthenticated: true,
        isLoading: false,
        role: res.user.role,
        sessionExpired: false,
      });
      startExpiryTimer();
      return res.user;
    },
    [startExpiryTimer],
  );

  const logout = useCallback(async () => {
    clearExpiryTimer();
    await api.logout();
    setState({
      user: null,
      isAuthenticated: false,
      isLoading: false,
      role: null,
      sessionExpired: false,
    });
  }, [clearExpiryTimer]);

  const refreshUser = useCallback(async () => {
    try {
      const user = await api.getCurrentUser();
      await AsyncStorage.setItem(USER_KEY, JSON.stringify(user));
      setState(prev => ({ ...prev, user, role: user.role }));
    } catch (error) {
      console.error('Failed to refresh user:', error);
      await logout();
    }
  }, [logout]);

  // Dismiss the session-expired modal (user will be sent to Login)
  const dismissExpiry = useCallback(() => {
    setState(prev => ({ ...prev, sessionExpired: false }));
  }, []);

  const updateUser = useCallback((user: User) => {
    setState(prev => ({ ...prev, user, role: user.role }));
  }, []);

  const value: AuthContextType = {
    user: state.user,
    isAuthenticated: state.isAuthenticated,
    isLoading: state.isLoading,
    role: state.role,
    login,
    register,
    logout,
    refreshUser,
    checkAuth,
    updateUser,
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
      <SessionExpiredModal
        visible={state.sessionExpired}
        onDismiss={dismissExpiry}
      />
    </AuthContext.Provider>
  );
}

// ── Kid-friendly session timeout modal ──────────────────────────────────

function SessionExpiredModal({
  visible,
  onDismiss,
}: {
  visible: boolean;
  onDismiss: () => void;
}) {
  const { t } = useLanguage();
  const { colors, isDark } = useAppTheme();
  const mStyles = createModalStyles(colors, isDark ? colors.textInverse : colors.textWarm);
  const bounce = useRef(new Animated.Value(0)).current;
  const scale = useRef(new Animated.Value(0.5)).current;

  useEffect(() => {
    if (!visible) return;
    // Entrance spring
    Animated.spring(scale, {
      toValue: 1,
      friction: 5,
      useNativeDriver: true,
    }).start();
    // Mascot gentle bounce loop
    Animated.loop(
      Animated.sequence([
        Animated.timing(bounce, {
          toValue: -12,
          duration: 600,
          useNativeDriver: true,
        }),
        Animated.timing(bounce, {
          toValue: 0,
          duration: 600,
          useNativeDriver: true,
        }),
      ]),
    ).start();
    return () => {
      scale.setValue(0.5);
      bounce.setValue(0);
    };
  }, [visible, bounce, scale]);

  if (!visible) return null;

  return (
    <Modal transparent animationType="fade" visible={visible}>
      <View style={mStyles.overlay}>
        <Animated.View
          style={[mStyles.card, { transform: [{ scale }] }]}
        >
          {/* Sleeping mascot */}
          <Animated.View
            style={{ transform: [{ translateY: bounce }] }}
          >
            <View style={mStyles.mascotCircle}>
              <Image
                source={ANIMAL_IMAGES[5]}
                style={mStyles.mascot}
                resizeMode="contain"
              />
            </View>
          </Animated.View>

          {/* Zzz bubbles */}
          <View style={mStyles.zzzRow}>
            <Text style={[mStyles.zzz, { fontSize: 18 }]}>💤</Text>
            <Text style={[mStyles.zzz, { fontSize: 26 }]}>💤</Text>
            <Text style={[mStyles.zzz, { fontSize: 20 }]}>💤</Text>
          </View>

          <Text style={mStyles.title}>{t.sessionTimeout.title}</Text>
          <Text style={mStyles.message}>{t.sessionTimeout.message}</Text>

          <TouchableOpacity
            style={mStyles.button}
            onPress={onDismiss}
            activeOpacity={0.8}
          >
            <Text style={mStyles.buttonText}>
              {t.sessionTimeout.button}
            </Text>
          </TouchableOpacity>
        </Animated.View>
      </View>
    </Modal>
  );
}

const createModalStyles = (colors: typeof lightColors, buttonTextColor: string) => StyleSheet.create({
  overlay: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.55)',
    justifyContent: 'center',
    alignItems: 'center',
    padding: spacing.lg,
  },
  card: {
    width: '100%',
    maxWidth: 340,
    backgroundColor: colors.background,
    borderRadius: radius.xl,
    padding: spacing.xl,
    alignItems: 'center',
    borderWidth: 3,
    borderColor: colors.warmYellow,
    shadowColor: 'rgba(255,180,0,0.4)',
    shadowOffset: { width: 0, height: 10 },
    shadowOpacity: 1,
    shadowRadius: 20,
    elevation: 10,
  },
  mascotCircle: {
    width: 110,
    height: 110,
    borderRadius: 55,
    backgroundColor: colors.warmYellowSoft,
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 4,
    borderColor: colors.warmYellow,
    marginBottom: spacing.sm,
  },
  mascot: { width: 85, height: 85 },
  zzzRow: {
    flexDirection: 'row',
    gap: 6,
    marginBottom: spacing.md,
  },
  zzz: { opacity: 0.7 },
  title: {
    ...typography.title,
    color: colors.textWarm,
    textAlign: 'center',
    marginBottom: spacing.sm,
  },
  message: {
    ...typography.body,
    color: colors.text,
    textAlign: 'center',
    lineHeight: 24,
    marginBottom: spacing.lg,
  },
  button: {
    backgroundColor: colors.warmYellow,
    paddingVertical: 14,
    paddingHorizontal: spacing.xl,
    borderRadius: radius.pill,
    shadowColor: 'rgba(255,180,0,0.4)',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 1,
    shadowRadius: 8,
    elevation: 4,
  },
  buttonText: {
    ...typography.subtitle,
    color: buttonTextColor,
    textAlign: 'center',
  },
});

// ── Hooks ───────────────────────────────────────────────────────────────

export function useAuth(): AuthContextType {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}

export function useIsTeacher(): boolean {
  const { role } = useAuth();
  return role === 'teacher' || role === 'admin';
}

export function useIsStudent(): boolean {
  const { role } = useAuth();
  return role === 'student';
}
