// Runtime validators for Component D responses, in the style of src/api/runtime-validation.ts:
// a response that does not match the contract is rejected by `requestJson` as 'invalid-response'
// rather than reaching a screen half-formed.

import type {
  DCognitiveFeatures,
  DCognitiveProfile,
  DCognitiveProfileResponse,
  DLatestProfileResponse,
  DLearnerStateResponse,
  DProfileListResponse,
} from '@/src/features/compd/api/compd-types';

const LEVELS = new Set(['low', 'medium', 'high']);
const SPEED_LEVELS = new Set(['Slow', 'Moderate', 'Fast']);
const LANGUAGES = new Set(['en', 'si']);

const FEATURE_KEYS: readonly (keyof DCognitiveFeatures)[] = [
  'accuracy',
  'avg_response_time_ms',
  'response_time_std_ms',
  'avg_attempts',
  'retry_rate',
  'hint_rate',
  'mean_clicks_per_question',
  'total_questions',
];

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function isNonEmptyString(value: unknown): value is string {
  return typeof value === 'string' && value.trim().length > 0;
}

function isFiniteNumber(value: unknown): value is number {
  return typeof value === 'number' && Number.isFinite(value);
}

function isFeatures(value: unknown): value is DCognitiveFeatures {
  return isRecord(value) && FEATURE_KEYS.every((key) => isFiniteNumber(value[key]));
}

export function isDCognitiveProfile(value: unknown): value is DCognitiveProfile {
  return (
    isRecord(value) &&
    isNonEmptyString(value.session_id) &&
    LEVELS.has(value.memory_level as string) &&
    LEVELS.has(value.attention_level as string) &&
    LEVELS.has(value.number_sense_level as string) &&
    SPEED_LEVELS.has(value.processing_speed_level as string) &&
    isFiniteNumber(value.confidence_score) &&
    typeof value.recommendation === 'string' &&
    isNonEmptyString(value.model_version) &&
    isFeatures(value.features) &&
    isNonEmptyString(value.generated_at)
  );
}

export function isDLearnerStateResponse(value: unknown): value is DLearnerStateResponse {
  return (
    isRecord(value) &&
    typeof value.intro_completed === 'boolean' &&
    LANGUAGES.has(value.language as string) &&
    isNonEmptyString(value.request_id)
  );
}

// `{profile, request_id}`, like `latest` but never null: the session read 404s instead (M-BE-013).
export function isDCognitiveProfileResponse(value: unknown): value is DCognitiveProfileResponse {
  return isRecord(value) && isDCognitiveProfile(value.profile) && isNonEmptyString(value.request_id);
}

export function isDLatestProfileResponse(value: unknown): value is DLatestProfileResponse {
  return (
    isRecord(value) &&
    (value.profile === null || isDCognitiveProfile(value.profile)) &&
    isNonEmptyString(value.request_id)
  );
}

export function isDProfileListResponse(value: unknown): value is DProfileListResponse {
  return (
    isRecord(value) &&
    Array.isArray(value.items) &&
    value.items.every(isDCognitiveProfile) &&
    isNonEmptyString(value.request_id)
  );
}
