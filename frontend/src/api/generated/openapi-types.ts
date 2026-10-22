// GENERATED FILE — do not hand-edit.
// Source: backend/contract/openapi.v1.json (contract version 0.1.0-be1.3).
// Regenerate with `npm run generate:contract-types` after the backend re-freezes the contract.

export interface ActiveSessionResponse {
  "request_id": string;
  "session": SessionFields | null;
}

export interface AttemptResponse {
  "attempt_index": number;
  "event_kind": "RESPONSE" | "TIMEOUT";
  "item_opportunity_id": string;
  "request_id": string;
  "response_matched": boolean | null;
  "server_submitted_at_utc": string;
}

export interface AuthenticatedPrincipal {
  "email"?: string | null;
  "user_id": string;
}

export interface CActiveSessionResponse {
  "request_id": string;
  "session": CSessionFields | null;
}

export interface CNextTaskResponse {
  "blanks": number | null;
  "c_task_instance_id": string;
  "difficulty_level": number;
  "game_family_id": string;
  "game_task_template_id": string;
  "interactive_assets": Record<string, unknown>;
  "prompt_payload": Record<string, unknown>;
  "prompt_text": string;
  "representation_mode": string;
  "request_id": string;
  "scaffold_state": string;
  "skill_id": string;
  "task_index": number;
  "technical_status": string;
  "valid_action_space": Record<string, string>;
}

export interface CSessionCommandResponse {
  "c_session_id": string;
  "grade": number;
  "request_id": string;
  "row_version": number;
  "session_mode": string;
  "session_phase": string;
  "started_at_utc": string;
  "state": string;
}

export interface CSessionFields {
  "c_session_id": string;
  "grade": number;
  "row_version": number;
  "session_mode": string;
  "session_phase": string;
  "started_at_utc": string;
  "state": string;
}

export interface CSubmitActionRequest {
  "action_payload": Record<string, unknown>;
}

export interface CSubmitActionResult {
  "c_task_instance_id": string;
  "request_id": string;
  "response_matched": boolean;
  "scaffold_level": string;
}

export interface ClassroomCreateRequest {
  "grade": "GRADE_2" | "GRADE_3";
  "name"?: string | null;
}

/**
 * The classroom name, typed by the teacher, as the confirmation for deleting it.
 */
export interface ClassroomDeleteRequest {
  "confirmation_name": string;
}

export interface ClassroomDeleteResponse {
  "classroom_id": string;
  "deleted_at_utc": string;
  "removed_membership_count": number;
  "request_id": string;
  "row_version": number;
}

export interface ClassroomLearnerListItem {
  "learner_id": string;
  "membership_id": string;
  "membership_state": "PENDING" | "APPROVED" | "REJECTED" | "REMOVED";
  "name": string | null;
}

export interface ClassroomLearnerListResponse {
  "learners": (ClassroomLearnerListItem)[];
  "request_id": string;
}

export interface ClassroomListItem {
  "classroom_id": string;
  "created_at_utc": string;
  "grade": "GRADE_2" | "GRADE_3";
  "name": string | null;
  "row_version": number;
}

export interface ClassroomListResponse {
  "classrooms": (ClassroomListItem)[];
  "request_id": string;
}

export interface ClassroomResponse {
  "classroom_id": string;
  "created_at_utc": string;
  "grade": "GRADE_2" | "GRADE_3";
  "name": string | null;
  "request_id": string;
  "row_version": number;
  "teacher_profile_id": string;
}

export interface CompleteCSessionRequest {
  "attendance_status": "attended" | "partial" | "missed";
  "technical_blocked_bootstrap"?: boolean;
}

/**
 * R-5 (Phase 4b continuation, supervisor ruling): carries grade and session_mode ONLY. B's
 * identity fields (mastery_source_student_id etc.) were removed from here -- accepting them from
 * an HTTP client let an untrusted caller assert B provenance it never produced (strictly worse
 * than the C-manufactures-its-own-provenance failure R1 was written to prevent). See
 * app/application/live_engine_c/mastery_fixture.py's module docstring for the fixture that now
 * supplies all of it, for every combined-mode session, server-side only.
 */
export interface CreateCSessionRequest {
  "grade": number;
  "session_mode": "combined" | "c_only";
}

