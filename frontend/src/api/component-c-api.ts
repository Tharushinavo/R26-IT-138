import { requestJson } from '@/src/api/request';
import { ApiClientError } from '@/src/api/errors';
import { loadFixtureTaskExemplar } from '@/src/api/dev-fixture-exemplars';
import {
  isCActiveSessionResponse,
  isCNextTaskResponse,
  isCSessionCommandResponse,
  isCSubmitActionResult,
} from '@/src/api/runtime-validation';
import type {
  CActiveSessionResponse,
  CNextTaskResponse,
  CompleteCSessionRequest,
  CreateCSessionRequest,
  CSessionCommandResponse,
  CSubmitActionRequest,
  CSubmitActionResult,
} from '@/src/api/generated/openapi-types';
import type { PublicConfig } from '@/src/config/env';

// None of the six Component C routes take an Idempotency-Key header. This is a deliberate
// backend divergence from Component B, not an omission to fix here — see
// backend/app/api/routes/c_session.py's module docstring: "no idempotency-key header (Phase
// 4a/4b ruling: v3.0 says only 'idempotent by learner state', which
// find_starting_or_active_for_learner already satisfies -- B's fuller idempotency-key/audit-
// event machinery is a scope expansion beyond that text, not built here)." Every C route file
// was checked; none declares one. No call below sends one.
type ComponentCApi = {
  createSession: (body: CreateCSessionRequest, accessToken: string) => Promise<CSessionCommandResponse>;
  getActiveSession: (accessToken: string) => Promise<CActiveSessionResponse>;
  abandonSession: (cSessionId: string, accessToken: string) => Promise<CSessionCommandResponse>;
  completeSession: (
    cSessionId: string,
    body: CompleteCSessionRequest,
    accessToken: string,
  ) => Promise<CSessionCommandResponse>;
  nextTask: (cSessionId: string, accessToken: string) => Promise<CNextTaskResponse>;
  submitAction: (
    cSessionId: string,
    cTaskInstanceId: string,
    body: CSubmitActionRequest,
    accessToken: string,
  ) => Promise<CSubmitActionResult>;
};

function getDevelopmentFixture(): string | null {
  if (process.env.EXPO_PUBLIC_APP_ENV !== 'development') return null;
  const fixture = process.env.EXPO_PUBLIC_COMPONENT_C_DEV_FIXTURE?.trim();
  return fixture || null;
}

// EXPO_PUBLIC_COMPONENT_C_DEV_FIXTURE_VERDICT drives `submitAction`'s canned `response_matched` --
// it does not make the fixture EVALUATE anything. There is still no comparison anywhere in this
// file between a submitted payload and any expected answer; the env var only selects which fixed
// literal to hand back, exactly as EXPO_PUBLIC_COMPONENT_C_DEV_FIXTURE_FAMILY selects a literal
// accent override two blocks below. This is what keeps this file's own long-standing comment
// ("nothing in this codebase ever computes response_matched client-side") true after this change,
// not just before it.
//
// `'alternate'` exists so a full retry cycle (not-matched, escalate scaffold_level, matched) is
// walkable in a browser without restarting the dev server between attempts -- the only way to SEE
// `answer-feedback-panel.tsx`'s two states and the remount-per-attempt key, since nothing in this
// repository can mount a component tree in an automated test.
type DevFixtureVerdict = 'correct' | 'incorrect' | 'alternate';

function readDevFixtureVerdict(): DevFixtureVerdict {
  const raw = process.env.EXPO_PUBLIC_COMPONENT_C_DEV_FIXTURE_VERDICT?.trim();
  if (raw === 'incorrect' || raw === 'alternate') return raw;
  return 'correct';
}

// C0..C4 is the real `scaffold_level` vocabulary (persistence_models.py's CHECK constraint), the
// same set `technical_status`/`scaffold_state` already draw from elsewhere in this file -- not an
// invented sequence.
const SCAFFOLD_LEVELS = ['C0', 'C1', 'C2', 'C3', 'C4'] as const;

