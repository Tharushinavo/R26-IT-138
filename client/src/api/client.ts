import AsyncStorage from '@react-native-async-storage/async-storage';

const API_URL = process.env.EXPO_PUBLIC_API_BASE ?? 'http://localhost:8000';

// ── Storage Keys ──
const TOKEN_KEY = 'mm.authToken';
const USER_KEY = 'mm.authUser';

// ── Types matching backend schemas ──

export type Level = 'low' | 'medium' | 'high';
export type SpeedLevel = 'Slow' | 'Moderate' | 'Fast';

export interface Question {
  id: string;
  question_code?: string;
  topic: string;
  difficulty: 'Easy' | 'Medium' | 'Hard';
  question_text: string;
  correct_answer: string;
  options?: string[];
}

export interface InteractionEvent {
  student_id: string;
  session_id: string;
  question_id: string;
  topic: string;
  difficulty: 'Easy' | 'Medium' | 'Hard';
  response_time_sec: number;
  attempts: number;
  is_correct: boolean;
  hint_used: boolean;
  click_count: number;
  session_time_sec: number;
  time_between_actions: number;
  error_type: 'none' | 'calculation' | 'conceptual' | 'careless' | 'unknown';
  expected_answer?: string;
  given_answer?: string;
}

export interface CognitiveFeatures {
  accuracy: number;
  avg_response_time_ms: number;
  response_time_std_ms: number;
  avg_attempts: number;
  retry_rate: number;
  hint_rate: number;
  answer_change_rate: number;
  total_questions: number;
}

export interface CognitiveProfile {
  student_id: string;
  session_id?: string;
  memory_level: Level;
  attention_level: Level;
  number_sense_level: Level;
  processing_speed_level: SpeedLevel;
  confidence_score?: number;
  recommendation?: string;
  model_version?: string;
  features: CognitiveFeatures;
  generated_at: string;
}

export interface StudentSummary {
  student_id: string;
  student_code?: string;
  name?: string;
  total_interactions: number;
  latest_profile?: CognitiveProfile;
  last_activity_date?: string;
}

// ── Auth Types ──

export type UserRole = 'student' | 'teacher' | 'parent' | 'admin';

export interface User {
  id: string;
  email?: string;
  full_name?: string;
  role: UserRole;
  grade?: string;
  created_at?: string;
}

export interface AuthResponse {
  message: string;
  user: User;
  access_token: string;
  token_type: 'bearer';
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface RegisterRequest {
  email: string;
  password: string;
  full_name: string;
  role: UserRole;
}

// ── Token Storage ──

export async function getStoredToken(): Promise<string | null> {
  return AsyncStorage.getItem(TOKEN_KEY);
}

export async function setStoredToken(token: string): Promise<void> {
  await AsyncStorage.setItem(TOKEN_KEY, token);
}

export async function removeStoredToken(): Promise<void> {
  await AsyncStorage.removeItem(TOKEN_KEY);
}

export async function getStoredUser(): Promise<User | null> {
  const json = await AsyncStorage.getItem(USER_KEY);
  return json ? JSON.parse(json) : null;
}

export async function setStoredUser(user: User): Promise<void> {
  await AsyncStorage.setItem(USER_KEY, JSON.stringify(user));
}

export async function removeStoredUser(): Promise<void> {
  await AsyncStorage.removeItem(USER_KEY);
}

export async function clearAuth(): Promise<void> {
  await AsyncStorage.multiRemove([TOKEN_KEY, USER_KEY]);
}

// ── HTTP helper ──

async function request<T>(path: string, init: RequestInit = {}, auth: boolean = false): Promise<T> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(init.headers as Record<string, string> || {}),
  };
  
  // Attach auth token if required or available
  if (auth) {
    const token = await getStoredToken();
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }
  }
  
  const res = await fetch(`${API_URL}${path}`, {
    ...init,
    headers,
  });
  const text = await res.text();
  const data = text ? JSON.parse(text) : null;
  if (!res.ok) {
    const detail = (data && (data.detail || data.message)) || res.statusText;
    throw new Error(typeof detail === 'string' ? detail : 'Request failed');
  }
  return data as T;
}

