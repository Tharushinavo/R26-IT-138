// Local-only telemetry capture (10.0-work-order.md SCOPE section 4; sequence doc ruling 6.4).
// Honest client-side timestamps, held in memory for the running session only, and NEVER
// transmitted -- there is no telemetry ingestion route on the wire (agent2.md section 6.2) and
// CSubmitActionRequest carries only `action_payload`, so nothing here could ride along on a
// submission even if it tried.
//
// Deliberately NOT persisted to SecureStore, unlike session-command-store.ts's pending-command
// recovery record. The owner's ruling is "captured locally, transmits nothing"; surviving an app
// relaunch is capability beyond that text, not implied by it. There is also a positive reason not
// to: telemetry that persists but is never transmitted would accumulate on a child's device
// indefinitely with no consumer and no retention story, which is worse than holding it for the
// running session and discarding it when the session ends.
//
// This file imports nothing from any API module, no `fetch`, no `XMLHttpRequest`, no `WebSocket`.
// c-telemetry-no-network-call.test.ts asserts that structurally, with an in-memory negative
// control. That guard strips comments before matching (regex-shaped, not a real tokenizer) and
// requires actual call/import syntax rather than a bare substring -- its stated blind spots are
// the same as the committed node-builtins guard: no constructed/dynamic specifier detection, and a
// string literal containing a literal "//" on the same line as real code could be mis-treated as
// commented out. No file in this codebase does that today.

export type TelemetryCategory = 'technical' | 'gameplay';

export type TelemetryEvent = {
  category: TelemetryCategory;
  label: string;
  atIso: string;
};

let log: TelemetryEvent[] = [];

function push(category: TelemetryCategory, label: string): TelemetryEvent {
  const event: TelemetryEvent = { category, label, atIso: new Date().toISOString() };
  log.push(event);
  return event;
}

// --- gameplay category. Never itself evidence of correctness, of the mathematical level, or of a
// safety action -- strictly a record that something happened, and when. ---

export function recordTaskOffered(): TelemetryEvent {
  return push('gameplay', 'task_offered');
}

export function recordTaskStarted(): TelemetryEvent {
  return push('gameplay', 'task_started');
}

export function recordActionSubmitted(): TelemetryEvent {
  return push('gameplay', 'action_submitted');
}

// --- technical category. Backgrounding and network loss are ALWAYS this category, never "learner
// inactivity". There is no inactivity-detection mechanism in this batch: an inactivity timeout is
// a timing threshold, and every timing threshold in this project is governance-unsigned, so
// building one here would be inventing a policy this client does not own. The two categories stay
// structurally distinct instead -- every function below always tags 'technical' and every function
// above always tags 'gameplay'; there is no shared code path and no parameter that lets a caller
// choose the category, so a label can never be mis-tagged across the boundary. ---

export function recordBackgrounded(): TelemetryEvent {
  return push('technical', 'app_backgrounded');
}

export function recordForegrounded(): TelemetryEvent {
  return push('technical', 'app_foregrounded');
}

export function recordTechnicalIssue(reason: 'network' | 'timeout'): TelemetryEvent {
  return push('technical', 'technical_issue:' + reason);
}

export function getTelemetryLog(): readonly TelemetryEvent[] {
  return log;
}

export function resetTelemetryLog(): void {
  log = [];
}
