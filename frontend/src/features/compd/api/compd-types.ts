// Component D (compD, Cognitive Skill Profiling) wire types for `/api/v1/d/*`.
//
// GENERATED, NOT HAND-WRITTEN: every wire type is the one `npm run generate:contract-types` emits
// from backend/contract/openapi.v1.json, re-exported under the name the contract fixes, so a
// backend change that alters a field fails typecheck here instead of failing a child's screen.
// (Until the contract checkpoint, M-BE-013, these were hand-written from the contract draft.)
// Only the narrow helper unions and `DLearnerState` below are FE's own, and they are derived from
// the generated types rather than retyped.

import type {
  DCognitiveProfile,
  DCognitiveProfileFeatures,
  DInteractionEvent,
  DLearnerStateResponse,
} from '@/src/api/generated/openapi-types';

export type {
  DCognitiveProfile,
  DCognitiveProfileResponse,
  DInteractionEvent,
  DLatestProfileResponse,
  DLearnerStateResponse,
  DLearnerStateUpdateRequest,
  DProfileCreateRequest,
  DProfileListResponse,
} from '@/src/api/generated/openapi-types';

export type DCognitiveFeatures = DCognitiveProfileFeatures;
export type DLanguage = DLearnerStateResponse['language'];
export type DLevel = DCognitiveProfile['memory_level'];
export type DSpeedLevel = DCognitiveProfile['processing_speed_level'];
export type DTopic = DInteractionEvent['topic'];
export type DDifficulty = DInteractionEvent['difficulty'];
export type DErrorType = DInteractionEvent['error_type'];

/** The two learner-state fields the app keeps; `request_id` is transport, not state. */
export type DLearnerState = Pick<DLearnerStateResponse, 'intro_completed' | 'language'>;
