// Motor-constancy layout constants (SPEC section 10; Component C Phase 10 Sub-Phase Sequence v1.1
// section 5.1). These are the touch-target sizes, hit-slop, gesture thresholds and animation
// durations every archetype surface (10a...10h) must build against, and the guarantee is
// structural rather than measured: this module takes no input of any kind, so the mathematical
// level a task is set at cannot influence a touch target, because the level is not in scope where
// touch targets are defined. There is no function here to call with a level and no branch that
// could read one.
//
// The two line archetypes (line-position, line-traversal) are named in the sequence doc as where
// this would break by default: a fixed-width line rendered at a growing step count makes a later
// level a finer motor act than an earlier one. The fix is architectural, not tunable -- a constant
// per-step touch target, with the line scrolling or paginating rather than compressing -- and nothing
// below varies by any external input.
//
// c-motor-constants.test.ts asserts two things: every export here is a plain value, never a
// function; and this file's own source, with comments stripped, contains no reference to the level
// concept at all. The comment-stripping matters -- an earlier guard in this codebase
// (no-node-builtins-outside-tests-and-scripts.test.ts) was first written as a bare substring match
// and failed on its own explanatory comments, which is exactly the trap this paragraph is written
// to survive.

export const TOUCH_TARGET_MIN_SIZE = 48;

export const HIT_SLOP = { top: 8, bottom: 8, left: 8, right: 8 } as const;

// The unit-stepper's per-step control. Constant regardless of how many steps a task needs; when a
// line has more steps than fit at this size, it scrolls or paginates -- it never shrinks the step.
export const STEP_TOUCH_TARGET_SIZE = 56;

export const STEP_SPACING = 12;

export const GESTURE_LONG_PRESS_MS = 400;

export const ANIMATION_DURATION_MS = 200;

// `value-token-row`'s own tokens (10a). Deliberately separate from STEP_TOUCH_TARGET_SIZE /
// STEP_SPACING above: those are commented as the unit-stepper's per-step control, a distinct,
// separately-owned primitive (Phase 10 Sub-Phase Sequence v1.1 §3.2 lists `unit-stepper` and
// `value-token-row` apart). Reusing the stepper's constants here would conflate two primitives the
// sequence doc keeps apart on purpose.
export const TOKEN_TOUCH_TARGET_SIZE = 56;

export const TOKEN_SPACING = 12;

// `digit-keypad`'s own keys (10a). A digit key is smaller than a token or a step control by
// design -- a keypad packs ten keys plus delete into one reachable panel, and constancy only
// requires this size be identical at every difficulty level, not identical to a different
// primitive's own control size.
export const KEYPAD_KEY_SIZE = 48;

export const KEYPAD_KEY_SPACING = 8;

// `object-quantity-display.tsx`'s own per-object size (10e-0) -- a PASSIVE, READ-ONLY display,
// never pressed, so SPEC section 10's 48px interactive-touch-target floor does not govern it at all
// (matching `value-report-surface.tsx`'s own `PAYLOAD_TOKEN_SIZE` precedent: "SPEC section 10
// governs interactive geometry... it says nothing about a label a child never presses"). Kept as
// its own constant pair, not reused from `TOKEN_TOUCH_TARGET_SIZE`/`STEP_TOUCH_TARGET_SIZE`, for the
// same reason those two are kept apart from each other: a third, conceptually distinct primitive
// gets a third pair, even where a value might otherwise coincide. Sized at half of
// `TOKEN_TOUCH_TARGET_SIZE`/`TOKEN_SPACING` -- small enough that a real quantity in the dozens wraps
// into a small, legible block on a typical phone width rather than one unusably long row, while
// still being a deliberately named constant, never a bare literal in the primitive itself.
export const OBJECT_TOKEN_SIZE = 28;

export const OBJECT_TOKEN_SPACING = 6;

// A ceiling on how large a key is allowed to grow (2026-08-26 request), never a floor -- keys
// still respect KEYPAD_KEY_SIZE as their minimum (SPEC section 10's 48px accessibility floor,
// untouched). Without a cap, `key`'s `flex: 1` lets each key's WIDTH grow to fill however wide its
// container happens to be, and `aspectRatio: 1` then grows its HEIGHT to match -- so on a wide
// panel the whole keypad grows taller than it needs to, purely as a side effect of screen width,
// not of anything about the keys themselves. Capping width (via KEYPAD_GRID_MAX_WIDTH, computed
// alongside this in digit-keypad.tsx from this same constant) caps height the same way, because
// the keys stay square either way -- the same `aspectRatio: 1` that guarantees squareness at the
// small end guarantees it at this end too.
export const KEYPAD_KEY_MAX_SIZE = 64;

// `array-grid.tsx`'s own per-cell size (10g, C-EG-02). A PASSIVE, READ-ONLY display -- never
// pressed -- so SPEC section 10's 48px interactive-touch-target floor does not govern it, matching
// `object-quantity-display.tsx`'s own stated precedent ("SPEC section 10 governs interactive
// geometry... it says nothing about a label a child never presses"). Kept as its own constant pair
// rather than reused from `OBJECT_TOKEN_SIZE` (a different, already-distinct passive primitive),
// for the same reason `OBJECT_TOKEN_SIZE` itself is kept apart from `TOKEN_TOUCH_TARGET_SIZE` /
// `STEP_TOUCH_TARGET_SIZE`: a third conceptually distinct primitive gets a third pair. Sized so a
// real grid up to 5x5 (the observed maximum) renders as a small, legible square block rather than
// spanning the card's own width.
export const GRID_CELL_SIZE = 32;

export const GRID_CELL_SPACING = 4;
