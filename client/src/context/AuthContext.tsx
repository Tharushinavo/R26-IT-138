/**
 * AuthContext - Global authentication state management
 * Provides user session, login, register, logout functionality
 * with automatic token persistence via AsyncStorage.
 */
import React, { createContext, useContext, useEffect, useState, useCallback } from 'react';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { api, type User, type UserRole, type LoginRequest, type RegisterRequest } from '../api/client';

// Storage keys (matching api/client.ts)
const TOKEN_KEY = 'mm.authToken';
const USER_KEY = 'mm.authUser';

interface AuthState {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  role: UserRole | null;
}

interface AuthContextType extends AuthState {
  login: (credentials: LoginRequest) => Promise<User>;
  register: (data: RegisterRequest) => Promise<User>;
  logout: () => Promise<void>;
  refreshUser: () => Promise<void>;
  checkAuth: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [state, setState] = useState<AuthState>({
    user: null,
    isAuthenticated: false,
    isLoading: true,
    role: null,
  });

  // Check for existing session on mount
  const checkAuth = useCallback(async () => {
    try {
      const [token, userJson] = await AsyncStorage.multiGet([TOKEN_KEY, USER_KEY]);
      
      if (token[1] && userJson[1]) {
        const user = JSON.parse(userJson[1]) as User;
        setState({
          user,
          isAuthenticated: true,
          isLoading: false,
          role: user.role,
        });
      } else {
        setState({
          user: null,
          isAuthenticated: false,
          isLoading: false,
          role: null,
        });
      }
    } catch (error) {
      console.error('Auth check failed:', error);
      setState({
        user: null,
        isAuthenticated: false,
        isLoading: false,
        role: null,
      });
    }
  }, []);

  useEffect(() => {
    checkAuth();
  }, [checkAuth]);

  const login = useCallback(async (credentials: LoginRequest): Promise<User> => {
    const res = await api.login(credentials);
    setState({
      user: res.user,
      isAuthenticated: true,
      isLoading: false,
      role: res.user.role,
    });
    return res.user;
  }, []);

  const register = useCallback(async (data: RegisterRequest): Promise<User> => {
    const res = await api.register(data);
    setState({
      user: res.user,
      isAuthenticated: true,
      isLoading: false,
      role: res.user.role,
    });
    return res.user;
  }, []);

  const logout = useCallback(async () => {
    await api.logout();
    setState({
      user: null,
      isAuthenticated: false,
      isLoading: false,
      role: null,
    });
  }, []);

  const refreshUser = useCallback(async () => {
    try {
      const user = await api.getCurrentUser();
      await AsyncStorage.setItem(USER_KEY, JSON.stringify(user));
      setState(prev => ({
        ...prev,
        user,
        role: user.role,
      }));
    } catch (error) {
      console.error('Failed to refresh user:', error);
      // If refresh fails, log out
      await logout();
    }
  }, [logout]);

  const value: AuthContextType = {
    ...state,
    login,
    register,
    logout,
    refreshUser,
    checkAuth,
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextType {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}

// Helper hook for role-based checks
export function useIsTeacher(): boolean {
  const { role } = useAuth();
  return role === 'teacher' || role === 'admin';
}

export function useIsStudent(): boolean {
  const { role } = useAuth();
  return role === 'student';
}