/**
 * The raw levels are carried as the engine produced them.
 * 
 * Owner decision **D-010** keeps compD's own labels (for example "Memory: low") on the
 * child-facing page, as a research prototype that needs much more development and data
 * collection. How that is worded for a child is the frontend's to render and is not a contract
 * concern -- this shape stays descriptive.
 * 
 * ``model_version`` is a rule-based version until a trained model exists -- ``"rule-based-v2"``
 * today, after the speed heuristic was corrected (``d_features.capped_mean_response_time_ms``).
 * It is on the public
 * shape so a reader can always tell which generation produced a profile; a history list can
 * hold both.
 */
export interface DCognitiveProfile {
  "attention_level": "low" | "medium" | "high";
  "confidence_score": number;
  "features": DCognitiveProfileFeatures;
  "generated_at": string;
  "memory_level": "low" | "medium" | "high";
  "model_version": string;
  "number_sense_level": "low" | "medium" | "high";
  "processing_speed_level": "Slow" | "Moderate" | "Fast";
  "recommendation": string;
  "session_id": string;
}

/**
 * The feature vector, returned as a unit because that is how it is computed and consumed.
 * 
 * ``total_questions`` is an int; everything else is a ratio or a duration. ``hint_rate`` keeps
 * its name -- see this module's docstring for why that is clean at the public layer.
 */
export interface DCognitiveProfileFeatures {
  "accuracy": number;
  "avg_attempts": number;
  "avg_response_time_ms": number;
  "hint_rate": number;
  "mean_clicks_per_question": number;
  "response_time_std_ms": number;
  "retry_rate": number;
  "total_questions": number;
}

/**
 * The single-profile response, for both the ``POST`` and the by-session ``GET``.
 * 
 * The ``POST`` returns the same 200 for a newly stored profile and for a repeat of one already
 * stored (contract v4) -- a client that retries cannot tell the two apart, which is the point.
 */
export interface DCognitiveProfileResponse {
  "profile": DCognitiveProfile;
  "request_id": string;
}

/**
 * One question answered in a profiling run -- the raw evidence a feature vector is computed
 * from, and the row shape ``d_interactions`` stores.
 * 
 * The numeric bounds here are the same ones the table's CHECK constraints enforce
 * (migration ``20261021_0010``), stated in both places on purpose: the API refuses a bad body
 * with a 422 naming the field, and the database refuses it again if anything ever reaches it by
 * another path.
 */
export interface DInteractionEvent {
  "assist_used": boolean;
  "attempts": number;
  "click_count": number;
  "difficulty": "Easy" | "Medium" | "Hard";
  "error_type": "none" | "calculation" | "conceptual" | "careless" | "unknown";
  "question_id": string;
  "response_matched": boolean;
  "response_time_sec": number;
  "session_time_sec": number;
  "time_between_actions": number;
  "topic": "Counting" | "Addition" | "Subtraction" | "Division";
}

/**
 * ``profile: null`` rather than a 404 when the learner has none.
 * 
 * A learner who has never done a profiling run is in a normal, expected state, and the home
 * screen's empty state is a render of that -- not an error to recover from.
 */
export interface DLatestProfileResponse {
  "profile": DCognitiveProfile | null;
  "request_id": string;
}

/**
 * ``intro_completed`` is derived from ``d_learner_state.intro_completed_at IS NOT NULL``.
 * 
 * A learner with no row reads as ``{intro_completed: false, language: "en"}`` and nothing is
 * created -- the default belongs to the read, not to the table, so the table never holds a
 * language the learner did not pick.
 */
export interface DLearnerStateResponse {
  "intro_completed": boolean;
  "language": "en" | "si";
  "request_id": string;
}

/**
 * At least one field is required; ``{}`` is a 422.
 * 
 * ``intro_completed`` is ``Literal[True]``, so ``false`` is a 422 too. The intro is a one-way
 * door: a learner who has seen it cannot un-see it, and accepting ``false`` would let a client
 * reset the first-run flow for a child who had already been through it.
 */
export interface DLearnerStateUpdateRequest {
  "intro_completed"?: true | null;
  "language"?: "en" | "si" | null;
}

export interface DProfileCreateRequest {
  "events": (DInteractionEvent)[];
  "language": "en" | "si";
}

/**
 * Newest first.
 */
export interface DProfileListResponse {
  "items": (DCognitiveProfile)[];
  "request_id": string;
}