function createFixtureApi(fixture: string): ComponentCApi {
  // Closed over by `submitAction` below, not module-level -- state private to one fixture api
  // instance, matching how `api` itself is held for the lifetime of one screen mount
  // (c-session-screen.tsx's own `useMemo`). Reset only by remounting the screen (or restarting the
  // dev server), same as every other fixture value in this file.
  let notMatchedCount = 0;
  let alternateCallCount = 0;
  return {
    async createSession() {
      return {
        c_session_id: 'dev-c-session-new-opaque',
        state: 'active',
        session_mode: 'c_only',
        session_phase: 'development-fixture-only',
        grade: 3,
        started_at_utc: '2026-08-23T12:00:00Z',
        row_version: 1,
        request_id: 'dev-c-create-ok',
      };
    },
    async getActiveSession() {
      return {
        session: null,
        request_id: 'dev-c-active-ok',
      };
    },
    // abandonSession and completeSession stay unimplemented -- an immediate throw, no delay, no
    // fake payload -- so a fixture run can never masquerade as a real session past the point a
    // real session could be abandoned or completed. Restates Component B's own fixture doctrine.
    // The owner's 2026-08-24 ruling (10.0-work-order.md §3) covers nextTask and submitAction
    // only; it says nothing about these two, and that silence is not read as an invitation to
    // widen it.
    async abandonSession() {
      throw new ApiClientError('unavailable', 'The development fixture does not implement session abandonment.');
    },
    async completeSession() {
      throw new ApiClientError('unavailable', 'The development fixture does not implement session completion.');
    },
    // THIS FIXTURE IS A DEVELOPMENT AND TEST PATH ONLY. It is not a production task-generation
    // path, and the backend remains the sole authority on task content in production -- the
    // client here relays a real generator-produced exemplar, it never invents one.
    //
    // prompt_payload, interactive_assets, valid_action_space, blanks and prompt_text are relayed
    // verbatim from one c-prompt-exemplars.json entry (loadFixtureTaskExemplar picks it
    // deterministically -- see dev-fixture-exemplars.ts). The remaining CNextTaskResponse fields
    // have no source in that artefact (its seven-field allow-list carries only
    // game_task_template_id, difficulty_level, prompt_payload, interactive_assets,
    // valid_action_space, blanks and prompt_text) and are supplied as follows, per owner
    // correction 2026-08-24:
    //   - technical_status: 'OK' and scaffold_state: 'C0' are real values from each field's
    //     actual backend vocabulary (persistence_models.py's CHECK constraint; C0..C4), not
    //     invented ones.
    //   - representation_mode is the genuine on-wire value for all 30 templates today
    //     (generation.py:100 selects it from the catalogue, and the only catalogue that exists
    //     carries this one literal) -- using it makes the fixture match production rather than
    //     diverge from it. It is carried, never branched on, per the same trap B's
    //     representation_type documents.
    //   - task_index is 1, not 0: GameTaskInstance requires >= 1 (task_service.py:392) and 0 is
    //     unreachable on the wire.
    //   - game_family_id, skill_id and c_task_instance_id are marker literals, deliberately NOT
    //     derived from the template id: no template-id-to-family or -to-skill mapping exists
    //     client-side, and a plausible-looking derived value would manufacture a join the backend
    //     supervisor states is absent (agent1.md §2.3). A fabricated-but-plausible id is worse
    //     than an honest placeholder. EXPO_PUBLIC_COMPONENT_C_DEV_FIXTURE_FAMILY is the one
    //     exception, and does not reopen this: it is an explicit, opt-in, developer-typed override
    //     for previewing a task screen's family accent colour (game-family-accents.ts) while this
    //     route's real session-creation path is unsigned, never a value this file derives or
    //     guesses on its own. Unset, the honest placeholder above is what ships, unchanged.
    //   - request_id follows this file's own dev-fixture-id convention (see createSession above).
    async nextTask() {
      const exemplar = loadFixtureTaskExemplar();
      const familyOverride = process.env.EXPO_PUBLIC_COMPONENT_C_DEV_FIXTURE_FAMILY?.trim();
      return {
        c_task_instance_id: 'dev-c-task-fixture-only',
        game_family_id: familyOverride || 'development-fixture-only',
        game_task_template_id: exemplar.game_task_template_id,
        task_index: 1,
        skill_id: 'development-fixture-only',
        difficulty_level: exemplar.difficulty_level,
        representation_mode: 'TEST_FIXTURE_ONLY_REPRESENTATION',
        prompt_payload: exemplar.prompt_payload,
        interactive_assets: exemplar.interactive_assets,
        valid_action_space: exemplar.valid_action_space,
        blanks: exemplar.blanks,
        prompt_text: exemplar.prompt_text,
        scaffold_state: 'C0',
        technical_status: 'OK',
        request_id: 'dev-c-next-task-ok',
      };
    },
    // response_matched here is a canned fixture value, not a computed verdict -- this fixture
    // never evaluates correctness. A real submission's response_matched comes from the server
    // alone; nothing in this codebase ever computes it client-side. Which canned value comes back
    // is selected by EXPO_PUBLIC_COMPONENT_C_DEV_FIXTURE_VERDICT (see its own comment above);
    // `payload` is accepted only because the real route signature requires it and is never read.
    async submitAction() {
      const verdict = readDevFixtureVerdict();

      if (verdict === 'correct') {
        return {
          c_task_instance_id: 'dev-c-task-fixture-only',
          response_matched: true,
          scaffold_level: 'C0',
          request_id: 'dev-c-submit-action-ok',
        };
      }

      if (verdict === 'incorrect') {
        const level = SCAFFOLD_LEVELS[Math.min(notMatchedCount, SCAFFOLD_LEVELS.length - 1)];
        notMatchedCount += 1;
        return {
          c_task_instance_id: 'dev-c-task-fixture-only',
          response_matched: false,
          scaffold_level: level,
          request_id: 'dev-c-submit-action-ok',
        };
      }

      // 'alternate': odd calls (1st, 3rd, ...) not-matched with an escalating scaffold level; even
      // calls (2nd, 4th, ...) matched -- so submitting the same wrong answer, then trying again,
      // walks the full retry cycle described in this file's header comment above.
      const callIndex = alternateCallCount;
      alternateCallCount += 1;
      const matched = callIndex % 2 === 1;
      if (matched) {
        return {
          c_task_instance_id: 'dev-c-task-fixture-only',
          response_matched: true,
          scaffold_level: 'C0',
          request_id: 'dev-c-submit-action-ok',
        };
      }
      const level = SCAFFOLD_LEVELS[Math.min(Math.floor(callIndex / 2), SCAFFOLD_LEVELS.length - 1)];
      return {
        c_task_instance_id: 'dev-c-task-fixture-only',
        response_matched: false,
        scaffold_level: level,
        request_id: 'dev-c-submit-action-ok',
      };
    },
  };
}

