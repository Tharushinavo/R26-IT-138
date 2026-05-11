import AsyncStorage from '@react-native-async-storage/async-storage';

const API_URL = process.env.EXPO_PUBLIC_API_BASE ?? 'http://localhost:8000';
const DEBUG_API = true;

// ── Storage Keys ──
const TOKEN_KEY = 'mm.authToken';
const USER_KEY = 'mm.authUser';
const EXPIRY_KEY = 'mm.authExpiry';

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

export interface QuestionInput {
  question_code?: string;
  topic: string;
  difficulty: 'Easy' | 'Medium' | 'Hard';
  question_text: string;
  correct_answer: string;
  options?: string[];
}

export type AIQuestionProvider = 'openai' | 'gemini' | 'deepseek';

export interface AIQuestionGenerateRequest {
  provider: AIQuestionProvider;
  api_key: string;
  topic: string;
  difficulty: 'Easy' | 'Medium' | 'Hard';
  count: number;
  model?: string;
  instructions?: string;
}

export interface AIQuestionGenerateSimpleRequest {
  topic: string;
  difficulty: 'Easy' | 'Medium' | 'Hard';
  count: number;
  instructions?: string;
}

export interface QuestionDraft {
  topic: string;
  difficulty: 'Easy' | 'Medium' | 'Hard';
  question_text: string;
  correct_answer: string;
  options?: string[];
  question_code?: string;
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

export interface TopicPerformance {
  topic: string;
  total_questions: number;
  accuracy: number;
  avg_response_time_sec: number;
  retry_rate: number;
  hint_rate: number;
}

export interface StudentPerformance {
  total_questions: number;
  completed_sessions: number;
  accuracy: number;
  avg_response_time_sec: number;
  avg_attempts: number;
  retry_rate: number;
  hint_rate: number;
  last_topic?: string;
  topics: TopicPerformance[];
}

export interface StudentSummary {
  student_id: string;
  student_code?: string;
  name?: string;
  total_interactions: number;
  latest_profile?: CognitiveProfile;
  last_activity_date?: string;
  grade?: string;
  performance: StudentPerformance;
}

export interface TeacherDashboardStats {
  total_students: number;
  students_with_profiles: number;
  total_interactions: number;
  average_accuracy: number;
  average_response_time_sec: number;
  needs_support_count: number;
}

export interface TeacherDashboardResponse {
  stats: TeacherDashboardStats;
  students: StudentSummary[];
}

// ── Auth Types ──

export type UserRole = 'student' | 'teacher' | 'parent' | 'admin';

export interface User {
  id: string;
  email?: string;
  full_name?: string;
  role: UserRole;
  grade?: string;
  avatar_url?: string;
  created_at?: string;
}

export interface ProfileUpdateRequest {
  full_name?: string;
  password?: string;
  avatar_url?: string;
}

export interface AuthResponse {
  message: string;
  user: User;
  access_token: string;
  token_type: 'bearer';
  expires_in: number; // seconds until expiry
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
  await AsyncStorage.multiRemove([TOKEN_KEY, USER_KEY, EXPIRY_KEY]);
}

export async function getTokenExpiryMs(): Promise<number | null> {
  const val = await AsyncStorage.getItem(EXPIRY_KEY);
  return val ? Number(val) : null;
}

export async function isTokenExpired(): Promise<boolean> {
  const expiryMs = await getTokenExpiryMs();
  if (!expiryMs) return true;
  return Date.now() >= expiryMs;
}

// ── HTTP helper ──

async function request<T>(path: string, init: RequestInit = {}, auth: boolean = false): Promise<T> {
  const method = init.method || 'GET';
  if (DEBUG_API) {
    console.log('[api] request start', { method, path, auth, baseUrl: API_URL });
  }
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
  
  let res: Response;
  try {
    res = await fetch(`${API_URL}${path}`, {
      ...init,
      headers,
    });
  } catch (error: any) {
    console.log('[api] request network error', { method, path, message: error?.message });
    throw error;
  }
  const text = await res.text();
  let data: any = null;
  try {
    data = text ? JSON.parse(text) : null;
  } catch {
    // Server returned non-JSON (e.g. HTML error page)
    if (!res.ok) {
      throw new Error(`Server error (${res.status}): ${text.slice(0, 100)}`);
    }
    throw new Error('Invalid server response');
  }
  if (!res.ok) {
    const detail = (data && (data.detail || data.message)) || res.statusText;
    console.log('[api] request failed', { method, path, status: res.status, detail });
    throw new Error(typeof detail === 'string' ? detail : 'Request failed');
  }
  if (DEBUG_API) {
    console.log('[api] request success', { method, path, status: res.status });
  }
  return data as T;
}

// ── API methods ──

export const api = {
  baseUrl: API_URL,

  // Questions
  getQuestions(topic?: string, difficulty?: string, limit = 20) {
    const params = new URLSearchParams();
    if (topic) params.set('topic', topic);
    if (difficulty) params.set('difficulty', difficulty);
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return request<Question[]>(`/questions${qs ? `?${qs}` : ''}`);
  },

  createQuestion(question: QuestionInput) {
    return request<Question>('/questions', {
      method: 'POST',
      body: JSON.stringify(question),
    }, true);
  },

  updateQuestion(questionId: string, patch: Partial<QuestionInput>) {
    return request<Question>(`/questions/${encodeURIComponent(questionId)}`, {
      method: 'PUT',
      body: JSON.stringify(patch),
    }, true);
  },

  deleteQuestion(questionId: string) {
    return request<{ message: string; id?: string }>(
      `/questions/${encodeURIComponent(questionId)}`,
      { method: 'DELETE' },
      true,
    );
  },

  generateQuestionsAI(params: AIQuestionGenerateRequest) {
    return request<Question[]>('/questions/generate', {
      method: 'POST',
      body: JSON.stringify(params),
    }, true);
  },

  generateQuestionsSimple(params: AIQuestionGenerateSimpleRequest) {
    return request<QuestionDraft[]>('/questions/generate-simple', {
      method: 'POST',
      body: JSON.stringify(params),
    }, true);
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
    language?: string;
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
    console.log('[auth] login start', { email: credentials.email });
    const res = await request<AuthResponse>('/auth/login', {
      method: 'POST',
      body: JSON.stringify(credentials),
    });
    // Store token, user, and expiry
    await setStoredToken(res.access_token);
    await setStoredUser(res.user);
    const expiryMs = Date.now() + (res.expires_in ?? 3600) * 1000;
    await AsyncStorage.setItem(EXPIRY_KEY, String(expiryMs));
    console.log('[auth] login success', { userId: res.user.id, role: res.user.role, expiresIn: res.expires_in });
    return res;
  },

  async register(data: RegisterRequest): Promise<AuthResponse> {
    console.log('[auth] register start', { email: data.email, role: data.role });
    const res = await request<AuthResponse>('/auth/register', {
      method: 'POST',
      body: JSON.stringify(data),
    });
    // Store token, user, and expiry
    await setStoredToken(res.access_token);
    await setStoredUser(res.user);
    const expiryMs = Date.now() + (res.expires_in ?? 3600) * 1000;
    await AsyncStorage.setItem(EXPIRY_KEY, String(expiryMs));
    console.log('[auth] register success', { userId: res.user.id, role: res.user.role, expiresIn: res.expires_in });
    return res;
  },

  async updateProfile(data: ProfileUpdateRequest): Promise<AuthResponse> {
    const res = await request<AuthResponse>('/auth/profile', {
      method: 'PUT',
      body: JSON.stringify(data),
    }, true);
    // Update stored token and user with fresh data
    await setStoredToken(res.access_token);
    await setStoredUser(res.user);
    const expiryMs = Date.now() + (res.expires_in ?? 3600) * 1000;
    await AsyncStorage.setItem(EXPIRY_KEY, String(expiryMs));
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

  getTeacherDashboard() {
    return request<TeacherDashboardResponse>('/teacher/dashboard', {}, true);
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