export interface HTTPValidationError {
  "detail"?: (ValidationError)[];
}

/**
 * Public health-check response.
 */
export interface HealthResponse {
  "request_id": string;
  "status": "alive" | "ready";
}

export interface HintRequestResponse {
  "catalogue_checksum": string;
  "catalogue_version": string;
  "content": string;
  "content_id": string;
  "hint_level": number;
  "item_opportunity_id": string;
  "request_id": string;
}

export interface InviteCreateResponse {
  "classroom_invite_id": string;
  "created_at_utc": string;
  "expires_at_utc"?: string | null;
  "invite_token": string | null;
  "request_id": string;
  "token_already_issued": boolean;
}

export interface InviteResolveResponse {
  "classroom_name": string | null;
  "grade": "GRADE_2" | "GRADE_3";
  "invite_resolution_id": string;
  "request_id": string;
}

export interface InviteRevokeResponse {
  "classroom_id": string;
  "classroom_invite_id": string;
  "request_id": string;
  "revoked_at_utc": string;
  "row_version": number;
}

export interface InviteTokenRequest {
  "invite_token": string;
}

export interface LearnerMembershipListItem {
  "classroom_id": string;
  "classroom_name": string | null;
  "decided_at_utc": string | null;
  "grade": "GRADE_2" | "GRADE_3";
  "membership_id": string;
  "requested_at_utc": string;
  "state": "PENDING" | "APPROVED" | "REJECTED" | "REMOVED";
}

export interface LearnerMembershipListResponse {
  "memberships": (LearnerMembershipListItem)[];
  "request_id": string;
}

export interface LearnerProfileResponse {
  "created_at_utc": string;
  "email": string | null;
  "learner_id": string;
  "name": string;
  "profile_type": "LEARNER";
  "request_id": string;
  "user_id": string;
}

export interface LearnerSkillStateItem {
  "observation_count": number;
  "p_l": number;
  "skill_id": string;
}

export interface LearnerSkillStatesResponse {
  "request_id": string;
  "skill_states": (LearnerSkillStateItem)[];
}

export interface MembershipDecisionResponse {
  "classroom_id": string;
  "classroom_membership_id": string;
  "decided_at_utc": string;
  "learner_id": string;
  "request_id": string;
  "row_version": number;
  "state": "PENDING" | "APPROVED" | "REJECTED" | "REMOVED";
}

export interface MembershipRequestListItem {
  "classroom_membership_id": string;
  "decided_at_utc": string | null;
  "learner_id": string;
  "learner_name": string | null;
  "requested_at_utc": string;
  "state": "PENDING" | "APPROVED" | "REJECTED" | "REMOVED";
}

export interface MembershipRequestListResponse {
  "request_id": string;
  "requests": (MembershipRequestListItem)[];
}

export interface MembershipRequestResponse {
  "classroom_id": string;
  "classroom_membership_id": string;
  "classroom_name": string | null;
  "grade": "GRADE_2" | "GRADE_3";
  "request_id": string;
  "requested_at_utc": string;
  "state": "PENDING" | "APPROVED" | "REJECTED" | "REMOVED";
}

export interface OpportunityAdvanceResponse {
  "item_opportunity_id": string;
  "next_opportunity": OpportunityPresentationFields | null;
  "opportunities_completed": number;
  "opportunities_total_bound": number;
  "request_id": string;
  "session_state": "active" | "completed";
}

/**
 * BE4b (BEplan §9 BE4.2) public response shape — an explicit, field-by-field mirror of
 * ``PresentedOpportunity`` (never ``**PresentedOpportunity.to_public_dict()``), so the FastAPI
 * response schema and the safe-DTO allow-list are two independently-written descriptions of the
 * same safe field set rather than one generated from the other.
 */
export interface OpportunityPresentationFields {
  "difficulty_level": string;
  "grade": number;
  "item_instance_id": string;
  "item_opportunity_id": string;
  "presentation_token": string;
  "presented_choices": (string)[];
  "prompt": Record<string, unknown>;
  "representation_type": string;
  "response_format": string;
  "server_timeout_deadline_utc": string;
  "skill_id": string;
}

export interface OpportunityPresentationResponse {
  "difficulty_level": string;
  "grade": number;
  "item_instance_id": string;
  "item_opportunity_id": string;
  "presentation_token": string;
  "presented_choices": (string)[];
  "prompt": Record<string, unknown>;
  "representation_type": string;
  "request_id": string;
  "response_format": string;
  "server_timeout_deadline_utc": string;
  "skill_id": string;
}