export function createComponentCApi(config?: PublicConfig): ComponentCApi {
  const fixture = getDevelopmentFixture();
  if (fixture) return createFixtureApi(fixture);
  if (!config) {
    throw new ApiClientError('unavailable', 'The Component C API is not configured.');
  }

  return {
    createSession: (body, accessToken) =>
      requestJson(config, {
        accessToken,
        body,
        method: 'POST',
        path: '/api/v1/c/sessions',
        validate: isCSessionCommandResponse,
      }),
    getActiveSession: (accessToken) =>
      requestJson(config, {
        accessToken,
        method: 'GET',
        path: '/api/v1/c/sessions/active',
        validate: isCActiveSessionResponse,
      }),
    abandonSession: (cSessionId, accessToken) =>
      requestJson(config, {
        accessToken,
        method: 'POST',
        path: `/api/v1/c/sessions/${cSessionId}/abandon`,
        validate: isCSessionCommandResponse,
      }),
    completeSession: (cSessionId, body, accessToken) =>
      requestJson(config, {
        accessToken,
        body,
        method: 'POST',
        path: `/api/v1/c/sessions/${cSessionId}/complete`,
        validate: isCSessionCommandResponse,
      }),
    nextTask: (cSessionId, accessToken) =>
      requestJson(config, {
        accessToken,
        method: 'POST',
        path: `/api/v1/c/sessions/${cSessionId}/tasks/next`,
        validate: isCNextTaskResponse,
      }),
    submitAction: (cSessionId, cTaskInstanceId, body, accessToken) =>
      requestJson(config, {
        accessToken,
        body,
        method: 'POST',
        path: `/api/v1/c/sessions/${cSessionId}/tasks/${cTaskInstanceId}/actions`,
        validate: isCSubmitActionResult,
      }),
  };
}

export function getComponentCDevelopmentFixture() {
  return getDevelopmentFixture();
}