// ── API methods ──

export const api = {
  baseUrl: API_URL,

  // Questions
  getQuestions(topic?: string, difficulty?: string) {
    const params = new URLSearchParams();
    if (topic) params.set('topic', topic);
    if (difficulty) params.set('difficulty', difficulty);
    const qs = params.toString();
    return request<Question[]>(`/questions${qs ? `?${qs}` : ''}`);
  },

  // Interactions
  logInteractions(events: InteractionEvent[]) {
    return request<{ message: string; id?: string }>('/interactions', {
      method: 'POST',
      body: JSON.stringify({ events }),
    });
  },

  logSingleInteraction(interaction: Omit<InteractionEvent, 'session_id'>) {
    return request<{ message: string; id?: string }>('/interactions/single', {
      method: 'POST',
      body: JSON.stringify(interaction),
    });
  },

  // Profiles
  generateProfile(params: {
    student_id: string;
    session_id?: string;
    events: InteractionEvent[];
  }) {
    return request<CognitiveProfile>('/profiles/generate', {
      method: 'POST',
      body: JSON.stringify(params),
    });
  },

  predictProfile(params: {
    student_id: string;
    question_id: string;
    topic?: string;
    difficulty?: string;
    response_time_sec: number;
    attempts: number;
    is_correct: boolean;
    hint_used?: boolean;
    click_count?: number;
    session_time_sec?: number;
    time_between_actions?: number;
    error_type?: string;
  }) {
    return request<CognitiveProfile>('/profiles/predict', {
      method: 'POST',
      body: JSON.stringify(params),
    });
  },

  getLatestProfile(studentId: string, sessionId?: string) {
    const q = sessionId ? `?session_id=${encodeURIComponent(sessionId)}` : '';
    return request<CognitiveProfile>(
      `/profiles/${encodeURIComponent(studentId)}/latest${q}`,
    );
  },

  getProfileHistory(studentId: string, limit = 20) {
    return request<CognitiveProfile[]>(
      `/profiles/${encodeURIComponent(studentId)}/history?limit=${limit}`,
    );
  },

  // ── Auth ──
  
  async login(credentials: LoginRequest): Promise<AuthResponse> {
    const res = await request<AuthResponse>('/auth/login', {
      method: 'POST',
      body: JSON.stringify(credentials),
    });
    // Store token and user
    await setStoredToken(res.access_token);
    await setStoredUser(res.user);
    return res;
  },

  async register(data: RegisterRequest): Promise<AuthResponse> {
    const res = await request<AuthResponse>('/auth/register', {
      method: 'POST',
      body: JSON.stringify(data),
    });
    // Store token and user
    await setStoredToken(res.access_token);
    await setStoredUser(res.user);
    return res;
  },

  async getCurrentUser(): Promise<User> {
    return request<User>('/auth/me', {}, true);
  },

  async refreshToken(): Promise<{ access_token: string; token_type: 'bearer' }> {
    const res = await request<{ access_token: string; token_type: 'bearer' }>('/auth/refresh', {
      method: 'POST',
    }, true);
    await setStoredToken(res.access_token);
    return res;
  },

  async logout(): Promise<void> {
    await clearAuth();
  },

  // Teacher (requires auth)
  getStudentSummary(studentId: string) {
    return request<StudentSummary>(
      `/teacher/students/${encodeURIComponent(studentId)}/summary`,
      {},
      true
    );
  },

  getStudentsList() {
    return request<StudentSummary[]>('/teacher/students', {}, true);
  },

  // Health
  status() {
    return request<{ model_loaded: boolean; model_path: string }>(
      '/profiles/status',
    );
  },

  health() {
    return request<{ status: string; service: string }>('/health');
  },
};