export interface PresentationAckResponse {
  "anchored": boolean;
  "item_opportunity_id": string;
  "request_id": string;
  "server_timeout_deadline_utc": string;
}

export interface ProfileCreateRequest {
  "name": string;
}

export interface ReadinessResponse {
  "checks": Record<string, string>;
  "request_id": string;
  "stage": "infrastructure";
  "status": "ready";
}

export interface SessionCommandResponse {
  "created_at_utc": string;
  "request_id": string;
  "row_version": number;
  "runtime_bundle_version": string;
  "session_id": string;
  "state": "active" | "completed" | "abandoned";
}

export interface SessionFields {
  "created_at_utc": string;
  "row_version": number;
  "runtime_bundle_version": string;
  "session_id": string;
  "state": "active" | "completed" | "abandoned";
}

export interface SessionStandingResponse {
  "opportunities_completed": number;
  "opportunities_total_bound": number;
  "request_id": string;
  "session_id": string;
  "session_state": "active" | "completed";
}

/**
 * Strict, size-capped request shape. ``client_elapsed_ms`` is TELEMETRY ONLY — never read
 * for correctness or BKT; server timestamps are authoritative.
 */
export interface SubmitResponseRequest {
  "client_elapsed_ms"?: number | null;
  "submitted_value": string;
}

export interface TeacherProfileResponse {
  "created_at_utc": string;
  "email": string | null;
  "name": string;
  "profile_type": "TEACHER";
  "request_id": string;
  "teacher_profile_id": string;
  "user_id": string;
}

export interface ValidationError {
  "ctx"?: Record<string, unknown>;
  "input"?: unknown;
  "loc": (string | number)[];
  "msg": string;
  "type": string;
}

export type ContractOperation = {
  method: string;
  path: string;
  operationId: string;
  request: string | null;
  response: string | null;
};

