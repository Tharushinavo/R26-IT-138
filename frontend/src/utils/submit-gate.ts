// --- submission re-entry gate -----------------------------------------------------------------
//
// Shared by BOTH components' answer paths. It began as a Component C primitive in
// c-session-logic.ts, which is where its tests still import it from (that module re-exports it, so
// nothing about C changed when this moved). It was hoisted here on 2026-10-09 when Component B was
// found to be missing the same guard: B's `submitAnswer` gated only on the `submitting` React
// state, which is exactly the check the header below explains does not work.
//
// Hoisted rather than copied, deliberately, and for the reason rotating-gradient-background.tsx
// gives for the same decision: "two screens that must look identical share the component; two
// screens that merely rhyme keep their own styles." A mutual-exclusion gate is not a style. Both
// components must behave identically here -- a copy is a pair that drifts, and the thing that
// would drift is a data-integrity guard.

export type SubmitGate = {
  /** `true` if the caller may proceed; `false` if a submission is already in flight. */
  tryEnter: () => boolean;
  /** Releases the gate. Always call from a `finally`, or the surface locks permanently. */
  release: () => void;
  /** For rendering the in-flight indicator. Never used to decide whether to submit. */
  isBusy: () => boolean;
};

/**
 * A one-slot mutual-exclusion gate around an answer submission.
 *
 * WHY THIS IS NOT REACT STATE. `setState` is asynchronous and batched: two taps dispatched in the
 * same frame both read the pre-update value, both pass a `if (submitting) return` check, and both
 * submit. The guard therefore has to be a synchronous mutable cell, which is what this closure is
 * and what a `useRef` holding it provides. State is still set alongside it, but only to render the
 * indicator -- never to decide whether a submission may proceed.
 *
 * WHAT IT PREVENTS IN COMPONENT C. The second submission on one task instance is refused by the
 * server with `task_already_terminal` (`task_service.py:573-576`), a 409, which
 * `classifySessionFailure` routes to the technical-block screen. That refusal is correct and stays
 * exactly as it is -- this gate does not soften it, and nothing here should ever be used to argue
 * the backend guard is redundant. What the gate changes is whether a child can reach it by
 * double-tapping SUBMIT while the first request is still in flight, which on a remote database
 * (measured: ~200 ms per query against a hosted Postgres, versus ~0.2 ms locally, across the
 * 15-25 queries one submission performs) is several seconds of an apparently dead button.
 *
 * WHAT IT PREVENTS IN COMPONENT B, which is different and worse. B's submit has no server-side
 * equivalent of C's `task_already_terminal` refusal: `submitAnswer` mints a FRESH
 * `Crypto.randomUUID()` idempotency key per call, and the server fingerprints the request BODY
 * against that key, so two taps are two unrelated requests that both succeed. The second one is
 * recorded as a real second attempt (`attempt_index = 2`). The adaptive model itself is safe --
 * `attempt_submission.py` gates the BKT observation on `attempt_index == 1 and event_kind ==
 * "RESPONSE"`, so a spurious second attempt contributes no observation -- but the attempt row is
 * still written, and this is a dyscalculia screening instrument whose attempt counts are research
 * data. A child recorded as having answered twice when they tapped twice on one answer is a data
 * defect, not a cosmetic one.
 *
 * A child seeing "Something changed on our end" after tapping twice reads it as the app breaking.
 * The backend was right; the interface simply let them ask twice.
 */
export function createSubmitGate(): SubmitGate {
  let busy = false;
  return {
    tryEnter: () => {
      if (busy) return false;
      busy = true;
      return true;
    },
    release: () => {
      busy = false;
    },
    isBusy: () => busy,
  };
}