export const CONTRACT_OPERATIONS: readonly ContractOperation[] = [
  {
    "method": "GET",
    "path": "/api/v1/b/learner/skill-states",
    "operationId": "get_learner_skill_states_api_v1_b_learner_skill_states_get",
    "request": null,
    "response": "LearnerSkillStatesResponse"
  },
  {
    "method": "POST",
    "path": "/api/v1/b/sessions/{session_id}/abandon",
    "operationId": "abandon_session_api_v1_b_sessions__session_id__abandon_post",
    "request": null,
    "response": "SessionCommandResponse"
  },
  {
    "method": "POST",
    "path": "/api/v1/b/sessions/{session_id}/complete",
    "operationId": "complete_session_api_v1_b_sessions__session_id__complete_post",
    "request": null,
    "response": "SessionCommandResponse"
  },
  {
    "method": "POST",
    "path": "/api/v1/b/sessions/{session_id}/opportunities/{item_opportunity_id}/assists",
    "operationId": "request_assist_api_v1_b_sessions__session_id__opportunities__item_opportunity_id__assists_post",
    "request": null,
    "response": "HintRequestResponse"
  },
  {
    "method": "POST",
    "path": "/api/v1/b/sessions/{session_id}/opportunities/{item_opportunity_id}/complete",
    "operationId": "complete_opportunity_api_v1_b_sessions__session_id__opportunities__item_opportunity_id__complete_post",
    "request": null,
    "response": "OpportunityAdvanceResponse"
  },
  {
    "method": "POST",
    "path": "/api/v1/b/sessions/{session_id}/opportunities/{item_opportunity_id}/presented",
    "operationId": "acknowledge_presentation_api_v1_b_sessions__session_id__opportunities__item_opportunity_id__presented_post",
    "request": null,
    "response": "PresentationAckResponse"
  },
  {
    "method": "POST",
    "path": "/api/v1/b/sessions/{session_id}/opportunities/{item_opportunity_id}/responses",
    "operationId": "submit_response_api_v1_b_sessions__session_id__opportunities__item_opportunity_id__responses_post",
    "request": "SubmitResponseRequest",
    "response": "AttemptResponse"
  },
  {
    "method": "POST",
    "path": "/api/v1/b/sessions/{session_id}/opportunities",
    "operationId": "select_opportunity_api_v1_b_sessions__session_id__opportunities_post",
    "request": null,
    "response": "OpportunityPresentationResponse"
  },
  {
    "method": "GET",
    "path": "/api/v1/b/sessions/{session_id}/summary",
    "operationId": "get_session_summary_api_v1_b_sessions__session_id__summary_get",
    "request": null,
    "response": "SessionStandingResponse"
  },
  {
    "method": "GET",
    "path": "/api/v1/b/sessions/active",
    "operationId": "get_active_session_api_v1_b_sessions_active_get",
    "request": null,
    "response": "ActiveSessionResponse"
  },
  {
    "method": "POST",
    "path": "/api/v1/b/sessions",
    "operationId": "start_session_api_v1_b_sessions_post",
    "request": null,
    "response": "SessionCommandResponse"
  },
  {
    "method": "POST",
    "path": "/api/v1/c/sessions/{c_session_id}/abandon",
    "operationId": "abandon_session_api_v1_c_sessions__c_session_id__abandon_post",
    "request": null,
    "response": "CSessionCommandResponse"
  },
  {
    "method": "POST",
    "path": "/api/v1/c/sessions/{c_session_id}/complete",
    "operationId": "complete_session_api_v1_c_sessions__c_session_id__complete_post",
    "request": "CompleteCSessionRequest",
    "response": "CSessionCommandResponse"
  },
  {
    "method": "POST",
    "path": "/api/v1/c/sessions/{c_session_id}/tasks/{c_task_instance_id}/actions",
    "operationId": "submit_action_api_v1_c_sessions__c_session_id__tasks__c_task_instance_id__actions_post",
    "request": "CSubmitActionRequest",
    "response": "CSubmitActionResult"
  },
  {
    "method": "POST",
    "path": "/api/v1/c/sessions/{c_session_id}/tasks/next",
    "operationId": "next_task_api_v1_c_sessions__c_session_id__tasks_next_post",
    "request": null,
    "response": "CNextTaskResponse"
  },
  {
    "method": "GET",
    "path": "/api/v1/c/sessions/active",
    "operationId": "get_active_session_api_v1_c_sessions_active_get",
    "request": null,
    "response": "CActiveSessionResponse"
  },
  {
    "method": "POST",
    "path": "/api/v1/c/sessions",
    "operationId": "create_session_api_v1_c_sessions_post",
    "request": "CreateCSessionRequest",
    "response": "CSessionCommandResponse"
  },
  {
    "method": "POST",
    "path": "/api/v1/classroom-invites/{classroom_invite_id}/revoke",
    "operationId": "revoke_invite_api_v1_classroom_invites__classroom_invite_id__revoke_post",
    "request": null,
    "response": "InviteRevokeResponse"
  },
  {
    "method": "POST",
    "path": "/api/v1/classroom-invites/resolve",
    "operationId": "resolve_invite_api_v1_classroom_invites_resolve_post",
    "request": "InviteTokenRequest",
    "response": "InviteResolveResponse"
  },
  {
    "method": "POST",
    "path": "/api/v1/classroom-memberships/{membership_id}/approve",
    "operationId": "approve_membership_api_v1_classroom_memberships__membership_id__approve_post",
    "request": null,
    "response": "MembershipDecisionResponse"
  },
  {
    "method": "POST",
    "path": "/api/v1/classroom-memberships/{membership_id}/reject",
    "operationId": "reject_membership_api_v1_classroom_memberships__membership_id__reject_post",
    "request": null,
    "response": "MembershipDecisionResponse"
  },
  {
    "method": "POST",
    "path": "/api/v1/classroom-memberships/requests",
    "operationId": "request_membership_api_v1_classroom_memberships_requests_post",
    "request": "InviteTokenRequest",
    "response": "MembershipRequestResponse"
  },
  {
    "method": "POST",
    "path": "/api/v1/classrooms/{classroom_id}/delete",
    "operationId": "delete_classroom_api_v1_classrooms__classroom_id__delete_post",
    "request": "ClassroomDeleteRequest",
    "response": "ClassroomDeleteResponse"
  },
  {
    "method": "POST",
    "path": "/api/v1/classrooms/{classroom_id}/invites",
    "operationId": "create_invite_api_v1_classrooms__classroom_id__invites_post",
    "request": null,
    "response": "InviteCreateResponse"
  },
  {
    "method": "GET",
    "path": "/api/v1/classrooms/{classroom_id}/learners",
    "operationId": "list_classroom_learners_api_v1_classrooms__classroom_id__learners_get",
    "request": null,
    "response": "ClassroomLearnerListResponse"
  },
  {
    "method": "GET",
    "path": "/api/v1/classrooms/{classroom_id}/membership-requests",
    "operationId": "list_membership_requests_api_v1_classrooms__classroom_id__membership_requests_get",
    "request": null,
    "response": "MembershipRequestListResponse"
  },
  {
    "method": "GET",
    "path": "/api/v1/classrooms/{classroom_id}",
    "operationId": "get_classroom_api_v1_classrooms__classroom_id__get",
    "request": null,
    "response": "ClassroomResponse"
  },
  {
    "method": "GET",
    "path": "/api/v1/classrooms",
    "operationId": "list_classrooms_api_v1_classrooms_get",
    "request": null,
    "response": "ClassroomListResponse"
  },
  {
    "method": "POST",
    "path": "/api/v1/classrooms",
    "operationId": "create_classroom_api_v1_classrooms_post",
    "request": "ClassroomCreateRequest",
    "response": "ClassroomResponse"
  },
  {
    "method": "GET",
    "path": "/api/v1/d/learner/profiles/latest",
    "operationId": "get_latest_profile_api_v1_d_learner_profiles_latest_get",
    "request": null,
    "response": "DLatestProfileResponse"
  },
  {
    "method": "GET",
    "path": "/api/v1/d/learner/profiles",
    "operationId": "list_profiles_api_v1_d_learner_profiles_get",
    "request": null,
    "response": "DProfileListResponse"
  },
  {
    "method": "GET",
    "path": "/api/v1/d/learner/state",
    "operationId": "get_learner_state_api_v1_d_learner_state_get",
    "request": null,
    "response": "DLearnerStateResponse"
  },
  {
    "method": "POST",
    "path": "/api/v1/d/learner/state",
    "operationId": "update_learner_state_api_v1_d_learner_state_post",
    "request": "DLearnerStateUpdateRequest",
    "response": "DLearnerStateResponse"
  },
  {
    "method": "GET",
    "path": "/api/v1/d/sessions/{session_id}/profile",
    "operationId": "get_profile_api_v1_d_sessions__session_id__profile_get",
    "request": null,
    "response": "DCognitiveProfileResponse"
  },
  {
    "method": "POST",
    "path": "/api/v1/d/sessions/{session_id}/profile",
    "operationId": "create_profile_api_v1_d_sessions__session_id__profile_post",
    "request": "DProfileCreateRequest",
    "response": "DCognitiveProfileResponse"
  },
  {
    "method": "GET",
    "path": "/api/v1/learner/classrooms",
    "operationId": "list_learner_classrooms_api_v1_learner_classrooms_get",
    "request": null,
    "response": "LearnerMembershipListResponse"
  },
  {
    "method": "GET",
    "path": "/api/v1/learner/profile",
    "operationId": "get_learner_profile_api_v1_learner_profile_get",
    "request": null,
    "response": "LearnerProfileResponse"
  },
  {
    "method": "POST",
    "path": "/api/v1/learner/profile",
    "operationId": "create_learner_profile_api_v1_learner_profile_post",
    "request": "ProfileCreateRequest",
    "response": "LearnerProfileResponse"
  },
  {
    "method": "GET",
    "path": "/api/v1/me",
    "operationId": "current_identity_api_v1_me_get",
    "request": null,
    "response": "AuthenticatedPrincipal"
  },
  {
    "method": "GET",
    "path": "/api/v1/teacher/profile",
    "operationId": "get_teacher_profile_api_v1_teacher_profile_get",
    "request": null,
    "response": "TeacherProfileResponse"
  },
  {
    "method": "POST",
    "path": "/api/v1/teacher/profile",
    "operationId": "create_teacher_profile_api_v1_teacher_profile_post",
    "request": "ProfileCreateRequest",
    "response": "TeacherProfileResponse"
  },
  {
    "method": "GET",
    "path": "/health/live",
    "operationId": "liveness_health_live_get",
    "request": null,
    "response": "HealthResponse"
  },
  {
    "method": "GET",
    "path": "/health/ready",
    "operationId": "readiness_health_ready_get",
    "request": null,
    "response": "ReadinessResponse"
  }
] as const;
