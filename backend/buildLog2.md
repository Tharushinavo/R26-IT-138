# Component B/C Backend Build Log (continued, second rotation)

> `backend/buildLog1.md` is closed as of its final entry, **FE-surface-remount-key** (2026-08-25),
> and must not be appended to or edited further. It had grown past 10,000 lines. This file,
> `buildLog2.md`, is its rotation and continues the same living, append-only development audit log
> from this point forward, under the same rules: future work is appended as a new dated phase or
> batch, earlier entries are never removed, rewritten, or silently altered. `buildLog.md` (closed at
> FE-0c) and `buildLog1.md` (closed at FE-surface-remount-key) remain the earlier history and are
> read-only.

---

## 2026-08-25 — FE-surface-remount-key: supervisor verification (batch committed to `buildLog1.md`, closed before this note could be appended there)

**Provenance.** The batch itself — commit `19d4530`, "Component C: remount the task surface per task
instance, so an entered answer cannot survive into the next question" — was implemented and its
builder register entry appended to `backend/buildLog1.md` (ending, per convention, with the literal
placeholder `**Verification.** — supervisor's, pending`) before the decision to rotate the log. This
entry is the supervisor's verification half of that same batch, recorded here rather than reopening
the closed file.

**Verification — supervisor's, measured.** Independently reproduced, redirected to a file rather than
piped (this project's own SIGPIPE mitigation): `npx tsc --noEmit` exit 0. `npm run test:contract`
**514 tests, 514 passed, 0 failed**, run twice. Reconciles against the pre-batch baseline of 505,
measured at HEAD `682e5ba` immediately before this change: `505 + 9 added − 0 removed = 514`. The nine
new tests were also run in isolation (`node --import tsx --test
src/api/__tests__/c-surface-remounts-per-task.test.ts`): 9/9 pass.

Diff read in full — exactly the one `key` prop on `<Surface>`, its explanatory comment, the new test
file `frontend/src/api/__tests__/c-surface-remounts-per-task.test.ts`, and the builder's own register
entry in `buildLog1.md`; no file outside that set was touched, including the five files the concurrent
game-hub work had already modified in the same tree, confirmed absent from `git diff --stat` and from
the commit itself. Guard proven to fire in both directions (red with the key removed, red with the key
bound to a string constant, green on the real fixed file), with a positive control against a vacuously
`null` predicate.

**What was not verified, restated from the builder's own disclosure.** The remount itself was not
observed — this project has no rendering library, so no test here can mount a tree, drive a submit,
and confirm the input actually clears between tasks. What is proven is that the source binds the key
to a real, non-repeating, required-string field on the wire contract. That React remounts on a changed
key is relied upon, not verified by this project. Confirmed correct as stated: under the dev fixture,
`c_task_instance_id` is constant, so the fix will not visibly change anything in the browser until a
real backend serves genuinely distinct task instances — not a regression, a fixture limitation.

Committed as `19d4530`.

## 2026-08-25 - FE-entry-row-opens-on-slots: the entry scene now opens on the entry slots, with a visible scroll indicator

**Why.** Second finding from the first browser look at a Component C surface, at
`EXPO_PUBLIC_COMPONENT_C_DEV_FIXTURE_DIFFICULTY=5` (C-NP-01, `blanks=2`).

`DisplayWithEntryRow` renders the read-only `shown_sequence` followed by the editable entry slots
inside one horizontal `ScrollView`. The row scrolls rather than shrinking its tokens -- that is the
motor-constancy ruling this file's own header records, and it is correct. The consequence nobody had
seen until it ran: at difficulty 5 the shown sequence is long enough that the entry slots, the only
interactive part of the scene, render past the right edge of the viewport.

The owner filled the one slot that was visible and could not press SUBMIT. The button was correctly
disabled throughout -- `entryValues` still held a `null` in slot 2 -- but there was no way to discover
that. The second slot was off-screen and `showsHorizontalScrollIndicator={false}` was set, so nothing
on screen indicated any further content existed at all. A correct disabled state with no discoverable
cause is, to a child, indistinguishable from a broken button.

**Owner ruling, from two options presented:** open the row on the entry slots rather than on the
read-only sequence. The child can still scroll left to review it.

**What.** Two changes, both confined to `DisplayWithEntryRow`:

1. The `ScrollView` takes a ref and scrolls once, on mount, to `shownSequence.length * TOKEN_STRIDE`.
   That offset is derived, never tuned: the row has no leading horizontal padding and every token
   occupies exactly one `TOKEN_STRIDE`, so that expression IS the first entry slot's position and it
   moves correctly if `TOKEN_TOUCH_TARGET_SIZE` or `TOKEN_SPACING` ever change.
2. `showsHorizontalScrollIndicator={false}` becomes a visible indicator.

The scroll is **not animated**. Content sliding sideways just as the screen appears is a worse
attention cost for this audience than content simply already being in the right place. The work order
required reporting rather than deciding if the project had a documented reason to prefer animation:
`motor-constants.ts` and this feature were both checked, and there is none. `ANIMATION_DURATION_MS`
exists but is documented for the drag-drop return in `DraggableToken`, not for scrolling.

It runs once per mounted scene, guarded by `hasScrolledToEntryRef` rather than by an empty dependency
list, so no later re-render can yank the row back and fight a child's own scrolling. Since
`FE-surface-remount-key` (`19d4530`) now keys the surface on the task instance, a new task is a new
mount -- which is what makes "once per mount" also mean "once per task".

**ReorderRow was not touched, and this was confirmed rather than assumed.** NP-04's arrangement scene
has no entry/read-only split -- every token is the same draggable control and none is hidden behind
another -- so this defect does not arise there. Its indicator setting is unchanged and it gained no
scroll-on-mount. A dedicated guard asserts both, per-function rather than file-wide, because the two
components render structurally similar `ScrollView`s and a whole-file scan could not tell which one
it had found.

Nothing in focus or typing changed: `focusedSlot`, `buffers`, `handleDigit`, `handleDelete` and
`commit` are untouched. This batch makes an existing slot reachable and visible; it does not change
what typing does.

**A separate finding, reported and NOT built here.** With `blanks=2`, filling slot 1 does not advance
focus to slot 2 -- the child must tap the second slot themselves. That is arguably its own
discoverability problem, adjacent to this one but distinct from it. It was explicitly out of this
batch's scope and no auto-advance was added. Recorded here so it is not rediscovered from scratch.

**Verification.**

- `npx tsc --noEmit` - exit 0, achieved by fixing code. No `any`, no `as` cast, no `@ts-ignore`.
- `npm run test:contract` - 528 tests, 528 pass, 0 fail. Baseline measured immediately before this
  change at HEAD 85d973f was 514. Reconciles: 514 + 14 added - 0 removed = 528.
- `npx expo lint` - clean.
- Both guards were proven in BOTH directions against the REAL file, not only against synthetic
  strings: the file is read, mutated in memory back to its exact pre-fix shape, and each guard
  asserted red on it -- with a prior assertion that the mutation actually applied, so a no-op replace
  cannot produce a false red. Nine further negative controls pin each clause individually: an
  animated scroll, a hardcoded pixel offset, a dropped once-guard, an unattached ref, a suppressed
  indicator, a missing function, and a file that only discusses the fix in comments.
- `expo export` NOT run. The change adds no new module import -- `useEffect` and `useRef` come from
  `react`, already imported in this file for `useState` -- so the bundle graph is unchanged.
- The backend suite was NOT run. No backend file was changed by this batch.

**What was NOT done, and cannot be.** The scroll was NOT observed. This project has no rendering
library in devDependencies, so nothing here can mount the row, measure a viewport and assert the entry
slots are on screen. Neither the scroll moving the viewport, nor its timing, nor the absence of
animation in the rendered result is verified by this suite -- only what the source says. One specific
risk this leaves open and unproven: a `scrollTo` issued from a mount effect depends on the row's
content having been laid out by the time the effect runs, and whether that holds on every platform is
exactly the sort of thing only a browser and a device can answer. A supervisor should look at
DIFFICULTY=5 before this is treated as fixed.

**Files touched.** `frontend/src/features/c-session/primitives/value-token-row.tsx`,
`frontend/src/api/__tests__/c-entry-row-opens-on-entry-slots.test.ts`.

**Verification.** — supervisor's, pending

---

## 2026-08-25 — Correction: FE-entry-row-opens-on-slots shipped as row-wrapping, not the auto-scroll described above

**Append-only correction, per this file's own rule.** The entry directly above this one is not edited or removed; it describes an implementation that was superseded in the working tree before it was committed, and nobody wrote that supersession down until now.

**What the entry above says was built:** `DisplayWithEntryRow`'s `ScrollView` takes a ref and scrolls once on mount to `shownSequence.length * TOKEN_STRIDE`, with a visible scroll indicator, guarded by `hasScrolledToEntryRef`.

**What is actually in `value-token-row.tsx` right now:** there is no `ScrollView` in `DisplayWithEntryRow` at all. The shown sequence and the entry slots render inside one `View` styled `entryTokenRow` (`flexWrap: 'wrap'`), so the row wraps onto further lines instead of scrolling. The entry slots cannot go off-screen, because there is no longer a scrollable axis for them to go off of. `ReorderRow` (`C-NP-04`) is unchanged — still a horizontally scrolling `ScrollView`, per its own different reason (the whole draggable token count can exceed one row).

This is a stronger fix than the one ruled and described above, not a weaker one: auto-scroll moves the visible window to a fixed offset computed from `shownSequence.length`, which depends on that length being what the scroll math assumed; wrapping removes the off-screen case as a category, regardless of sequence length. Nobody has reported why the approach changed between the ruling and what shipped — recorded as an open question, not resolved here.

**Verification — supervisor's, measured, of the CURRENT code, independently of the entry above.**

- `npx tsc --noEmit` — exit 0.
- The test file `c-entry-row-opens-on-entry-slots.test.ts` run in isolation (`node --import tsx --test src/api/__tests__/c-entry-row-opens-on-entry-slots.test.ts`): **10 tests, 10 passed, 0 failed.** Its own test names assert the wrapping design directly — *"renders one wrapping row, not a ScrollView"*, *"the row guard fires when a ScrollView is reintroduced"* — which would not describe an auto-scroll implementation if one existed.
- Whole-suite `npm run test:contract`: **512 tests, 510 passed, 2 failed.** The two failures are the pre-existing, unrelated game-hub barrel-import defect (a test whose import graph reaches `react-native` via a theme barrel; diagnosed and documented separately in `10b-10h-master-work-order.md` §5).

**Arithmetic NOT reconciled, and stated as such rather than guessed.** The entry above's own baseline was 514, measured at `85d973f`. This tree also carries several other uncommitted, interleaved changes to the same files (`digit-keypad.tsx`'s calculator-order relayout, `c-session-screen.tsx`'s card-based redesign, `component-c-api.ts`'s dev-fixture family override) whose own individual test-count deltas have not been isolated from this one. A crashed test file's exact contribution to `node --test`'s aggregate `tests`/`fail` counts was also not independently confirmed here. Rather than publish a guessed reconciliation into a permanent record, this is left open: clean arithmetic is only possible from a real before/after diff at the point this work is actually committed, which is when it will be measured.

**What was NOT verified**, restated from the superseded entry's own disclosure and still true of the current code: nothing here can mount a component tree, so the wrapping itself — whether the entry slots genuinely render on-screen at difficulty 5, on a real device — has not been observed. `npx expo export` was not re-run for this correction; no new module import was introduced by switching `ScrollView` to `View`.

---

## 2026-08-25 — fix: game-family-accents.ts no longer reaches react-native through the theme barrel

**Diagnosed while splitting the task-screen redesign (committed `84874ce`) from the concurrent game-hub batch.** Two of the game-hub's own test files (`c-game-hub-catalogue.test.ts`, `c-game-hub-layout.test.ts`) failed with `Transform failed: node_modules/react-native/index.js:27:7: ERROR: Unexpected "typeof"` -- `node --import tsx --test` cannot transform react-native's own Flow-typed entry file.

**The chain:** `game-catalogue.ts` → `game-family-accents.ts` → `@/src/theme/tokens` (barrel) → re-exports `createGlobalStyles` from `@/src/theme/styles` → `styles.ts`'s **value** import `import { StyleSheet } from 'react-native'`. `game-family-accents.ts`'s own header states *"It also imports NOTHING that reaches React Native"* -- that claim was false; the module is careful to inject the surface lookup rather than import `archetype-surfaces.ts` directly, then reached react-native anyway, three hops down a theme barrel nobody had checked.

**A correction to this project's own earlier diagnosis of the same chain, recorded above in `10b-10h-master-work-order.md`:** the first fix considered was importing `colors` from `@/src/theme/colors` instead of the barrel. That module is marked `@deprecated` and re-exports from `@/src/theme/theme.ts` -- which was confirmed, by reading its import line rather than assuming, to carry only `import type { TextStyle, ViewStyle } from 'react-native'`. A type-only import is erased entirely at compile time and never resolves the real react-native package, so that path is safe. `theme/styles.ts`'s import is a genuine value import and is what actually crashes the transform. Both were checked by reading the source, not inferred from a naive substring grep for `"from 'react-native'"`, which cannot distinguish the two.

**Fix.** One line: `game-family-accents.ts` now imports `colors` from `@/src/theme/colors`, never the `tokens` barrel. A comment in the file explains why the deprecated leaf is used deliberately here, so a future edit does not "clean it up" back to the barrel.

**Verification — supervisor's, measured.**

- `npx tsc --noEmit` — exit 0.
- `c-game-hub-catalogue.test.ts` + `c-game-hub-layout.test.ts` in isolation: **15 tests, 15 passed, 0 failed** (11 + 4, both files now load).
- Whole suite, immediately before this fix: **512 tests, 510 passed, 2 failed.** Immediately after: **525 tests, 525 passed, 0 failed.** Reconciles cleanly: the two crashed-file placeholders (each counted as exactly one test and one failure by `node --test` when a file's top-level import throws before any `test()` registers) are replaced by their real 15 tests, all passing: `512 + 13 = 525`, and `510 + 15 = 525` with `2 − 2 = 0` failures. This also settles, after the fact, an assumption used but not confirmed in the correction entry immediately above this one -- that a crashed file contributes exactly one to both counts regardless of its real test count -- which this clean before/after now demonstrates directly.
- No other file was touched. `game-family-accents.ts` is a single-file change on top of an already-committed file (`84874ce`); it is not folded into that commit.

**What was NOT verified.** `npx expo export` was not re-run — the change swaps one import path for another within the existing dependency graph and adds no new module. The backend suite is unaffected; no backend file changed.

---

## 2026-08-26 — feat: `value-report` archetype registered (10b), eight templates

Component C frontend, sub-phase 10b (`10b-10h-master-work-order.md` §4). Registers the
`value-report` archetype for eight templates: `C-TC-01`, `C-TC-03`, `C-TC-04`, `C-JB-01`,
`C-JB-03`, `C-JB-04`, `C-EG-03`, `C-SF-03`. `C-TC-02` is excluded from this batch by owner ruling
(§2.1 of the master work order — its `directed` boolean payload discriminator's evaluator behaviour
is unresolved and private to the engine) and appears in none of the files added.

**New files:** `frontend/src/features/c-session/archetypes/value-report-logic.ts` (pure resolution,
no React/RN import — classifies `valid_action_space` by declared TYPE via the existing
`field-kinds.ts`, never by template id or key name: exactly one `integer-field`-kind key becomes
the scene key, any other declared key must bind to `boolean-control` or resolution fails closed),
`value-report-surface.tsx` (reuses 10a's screen chrome, `SubmitButton` and boolean-toggle shapes
reproduced from `ordered-value-sequence-surface.tsx`'s private `GenericExtraField`, plus the shared
`DigitKeypad` — no new visual primitive introduced), and eight test files under
`frontend/src/api/__tests__/` covering resolution, the key-set-equality proof (six distinct `int`
key names, both boolean-bearing templates), the boolean-control derivation proof, prompt-text
identity, motor constancy, fail-closed paths, the `representation_mode` guard, and
`interactive_assets` carry-through — each with negative controls.

**Edited:** `frontend/src/features/c-session/archetype-surfaces.ts` — one import and one
`SURFACE_TABLE` entry (`'value-report': ValueReportSurface`). No other file in this batch was
touched; `game-catalogue.ts`/`game-hub/` were not touched (family readiness is computed from
`SURFACE_TABLE` at call time, per the master work order's own finding).

**A consequence worth recording, not a defect in this batch's own files.** `registry.ts`'s
`ARCHETYPE_TABLE` (pre-existing, unmodified here) already maps `C-TC-02` to `value-report`. Because
`value-report-logic.ts` classifies purely by declared type — never by template id — and `C-TC-02`'s
`valid_action_space` (`submitted_difference: int`, single key, `blanks: null`) is structurally
identical in shape to `C-TC-03`'s, registering a `value-report` surface at all means `C-TC-02` now
also resolves to a live, mounted surface, where before this batch it fell through to
`FailClosedFrame` (no surface registered for any `value-report` id). This was not introduced by
adding template-id logic — none exists — it is an emergent consequence of the two-layer rule
applied faithfully: the archetype cannot tell `C-TC-02` apart from the other eight from the wire
shape alone. If `directed=true` at difficulty 5 in fact requires a signed answer, `C-TC-02` will now
render an interactive but unusable surface (no minus key) rather than the neutral fail-closed
screen it rendered before. Flagged here for the owner rather than resolved unilaterally: excluding
`C-TC-02` structurally would require either a template-id branch (violates the two-layer rule this
archetype is built to prove) or a change to `registry.ts` (out of scope for this batch, and not
requested).

**Verification — measured.**

- `npx tsc --noEmit` — exit 0.
- The eight new test files run in isolation
  (`node --import tsx --test src/api/__tests__/c-value-report-*.test.ts`): **98 tests, 98 passed, 0
  failed.**
- Whole-suite `npm run test:contract`, immediately before this batch: **525 tests, 525 passed, 0
  failed.** Immediately after: **625 tests, 625 passed, 0 failed.** Reconciles: `525 + 100 = 625`,
  `0` failures throughout. The extra 2 tests beyond the 98 added directly by this batch's own files
  come from pre-existing table-driven tests over `SURFACE_TABLE` / the game-hub catalogue
  (`c-game-hub-catalogue.test.ts`, `c-plan-task-surface.test.ts`,
  `c-session-screen-task-branch.test.ts`) picking up the newly-registered `value-report` entry on
  their own — confirmed by running those three files in isolation (21 tests, 21 passed) — which is
  the self-updating wiring the master work order's §0 describes, not a hand-edit to those files.
- `npx expo export --platform ios` — succeeded (`_expo/static/js/ios/entry-*.hbc`, 5.09 MB
  bundle). `dist/` removed immediately after, per the gate's own instruction.

**What was NOT verified.** Nothing in this repository can mount a React Native tree, so no test
here proves the surface renders correctly on a real screen at difficulty 1 and 5 for any of the
eight templates — that is the standing "look at it in a browser before the next sub-phase" step
(master work order §6), not yet done. The backend suite is unaffected; no backend file changed
besides this log entry.

---

## 2026-08-26 — fix: `value-report` now renders `prompt_payload`'s numbers (10b correction)

**Found by the standing "look at it in a browser" step** (master work order §6) — exactly the
practice A2 established and this entry vindicates again. The user pointed the dev fixture at
`C-TC-01` and clicked into it: the screen showed the prompt text and the digit keypad, nothing
else. The original 10b entry above stated *"every real `prompt_text` for these eight templates is
fully backend-composed with no deictic pointer into `prompt_payload`... so there is nothing in
`prompt_payload` this surface needs to display."* **That claim was wrong.** All eight
`prompt_text` strings point at a quantity the text itself never states — *"Take away the amount
shown"*, *"Add the two numbers"*, *"Subtract the second number from the first"*, *"Find the total
for the equal groups shown"*, *"Split the number in half"* — and `interactive_assets` is `{}` on
every real exemplar for all eight, so there was no picture standing in for the missing numbers
either. The surface was rendering a fully unusable task: a child had no way to know what number to
subtract, add, or split.

**Fix.** `value-report-logic.ts`'s `resolveValueReportSpec` now extracts every `prompt_payload`
value generically (never a per-template key-name table — `initial_count`/`removed_count`,
`minuend`/`subtrahend`, `count_a`/`count_b`, `addend_a`/`addend_b`, `operand_a`/`operand_b`,
`multiplicand`/`multiplier`, `dividend` all satisfy the same rule: every payload value must be a
finite number, carried through in wire order as `payloadValues`), and fails closed on an empty
`prompt_payload` or a non-numeric value (this also means a task shaped like `C-TC-02`'s, whose
`prompt_payload` carries a boolean `directed` discriminator alongside its numbers, now fails to
resolve rather than rendering incompletely — an emergent consequence of the generic rule, not a
template-id check added for that purpose). `value-report-surface.tsx` renders these as read-only
tokens between the prompt and the answer keypad, reusing `value-token-row.tsx`'s own token style
and `TOKEN_TOUCH_TARGET_SIZE`/`TOKEN_SPACING` constants (motor-constants.ts) — no new geometry.
`ValueTokenRow` itself was not reused directly: its only display mode couples shown values to its
own entry slots and keypad, which would have duplicated this surface's separate answer field.

**Test changes.** 7 new negative controls across `c-value-report-logic.test.ts` (empty
`prompt_payload`, a non-numeric value) and `c-value-report-fail-closed.test.ts` (empty payload, a
boolean value, a string value, `NaN`), plus content assertions that `payloadValues` matches each
real exemplar's `prompt_payload` in key and value, in order, across all eight templates and all
five difficulty levels. One motor-constancy addition confirming the payload tokens use the same
shared constants, not a new size.

**Verification — measured.**

- `npx tsc --noEmit` — exit 0.
- The nine `c-value-report-*.test.ts` files in isolation: **105 tests, 105 passed, 0 failed**
  (up from 98 before this fix — the 7 new negative controls, 0 removed).
- Whole-suite `npm run test:contract`, immediately before this fix: **625 tests, 625 passed, 0
  failed.** Immediately after: **632 tests, 632 passed, 0 failed.** Reconciles: `625 + 7 = 632`.
- `.env.local` (gitignored, not part of this diff) was repointed at
  `EXPO_PUBLIC_COMPONENT_C_DEV_FIXTURE_TEMPLATE=C-TC-01` /
  `EXPO_PUBLIC_COMPONENT_C_DEV_FIXTURE_FAMILY=C-GF-06` so the user could re-check the fix visually
  after restarting the dev server; not reverted here, left for the user.

**What was NOT verified by this entry itself.** The corrected render has not yet been independently
re-confirmed by a screenshot on this side — the user reported the original defect and this fix
responds to that report; the user is re-checking directly in their own browser.

---

## 2026-08-26 — fix: `value-report`'s payload numbers are now labelled (10b correction, part 2)

**Found by the user's own re-check of the fix immediately above.** With the two numbers now
rendered (`4`, `2` for a `C-TC-01` task), the user reported they still couldn't tell what to do:
*"even i cant understand is it 4-2?"*. Two unlabeled tokens carry no indication of which number is
the starting amount and which is the amount removed, or of any operation at all — the same gap as
before, one layer down: showing the numbers wasn't sufficient without also showing what they mean.

**Decision, made with the user rather than guessed.** Presented three options (humanised key
labels; a neutral order-only visual separator; treat as a backend/content gap and stop). The user
chose labelled tokens.

**Fix.** New file `value-report-payload-labels.ts`: a fixed lookup, `labelForPayloadKey(key)`,
covering the real `prompt_payload` key vocabulary across all eight approved templates
(`initial_count`→"Start", `removed_count`→"Taken away", `minuend`→"Start",
`subtrahend`→"Taken away", `count_a`/`count_b`→"First group"/"Second group",
`addend_a`/`addend_b` and `operand_a`/`operand_b`→"First number"/"Second number",
`multiplicand`/`multiplier`→"First number"/"Second number", `dividend`→"Number"), keyed by
`prompt_payload` key name rather than template id (so a future template reusing an existing key,
e.g. another `minuend`, is labelled identically with zero code change), with a mechanical
humanised-key fallback (`some_future_quantity` → "Some Future Quantity") for any key outside the
table, rather than failing the task closed over a label gap. `value-report-logic.ts`'s
`PayloadValue` now carries a `label` alongside `key`/`value`; `value-report-surface.tsx` renders
the label above each token.

**Verification — measured.**

- `npx tsc --noEmit` — exit 0.
- The ten `c-value-report-*.test.ts` files in isolation: **125 tests, 125 passed, 0 failed** (up
  from 105 — 18 in the new `c-value-report-payload-labels.test.ts` file, plus 2 more from two
  existing source-scan tests (`c-value-report-no-representation-mode.test.ts`,
  `c-value-report-motor-constancy.test.ts`) that iterate a file list and picked up the new module
  automatically).
- Whole-suite `npm run test:contract`, after this fix: **653 tests, 653 passed, 0 failed.**
  Reconciles directly: running every OTHER test file (excluding all `c-value-report-*`) in isolation
  gives **528**, and `528 + 125 = 653` exactly.
- Scope unchanged from the entry above — same file family, one new file added
  (`value-report-payload-labels.ts` + its test), nothing outside it touched.

**What was NOT verified by this entry.** Whether "Start"/"Taken away"/"First number"/"Second
number"/"Number" are the right words for the target population (children with dyscalculia) is a
content/pedagogy judgment, not something a test can confirm — flagged to the user as a real
possibility (option offered, not chosen) that this may still want an owner content review rather
than resting on this label set as final. The corrected render has not been independently
re-confirmed by a screenshot on this side; the user is re-checking directly.

---

## 2026-08-26 — 10b CLOSED: visual pass across all eight templates, remaining polish, two shared-file fixes

**This entry closes 10b.** Everything below happened in direct response to the user driving the
running surface in their own browser, one template at a time, exactly the standing practice the
master work order's §6 calls for — and, as with A2, it found real things a passing test suite could
not: a missing render, ambiguous labelling, misaligned boxes, an unclear boolean control, an
oversized shared keypad, and a genuine bug in a shared file two turns away from `value-report`
itself. Each is recorded here in one place rather than left scattered across the session.

### Remaining `value-report-surface.tsx` polish, after the two correction entries above

- The bordered box first wrapping the payload tokens was added, then removed on the user's own
  follow-up — tokens and labels stay centred without it (`payloadRow`'s own `justifyContent:
  'center'` already did the centring; the box was redundant).
- Gap between tokens doubled (`TOKEN_SPACING * 2`), per direct request.
- The answer field, previously a bare buffer of text below the payload row with its own `DigitKeypad`
  underneath, is now its **own labelled column** ("Answer") in the *same* row as the given values,
  sharing the row's `flex: 1`-per-column division so the row splits evenly across however many
  columns exist (2 given values + 1 answer for six templates, 1 given value + 1 answer for
  `C-SF-03`). Shows a `'?'` placeholder before the child types a digit, replacing an empty box that
  gave no cue which one was theirs to fill in.
- **Real defect, found by the user, not by a test:** "Taken away" wraps to two lines in its narrow
  column while "Start"/"Answer" stay on one line, which left that box sitting visibly lower than its
  neighbours — the three boxes were not level. Fixed by reserving a fixed two-line-tall,
  bottom-aligned block (`payloadLabelBlock`, height `PAYLOAD_LABEL_LINE_HEIGHT * 2`) for every
  label regardless of how many lines its own text needs, so a token's top edge no longer depends on
  whether its label happened to wrap.
- The single boolean toggle (one button whose text flipped between "YES" and "NO") is now **two
  separate buttons**, neither shown as selected until the child actually picks one — the old single
  toggle defaulted to displaying "NO" before any real choice was made, which read as an answer
  already given. Still driven generically off `valid_action_space`'s declared `bool` keys, same as
  before; only the rendering changed.
- `payload-value-labels.ts` (renamed from `value-report-payload-labels.ts`, generalised out of the
  `value-report`-only framing its first version carried) is now a shared lookup any archetype can
  reuse for the same "which number is which" disambiguation, since `line-traversal` (next, 10c) needs
  identical treatment for `start`/`addend_a`/`addend_b`. No behaviour change for `value-report` — the
  same 13 (now 14, `start` added) keys resolve to the same labels; only the file's name, header, and
  import path moved. Its test file moved with it, `c-value-report-payload-labels.test.ts` →
  `c-payload-value-labels.test.ts`.

### Two fixes outside the `value-report` file family, both direct user requests

- **`DigitKeypad` (shared primitive, `primitives/digit-keypad.tsx`) — capped key size.** The user
  asked for a visibly shorter keypad with keys that stay square. Added `KEYPAD_KEY_MAX_SIZE` (64) to
  `motor-constants.ts` as a ceiling alongside the pre-existing `KEYPAD_KEY_SIZE` (48) floor; the
  grid's own width is now capped at `KEYPAD_KEY_MAX_SIZE * 3 + KEYPAD_KEY_SPACING * 2` and
  centred, so `key`'s existing `aspectRatio: 1` caps height the same way width is capped — no second,
  independent height rule. Applies everywhere `DigitKeypad` is used, so this also changed 10a's
  Number Path and Order (card #2), not only `value-report`'s cards — confirmed by the user checking
  both after the change.
- **`c-session-screen.tsx` — the X button routed to a "Something went wrong" screen.** Pre-existing
  behaviour, unrelated to `value-report`'s own code: the exit control's `leaveSession()` awaited
  `api.abandonSession(...)` and routed to the generic `technical` failure screen (`NeutralMessageScreen`,
  title "Something went wrong", its own "go to home" button) on any rejection — and the dev fixture's
  `abandonSession` is documented to throw by design every time, so X reliably produced that screen
  under the fixture. Fixed: `leaveSession` still attempts `abandonSession` (needed for the real
  backend) but no longer gates navigation on its result — success or failure, X now always lands on
  the Play hub (`/(learner)/play`, via the new `goToGameHub`), never home, never the failure screen.

### Full visual pass — all eight approved templates, difficulty 5, confirmed by the user directly

| Template | Card | Result |
|---|---|---|
| `C-TC-01` | #6 Take Away and Compare | ✅ (drove the payload-numbers and labelling corrections above) |
| `C-TC-03` | #6 | ✅ (drove the keypad max-size fix) |
| `C-TC-04` | #6 | ✅ (drove the YES/NO two-button fix) |
| `C-JB-01` | #5 Join and Bridge | ✅ |
| `C-JB-03` | #5 | ✅ |
| `C-JB-04` | #5 | ✅ |
| `C-EG-03` | #7 Equal Groups and Arrays | ✅ |
| `C-SF-03` | #8 Share Fairly | ✅ (single-given-value case: two-column row, "Number"/"Answer") |

`C-TC-02` was not shown at any point in this pass — it stays excluded per the owner ruling, and
nothing in this entry's changes touches it.

**Verification — measured, current tree.**

- `npx tsc --noEmit` — exit 0.
- Whole-suite `npm run test:contract`: **659 tests, 659 passed, 0 failed.**
- `npx expo export --platform ios` — re-run after all of the above (not just after the first
  registration entry): succeeded, `dist/` removed after.
- `.env.local`'s dev-fixture override, used throughout this visual pass to point at each template in
  turn, has been reset to its original default (`C-NP-01` / `C-GF-02`) now that the pass is complete.
  It is gitignored and was never part of any diff.

**What was NOT verified.** The label wording itself ("Start"/"Taken away"/"First number"/"Second
number"/"Number"/"Answer") still has no owner content/pedagogy sign-off — flagged twice now, still
open. No automated test can substitute for that judgment call.

---

## 2026-08-26 — feat: `line-traversal` archetype registered (10c), C-JB-02 only

Component C frontend, sub-phase 10c. Registers `line-traversal` for `C-JB-02` ("Count On from an
Addend") — the only template that archetype covers. Baseline: HEAD `ead55a9`, `npx tsc --noEmit`
exit 0, `npm run test:contract` 659/659/0.

**A stale work-order finding, reported rather than silently worked around.** `10b-10h-master-work-
order.md`'s §2.3 names `C-JB-04` as 10c's own "first two-layer falsification test" (a second,
boolean declared key added to an already-built archetype). That already happened, inside 10b:
`C-JB-04` was one of the eight templates 10b registered under `value-report`, and its
`exchange_performed` key was rendered generically off `valid_action_space` with no per-template
branch — proven by `c-value-report-boolean-control.test.ts`, which source-scans the logic file to
assert it never contains the literal strings `C-JB-04` or `exchange_performed`. 10c's real scope is
`C-JB-02` alone; `C-JB-01`/`C-JB-03`/`C-JB-04` are untouched and unrebuilt here. A regression check
(`c-line-traversal-logic.test.ts`) confirms all three still resolve to `value-report`.

**The backend evaluator resolved what the docs left ambiguous.** Read directly from
`backend/packaging/component_c_internal/component_c_generator/tasks/join_and_bridge.py`
(`_generate_jb02`/`_evaluate_jb02`): `start` = `max(addend_a, addend_b)`; the jump unit is fixed at
1; `expected_jump_count` = `min(addend_a, addend_b)`; the server checks `final_position == sum`,
`len(jumps) == expected_jump_count`, every jump equals 1, and `start + sum(jumps) == sum`. So the
child makes unit +1 jumps only, never chooses a jump size — confirming the sequence doc's
`unit-stepper` primitive and ruling out a free-form jump-value entry, which would only ever produce
lists the server rejects by construction. The client checks none of this itself (no jump-count
validation, no consistency check) — it relays what the child did.

**An answer-leak hazard not named in any doc.** The task's answer is `addend_a + addend_b`. A
number line whose extent were derived from that sum would display the answer as its own endpoint
before the child did anything. `MAX_LINE_FORWARD_STEPS` (`unit-stepper.tsx`) is therefore a fixed
layout constant (30, comfortably above the generator's theoretical ceiling of `min(addend_a,
addend_b) ≤ 18` at difficulty 5), never computed from the payload — guarded by a dedicated new test
file, `c-line-traversal-no-answer-derivation.test.ts`, source-scanning every new file for the literal
shapes an addend-sum would take.

**`final_position` is a separate keypad field, not auto-derived from the marker's position** — a
direct decision, confirmed with the user before building: auto-deriving it would make the client
guarantee `start + sum(jumps) == final_position`, which is literally one of the server's four
correctness conditions. The client relaying two independent pieces of what the child did (the jumps
made, and where they say they landed) keeps the authority boundary intact; the server is the one
that checks they agree.

**Growing jump count across difficulty is accepted, per sequence doc §5.1**, also confirmed with the
user before building: per-step touch target and spacing are constant at every level
(`STEP_TOUCH_TARGET_SIZE`/`STEP_SPACING`, motor-constants.ts, previously reserved but unused);
only the *number* of steps varies, which §5.1 classifies as mathematical demand, not motor demand —
counting on N times is the assessed skill for this template. The real frozen exemplar fixture's
jump counts across L1–L5 are `[2, 2, 1, 1, 3]` (measured, not assumed — a random draw can put the
larger addend on either side, so this stays well under the generator's theoretical ceiling); the
motor-constancy test states this measurement rather than a guessed "grows to N" claim.

**New files:**
- `frontend/src/features/c-session/archetypes/line-traversal-logic.ts` — pure resolution, no
  React/RN import. Classifies `valid_action_space` by declared TYPE (exactly one `integer-field` +
  exactly one `ordered-integer-collection`, any other declared kind or count fails closed), never
  by key name. Reads the `start` payload key by name as the line's origin — the same "reading the
  wire's own scene vocabulary" precedent `ordered-value-sequence-logic.ts` already set for
  `entered_values`/`arranged_values` — and excludes it from the rendered payload-token row (it
  duplicates the larger addend's value; the line itself shows it instead).
- `frontend/src/features/c-session/archetypes/line-traversal-surface.tsx` — reuses the screen
  chrome, `SubmitButton`, and payload-token shapes `value-report-surface.tsx` established, at the
  plain `TOKEN_TOUCH_TARGET_SIZE`/`TOKEN_SPACING` (not that file's own 1.6x/1.5x enlargement, which
  was a request scoped to that one screen, not a standing rule).
- `frontend/src/features/c-session/primitives/unit-stepper.tsx` — the shared discrete stepping
  primitive (ruling 6.3: discrete integer stepping, never continuous drag; constant per-step touch
  target; the line scrolls, never compresses), built generic enough for 10d's `line-position` to
  compose over unmodified, per the master work order's own instruction. Auto-scrolls to keep the
  marker on screen as it advances — a direct application of the A2 finding (10a's entry slots
  rendering off-screen at difficulty 5).
- `frontend/src/features/c-session/primitives/jump-accumulator.tsx` — the read-only record of jumps
  made. Deliberately not `value-token-row.tsx`: sequence doc §3.2 states the archetype chooses which
  of two primitives a `list[int]` key renders through, because the scene decides whether the list is
  entered or accumulated, and `jumps` is accumulated.
- Eight test files under `frontend/src/api/__tests__/` (`c-line-traversal-*.test.ts`) covering
  resolution across all 5 difficulty levels, the key-set-equality proof, fail-closed paths, prompt-
  text identity, motor constancy (including the jump-count-vs-step-size distinction), the
  `representation_mode` guard, `interactive_assets` carry-through, and the answer-leak guard.

**Edited:** `frontend/src/features/c-session/archetype-surfaces.ts` — one import and one
`SURFACE_TABLE` entry (`'line-traversal': LineTraversalSurface`). No other file touched;
`game-catalogue.ts`/`game-hub/` untouched — card #5 "Join and Bridge" flips from *Partly ready* to
*Ready to play* on its own, the same self-updating wiring 10b relied on.

**Verification — measured.**

- `npx tsc --noEmit` — exit 0.
- The eight new test files in isolation
  (`node --import tsx --test src/api/__tests__/c-line-traversal-*.test.ts`): **80 tests, 80 passed,
  0 failed.**
- Whole-suite `npm run test:contract`, immediately before this batch: **663 tests, 663 passed, 0
  failed** (up from 10b's 659 — the 4 extra came from pre-existing `SURFACE_TABLE`-driven tests
  picking up nothing new yet at that point; unrelated to this entry). Immediately after: **743
  tests, 743 passed, 0 failed.** Reconciles: `663 + 80 = 743`.
- `npx expo export --platform ios` — succeeded. `dist/` removed after.
- `.env.local` (gitignored, not part of this diff) repointed at
  `EXPO_PUBLIC_COMPONENT_C_DEV_FIXTURE_TEMPLATE=C-JB-02` /
  `EXPO_PUBLIC_COMPONENT_C_DEV_FIXTURE_FAMILY=C-GF-05`, difficulty 5, so the user can check card #5
  in a browser at difficulty 1 and 5 next — the standing, non-optional step before any further
  sub-phase, per the sequence this project has followed since A2.

**What was NOT verified.** Nothing in this repository can mount a React Native tree, so no test
here proves the stepper renders correctly on a real screen, that the marker's auto-scroll actually
keeps it visible at 18 jumps, or that the line never compresses — that is the standing browser-check
step, not yet done as of this entry. The backend suite is unaffected; no backend file changed.

---

## 2026-08-26 — fix: `line-traversal` no longer asks the child to re-type a visible number (10c correction)

**Found by the user looking at the running surface**, same standing practice that has caught every
real defect in this project so far. The marker on `UnitStepper`'s line already shows the landed
position (circled, at the current tick) — the surface's first draft then asked the child to
separately type that same number into a keypad field labelled "Where you landed", which was pure
redundancy: nothing new was being assessed by re-typing a value already on screen.

**Fix.** `line-traversal-surface.tsx` no longer renders a position keypad field. `final_position` is
now derived as `spec.startValue + jumps.length` and submitted alongside `jumps` when SUBMIT is
pressed; SUBMIT is gated on `jumps.length > 0` instead of a typed value being present.

**Re-checked against the authority boundary before making this change**, not assumed safe: this is
not the client computing an answer it shouldn't. `startValue` and `jumps.length` are never the
forbidden `addend_a + addend_b` sum — they read off exactly what the child's own jumps already
produced and made visible (the identical `originValue + forwardSteps` arithmetic `UnitStepper`
already uses for its own marker), not the task's unseen answer. `c-line-traversal-no-answer-
derivation.test.ts` gained a test pinning this distinction explicitly: the surface's own derivation
matches `spec.startValue + jumps.length` and is confirmed to never match the addend-sum guard.

**Also in this pass, both direct user requests, confirmed against the theme's real palette:**
- `UnitStepper`'s jump/back controls are now stacked vertically (jump forward above, back below,
  each with an up/down arrow) instead of side-by-side, filled with `colors.accentGreen` (the theme's
  own green, also C-GF-03's family accent — not a colour invented for this file), with white
  (`colors.surface1`) text matching `SubmitButton`'s own text colour exactly.

**Verification — measured.**

- `npx tsc --noEmit` — exit 0.
- The eight `c-line-traversal-*.test.ts` files in isolation: **81 tests, 81 passed, 0 failed** (up
  from 80 — one new test pinning the position-derivation distinction).
- Whole-suite `npm run test:contract`, immediately before this fix: **743 tests, 743 passed, 0
  failed.** Immediately after: **744 tests, 744 passed, 0 failed.** Reconciles: `743 + 1 = 744`.
- `npx expo export --platform ios` — re-run after these UI changes: succeeded, `dist/` removed after.
- Scope unchanged from the entry above — same file family, nothing outside it touched.

**What was NOT verified.** Same limitation as the entry above: nothing here can mount a React Native
tree, so the vertical stacking, the green fill, and the auto-derived position have not been
independently re-confirmed by a screenshot on this side — the user is checking directly in their own
browser via the dev fixture already pointed at `C-JB-02`/`C-GF-05`.

---

## 2026-08-26 — fix: `JumpAccumulator` no longer pushes SUBMIT off-screen at a high jump count (10c correction 2)

**Found by the user hand-testing at difficulty 1 after making many jumps** (a screenshot showed 32
jump chips wrapped across six rows, SUBMIT clipped near the bottom edge). The chip list had no
height bound, so every jump added grew the whole screen's layout — the exact "control grows past the
visible area" failure this project already hit once, in 10a's entry slots at difficulty 5.

**Fix.** `jump-accumulator.tsx`: the chip row is now inside a `ScrollView` capped at
`JUMP_LIST_MAX_HEIGHT` (two chip-rows tall, derived from the same `TOKEN_TOUCH_TARGET_SIZE`/
`TOKEN_SPACING` constants the chips themselves already used — not a new bare literal), so SUBMIT's
screen position no longer depends on jump count at all. The list auto-scrolls to keep the most
recent jump visible as it grows, mirroring `unit-stepper.tsx`'s own marker auto-scroll. Renders
`null` when there are no jumps yet (nothing to scroll to).

**Verification — measured.**

- `npx tsc --noEmit` — exit 0.
- The eight `c-line-traversal-*.test.ts` files in isolation: **81 tests, 81 passed, 0 failed**
  (unchanged count — a layout fix with no new assertions written against it).
- Whole-suite `npm run test:contract`: **744 tests, 744 passed, 0 failed** (unchanged).
- `npx expo export --platform ios` — re-run after this fix and after an unrelated full
  `node_modules` reinstall (see note below): succeeded, `dist/` removed after.
- User confirmed in their own browser, at difficulty 1: SUBMIT stays fixed as jumps accumulate.

**Unrelated note for the record:** between the previous entry and this one, `frontend/node_modules`
was found empty (0 packages) mid-session, cause undetermined — neither the user nor this session's
own actions were confirmed to have caused it. `npm install` (937 packages) restored it before this
fix's own verification ran; the restore is not part of this diff (dependencies only, no
`package.json`/lockfile change made here).

**What was NOT independently verified.** SUBMIT's own press behaviour (whether the dev fixture
completes and advances to a next task) has not been confirmed by the user as of this entry — asked,
not yet answered. Marker auto-scroll at very high jump counts (e.g. difficulty 5's real maximum of
18) has also not been specifically exercised; the difficulty-1 check that surfaced this fix only
reached 32 jumps because difficulty 1's real jump count is small (2) and the child pressed jump +1
many times past the mathematically required count, which the client does not gate.

---

## 2026-08-26 — 10c CLOSED: SUBMIT confirmed working, user satisfied with the full visual pass

The user confirmed SUBMIT works correctly under the dev fixture (advances as expected) and that
everything checked across difficulty 1 and 5 works properly. This closes 10c.

**Final state:** `line-traversal` registered for `C-JB-02`; `C-JB-01`/`C-JB-03`/`C-JB-04` untouched,
still `value-report` from 10b. `npx tsc --noEmit` clean, `npm run test:contract` 744/744/0,
`npx expo export --platform ios` verified. `.env.local` (gitignored) currently points at
`C-JB-02`/`C-GF-05`, difficulty 1 — left as-is, the user's call whether to reset it before the next
sub-phase.

**Full change list this sub-phase:** `line-traversal-logic.ts`, `line-traversal-surface.tsx`,
`primitives/unit-stepper.tsx`, `primitives/jump-accumulator.tsx` (all new), one import + one
`SURFACE_TABLE` entry in `archetype-surfaces.ts`, eight new test files. Three corrections landed
during the user's own hand-testing pass, each logged above in its own entry: the redundant typed
position field removed (auto-derived from the child's own jumps instead), the stepper controls
restyled (vertical, green, white text) per direct request, and the jump-chip list capped with
internal scroll so SUBMIT's position never depends on jump count.

**Still open, not blocking:** marker auto-scroll has not been specifically exercised at a large
*required* jump count (the frozen exemplar fixture's real maximums stay small, 1–3, across all five
difficulty levels) — only at an artificially large count from tapping past the answer. Not treated
as a gap in 10c's own scope, since the mechanism (`unit-stepper.tsx`'s `useEffect` on
`forwardSteps`) is identical to the one already exercised in that same test, just not separately
confirmed by eye at the larger end.

---

## 2026-08-26 — fix: C-TC-02 live-resolution leak closed; boolean toggle unified into one shared primitive

Two gaps found while catching up on 10b (`ead55a9`) and 10c (`681415c`), both closed here, neither
touching 10c's own content.

**C-TC-02 was silently resolving to a live, mounted surface.** `registry.ts`'s `ARCHETYPE_TABLE`
mapped `'C-TC-02': 'value-report'` from before 10b existed, and `value-report`'s resolver
(`resolveValueReportSpec`) is purely type-based -- it never branched on template id. 10b's own real
scope explicitly excluded C-TC-02 (its `directed` payload flag may need a signed answer at
difficulty 5, and `DigitKeypad` has no minus key -- `10b-10h-master-work-order.md` §2.1), but nothing
in the shipped code actually enforced that exclusion. Production refuses all real sessions today, so
there was no live-child risk -- but the gap was real and would have compounded silently under 10d/10e.

**A coincidence was doing the job by accident, and it was fragile.** C-TC-02's real payload happens
to contain a boolean `directed` key at every difficulty level (measured: `false` at L1-4, `true` at
L5), which the resolver's pre-existing "prompt_payload contains a non-numeric value" guard also
rejects -- so C-TC-02 was already failing closed today, for a reason that had nothing to do with the
actual policy question. If a future payload revision ever dropped `directed`, C-TC-02 would have
started resolving with no review at all.

**Two options considered, one chosen.** (A) an explicit `game_task_template_id === 'C-TC-02'` early
return inside `resolveValueReportSpec`; (B) removing the `registry.ts` mapping entirely, which fails
it closed via the existing "unresolvable template" path with zero template-id branching inside any
archetype's own logic. (B) keeps `value-report-logic.ts` completely free of template-id branching,
but `registry.ts`'s table is a **shape classification**, not an authorization list -- its own header
states this explicitly, and `archetype-surfaces.ts`'s `SURFACE_TABLE` is what separately owns
readiness. Removing a factually-true shape mapping to encode a policy refusal would blur that
separation, and would report the wrong fail-closed reason (`unresolvable-template`, when C-TC-02 is
in fact resolvable -- it is specifically withheld). It would also require changing the 30-entry
coverage test (`c-archetype-resolution.test.ts`) that hard-asserts the table's size against the
frozen registry, for a guard meant to be temporary. **Chose (A)**: smaller, easier to delete later --
and the same file that gains the line is exactly the file that will need to change again once the
`directed` question is answered, so nothing else has to change back.

**What changed:** `value-report-logic.ts:81-89` -- one explicit early return, heavily commented with
the reason and the removal condition, placed before every other (template-id-blind) check in the
function; the docstring's "fails closed for" list updated to name it first.

**The boolean toggle now exists in exactly one place.** Before this fix: `ordered-value-sequence-
surface.tsx`'s `GenericExtraField` had a single-switch version (flips between "YES"/"NO" text,
defaulting to showing "NO" before the child had touched it at all -- a real defect, not a style
difference: `SubmitButton`'s disabled check correctly required the key to be explicitly set, but the
toggle *looked* answered when it wasn't); `value-report-surface.tsx`'s `BooleanExtraField` had a
two-button version (neither button selected until `onChange` fires once -- the correct behaviour for
an unanswered field in an assessment). Extracted the two-button version into
`primitives/boolean-toggle.tsx` as `BooleanToggle`, decoupled from any single archetype's extra-field
type (matches `digit-keypad.tsx`'s own callback-only precedent). Both surfaces now import and render
it; neither reproduces it locally. `line-traversal-surface.tsx` (10c) was checked and declares no
boolean-control key today, so nothing there needed changing.

**Files:**
- new: `frontend/src/features/c-session/primitives/boolean-toggle.tsx`
- edit: `frontend/src/features/c-session/archetypes/value-report-logic.ts` (the C-TC-02 refusal)
- edit: `frontend/src/features/c-session/archetypes/value-report-surface.tsx` (toggle now imported,
  local `BooleanExtraField` and its now-unused styles removed)
- edit: `frontend/src/features/c-session/archetypes/ordered-value-sequence-surface.tsx` (toggle now
  imported; its `boolean-control` branch is dead code against real NP templates today, so this is a
  precautionary correctness fix, not a behaviour change any current template exercises)
- edit: `frontend/src/api/__tests__/c-value-report-fail-closed.test.ts` (three new tests: the id-check
  isolated from the payload coincidence; a covered-id positive control on the same shape; the real
  C-TC-02 exemplar shape at L1 and L5 both)

**A related, disclosed, but out-of-scope observation.** `line-traversal-surface.tsx` also reproduces
`SubmitButton` as its own local copy (a third instance, after `ordered-value-sequence-surface.tsx`'s
and `value-report-surface.tsx`'s). Not touched here -- this fix was scoped to the boolean toggle
specifically, and 10c's in-flight/committed content was explicitly out of scope. Worth a similar
extraction in a future small batch, following the exact precedent this entry just set.

**Verification -- supervisor's, measured.**

- `npx tsc --noEmit` -- exit 0.
- `npm run test:contract` -- **748 tests, 748 passed, 0 failed.** Baseline immediately before this
  fix, measured fresh: **744 / 744 / 0.** Reconciles: three new tests in
  `c-value-report-fail-closed.test.ts`, plus one more from `no-node-builtins-outside-tests-and-
  scripts.test.ts`'s own whole-tree source scan picking up the one new source file
  (`primitives/boolean-toggle.tsx`) automatically -- `744 + 3 + 1 = 748`.
- The C-TC-02 guard was proven to fire in both directions: with the exclusion line temporarily
  commented out, the isolated-payload test (the one that changes only the template id, keeping an
  otherwise fully valid numeric payload) failed exactly as expected, resolving to a real spec instead
  of `null`; restored from a backup taken before the edit, and the full 17-test file confirmed green
  again immediately after.
- `ordered-value-sequence`'s own test suite (`c-ordered-value-sequence-*.test.ts`, 67 tests) run in
  isolation after the toggle extraction: 67/67 pass, unchanged -- confirms the retrofit did not
  regress the archetype whose real templates never exercise this branch.
- `npx expo export --platform ios` -- succeeded, `entry-2dfd91d2e02951c6812405e2a3054120.hbc`,
  5.11 MB; `dist/` removed after.

**What was NOT verified.** Nothing here can mount a component tree, so the toggle's new visual
appearance in `value-report`'s own surface (already shipped in 10b) is unchanged and was not
re-observed; only `ordered-value-sequence`'s branch is new, and it renders no real template today, so
there is nothing to look at yet. The backend suite was not re-run -- no backend file changed.

## 2026-08-26 — feat: `option-select` archetype registered (10d, partial) — C-MCL-02/C-MCL-03 only;
three findings escalated, none resolved here

**Scope actually shipped.** The `exact-choice-control` (pipe-string) option source only:
`C-MCL-02` (`left|right|equal`) and `C-MCL-03` (`<|>|=`). The `integer-field` option source
(`C-MCL-01`, and `C-CC-03` -- registry.ts routes both to this same archetype id, pre-dating this
batch) is a documented STRUCTURAL REFUSAL in `option-select-logic.ts`, keyed on declared type alone,
naming no template id. `C-MCL-04` (`line-position`) stays entirely unregistered, per its own
STOP-AND-REPORT (below) -- no surface, no logic file, no test, `unit-stepper.tsx` untouched.

**Finding 1 -- C-MCL-01 / C-CC-03: the payload number IS the answer, and no quantity-as-objects
renderer exists to show it safely.** Owner ruling overturned the original plan's design (which would
have rendered `target_representation_value` / `set_size` as a read-only numeral token, exactly like
`value-report`'s own operand tokens). Re-verified directly against every real exemplar, all five
difficulty levels, both templates: `target_representation_value` (C-MCL-01) and `set_size` (C-CC-03)
are always present, unmodified, inside their own `numeral_options` array --
`{[3,5,9], target=9}` ... `{[21,35,46,47,66], target=66}` for C-MCL-01;
`{[1,3], set_size=3}` ... `{[16,17,18,19], set_size=16}` for C-CC-03. Rendering that number as a
token reduces "choose the number that matches the amount shown" / "count the objects" to "find the
matching digit" -- the same class of defect `line-traversal-logic.ts`'s header exists to prevent.
It cannot be omitted either: every `prompt_text` on this path is deictic and `interactive_assets` is
`{}` at every level, so the quantity can only be shown honestly as a QUANTITY OF OBJECTS, and no such
primitive exists in this codebase. **Not decided here:** what that primitive looks like, whether it
overlaps with 10e's `object-pool` (which needs the same thing for `C-CC-01`/`C-CC-02`), or when it
gets built. The refusal self-deletes the day it is approved and built -- no template-id list to
maintain or grow in the meantime.

**Finding 2 -- `C-MCL-04` (`line-position`) interaction-cost confound, independently re-derived:**

| `difficulty_level` | `interval_max` | `target_position` | taps (origin 0, `UnitStepper`'s +1 only) |
|---|---|---|---|
| 1 | 10 | 2 | 2 |
| 2 | 20 | 7 | 7 |
| 3 | 50 | 26 | 26 |
| 4 | 100 | 36 | 36 |
| 5 | 200 | 34 | 34 |

17x difficulty-5-vs-1 effort. Ruling 6.3's own justification ("mathematical demand grows with step
count") holds for `line-traversal` (each unit jump IS the counting-on act scored) but not for
`line-position` (locating 34 on a 0-200 line is a magnitude-estimation act made ONCE; the 34 taps
that follow are pure transit cost, assessing nothing). Options seen, none chosen: coarse+fine
stepping (±10/±1, ~7 taps at L5, plausibly still "discrete" under 6.3 but its own confound-freeness
is unverified); direct placement (reopens the already-closed size confound); an unexplored
log/paginated control. The layout-bound reasoning originally drafted for a `numeral_options` ceiling
(10, i.e. 2x the observed max of 5) is recorded here for the next builder, though moot while the
`integer-field` path stays refused (Finding 1). **Not decided here:** which fix, or whether this is
a ship-blocking population-level concern. `line-position` stays unregistered.

**Finding 3 -- `C-MCL-02` renders as numeral comparison, same act as `C-MCL-03`, not flagged
before.** `left_count`/`right_count` render as plain numeral tokens under this design -- no answer
leak (the child still has to compare), but "Choose which side has more, or say if they are equal"
and "Compare the two numbers" (`C-MCL-03`) now resolve to the identical child-facing act: comparing
two numerals. Two templates collapsing to one act suggests `C-MCL-02` was meant as *non-symbolic*
quantity comparison (a picture of dots per side, not digits) -- symbolic vs. non-symbolic magnitude
comparison are distinct constructs in the literature this tool is built against. Built as numerals
for now, per explicit owner ruling to ship it that way and flag the question rather than resolve it.
**Not decided here:** whether `C-MCL-02` needs a non-symbolic rendering, and if so whether it shares
the same still-nonexistent quantity-as-objects primitive Finding 1 names.

**`trial_type` note (C-CC-04).** `C-CC-04`'s pipe-string path (`judgment: "same|changed"`) is held
shut entirely by the generic "every non-option `prompt_payload` value must be a finite number, or
fail closed" guard -- `trial_type` (`rearrange_only` / `add_remove`) is itself answer-bearing for the
same/changed judgment, so rendering it would leak that answer too. This guard must never be relaxed
to skip or tolerate a non-numeric value on the strength of `trial_type` being the only one seen in
real data; doing so would silently unlock `C-CC-04` with no review. Proven load-bearing by breaking
it directly (see Verification).

**Files:**
- new: `frontend/src/features/c-session/archetypes/option-select-logic.ts`
- new: `frontend/src/features/c-session/archetypes/option-select-surface.tsx`
- new: `frontend/src/features/c-session/primitives/option-choice-row.tsx` (generalizes
  `GenericExtraField`'s `exact-choice-control` branch from an extra field into the primary scene;
  geometry from `TOKEN_TOUCH_TARGET_SIZE`/`TOKEN_SPACING`, motor-constants.ts, never a bare literal)
- edit: `frontend/src/features/c-session/archetype-surfaces.ts` (one import, one `SURFACE_TABLE`
  entry -- this single entry also lights up `C-CC-03`/`C-CC-04` at the plan level, since
  `resolveArchetypeSurface` keys on archetype id, not template id; see Finding 1/the `trial_type`
  note for why neither renders anything unsafe as a result)
- new tests, flat in `frontend/src/api/__tests__/`: `c-option-select-logic.test.ts`,
  `c-option-select-fail-closed.test.ts`, `c-option-select-key-set-proof.test.ts`,
  `c-option-select-prompt-text.test.ts`, `c-option-select-no-representation-mode.test.ts`,
  `c-option-select-carries-interactive-assets.test.ts`, `c-option-select-motor-constancy.test.ts`,
  `c-mcl-family-surface-registration.test.ts` (source-scan against `archetype-surfaces.ts` plus
  `resolveArchetype` cross-checks -- does NOT import `archetype-surfaces.ts` as a value; that module
  transitively imports every real RN surface, and `node --import tsx --test` cannot transform
  `react-native/index.js`'s own Flow syntax, the same class of defect `ffe543d` fixed for the theme
  barrel, just with no RN-free leaf available here)

**Verification -- measured.**

- `npx tsc --noEmit` -- exit 0.
- `npm run test:contract` -- **832 tests, 832 passed, 0 failed.** Baseline immediately before this
  batch, measured fresh: **748 / 748 / 0.** Reconciles: 84 new tests added across the 8 new test
  files above; 0 removed; no existing test file edited.
- `line-traversal`'s and `value-report`'s own test files: untouched, unchanged in count (no file
  belonging to either was opened for edit this batch).
- Every guard in `option-select-logic.ts` proven to fire by disabling it in place, confirming the
  targeted negative control(s) went red, then restoring and confirming the full two-file suite (37
  tests) green again: `prompt_text` empty/absent; `prompt_payload` null or non-object; empty
  `prompt_payload`; a non-numeric `prompt_payload` value (this is the one holding `C-CC-04` shut --
  disabling it turned exactly the `C-CC-04` test and three synthetic ones red, nothing else); the
  `integer-field` structural refusal (disabling it, by letting that branch succeed instead of
  refusing, turned the `C-MCL-01`/`C-CC-03` refusal tests red); a duplicate `exact-choice-control`
  key; a non-boolean extra field; `blanks` not null. One guard (`valid_action_space` declares no
  key) was found to be redundant-but-harmless: disabling it alone did not turn any test red, because
  the later `scoreKey === null` check independently catches the same empty-payload-space case --
  behavior is correct either way, but that particular line is not independently load-bearing, unlike
  every other guard listed above. Recorded rather than silently left as an unverified claim.
- `npx expo export --platform ios` -- succeeded, `entry-2ea928b0e6abe626da010aa3c970b709.hbc`,
  5.12 MB; `dist/` removed after.

**What was NOT verified.** Nothing here can mount a component tree -- `OptionChoiceRow`'s and
`option-select-surface.tsx`'s actual on-screen appearance and touch behaviour were never observed,
only their source and the pure resolver's decisions. `C-MCL-01`/`C-CC-03` were confirmed to reach
the archetype table (`resolveArchetype` still returns `'option-select'` for both) and to refuse at
the `resolveOptionSelectSpec` layer, but the actual `FailClosedFrame` render path for either was not
observed rendering, for the same reason. The backend suite was not re-run -- no backend file changed
except this entry.

## 2026-08-26 — feat: `option-select`'s numeral-options path unblocked (10e-0) — C-MCL-01, C-CC-03
now ship; two findings escalated, both unresolved

**Scope shipped.** The `integer-field` refusal in `option-select-logic.ts` (10d) is replaced by
real resolution. Both templates on this path resolve and mount at every difficulty level: `C-MCL-01`
(quantity range 2-66) and `C-CC-03` (quantity range 3-16). A magnitude-only structural bound cannot
cleanly ship one and refuse the other -- see Finding 1 -- so both ship together, per explicit ruling.
A new shared primitive, `object-quantity-display.tsx`, renders the quantity as a wrapped block of
uniform objects, never as a numeral.

**A correction to the 10e-0 work order itself, caught before any code was written.** The prompt
proposed "ship C-CC-03 only, refuse C-MCL-01 on a bound" as a live possibility. It isn't: `C-MCL-01`'s
quantity range is {2, 9, 13, 32, 66} and `C-CC-03`'s is {3, 5, 8, 12, 16} -- `C-MCL-01`'s own low
levels (2, 9, 13) sit *inside* `C-CC-03`'s full range. No single magnitude threshold separates "every
C-MCL-01 value" from "every C-CC-03 value" without either (a) partially breaking `C-MCL-01` --
resolving at low difficulty, fail-closed at high difficulty, a new defect in its own right (a child
hits a wall specifically at a game's harder levels) -- or (b) also excluding some of `C-CC-03`'s own
legitimate values. The one other candidate (a `C-TC-02`-style named template-id exclusion) was
foreclosed by this same batch's own no-template-id-branching requirement. Ruling: ship both, bound at
100 as pure corruption-safety, and stop proposing a value-based split for these two templates --
record it here so nobody re-derives this from scratch. Third such correction in this sub-phase
sequence (after the `line-position` tap-count finding and the `C-CC-03`/`C-CC-04` spillover finding).

**Finding 1 (escalated, unresolved) -- can a flat, ungrouped, wrapped display of a large quantity
honestly represent it at all, independent of the grouping question?** Two distinct concerns, not
one:
- **Whole-set apprehension.** If `C-MCL-01`'s "amount shown" is meant to be estimated at a glance
  (plausible: at L5 the correct answer, 66, sits far from every distractor -- 21/35/46/47 -- reading
  like coarse discrimination), a display requiring the child to scroll or scan across many wrapped
  rows to take in the whole quantity may make that single-glance act impossible, not merely costlier.
- **Exact counting.** If instead exact counting is intended (plausible for `C-CC-03`: "Count the
  objects. Then choose the number that matches."), counting dozens of identical, unlabeled, ungrouped
  objects accurately is a demanding ask for the target population independent of layout.
Wrapping (ruling 2, this batch) is the best available layout without resolving either question --
direct precedent, `84874ce`'s fix of 10a's off-screen entry slots by wrapping rather than scrolling.
It is measurably better than a single scrolling row (the worst case for both concerns above) but does
not resolve either. **Not decided here:** whether either concern makes the current design invalid for
`C-MCL-01` at its higher difficulty levels, and whether grouping (Finding 2) is the fix or a
different, deeper redesign is.

**Finding 2 (escalated, unresolved, carried from 10d, restated with corrected framing) -- should the
quantity be grouped (base-ten, subitizing blocks) rather than shown flat?** A scientific
representation choice, not a builder's or a layout question, per this project's repeated ruling on
exactly this class of decision (`C-MCL-04`'s tap-count confound, `C-MCL-02`'s symbolic-comparison
question). The wrap-not-scroll layout (ruling 2) was deliberately implemented to never fall out at a
fixed per-row count (10 = a ten-frame; 5 = subitizing groups) for exactly this reason -- row length
is purely a function of container width and fixed object size, asserted by a dedicated test
(`c-object-quantity-display.test.ts`) that fails if a future edit hardcodes one. **Not decided
here:** whether grouping is needed at all, and if so, which.

**The 100-quantity bound is corruption-safety only**, deliberately set (100) above every real
quantity either template produces (66, `C-MCL-01`'s own hardest level) so it never fires against real
data at any level of either template -- not a considered judgement about how many objects a child can
count, and not chosen to separate the two templates (see the correction above). The `numeral_options`
array-length bound (10) is 10d's own already-reasoned, previously-unapplied value, now live.

**Files:**
- new: `frontend/src/features/c-session/primitives/object-quantity-display.tsx` -- read-only,
  wraps (never scrolls), geometry from new `motor-constants.ts` constants, accessibility label
  carries no digit and individual objects are hidden from the accessibility tree entirely (the
  screen-reader leak vector a plain per-object accessible list would have opened).
- edit: `frontend/src/features/c-session/motor-constants.ts` -- new `OBJECT_TOKEN_SIZE` (28) /
  `OBJECT_TOKEN_SPACING` (6), half of `TOKEN_TOUCH_TARGET_SIZE`/`TOKEN_SPACING`, justified as a
  passive-display exemption from SPEC section 10's interactive-touch-target floor (same reasoning
  `value-report-surface.tsx`'s `PAYLOAD_TOKEN_SIZE` already established).
- edit: `frontend/src/features/c-session/archetypes/option-select-logic.ts` -- restructured to
  classify `valid_action_space` before validating `prompt_payload` (the two option sources need
  genuinely different payload shapes); the `integer-field` refusal replaced by real resolution; the
  quantity key resolved structurally ("the one `prompt_payload` key that is not `numeral_options`"),
  never a two-name table. Return type is now a `'choice' | 'numeral-options'` discriminated union --
  the answer-leak guard is a fact about the TYPE (only `'choice'` has a `payloadValues` field at
  all), not merely a runtime check.
- edit: `frontend/src/features/c-session/archetypes/option-select-surface.tsx` -- renders
  `ObjectQuantityDisplay` + `OptionChoiceRow` bound to `numeralOptions` for the new scene.
- new tests: `c-object-quantity-display.test.ts`, `c-option-select-numeral-options-resolution.test.ts`,
  `c-option-select-numeral-options-fail-closed.test.ts`, `c-option-select-numeral-options-coverage.test.ts`.
- edit (named exception): `c-option-select-logic.test.ts` -- 3 tests inverted from asserting refusal
  to asserting resolution (`"C-MCL-01 refuses..."` -> `"C-MCL-01 resolves..."`, `"C-CC-03 refuses..."`
  -> `"C-CC-03 resolves..."`, `"the refusal is keyed on declared type alone..."` -> `"resolution is
  keyed on declared type alone..."`). Every other test in this file untouched.
- edit (named exception): `c-option-select-fail-closed.test.ts` -- 4 tests replaced (2 assertions
  flip null->resolves; 1 already asserted resolution, comment corrected only; 1 still asserts null,
  now for the real reason -- wrong payload key count -- not the old refusal). Every pipe-string-path
  negative control in this file untouched.
- edit (named exception, comment only): `c-mcl-family-surface-registration.test.ts` -- one stale
  claim corrected ("option-select-logic.ts is what refuses it at render time" -> now resolves it for
  real); no assertion changed.

**Verification -- measured.**

- `npx tsc --noEmit` -- exit 0.
- `npm run test:contract` -- **894 tests, 894 passed, 0 failed.** Baseline immediately before this
  batch: **832 / 832 / 0.** Reconciles: 61 new tests across the 4 new files (20 + 18 + 11 + 12); + 1
  automatic pickup from `no-node-builtins-outside-tests-and-scripts.test.ts`'s own whole-tree scan
  finding the one new source file (`object-quantity-display.tsx`) -- the same mechanism the
  `boolean-toggle.tsx` batch's own entry already documented; 0 removed (every named-exception edit
  replaced tests 1:1, in place).
- Per-test-name check (not just the aggregate count), per ruling: the three named-exception files
  were run standalone before and after the full change (44/44 both times) and every test name outside
  the explicitly-listed changed ones is byte-identical between runs; the restructuring (classify
  `valid_action_space` before `prompt_payload`) provably cannot change any single-violation negative
  control's outcome, since each isolates exactly one guard against an otherwise-valid baseline and
  both orderings still reach that guard.
- Every new guard in the numeral-options path proven by disabling it in place, confirming the
  targeted negative control(s) went red, then restoring and confirming green again: quantity
  type/finite/integer/negative/bound (one batch, 6 controls incl. the boundary test); `numeral_options`
  array/length/element (one batch, 7 controls incl. the boundary test); the payload-key-count guard
  (1 control -- "more than two payload keys"); the shared `prompt_text`/`blanks` guards, spot-checked
  across both scenes at once (4 controls). **Two guards found redundant-but-harmless**, disclosed
  rather than silently claimed independently necessary: the `numeral_options`-key-presence
  `hasOwnProperty` check (subsumed by the immediately-following `Array.isArray` check --
  `promptPayload[key]` on a missing key is `undefined`, which is not an array either way) and,
  within the payload-key-count guard, its own coverage of "the quantity key is missing entirely" (that
  specific case is independently caught by the downstream quantity-type check; only "more than two
  payload keys" depends on this line, since a `.find()` over 3 keys would otherwise silently pick the
  first non-`numeral_options` key and drop the third).
- The accessibility answer-leak guard proven in both halves: the label's own digit-free text
  (broke it by inserting "7", confirmed red, restored, confirmed green) and the per-object
  accessibility-hiding attributes (removed them, confirmed red, restored, confirmed green).
- `C-CC-04` regression: its own pre-existing test (`c-option-select-logic.test.ts`) still passes
  unmodified after the restructuring -- its `trial_type` guard is untouched code, confirmed by the
  full suite run, not a new assertion.
- `C-MCL-04`/`line-position` regression: `resolveArchetype('C-MCL-04', ...)` still returns
  `'line-position'`; `SURFACE_TABLE` still has no entry for it (new dedicated assertions in
  `c-option-select-numeral-options-coverage.test.ts`, alongside the pre-existing plan-level proof in
  `c-mcl-family-surface-registration.test.ts`).
- `npx expo export --platform ios` -- succeeded, `entry-15ff18ff9ea6c6cfa692eb7cf45266c4.hbc`,
  5.12 MB; `dist/` removed after.

**What was NOT verified.** Nothing here can mount a component tree -- `ObjectQuantityDisplay`'s and
the new scene's actual on-screen appearance (including whether 66 wrapped objects fit legibly on a
real screen without the surrounding chrome overflowing) was never observed, only source and the pure
resolver's decisions. The screen container (`option-select-surface.tsx`'s own `styles.container`,
reused unmodified) has no `ScrollView` wrapper at the screen level (checked: `c-session-screen.tsx`'s
`taskContentMiddle` is a bare `flex: 1`) -- if a wrapped 66-object block plus the existing chrome
exceeds the visible screen height, nothing makes the rest of the screen (including SUBMIT) reachable.
This was not fixed, since the surrounding screen chrome is explicitly reuse-unmodified this batch;
it is exactly the kind of thing ruling 1 anticipated becoming visible only by looking at the result
in a browser, and is flagged here so it is looked for, not discovered cold. The backend suite was not
re-run -- no backend file changed except this entry.

## 2026-08-26 — feat: `object-set-action` archetype registered (10e), C-CC-01 and C-CC-02

**What was built.** `object-set-action`, the archetype for C-GF-01 Count and Collect's last two
templates. Card #1 flips from *Partly ready* to *Ready to play* on its own (`readinessOf` computes
family readiness from `SURFACE_TABLE` at call time) -- no hub file touched. Baseline measured before
this batch: HEAD `d78de79`, `npx tsc --noEmit` exit 0, `npm run test:contract` **999 / 999 / 0**
(after the uncommitted 10e-0 numeral-options batch landed as its own commit).

**The composite proof this sub-phase owed (master work order §3/§4).** C-CC-01 declares BOTH an
`id-set-collection` and a companion `integer-field`; C-CC-02 declares ONLY the `id-set-collection`.
One resolver (`resolveObjectSetActionSpec`) covers both, classifying purely by which declared TYPES
are present -- never by template id or key name. `totalKey: string | null` is the type-level fact
the surface switches on (`SelectAndCountScene` for C-CC-01, `PlaceIntoBoxScene` for C-CC-02), proven
by a dedicated structural test (`c-object-set-action-no-template-branch.test.ts`) that the new files
never contain either template id or any of the four real payload/action key names.

**Structural, not by-name, id-set resolution.** C-CC-01 carries ids across TWO payload keys
(`valid_object_ids`, `distractor_object_ids`); C-CC-02 in ONE (`available_object_ids`). Every
`string[]`-valued `prompt_payload` key is concatenated, in wire key order, into one flat `objectIds`
list -- so C-CC-01's valid and distractor ids render as ONE undifferentiated pool, with no
client-side distinction beyond rendering them (matching the sequence doc's own "Does NOT deliver").

**Two decisions ruled by the owner this session, both written into `object-set-action-logic.ts`'s
and `object-set-action-surface.tsx`'s own headers:**
- `submitted_total` (C-CC-01) is NEVER auto-derived from `selectedIds.size`. Counting the selection
  IS the assessed skill, and unlike `line-traversal`'s derived `final_position` (already visible on
  the number line), nothing on this screen already shows the count. Also never gated by a minimum
  selection -- an intermediate draft disabled "ADD ANSWER" until at least one object was selected,
  and the owner corrected that: a child who believes NONE of the objects should count must be able
  to advance and type `0`; `submitted_total` is validated server-side, not pre-judged client-side.
- `target_n` (C-CC-02) renders as a bare numeral token, no label. It is the GIVEN size of the set to
  build, not the answer, so nothing needs disambiguating the way `value-report`'s multi-operand
  labels do.

**Escalated finding, accepted with an explicit trade-off (2026-08-26, owner decision).** After
testing at difficulty 5 (~22-object pool for C-CC-01), the owner asked for a staged reveal (pool,
then a separate keypad step) so a large pool didn't have to share the screen with the keypad. A
follow-up request then asked for this to apply ONLY at large pool sizes, not small ones -- meaning
the SCREEN FLOW ITSELF now varies with content size (`STAGED_FLOW_MIN_POOL_SIZE = 8`, keyed on
`spec.objectIds.length`, never on `difficulty_level`, which this file never reads at all). This is a
departure from SPEC section 10's motor-constancy doctrine as this codebase has otherwise applied it
everywhere else (every other archetype keeps interaction FLOW fixed across every difficulty level,
letting only magnitude vary) -- flagged explicitly rather than left silent, since it was raised as a
concern and the owner reaffirmed the request anyway. The threshold (8) is derived from C-CC-01's own
five real exemplar pool sizes (3, 6, 10, 15, 22 across L1-L5): it sits in the gap between L2's 6 and
L3's 10, so only L1/L2 render single-screen; L3-L5 stage (pool -> ADD ANSWER -> keypad/VIEW/SUBMIT,
fully reversible either direction, `selectedIds`/`totalDigits` never cleared on a phase change).

**C-CC-02's own UI iteration, also owner-driven from browser testing at difficulty 5 (~20 objects):**
the box (placed objects) renders every object at once (`ObjectPool`'s new `scrollable={false}` mode,
added this batch alongside the existing bounded-scroll default) rather than scrolling internally, so
the child can see exactly how many are in the box. SUBMIT is pinned to a fixed position (`position:
absolute`, anchored to the scene's own bottom edge) that never moves regardless of box size -- two
earlier drafts got this wrong (first: SUBMIT still in normal flow after the box, so it moved as the
box grew; second: the remaining-available pool hidden entirely behind SUBMIT via an opaque overlay,
which the owner rejected -- "it should only disappear once it runs out of room, not always"). The
shipped shape: the available pool renders in the white space between the box and SUBMIT inside a
`flex: 1, overflow: 'hidden'` viewport that exactly fills the leftover vertical space above SUBMIT's
own reserved bottom band, so a pool that fits shows in full and a pool that doesn't clips at the
boundary, appearing to emerge from underneath as objects are added or removed -- SUBMIT itself never
participates in that clipping and never shifts. A related bug found along the way: the disabled
SUBMIT state's standard opacity-0.5 dim let whatever sat behind/near it show through; C-CC-02's
SUBMIT now uses an opaque muted-grey disabled style (`submitButtonDisabledOpaque`) instead, via a new
optional `disabledStyle` prop on the shared `SubmitButton`.

**Shared-chrome change, also owner-driven (`c-session-screen.tsx`, all archetypes affected).** The
task screen's own background is now a fixed neutral (`#F4F4F6`, `TASK_SCREEN_BACKGROUND`) rather than
the family accent; the accent moved to the card's own border instead (`borderColor` applied inline
from `accentForGameFamily`). The card's border width, shadow, and elevation now match
`learner-home-screen.tsx`'s own hero card exactly (`borderWidth: 4`, `elevation: 5`, `shadowOffset:
{0,4}`, `shadowOpacity: 0.18`, `shadowRadius: 7` -- values copied, not imported, since that style is
private to its own file). This changes every archetype's screen, not just this batch's own two
templates -- flagged here since it is outside 10e's own file list but was a direct, explicit request.

**Other object-pool.tsx additions this batch:** a `scrollable` prop (default `true`, unchanged
bounded-scroll behaviour for callers that don't opt out) and an `accent` prop -- every object's fill
is a low-alpha tint of the family accent (`hexToRgba`, computed locally, no accent-specific "soft"
palette existed to reuse) with a solid-accent fill once selected, and the border is always the solid
accent. A layout bug found early (objects rendering as flat-bottomed half-circles) traced to a React
Native Web flex-shrink pitfall: a `ScrollView` with only `maxHeight` set, nested inside a
`justifyContent: 'space-between'` column, can be compressed below its own content's natural height:
fixed with `flexShrink: 0` + `minHeight` on the scroll bound.

**Files:**
- new: `object-set-action-logic.ts` (pure resolver), `object-set-action-surface.tsx` (two scenes),
  `primitives/object-pool.tsx` (shared pool primitive, built once per master work order §5A).
- edit: `payload-value-labels.ts` (`target_n: 'How many'` entry, added then made moot when the label
  was removed per a later request -- the table entry stays, harmless, for any future reuse).
- edit: `archetype-surfaces.ts` (one import, one `SURFACE_TABLE` entry).
- edit: `c-session-screen.tsx` (shared chrome, described above).
- new tests, flat in `src/api/__tests__/`: `c-object-set-action-logic.test.ts`,
  `c-object-set-action-key-set-proof.test.ts`, `c-object-set-action-fail-closed.test.ts`,
  `c-object-set-action-no-template-branch.test.ts`, `c-object-set-action-no-client-validation.test.ts`,
  `c-object-set-action-motor-constancy.test.ts`, `c-object-set-action-no-representation-mode.test.ts`,
  `c-object-set-action-carries-interactive-assets.test.ts`, `c-object-pool-layout.test.ts`.

**Verification -- measured.**
- `npx tsc --noEmit` -- exit 0, throughout every UI iteration in this batch.
- `npm run test:contract` -- **999 tests, 999 passed, 0 failed**, final state, re-confirmed after
  every source change in this batch (re-run well over a dozen times across the session).
- Every fail-closed guard in `object-set-action-logic.ts` proven by disabling it in place, confirming
  the targeted negative control went red, restoring, confirming green again: the duplicate-id guard,
  the `MAX_POOL_OBJECTS` bound, the "more than one non-array payload key" guard, and the
  `MAX_TARGET_VALUE` bound -- each isolated against the same otherwise-valid baseline.
- `npx expo export --platform ios` -- succeeded twice (once mid-batch, once as the final check after
  all UI corrections); `dist/` removed both times.
- **Every screen looked at in a browser, at every difficulty level, by the owner directly**: C-CC-01
  at L1-L5 (L1/L2 single-screen; L3-L5 staged flow, VIEW/ADD ANSWER round-trip, pool wrap and accent
  fill, entrance animation) and C-CC-02 at L1-L5 (target token, dashed accent-bordered box, fixed
  SUBMIT, clipped available-pool viewport at L5's larger pool) -- all confirmed correct by the owner
  after the iterations described above. Card #1 confirmed reading **Ready to play** in the hub.

**What was NOT independently re-verified.** The backend suite was not re-run -- no backend file
changed. `ObjectPool`'s `accent`-tint contrast and the shared chrome's new border/shadow were judged
visually by the owner, not measured against any accessibility contrast standard.

## 2026-08-26 — feat: `line-position` archetype registered, completing 10d (C-MCL-04)

**What was built.** `line-position`, the archetype for C-MCL-04 alone -- the fourth and last
template of C-GF-03 Match, Compare, Locate. Card #3 flips from *Partly ready* to *Ready to play* on
its own (`readinessOf` computes family readiness from `SURFACE_TABLE` at call time) -- no hub file
touched. This closes out 10d, left partial since `de91132` (C-MCL-02/C-MCL-03 shipped) and 10e-0
(C-MCL-01 unblocked): all four MCL templates are now registered.

**Why this was still open.** The master work order's own §2.2 blocker was never actually about the
STEPPING MECHANISM -- that was already ruled ("discrete integer stepping, constant per-step touch
target, the line scrolls or paginates, never compresses") and `unit-stepper.tsx` was already built
generic for this reuse in 10c. What was genuinely unresolved was the INTERACTION-COST CONFOUND `de91132`'s
own Finding 2 measured and left open: unit-only stepping from 0 costs 2 taps at L1 and 34 at L5 (a
17x spread), and unlike `line-traversal` (where each unit jump IS the counting-on act being scored),
every tap past the first here is pure transit cost, assessing nothing -- exactly the SPEC section 10
confound that killed 10a's original stepper design. Finding 2 named candidate fixes without choosing
one; the owner this session picked coarse+fine stepping over unit-only (accepting the residual tap
cost) or escalating without shipping.

**The fix: coarse+fine discrete stepping, built into `unit-stepper.tsx` itself, not a new primitive.**
A new optional `coarseStep` prop adds a second `+N`/`-N` button pair alongside the existing `+1`/`-1`
pair -- `line-position` passes a fixed `LINE_POSITION_COARSE_STEP = 10` (never derived from
`interval_max` or `difficulty_level`); `line-traversal` passes nothing, so its own two-button shape
is unchanged. At L5 (target 34) this collapses 34 taps to 7 (3 coarse + 4 fine), measured and
asserted by a dedicated test. Two other additions to the shared primitive, both additive and
`line-traversal`-inert: `maxForwardSteps` (defaults to the old corruption-only
`MAX_LINE_FORWARD_STEPS`; `line-position` passes `interval_max` instead, legitimate here because
that value is the task's own stated range, not an answer to protect) and `targetForwardOffset`
(marks one tick with a distinct visual, omitted by `line-traversal`, which has no such given position
to show).

**`target_position` is the GIVEN, not the answer -- and still never rendered as a bare numeral.**
The prompt ("Move the marker to the target spot on the line") is deictic and needs a visible target;
unlike `line-traversal`'s sum, there is no way to complete the task without showing where the target
is. It renders as a marked tick on the line itself (a solid green circle, after two rounds of visual
correction -- see below), never as a printed digit next to the prompt. A dedicated leak-guard test
(`c-line-position-no-target-leak.test.ts`) proves `spec.targetPosition` is passed to exactly one
place in the surface (`UnitStepper`'s `targetForwardOffset` prop) and never interpolated into any
`AppText` node.

**A real discoverability gap, found by the owner testing at L5, fixed with a bucketed range hint.**
`UnitStepper`'s own auto-scroll only follows the MARKER (which starts at 0); with a target up to 200
units away and entirely off-screen, nothing told the child which direction or how far to go. Fixed
with `targetRangeStart`/`targetRangeEnd` -- a `TARGET_HINT_BUCKET_SIZE`-wide (5) window containing
`target_position`, computed structurally and rendered as "Target is between 30 and 35" above the
line. This narrows the search space without pinpointing the exact value, the same trade-off a paper
number line's own printed gridlines make. Bucket boundaries fall on multiples of 5 ("0-5, 5-10,
10-15"), corrected once after an initial off-by-one draft ("30-34" instead of "30-35").

**UI iteration, owner-driven from browser testing across all 5 difficulty levels:**
- The target tick went through two visual drafts before landing: a 🏁 emoji (did not render
  consistently, showed as a placeholder box) → a hollow green ring → a solid green filled circle.
- The current-position marker and its own tick ring went through a similar correction: solid red
  dot / red ring (original) → faded green dot (rejected, hard to read) → back to a solid red dot,
  but with the ring around it changed to green (accepted) → both reverted to red after the target's
  dot went solid green, since a red-ringed red dot next to a green-ringed green dot reads more
  clearly than a red dot inside a green ring. Final state: current position is entirely red (ring +
  dot), target is entirely green (ring + solid dot) -- two internally-consistent colour pairs, never
  mixed.
- A "The marker is at N" live caption was added, then removed at the owner's request in the same
  session -- the marker's own tick-label numeral already shows this.

**Shared-primitive consequence, flagged rather than left silent.** `unit-stepper.tsx` is shared with
`line-traversal` (10c, shipped and previously browser-verified). Every change above to `tickMarked`'s
ring colour and the `marker` dot's fill also applies to `line-traversal`'s own rendering, since
neither archetype-specific colour was gated behind a prop -- `line-traversal`'s marker now renders
with the same red ring + red dot combination line-position settled on, which happens to match what it
already had (red ring, red dot) after this round's reversions, so no visual regression resulted, but
this was not independently re-confirmed in the browser for `line-traversal` specifically this
session -- only reasoned about from the diff.

**Files:**
- new: `line-position-logic.ts` (pure resolver), `line-position-surface.tsx`.
- edit: `unit-stepper.tsx` (`coarseStep`, `maxForwardSteps`, `targetForwardOffset` props; `marker`/
  `tickMarked`/`tickTarget`/`targetDot` style changes, described above).
- edit: `archetype-surfaces.ts` (one import, one `SURFACE_TABLE` entry).
- edit (named exception): `c-mcl-family-surface-registration.test.ts` -- 3 tests inverted from
  asserting `line-position` has NO surface entry to asserting it now does (the fact this file
  documented changed); every other test in the file untouched.
- new tests, flat in `src/api/__tests__/`: `c-line-position-logic.test.ts`,
  `c-line-position-fail-closed.test.ts`, `c-line-position-key-set-proof.test.ts`,
  `c-line-position-prompt-text.test.ts`, `c-line-position-carries-interactive-assets.test.ts`,
  `c-line-position-no-representation-mode.test.ts`, `c-line-position-motor-constancy.test.ts`,
  `c-line-position-no-target-leak.test.ts`.

**Verification -- measured.**
- `npx tsc --noEmit` -- exit 0, throughout every iteration in this batch.
- `npm run test:contract` -- **1087 tests, 1087 passed, 0 failed**, final state. Baseline
  immediately before this batch: 999 / 999 / 0 (post-10e). Re-run after every source change in this
  batch.
- Both `MAX_INTERVAL_MAX` and the `target_position` range bound (`[0, intervalMax]`) proven by
  disabling each in place, confirming the targeted negative controls went red, restoring, confirming
  green again.
- `npx expo export --platform ios` -- succeeded; `dist/` removed after.
- **Every difficulty level looked at in a browser by the owner directly**: C-MCL-04 at L1-L5
  (interval_max 10/20/50/100/200, target_position 2/7/26/36/34), through every visual correction
  described above, all confirmed correct at the final state. Card #3 confirmed reading **Ready to
  play** in the hub.

**What was NOT independently re-verified.** `line-traversal`'s own rendering, after the shared
`unit-stepper.tsx` colour changes -- see the "Shared-primitive consequence" paragraph above. The
backend suite was not re-run -- no backend file changed.

---

## 10f -- `named-integer-fields` archetype registered, completing C-GF-04 Build and Trade (C-BT-01..04)

**What shipped.** A sixth archetype, `named-integer-fields`, registered in `archetype-surfaces.ts`,
covering all four C-BT-* templates: C-BT-01 (`target_number` -> `tens`/`ones`), C-BT-02
(`target_number` -> `hundreds`/`tens`/`ones`), C-BT-03 and C-BT-04 (`pre_tens`/`pre_ones` ->
`post_tens`/`post_ones`, the two "trade" templates). Card **#4 Build and Trade** now reads **Ready to
play** in the hub, computed by `readinessOf` from the same `SURFACE_TABLE` the task loop reads --
no hub file touched. New files: `archetypes/named-integer-fields-logic.ts` (pure resolver),
`archetypes/named-integer-fields-surface.tsx`, `primitives/named-field-row.tsx` (the labelled
multi-field entry control). Modified: `archetype-surfaces.ts` (one import + one `SURFACE_TABLE`
entry), `payload-value-labels.ts` (three payload-key label entries: `target_number`, `pre_tens`,
`pre_ones`).

**The composite-archetype proof this sub-phase owed.** One resolver covers both the 2-field shape
(BT-01/03/04) and the 3-field shape (BT-02), discriminated purely by the COUNT of `integer-field`
keys `valid_action_space` declares (`MIN_FIELDS = 2`), never by template id or key count table.
`c-named-integer-fields-no-template-branch.test.ts` source-scans the three new files for any
`C-BT-0*` literal or `game_task_template_id` read and finds none.

**Field labels are mechanically derived from the key, never a table** (master work order §3's own
`named-integer-fields` row, verbatim). `humanizeActionKey` (`named-integer-fields-logic.ts`) turns
`post_tens` into "Post Tens" by splitting on `_` and capitalising -- deliberately kept apart from
`payload-value-labels.ts`'s own `FRIENDLY_LABELS` table, which still governs PAYLOAD keys
(`target_number`, `pre_tens`, `pre_ones`) since a payload key is content the child reads, not a field
the child fills, and that table has always been allowed there. The owner was asked explicitly
(AskUserQuestion) whether to extend the payload-label table to action keys too, for friendlier
copy ("Tens now" instead of "Post Tens") -- declined in favour of the strict mechanical rule, to stay
inside the work order's letter and avoid a second name table.

**No auto-carry, no auto-borrow, no pre-fill** (work order §10f row, verbatim). Decomposing
`target_number` (BT-01/02) and performing the trade from `pre_tens`/`pre_ones` (BT-03/04) ARE the
assessed skills. Every entry field starts empty (`useNamedFieldEntry`'s buffers all seed to `''`),
nothing is derived from another field or from a payload value, and SUBMIT gates only on "every field
has a value" (required for `encodeActionPayload` to succeed at all) -- never on the fields summing to
the given number or matching the trade correctly. `c-named-integer-fields-no-client-arithmetic.test.ts`
source-scans for arithmetic performed on a payload-shaped identifier and finds none.

**C-EG-02 reaches this archetype and fails closed structurally, not by template-id refusal.**
`registry.ts` already mapped `C-EG-02` -> `named-integer-fields` before this batch (10g's own future
template, per the work order's sequence table), so registering the surface makes EG-02 reachable
before 10g has designed for it. It fails closed on its own wire shape: its `prompt_payload` carries
`direction: "read"`, a STRING, and the numbers-only payload guard every archetype since 10b has
carried rejects it -- the same class of guard, not a special case. This is deliberately NOT the
explicit `game_task_template_id === 'C-TC-02'` line `value-report-logic.ts` had to carry;
`named-integer-fields-logic.ts` stays entirely template-id-blind.
`c-named-integer-fields-eg02-fails-closed.test.ts` pins both the outcome and the reason, with a
positive control (stripping the offending key resolves fine) proving the refusal traces to that one
guard and not to hidden template-id logic.

**A new primitive was built, not an extension of an existing one -- owner decision (AskUserQuestion,
this batch).** The labelled multi-field entry control (`primitives/named-field-row.tsx`) reuses the
focus/buffer mechanism `value-token-row.tsx`'s entry mode already established, but as a deliberately
separate, copied ~15-line implementation rather than an additive mode on that file. Reasoning: the
two are different scenes (positional blanks vs. named place-value fields), and extending the shared
file would mean a later style change reaches two shipped surfaces at once -- exactly the
`unit-stepper.tsx` / `line-traversal` side effect 10d's own entry already flags. `named-field-row.tsx`
was restructured mid-batch (see "UI iteration" below) from a self-contained row-plus-keypad component
into a state hook (`useNamedFieldEntry`, keyed by field KEY not display position) plus a single-box
renderer (`NamedFieldBox`), so the surface could compose a merged layout freely without the reorder
ever risking a value landing under the wrong submitted key.

**UI iteration, entirely owner-driven from the running app (2026-08-26), in order:**
1. Initial shape: entry fields in a visually separate block below the payload row, smaller box size,
   grey dashed borders, wire-alphabetical field order (`ones` before `tens`, since the wire's own
   `valid_action_space` key order is alphabetical -- not the intuitive place-value order). Owner
   flagged all three as wrong in one pass from a C-BT-01 screenshot.
2. Corrected to: one merged row (payload token + entry fields, same box size, same label style,
   reproducing `value-report-surface.tsx`'s own shapes), fields reordered to descending place value
   (`Tens` before `Ones`) via a new `PLACE_VALUE_RANK` table scoped to display order only (state
   stays keyed by field key, so reordering can never misattribute a submitted value), and unfocused
   borders recoloured from `colors.border` to the family accent.
3. C-BT-02 (3 fields + 1 payload token = 4 columns) then overflowed that merged row: `flex: 1`
   columns inside a `flexWrap: 'wrap'` row compressed instead of wrapping -- the identical RN Web
   flex-shrink pitfall 10e's own `object-pool.tsx` header already documents, recurring in a second
   file. Owner rejected the compressed result outright ("not like that").
4. Owner's actual requested shape, arrived at over three more corrections: the GIVEN payload
   value(s) alone in their own row directly under the prompt (gap halved from the container's
   default); the entry fields as a SEPARATE row directly below that (gap halved again); box size
   reduced from `TOKEN_TOUCH_TARGET_SIZE * 1.6` to `TOKEN_TOUCH_TARGET_SIZE` alone (still above SPEC
   §10's 48px floor, and now the SAME fixed size across every template and level, never a per-scene
   resize) so the widest real row -- C-BT-02's three fields -- fits on one line without wrapping;
   field labels moved from above their box to below it; and, once both rows were reordered
   independently, the given-value row's own alphabetical order (`pre_ones` before `pre_tens`) no
   longer lined up column-for-column under the now-reordered field row (`Post Tens` before
   `Post Ones`) -- so `displayOrder` was generalised to apply the same `PLACE_VALUE_RANK` table to
   both rows, restoring column alignment (`Tens to start` above `Post Tens`, `Ones to start` above
   `Post Ones`).

**The touch-target-size reduction is a single global constant, not a per-scene one.** `PAYLOAD_TOKEN_SIZE`
(surface) and `FIELD_BOX_SIZE` (primitive) both changed from `TOKEN_TOUCH_TARGET_SIZE * 1.6` to
`TOKEN_TOUCH_TARGET_SIZE` alone, together, for every template and every level -- motor constancy
(SPEC §10) holds because C-BT-01/03/04's 3-column row and C-BT-02's 4-column row use the identical
box size; only the row's own WIDTH grows with column count, never any one target's size. Verified by
`c-named-field-row-layout.test.ts`, which asserts both constants share the same literal value.

**Verification.**
- `npx tsc --noEmit` -- exit 0 throughout every UI iteration.
- `npm run test:contract` -- green at 1187/1187 (was 1184 before this batch's 8 new test files:
  `c-named-integer-fields-logic`, `-fail-closed`, `-key-set-proof`, `-no-template-branch`,
  `-no-client-arithmetic`, `-motor-constancy`, `-no-representation-mode`,
  `-carries-interactive-assets`, `-eg02-fails-closed`, plus `c-named-field-row-layout` -- 9 files,
  net +3 tests after several were revised mid-batch to match the two-row restructure).
- Every new guard proven load-bearing by disabling it in place (the numbers-only payload guard / the
  MIN_FIELDS and MAX_FIELDS bounds / the integer-field-kind guard), confirming the targeted negative
  controls went red, restoring from a `$TEMP`-directory backup, confirming an exact diff and green
  tests again.
- `npx expo export --platform ios` -- succeeded twice (initial batch and after the UI restructure);
  `dist/` removed both times.
- **Every difficulty level looked at in a browser by the owner directly**: C-BT-01 at L1 and L5
  (target_number 3, 37), C-BT-02 at L1 and L5 (target_number 185, 586 -- the 4-column overflow case),
  C-BT-03 at L1 and L5 (pre_tens/pre_ones 0/10 and 5/12), C-BT-04 at L1 and L5 (pre_tens/pre_ones
  1/3 and 3/4), through every visual correction described above, all confirmed correct at the final
  state. A full submission (typing digits into both fields, SUBMIT enabling and advancing) was also
  confirmed working end to end. Card #4 confirmed reading **Ready to play** in the hub.

**What was NOT independently re-verified.** Nothing shared -- unlike 10d's `unit-stepper.tsx` change,
every file this batch touches or introduces is new or owned solely by this archetype
(`archetype-surfaces.ts` and `payload-value-labels.ts` were edited additively, one entry each, with
no existing entry altered). The backend suite was not re-run -- no backend file changed.

---

## 2026-08-26 — FE-B-session-ui: Component B's live session screen restyled, home navigation/layout fixes, and a new profile screen

**Scope note.** This batch is Component B frontend work only, driven entirely by the owner iterating
live against the running app in the browser (screenshots, arrows, corrections) rather than a written
work-order spec -- closer in shape to 10f's own "UI iteration" log than to a template-registration
batch. No Component C file was touched; a concurrent agent was working in `c-session/` at the same
time (`archetype-surfaces.ts`, `payload-value-labels.ts`, the `partition-allocation` archetype) and
none of its files are included in this entry or its commit.

**What shipped, `live-session-screen.tsx` (the `/session/:id` game screen):**
- Card layout matching c-session's own task panel shape: a cream card on a neutral ground, edged in
  a per-skill accent colour (`session-skill-accents.ts`, new -- B's own `skill_id`-keyed
  border/soft/text triple, mirroring `game-family-accents.ts`'s pattern without depending on it).
  The skill pill is centred on the card's own x-axis, in the same fixed header row as the exit (X)
  control, and now tints to the skill's own colours instead of a fixed coral.
- Hint control moved from an inline "I NEED A HINT" pill to a top-right circle matching the exit
  button's size and corner, showing only the MOST RECENT hint (a deliberate change from every
  received level staying visible, at the owner's request) in a fixed-`minHeight` box.
- The answer pad centres in the leftover space between the prompt card and the footer (`answerCenter`,
  `flex: 1` inside a `flexGrow: 1` scroll container).
- The correct/incorrect/timeout outcome is now a floating popup (50% width/height of the card's own
  working area, `expo-blur` behind it, no background fill -- just a full-opacity colour-matched glow
  as its edge) instead of an inline banner; the `outcome==='timeout'` case was found mid-batch to
  fall through both style branches (`&&` instead of a ternary) leaving RN's default black shadow --
  fixed to a ternary matching the icon/text logic already in place.
  `outcomeView`'s `incorrect` copy had its second sentence ("...you can try as many times as you
  like") removed at the owner's request; `canTryAgain: true` alone still drives TRY AGAIN.
- CHECK MY ANSWER / NEXT QUESTION / TRY AGAIN restyled to match c-session's flat `SubmitButton`
  (no border, no 3D press effect, `opacity: 0.72` on press) and moved into a fixed footer box below
  the ScrollView, whose gap to the card's own bottom edge is measured live via `onLayout` (three
  `onLayout` calls -- the skill pill, the scroll wrapper, and the prompt card -- combined in one
  shared coordinate space) to exactly equal the pill-bottom-to-prompt-card-top gap, per the owner's
  request that the two match, rather than a static guessed constant.
- Background: a two-colour gradient (`expo-linear-gradient`), the two colours drawn at random each
  question from the same five "game-type" colours `learner-home-screen.tsx`'s own path uses,
  excluding the current skill's own accent so the background can never coincide with the card's
  border, rotating continuously clockwise around the screen's own centre (`react-native-reanimated`,
  45s/revolution). The rotating gradient's own bounding box is sized to the screen's measured
  diagonal (`sqrt(w²+h²)`, via `onLayout`), not a flat `200%` guess -- the flat guess under-covered a
  tall, narrow phone screen's width and showed up as a hard-edged crop in two opposite corners at
  certain rotation angles; found and fixed from an owner screenshot mid-batch.
- Progress bar restyled to a filled pill track (was plain "3 of 8" text); its gap to the prompt card
  specifically doubled at the owner's request (`promptCardAfterProgress`, additive to the scroll's
  own uniform `gap`, applied only when a progress bar is actually rendered).
- `live-session-logic.ts`'s `SessionPlan` gained a `skillId` field alongside the existing formatted
  `skillLabel`, since the accent/pill colouring needs the raw wire id, not the display string.

**What shipped, `learner-home-screen.tsx` (two rounds of navigation/layout bugs, both owner-reported
from the running app):**
1. `openBLearning` (the hero button) was changed to always route through `/prepare`, even when a
   session is already active (previously it skipped straight to `/session/:id` when one was open) --
   restoring the prepare-first flow the owner said used to exist. The "Your Session" card's own
   current-question node then got a SEPARATE handler, `resumeCurrentQuestion`, that DOES skip
   straight to the session: it is reached only when `sessionState.kind === 'in-progress'` already
   (this screen has already confirmed via a live `GET .../summary` read exactly which session and
   question is open), so routing that back through `/prepare`'s own readiness check would be
   redundant on every tap.
2. "Buttons glitch on returning to home" -- root cause: this screen fully remounts on every return
   (`router.replace`, not a stack pop), and `measuredViewportHeight` starts at 0 for one frame, so
   the percentage-positioned path-stage buttons render once at a rough fallback position/size before
   snapping to the real one the instant `onLayout` reports the true height. Fixed with a
   `layoutReady` flag that keeps the ScrollView at `opacity: 0` (still laid out and measured, not
   `display: none`) until the first real layout has landed.
3. "Can't scroll up to see the hero again" -- root cause: `scrollEnabled` was set to `false`
   permanently the first time the hero was scrolled past, as a `handleGestureSettle` side effect.
   Removed entirely; scrolling now stays enabled always. Decoupled from that: `startScrolledToPath`
   (a `useRef`, read once per mount from the module-level `heroDismissedThisAppSession` flag) still
   decides whether THIS mount opens pre-scrolled past the hero, applied exactly once via a new
   `initialScrollAppliedRef` guard so it can never re-fire and yank the child back down after a
   deliberate manual scroll-up.
4. The hero's own CTA button press now also sets `heroDismissedThisAppSession = true` (previously
   only a scroll-past did), and a new cleanup-only `useEffect` sets the same flag on ANY unmount of
   this screen -- covering the Play tab's own `router.replace('/(learner)/play')`, which had no other
   hook into this screen's dismiss logic and was the specific gap the owner reported last.

**What shipped, new profile screen (`/profile`, previously `LearnerEmptyTabScreen` -- deleted, now
unreferenced anywhere).** `learner-profile-screen.tsx`: name (first name, via the header greeting),
classroom and grade (only rendered once an APPROVED `classroomMembership` exists -- the identical
derivation the prep screen already uses, so the two screens can never disagree about whether a
classroom is showing), gender, and a LOG OUT button (`useAuth().signOut()`, same pattern as the two
existing sign-out call sites). Gender required a new field, `profileGender`, added to
`auth-context.tsx`: the backend's `LearnerProfileResponse` carries no gender field at all -- it is
captured once at sign-up into Supabase's own `user_metadata` (alongside `display_name`) and read back
the same way `readDisplayName` already reads the name, via a new `readGender`. Wired into every place
`profileName` was already being set or cleared (sign-in, sign-up, sign-out, session-expiry, the
`SIGNED_OUT` auth-state listener) so the two can never drift out of sync.

**`firstNameOf` (`src/utils/display-name.ts`) now capitalises the first letter** of the returned
token (`"yass"` -> `"Yass"`), leaving the rest exactly as typed (so a name with its own internal
capitalisation, e.g. `"McKay"`, is not fought). All five call sites (home, game hub, profile x2, the
prep screen) share this one helper, so the fix applies everywhere at once with no per-screen change.
Two new test cases added to the existing `display-name.test.ts`.

**Verification -- measured.**
- `npx tsc --noEmit` -- exit 0 after every edit in this batch (checked incrementally, not just at the
  end), filtering only pre-existing, unrelated errors in the concurrently-edited `c-session/` tree
  (`unit-stepper.tsx`'s `targetDot` property, not this batch's file, not fixed here).
- This project's own `node --import tsx --test` suite (Component B has no equivalent of C's
  `npm run test:contract` battery): `live-session-logic.test.ts`, `session-advance.test.ts`,
  `session-hints.test.ts`, `session-results.test.ts`, `session-timeout.test.ts` -- 78/78 passed,
  re-run after every source change touching `live-session-screen.tsx` or `live-session-logic.ts`.
  `home-session-progress.test.ts` -- 20/20, then 24/24 with `resume-decision.test.ts` added to the
  same run, then 27/27 once `display-name.test.ts` gained its two new cases -- re-run after every
  `learner-home-screen.tsx` / `auth-context.tsx` / `display-name.ts` change.
- `npx expo install expo-blur` / `expo-linear-gradient` -- both resolved to SDK 54-compatible
  versions by the Expo CLI itself, not hand-pinned.
- No RNTL/browser rendering was performed by the agent (this environment has no display); every
  visual claim in this entry (crop location, glitch, gradient look, popup shadow visibility) was
  confirmed by the owner directly from the running app, screenshot by screenshot, in the same
  iterative loop 10f's own "UI iteration" section documents -- several stated fixes (the corner crop,
  the black timeout shadow, the glitch, the scroll lock) were themselves owner-reported defects found
  exactly that way, not anticipated by the agent in advance.

**What was NOT independently re-verified.** The backend suite was not re-run -- no backend file
changed. Component C's own `c-session/` files, concurrently modified by a separate agent in the same
working tree, were deliberately left out of this batch's diff and its commit entirely -- confirmed via
`git status`/`git diff --stat` immediately before staging, matching FE-surface-remount-key's own
precedent for excluding concurrent, unrelated in-flight work from a commit.

**Provenance.** Commit `2de9da9`, "Component B: game-styled session UI, home nav fixes, and profile
screen" -- 12 files changed (`app/(learner)/profile.tsx`, `package.json`/`package-lock.json`,
`display-name.test.ts`, `auth-context.tsx`, `learner-home-screen.tsx`,
`learner-empty-tab-screen.tsx` deleted, `live-session-logic.ts`, `live-session-screen.tsx`,
`session-skill-accents.ts` new, `profile/learner-profile-screen.tsx` new, `display-name.ts`).

---

## 10g -- `partition-allocation` archetype + the C-EG-02 array grid, completing C-GF-07 Equal Groups and Arrays

**What shipped.** The seventh of eight archetypes. Two parts:

- **`partition-allocation`** (new): C-EG-01 (`number_of_groups`/`group_size` -> `groups: list[int]`)
  and C-SF-01 (`recipient_count`/`total` -> `allocations: list[int]`), one resolver, no template
  branch. `ValueTokenRow`'s own `display-with-entry` mode is reused UNMODIFIED, exactly as its own
  header and master work order §5A already committed to -- no new label prop, no
  `partition-allocation`-specific behaviour added to that file. `C-SF-02` also resolves to this
  archetype id (its own `groups: list[int]` collection) but fails closed structurally on a
  type-level discriminant: the presence of `submitted_group_count: int` alongside the collection
  marks the variable-bin-count shape §2.3 names as 10h's own falsification test, and pre-building
  that path now would spoil it.
- **The C-EG-02 array grid** (extends 10f's `named-integer-fields`, reversing its own deliberate
  refusal): a new `array-grid.tsx` primitive renders a read-only r x c grid; `rows`/`cols` are read
  by name from `prompt_payload` and consumed STRUCTURALLY as grid dimensions rather than rendered as
  numeral tokens, because both are simultaneously GIVEN and declared `valid_action_space` keys --
  printing either would leak 2 of the 3 answers. `direction` (`"read"` L1-4, `"build"` L5, driving
  different `prompt_text`) is admitted through a single narrow, named string exception and carried
  in the spec, rendered nowhere, branched on nowhere -- 10a's own standing ruling for
  `C-NP-04.direction`, applied unchanged.

**Files.** New: `archetypes/partition-allocation-logic.ts`, `archetypes/partition-allocation-surface.tsx`,
`primitives/array-grid.tsx`. Modified: `archetype-surfaces.ts` (two entries),
`payload-value-labels.ts` (`group_size`, `total`), `archetypes/named-integer-fields-logic.ts` (the
`rows`/`cols`/`direction` extension), `archetypes/named-integer-fields-surface.tsx` (the grid render
branch and the equation-row layout below), `motor-constants.ts` (`GRID_CELL_SIZE`/
`GRID_CELL_SPACING`).

**Named-exception test edit.** `c-named-integer-fields-eg02-fails-closed.test.ts` previously asserted
C-EG-02 fails closed at every level -- that fact is exactly what this batch changes. Inverted in
place (kept its name, following 10d's own `c-mcl-family-surface-registration.test.ts` precedent for
the identical situation) to assert resolution instead, with the corrected reasoning documented in
its own header.

**Shared-primitive consequences, all owner-directed, all re-verified in the browser.** Testing
C-EG-01 at difficulty 5 (5 entry slots) surfaced three issues in `value-token-row.tsx` -- the SAME
primitive NP-01..04 (10a) already ships on:

1. **A latent RN Web flex-shrink wrap bug**, the same class `object-pool.tsx`'s own header already
   documents: `flex: 1` columns inside a `flexWrap: 'wrap'` row compress to fit one line instead of
   wrapping. Fixed by halving `entryTokenRow`'s gap (`TOKEN_SPACING` -> `TOKEN_SPACING / 2`).
2. **The entry-slot token size itself needed splitting in two.** `display-with-entry`'s tokens
   (NP-01..03, and this batch's own `partition-allocation` reuse) are now pinned to
   `TOUCH_TARGET_MIN_SIZE` (48, SPEC §10's own accessibility floor -- the smallest a real touch
   target may shrink to) so 5 entry slots fit one row; `reorder`'s draggable tokens (NP-04 only) stay
   at the original, larger `TOKEN_TOUCH_TARGET_SIZE` (56), per the owner's own separate request that
   NP-04's cards read "a bit bigger." Splitting this surfaced a **latent bug from the size's brief
   single-constant period**: `TOKEN_STRIDE` (driving the reorder-mode drag gesture's slot-movement
   math) would have silently used the entry token's size rather than the dragged token's own the
   moment the two diverged -- caught and fixed (`TOKEN_STRIDE` now derives from
   `TOKEN_TOUCH_TARGET_SIZE` specifically) before it ever shipped as a real bug.
3. **`entryTokenRow` was missing `justifyContent: 'center'`** -- found testing C-SF-01's own
   2-slot row, which left-aligned rather than centering under the prompt/payload token above it.

**A genuinely pre-existing gap, found and fixed in the same pass.** The owner reported NP-04's
drag-to-reorder simply did not respond in the browser. Root cause: `app/_layout.tsx` never wrapped
the app root in `GestureHandlerRootView`, which `react-native-gesture-handler` requires on every
platform including web for gestures to register touches at all -- missing since 10a shipped the
primitive, invisible until someone actually tried to drag in a real browser (nothing in this
repository can mount a tree to catch it structurally). Fixed with one wrapper in the root layout.
Separately, `DraggableToken`'s `.activateAfterLongPress(GESTURE_LONG_PRESS_MS)` (400ms) is by design,
not a bug -- a deliberate discoverability gap with a mouse rather than a touchscreen, documented
here in case it resurfaces.

**A second shared-surface layout fix.** NP-04's own `ArrangeSceneSurface` used the same `container`/
`justifyContent: 'space-between'` shape the entry scene (NP-01..03) uses, which -- with only ONE
middle child (the token row) -- concentrated ALL leftover vertical space into a single gap above and
below it, producing large empty bands the owner flagged. Fixed with scene-scoped styles
(`arrangeContainer`/`arrangeTopBlock`/`arrangeRowWrapper`), left `container`/`promptText` (still used
by the entry scene) completely untouched.

**The C-EG-02 equation row, `named-integer-fields-surface.tsx`'s own addition.** The generic wrapped
`fieldsRow` every other named-integer-fields template uses put C-EG-02's "Submitted Product" field on
its own line -- that label's own unabbreviated width, not a wrapping bug in the general sense, was
wider than the row's remaining space once "Cols"/"Rows" took their share. A dedicated
`EquationFieldsRow` renders "Cols x Rows = Product" as one non-wrapping row instead, using a
DISPLAY-ONLY label override (`EQUATION_FIELD_LABEL_OVERRIDE`, scoped to this one component) that
shortens "Submitted Product" to "Product" -- `spec.fields`' own resolver-produced label stays
"Submitted Product", unchanged, exactly as `humanizeActionKey` produces it; only this one row's own
rendering substitutes the shorter text.

**Verification.**
- `npx tsc --noEmit` -- exit 0 throughout every UI iteration.
- `npm run test:contract` -- green at 1298/1298 (was 1187 before this batch's ~17 new test files
  across both parts, net +111 tests after several existing files were revised mid-batch: the eg02
  inversion, the fail-closed table's new grid/direction controls, and the motor-constancy file's
  updated `NamedFieldBox` call-site count).
- Every new guard proven load-bearing by disabling it in place (partition-allocation's
  fixed/variable-shape discriminant, its bin-count-validity and collection-vocabulary guards; the
  grid-dimension-validity, direction-string, and rows/cols-symmetry guards), confirming the targeted
  negative controls went red, restoring from a `$TEMP`-directory backup, confirming an exact diff and
  green tests again.
- `npx expo export --platform ios` -- succeeded across all three UI-iteration rounds; `dist/` removed
  each time.
- **Every difficulty level looked at in a browser by the owner directly, in two passes as planned**:
  C-EG-01 at L1 and L5 (2 groups of 2, 5 groups of 4 -- the 5-slots-on-one-row case), C-SF-01 at L1,
  C-EG-02 at L1 and **L5** (the only `"build"` row, confirming its own different `prompt_text` and a
  5x5 grid), C-EG-03 spot-checked unchanged. Re-verification of the shared-primitive changes: NP-01
  (twice, after the size split and again after the centering fix), NP-04 (after the gesture-root fix,
  the token-size split, and the layout restructure -- drag-to-reorder confirmed working end to end).
  Card #7 confirmed reading **Ready to play**; card #8 confirmed still not-ready.

**What was NOT independently re-verified.** NP-02/NP-03 (10a's other two entry-scene templates) --
they share `value-token-row.tsx`'s `display-with-entry` mode with NP-01, which WAS re-verified, but
were not separately opened in the browser this session.

## 2026-08-26 — 10h Share Fairly: C-18 FALSIFIED. The final sub-phase builds no screen and ships
four findings instead.

**What 10h delivers.** No new archetype, no new surface, no behaviour change of any kind. Source
edits are comment-only. This was always the plan's shape -- 10h is the second falsification test of
the two-layer rule (master work order §2.3) -- but the result is the one the sequence doc hoped to
avoid and deliberately positioned to catch cheaply: **C-18's claim does not hold for `C-SF-02`.**

**Already complete before this batch started, verified not re-derived.** `C-SF-01` shipped in 10g
(browser-verified there). `C-SF-03` has resolved through `value-report` since 10b (registry.ts:46;
five existing test files cover it: `c-value-report-{logic,key-set-proof,prompt-text,carries-
interactive-assets}.test.ts` plus `c-payload-value-labels.test.ts`). **The registry-coverage test
the work order assigns to 10h (§4, "the archetype registry's 30 entries must equal the id set in
`c-template-registry.json`, written to fail loudly if the artefact is absent") already exists and
passes** -- `c-archetype-resolution.test.ts:68-81`, asserting exact set equality with two negative
controls (an added id and a removed id both break it), reading the artefact at module scope via
`readFileSync` so an absent artefact throws rather than skipping. 10h verifies and cites it; writing
a second one would have been duplication, not coverage. `C-SF-02` was therefore the entire remaining
question.

### FINDING 1 (headline) -- C-18 held for the key §2.3 named, and is FALSIFIED by a key no document anticipated

C-18's claim (Master Build Plan v3.0:959-966): *"A new template within an existing archetype is
configuration, not a new screen."* Sequence doc §3.5 predicted `C-SF-02` would confirm it, reasoning
that `submitted_group_count` is *"a second report about that same partition, not a second
interaction."*

**That prediction is correct about the key it named, and wrong about the one it did not.**

**Where C-18 HELD.** `submitted_group_count: int` really is trivial -- one additional declared key
becomes one additional `DigitKeypad`-backed field, archetype scene untouched. This is structurally
identical to `C-JB-04`'s `exchange_performed: bool` in 10c, which passed the same test. The
two-layer rule itself is intact and is not what failed here.

**Where C-18 is FALSIFIED -- the absent key.** Every other `partition-allocation` template declares
its bin count in `prompt_payload`; `C-SF-02` does not declare one at all:

| Template | `prompt_payload` | bin count |
|---|---|---|
| `C-EG-01` | `number_of_groups`, `group_size` | **given** (`number_of_groups`) |
| `C-SF-01` | `recipient_count`, `total` | **given** (`recipient_count`) |
| `C-SF-02` | `group_size`, `total` | **ABSENT** |

Re-verified directly against all five difficulty levels of each: `C-SF-02`'s payload is exactly
`{group_size, total}` at L1-L5 (`{2,4} {2,6} {3,9} {3,12} {4,20}`), matching neither name in
`partition-allocation-logic.ts`'s own `BIN_COUNT_KEY_VOCABULARY` (`['number_of_groups',
'recipient_count']`, line 63).

**Why the absence is decisive rather than merely awkward.** `C-SF-02`'s `prompt_text` is *"Split the
total into equal groups of the size shown. Write the groups you made."* Each bin's value is
`group_size`, which IS given -- so **the number of bins is the answer**, and it is simultaneously a
declared `valid_action_space` key (`submitted_group_count`). That produces a closed trap:

- **Rendering the correct number of bins IS rendering the answer.** A fixed-slot scene that draws
  the right count has already told the child what `submitted_group_count` is.
- **Deriving it computes a declared answer key client-side.** `total / group_size` is exact at every
  real level (4/2=2, 6/2=3, 9/3=3, 12/3=4, 20/4=5). Doing that arithmetic and rendering exactly that
  many slots is the same leak class this codebase has already ruled against twice: `C-EG-02`'s
  `rows`/`cols` (consumed as `ArrayGrid` dimensions rather than printed, precisely because they
  double as answer keys) and `C-MCL-01`'s numeral-options path (10e-0). It is also flatly barred by
  the archetype's own disclaimer -- master work order §3: *"No validation that groups are equal,
  that a partition is exhaustive, or that a product is right. The client submits; the server
  evaluates."*
- **The only non-leaking shape is a two-stage interaction** -- the child enters the count first,
  then fills that many bins -- **and `DisplayWithEntryRow` structurally cannot do it.** `blanks` is
  read exactly once, in a `useState` lazy initializer (`value-token-row.tsx`: `useState<string[]>(()
  => Array.from({ length: blanks }, () => ''))`), never re-synced on a prop change, with no
  add-bin/remove-bin affordance anywhere in the component. That primitive's own header additionally
  commits to being reused *unmodified* by `partition-allocation`.

**A two-stage interaction is a new interaction, not configuration.** That is the falsification.

**The specific configuration points a variable-bin-count scene would need** (recorded per the
sequence doc's requirement that these be listed "either way", so a future batch starts from a spec
rather than rediscovering this):

1. A `value-token-row` mode -- or a new sibling primitive -- whose slot count is a controlled prop
   re-synced on change, not a lazy-initialized constant. Whichever it is, `DisplayWithEntryRow`'s
   unmodified-reuse commitment has to be renegotiated or explicitly narrowed.
2. A two-stage submit gate: the count field must be answered before the bin row exists at all, so
   the scene never renders a slot count the child did not choose.
3. A resolver variant on `partition-allocation-logic.ts` that treats "collection key + integer-field
   key, and NO payload bin-count key" as a distinct, buildable shape rather than the refusal it is
   today -- keyed structurally on that key combination, never on a template id.
4. A motor-constancy answer for a child-chosen bin count: `MAX_BINS = 12` today is a layout bound
   over payload-supplied counts; a child-driven count needs its own bound and its own cost argument,
   since adding bins one at a time is an interaction cost that scales with the answer's magnitude --
   the same confound class as `C-MCL-04`'s tap count.
5. An answer-leak guard equivalent to the ones `C-EG-02` and `C-MCL-01` already carry, asserting no
   code path derives the bin count from `total`/`group_size`.

**Correcting the record.** §3.5 grouped `C-SF-02`'s extra scalar with `C-CC-01`'s extra
`submitted_total` and `C-JB-04`'s extra boolean and called all three "the identical case." They are
not identical: the other two sit in scenes whose shape is fully determined by the payload, while
`C-SF-02`'s scene shape is determined by its own answer. The risk was never the extra key §3.5
named; it was the missing one it did not.

**Ruling applied (owner, 2026-08-26): the refusal STAYS. No screen is built this batch.** Per §2.3,
this is an owner finding, not a builder's to resolve. `partition-allocation-logic.ts`'s guard is now
recorded as permanent rather than provisional-pending-10h.

### FINDING 2 -- hub readiness overclaims: a family reads "Ready to play" while a template inside it fails closed

`readinessOf` (`game-catalogue.ts`) computes readiness per ARCHETYPE, not per template: it maps the
family's template ids to their archetype ids, then returns `'playable'` when
`registered === archetypeIds.length`. A family therefore reads "Ready to play" as soon as every
archetype it touches has a registered surface -- regardless of whether a specific template behind
one of those archetypes fails closed on its own declared shape.

**This is pre-existing and systemic, not introduced by 10g or 10h.** Two live instances, both
confirmed by reading the code (`SURFACE_TABLE` now holds all 8 archetype ids):

- **Card #6 "Take Away and Compare" (C-GF-06), since 10b.** All four templates map to
  `value-report`, which is registered -- yet `C-TC-02` is explicitly refused inside
  `value-report-logic.ts` pending the unresolved `directed`-flag question. The card has claimed
  playable for one refused template for five sub-phases.
- **Card #8 "Share Fairly" (C-GF-08), as of 10g.** Its templates span `partition-allocation` +
  `value-report`; 10g registered the former and the latter has been registered since 10b, so both
  are present and the card computes `'playable'` -- while `C-SF-02` fails closed, permanently as of
  this batch's own Finding 1.

**Recorded, deliberately not fixed** (owner ruling, 2026-08-26). Making the hub template-granular
would require it to resolve each template's spec, which `game-catalogue.ts`'s own header argues
against on separation grounds, and it interacts with Finding 1's still-open question about what
`C-SF-02` should eventually become. **Not decided here:** whether the hub should show a partial
state for these families, whether the affected templates should be delisted from their family's
`templateIds` until buildable, or whether the overclaim is acceptable while Component C stays inert
and no real child can reach it.

### FINDING 3 -- correction to this register's own 10g entry

The 10g entry states: *"Card #7 confirmed reading **Ready to play**; card #8 confirmed still
not-ready."* **The second half is wrong.** By `readinessOf`'s archetype-granular logic (Finding 2),
C-GF-08's two archetypes were both registered the moment 10g landed `partition-allocation`, so card
#8 became `'playable'` in that same batch. The error came from a compound question whose "ok" was
read as confirming both halves. Corrected here rather than by editing the 10g entry, since this
register is append-only.

### FINDING 4 -- the §7.1 standing obligation, discharged

`Component_C_Frontend_Build_Steps.md` §7.1 (added 2026-08-26) carries the finding *"the server's
verdict is computed, relayed, validated -- and thrown away"* and instructs: **"This finding must
also be appended to `backend/buildLog2.md` at the next batch -- the documents in this folder are not
in git, and the register is the only record that survives."** It was not present here. 10h is the
last sub-phase, so this is the last chance to discharge it. Recorded now, in full substance:

`CSubmitActionResult` carries `response_matched: boolean` (the server's correct/incorrect verdict)
and `scaffold_level: string`. The client validates both -- `isCSubmitActionResult`
(`src/api/runtime-validation.ts`), whose own comment reads *"the server's verdict, read and relayed,
never computed"* -- and then **does nothing with either**: `handleSubmit`
(`c-session-screen.tsx`) awaits `api.submitAction(...)` without assigning the result and calls
`loadNextTask` immediately. No correct/incorrect display, no score, no "try again", no pause.
Submitting a question fetches the next one.

**This is unassigned, not deferred.** No sub-phase in 10a-10h scopes it; the sequence doc and master
work order define every sub-phase in terms of archetypes and surfaces, and none mentions rendering
the verdict. Component B's live-session screen DOES show outcomes, so C's silence is a divergence
from this codebase's own pattern, not a house style. It stayed invisible because the development
fixture returns a canned `response_matched: true` and re-serves the same task forever
(`component-c-api.ts`, its own comment: *"a canned fixture value, not a computed verdict"*) -- every
browser check to date ran against a loop that could not have shown a verdict even if the screen were
wired for one.

**Two rulings are needed, from two different owners.** (1) *Pedagogical/scientific:* whether a tool
for children with dyscalculia should show immediate correct/incorrect at all -- immediate negative
feedback to a child already struggling with number sense is exactly the class of decision this
project escalates rather than settles in a builder's judgment; the question is not which colour the
wrong answer is, but whether the wrong answer is named to the child at all. (2) *Backend contract:*
**"try again" is not expressible as the contract stands** -- `CSubmitActionRequest` carries only
`action_payload`, with no attempt number and no retry flag, and the exact-key-set rule forbids
adding one. Since BKT conventionally scores on the FIRST attempt, a retry would either silently
contaminate the model or require a contract change. A frontend "try again" built on today's contract
would be a scientific defect wearing a UI.

**Standing instruction, unchanged:** do not implement feedback, retry, scoring, or any persistence
of `response_matched`. Do not delete the validator -- it is correct and will be needed. 10h did not
touch `handleSubmit`.

**Files (comment-only, no behaviour change):**
- edit: `frontend/src/features/c-session/archetypes/partition-allocation-logic.ts` -- the refusal's
  header comment now records the 10h ruling (permanent, not provisional) and its reasoning, replacing
  the "remove only this file's own said guard the moment 10h answers the question" instruction that
  a future builder would otherwise have followed into the leak.
- edit: `frontend/src/features/c-session/archetype-surfaces.ts` -- the `partition-allocation` entry's
  comment no longer describes C-SF-02's refusal as "the variable-bin-count shape 10h, not this batch,
  builds".
- edit: `frontend/src/api/__tests__/c-partition-allocation-sf02-fails-closed.test.ts` -- header
  updated to record that this file now pins a RULED, permanent refusal rather than a
  pending-10h one. No assertion changed; the file's four tests are exactly the right permanent guard
  for the ruling and needed no edit.
- edit: `backend/buildLog2.md` -- this entry.
- edit (not in git): `Component_C_Frontend/INDEX.md`, `Component_C_Frontend_Build_Steps.md` -- state
  sections refreshed; both still claimed "10e-10h are not started" and "4 of 8 entries populated"
  when the real state is 8 of 8 registered and 10b-10g all landed.

**Verification -- measured.**
- `npx tsc --noEmit` -- exit 0.
- `npm run test:contract` -- **1298 tests, 1298 passed, 0 failed**, identical to the pre-batch
  baseline measured at `c52c1e9`. Unchanged is the correct outcome and the point: every edit this
  batch is a comment, and a changed count would have meant an accidental behaviour change.
- `C-SF-02`'s refusal re-confirmed still firing at all five difficulty levels by its own existing
  test file, unmodified.
- `npx expo export --platform ios` -- succeeded; `dist/` removed after.
- No git command run; the owner commits.

**What was NOT verified.** No browser check this batch -- nothing renders differently, since no
executable line changed. Findings 2 and 3 were settled from the code path (`readinessOf`'s
`registered === archetypeIds.length` branch, against a `SURFACE_TABLE` now holding all eight
archetype ids) rather than by opening the hub, on an explicit owner ruling that the code evidence
was sufficient. Finding 1's claim that a two-stage interaction is the ONLY non-leaking shape is a
reasoned argument from the payload and the primitive's structure, not an exhaustively enumerated
proof -- if someone finds a leak-free single-stage scene, that would overturn the falsification and
should be recorded as such.

## 2026-08-26 -- Answer feedback + retry loop for Component C: the server's verdict, finally read

**Base commit `46736ab`** (10h, Share Fairly / C-18 falsification). Frontend baseline measured
fresh at the start of this batch: `1298 tests, 1298 pass, 0 fail`, `tsc` clean -- **not** the
`832/832/0` figure from an earlier turn, which four sub-phases had already superseded by this point.

**What was asked, and what was actually buildable.** The owner asked for four things: connect the
UI to the real backend, remove the dev fixture, wire each game-hub card to its own family, and add
correct/incorrect + retry feedback. Investigation (not assumption) showed three of the four are
blocked outside the frontend:

- **Live backend** -- `create_session` refuses every production request with HTTP 409, on two
  independent gates (bundle per-field approval status, and a hardcoded non-smoke code gate). The
  backend's own comment states this is deliberate: "NO bundle committed anywhere in this codebase
  can ever satisfy this gate today... not a bug" (`session_lifecycle.py:135-143`). Opening it is a
  sign-off act across seven parameter families, not a code change.
- **Dev fixture removal** -- blocked by the above; removing it first leaves an app that can only
  render the 409 failure screen.
- **Hub card per family** -- out of scope for this batch on the owner's explicit instruction after
  investigation showed it is not a simple wiring gap: `CreateCSessionRequest` carries only
  `{grade, session_mode}`, `next_task` takes no body, and `adapter.select_task` has no family
  parameter anywhere in its call chain (`task_service.py:440-458`, `adapter.py:1077-1097`). Deeper
  than the missing parameter: skills and families are many-to-many (7 skills, 8 families,
  `loader.py:191-194,257,261-263`), so "select only from family X" has no natural meaning against
  the current BKT/skill-mastery model. Recorded and then explicitly dropped from this batch's scope
  by the owner -- not carried into `ESCALATIONS.md`, per instruction.
- **Correct/incorrect + retry** -- buildable, and built. The rest of this entry is this item only.

**A correction to the supervisor's own earlier claim, caught before code was written.** An earlier
session recorded that "'try again' is not expressible in the current contract." That was wrong.
Re-reading `task_service.py` directly showed a terminal event is written only on a **correct**
answer (`write_completed_correct_terminal_event`); an incorrect answer may be resubmitted on the
same `c_task_instance_id` without limit (`has_terminal_for_instance` only blocks a second
submission once a terminal event exists), and each resubmission re-runs
`decide_and_persist_scaffold_level`, escalating `scaffold_level`. **Retry-with-scaffolding was the
flow the backend was already built for; the frontend simply never read the result needed to drive
it.** Corrected in `Component_C_Frontend_Build_Steps.md` section 7.1 the same day, append-only.

### What was built

1. **`planSubmissionOutcome`** (`c-session-logic.ts`) -- `{kind:'advance'}` on
   `response_matched`, else `{kind:'retry', scaffoldLevel}`, carrying the server's own
   `scaffold_level` verbatim. Computes nothing about correctness; a source-scan test
   (`c-submission-outcome.test.ts`) asserts its body reads only `result.response_matched` /
   `result.scaffold_level` and contains no reference to `action_payload`, `valid_action_space`, or
   `prompt_payload`.
2. **`answer-feedback-panel.tsx`** (new) -- two states (not-matched / matched), one button each
   (Try again / Next), both child-initiated. No auto-advance timer, on the same reasoning that
   ruled out 10a's per-slot stepper: a new timing constant would need to live in
   `motor-constants.ts` and be justified there; a button sidesteps the question entirely.
3. **`c-session-screen.tsx`** -- the `task` phase gained `attempt: number` and
   `feedback: {matched, scaffoldLevel} | null`. `feedback === null` renders the archetype surface
   (unchanged); `feedback !== null` renders `AnswerFeedbackPanel` **instead of**, never alongside,
   the surface -- a correctness requirement, not a layout choice: a correct answer writes the one
   terminal event a task instance may ever have, and resubmitting a terminal instance 409s
   (`task_already_terminal`), which `classifySessionFailure` would route to the technical-block
   screen. Rendering the panel instead of the surface is what makes a second submission
   structurally impossible while feedback is showing. The `<Surface>` remount key changed from
   `task.c_task_instance_id` alone to a template literal combining it with `attempt` -- without the
   attempt component, "Try again" would reconcile into the same component instance and the wrong
   answer would still be sitting there, unentered, for the child to resubmit unchanged; the
   existing key comment was corrected in place (not left stale) to explain both components.
4. **Dev fixture verdict** (`component-c-api.ts`) -- `EXPO_PUBLIC_COMPONENT_C_DEV_FIXTURE_VERDICT`:
   `correct` (default, unchanged behaviour) / `incorrect` (always not-matched, escalates
   `scaffold_level` C0 through C4 across calls, ceilinged at C4) / `alternate` (not-matched,
   matched, not-matched, ... -- a walkable full retry cycle). Still evaluates nothing: the value
   returned depends only on the env var and a per-fixture-instance call counter, never on the
   submitted payload -- proven by a test comparing two independent fixture instances' first-call
   results across different payload content, for all three verdict modes.

### Tests -- four new files, one existing file extended

- `c-submission-outcome.test.ts` (5) -- advance/retry, verbatim `scaffold_level` relay including an
  unexpected string, the source-scan purity proof.
- `c-feedback-replaces-surface.test.ts` (7) -- the no-double-submit structural guard: a
  balanced-paren extractor confirms `<Surface>` and `<AnswerFeedbackPanel>` are the two branches of
  one `feedback === null` ternary, never siblings and never two independent `&&` blocks. Five
  negative controls, one positive control, one real-file assertion, all proven to fire correctly
  after two real bugs in the guard itself were caught and fixed (see below).
- `c-dev-fixture-verdict.test.ts` (7) -- all three verdict modes, the C4 ceiling, the
  payload-blindness proof.
- `c-surface-remounts-per-task.test.ts` (extended, 9 to 15) -- the pre-existing key-extraction
  predicate was rewritten to brace-balance the key expression (the real key is now a template
  literal, not a bare `task.field` member expression, which the old regex could not see at all --
  proven by running the suite before this fix and watching it fail red against the real file) and
  a second predicate, `keyIncludesAttempt`, was added with its own five controls.
- `c-mcl-family-surface-registration.test.ts` and every other pre-existing test file: unchanged in
  count, confirmed by running each in isolation before and after.

### Two real bugs this batch's own guards caught before being reported green

1. **The mutual-exclusivity regex anchored on the wrong occurrence of "feedback".** First draft
   matched the literal substring "feedback" to find the ternary condition, and matched the import
   path for answer-feedback-panel.tsx (which also contains "feedback") long before the real
   `feedback === null` condition in the file. Fixed by anchoring on the full comparison
   (`feedback` followed by a comparison operator followed by `null`), not the bare identifier.
2. **The same guard's branch extraction used a non-greedy colon match**, which stopped at the
   first colon it found -- and the real key expression is a template literal containing its own
   colon between the instance id and the attempt count, so the "false branch" was sliced open
   mid-key rather than at the ternary's actual separator. Fixed with a brace-balanced extractor
   now in the test file, which cannot be fooled by a colon or question mark nested inside either
   branch.
3. **`withDevFixtureEnv` in the verdict test file did not await its own async callback before its
   `finally` restored the env vars.** Since every callback's first line was an awaited call to
   `submitAction`, the helper returned control to `finally` the instant that await was reached --
   restoring the environment before the callback's assertions ever actually ran against the
   intended verdict. Two tests ("correct" and "unset") passed anyway, by coincidence: their
   expected values matched what the RESTORED (default) environment would produce regardless.
   "incorrect" and "alternate" could not pass by the same coincidence and failed loudly, which is
   what surfaced the bug -- fixed by making the helper `async` and awaiting `run()` inside `try`.

None of the three reached this entry as a false "green" -- each was caught by its own test failing
before being reported.

### Verification

- `npx tsc --noEmit` -- exit 0.
- `npm run test:contract` -- **1324 / 1324 / 0**. Reconciled: 1298 plus 25 written plus 1
  auto-generated equals 1324. The +1 is `no-node-builtins-outside-tests-and-scripts.test.ts`, which
  generates one assertion per source file it scans and picked up the new `answer-feedback-panel.tsx`
  -- confirmed by name, not assumed.
- `npx expo export --platform ios` -- succeeded (`entry-f4a0686ce62b1aad0d4deeddba4bf916.hbc`,
  5.21 MB); `dist/` removed after.
- No file under `archetypes/` appears in this batch's diff -- confirmed by `git status` against
  that directory specifically. No archetype surface was touched.
- Every new guard proven bidirectionally (break it, confirm red, restore, confirm green), including
  the three bugs above, each of which is itself an instance of "broke, confirmed red, fixed,
  confirmed green" rather than a defect shipped unnoticed.
- **Browser-verified**, `C-NP-01` at difficulty 1, verdict mode `alternate`: submit wrong -- "Let's
  try that again" plus support-level text shown, no premature "answered" appearance -- Try again --
  surface reappears with the previous entry actually gone, not just hidden -- submit correct --
  "Nice work!" -- Next -- next task loads. Confirmed by the owner directly, not inferred from
  source.

### What was not verified

Nothing here proves the child's actual entered value is cleared by React's remount as opposed to
merely being re-initialized state that happens to look empty -- that distinction is React's own
documented remount behaviour, relied on and not independently re-verified, matching every other
`key`-based remount guard already in this codebase (`c-surface-remounts-per-task.test.ts`'s own
long-standing disclaimer). The pedagogical appropriateness of showing correct/incorrect at all was
not decided by building this, and the copy was deliberately kept neutral so building it would not
default that question shut.

### Findings recorded, not resolved -- full text in `ESCALATIONS.md`

1. The seven-parameter-family sign-off gate blocking every live session (verified this batch by
   reading `bundle_resolution.py`, `c_session_service.py`, `session_lifecycle.py` directly).
2. `attempt_number` hardcoded to `1` server-side, newly consequential now that retry is a reachable
   flow (was always true; this batch is the first time it matters).
3. Section 7.1's discard-the-verdict finding, now closed by construction rather than by ruling.
4. The feedback-copy departure from Component B's own "identical for every outcome, nothing
   evaluative" precedent -- shipped neutral, not decided.
5. Carried forward unchanged: `C-TC-02`'s `directed` flag, `C-SF-02`'s permanent C-18 hold,
   `C-CC-04`'s answer-bearing `trial_type`, `C-MCL-02`'s symbolic question, the object-grouping
   question.

The hub-card-per-family investigation (BKT selection is a single cross-family adaptive stream;
skills and families are many-to-many, not one-to-one) is recorded above for provenance but was
explicitly dropped from scope by owner instruction and does **not** appear in `ESCALATIONS.md`.

## 2026-08-26 -- CONNECT Step 1: owner approval recorded for the seven parameter families

The owner signed off on all seven Component C parameter families -- 1 (Selection) and 2 (Safety)
unconditionally, 3-7 with binding conditions -- authorising the CONNECT work order to open the
production session gate. Full table transcribed verbatim into
`Component_C_Frontend/APPROVAL-2026-08-26-seven-families.md` (approver: Yasindu (owner), date
2026-08-26, scope: the seven Component C parameter families only). No other approver, role,
signature, or threshold is recorded anywhere.

Two recorded limits, carried into that document rather than resolved in code:

- Family 1's text names "BKT" as the selection authority; in this codebase BKT is Component B's
  (`app/application/attempt_submission.py`, `opportunity_selection.py`), while Component C's active
  policy is `policy/rule_based.py` (`QLearningDisabledError` on both Q-learning modes). Read for
  this runtime as "selection is backend-controlled, frontend never chooses."
- Family 7's second sentence (BKT distinguishing first-attempt from retry performance) is out of
  scope for this work order, per the same table's third sentence forbidding an invented
  retry-weighting formula. CONNECT Step 5 makes the underlying attempt-level data real; it does not
  implement Family 7 in full.

### Step 0 baseline, measured at `b228564` (not relayed from any prior document)

- Backend, rebuilt container (`docker compose build api` then
  `docker compose run --rm --no-deps api python -m pytest -q`): **650 passed, 1 failed, 76
  skipped**. The single failure is `tests/test_auth.py::test_invalid_tokens_fail_closed[expired]`
  -- root-caused to the uncommitted `auth.py` `leeway=30` change (`auth.py:104`) keeping a token
  built at `exp-1s` (`test_auth.py:127`) valid. Owner ruling: **carry forward as a pinned
  known-bad baseline** -- do not fix, do not revert `auth.py`, out of scope and in security code.
  From this point on, "green" means exactly this set of one failing node id; any change to that
  set (a different id, an additional failure, or this one disappearing) is a regression, not an
  improvement, and stops the work order.
- Frontend: `npx tsc --noEmit` exit 0; `npm run test:contract` 1324/1324/0; `npx expo export
  --platform ios` succeeded (`dist/` removed after).
- Git: `b228564078574a75063c04da77303dc0365c0f3f`, branch `C_backend`, 27 commits ahead of
  `origin/C_backend`; working tree unchanged from HANDOVER.md §7 (2 modified: `auth.py`,
  `secure-storage.ts`; 2 untracked: `hub.png`, `.playwright-mcp/`).

Both the previously-cited `651 passed / 76 skipped` backend figure and the assumption of a clean
backend suite are superseded by the pinned baseline above.

## 2026-08-26 -- CONNECT Steps 2+3 (merged): the governed catalogue, vendored, and the first approved runtime bundle

Step 2 as originally written (author a PROVISIONAL catalogue) was based on a wrong premise: that
no governed catalogue existed anywhere reachable. It does --
`R26-IT-138_Component_C_Game_Task_Catalogue_v1.0.md` (2133 lines, dated 2026-07-13), in a sibling
tree outside `Upadya/` (`ResearchProject/Yass/Component_C_v1.0/`), reachable only via a path
constant inside the installed generator wheel
(`component_c_generator.catalogue.loader.DEFAULT_CATALOGUE_PATH`). Nothing in `Upadya/` referenced
it; every frontend document here was written as though it did not exist. Full account, with no
recommendation, in `Component_C_Frontend/ESCALATIONS.md` §6.

Corrected plan: vendor the real file rather than author a substitute. Verified byte-identical both
directions (source and vendored copy, `sha256 82004a5fef94528ea1e4187473420453bdfb7e1d3b5ade48ce2bc03486630851`,
recomputed independently, not trusted from anyone's paste) into
`backend/provenance/R26-IT-138_Component_C_Game_Task_Catalogue_v1.0.md`. `_CATALOGUE_PATH`
repointed in both `c_session_service.py` and `task_service.py`. `load_catalogue` confirmed to
accept it from the new location inside a rebuilt container: 30 templates, 8 families,
`catalogue_status: PROPOSED_FOR_APPROVAL` -- not `APPROVED`. Two build-context defects found and
fixed along the way, both required for the file to actually reach a fresh image rather than only
working locally: `.dockerignore` excludes all of `provenance/` by default and needed a
path-specific carve-out (following the existing wheel/schema carve-out pattern); the Dockerfile
copies `provenance/` files individually, one `COPY` line per file, and needed a new line for this
one. A third, more serious instance of the same class of defect was found only during owner
verification: `.gitignore`'s blanket `*.md` rule (line 29) has no negation for this path either,
so the vendored file was untracked-but-ignored -- committable only by accident of the working tree,
invisible to a fresh clone, which would 409 on every session with no test able to catch it (the
suite is only ever green because the file happens to be present locally). Fixed with a
path-specific `.gitignore` negation, same pattern as the existing BE3b/BE3c test-fixture carve-out;
confirmed both directions (`git check-ignore` exits 1 with no output; `git status` lists the file
as untracked/committable).

Step 3, merged into the same step per owner correction (the original split guaranteed a red tree
between the two STOP gates, since the catalogue repoint and the bundle's checksum recomputation
are one atomic change, not two): authored
`backend/provenance/c-runtime-bundle-approved-1.0.json`, schema-validated against
`c-runtime-bundle.schema.json` (schema_version 1.3). `bundle_version: "c-approved-1.0"`,
`approval_status: "APPROVED"`, `publication_state: "PUBLISHED"`. The three bundle-data families
(selection, safety, evidence_window) carry every per-field `status: "APPROVED"`, values carried
forward unchanged from the prior fixture, each `source` citing
`APPROVAL-2026-08-26-seven-families.md` by family number -- the change is provenance, not numbers.
`catalogue.checksum` recomputed from the vendored file (not copied); `catalogue.version: "1.0"`
taken from the real catalogue's own declared version. `catalogue.approval_status` records
`"PROPOSED_UNSIGNED"` -- the catalogue's own literal status ("PROPOSED FOR APPROVAL") has no exact
match in this schema's `approvalStatus` enum, and PROPOSED_UNSIGNED's own description ("a cited
source specifies this exact value, but that source's own approval/sign-off process has not
completed") is the nearest true one; the mapping is not left implicit -- the schema gained one new
OPTIONAL, additive field (`versionedArtifact.source_status_note`) and the bundle's `catalogue`
block carries the catalogue's literal status string verbatim in it, with the file:line citation.
`database_schema_revision`/`compatibility.database_schema_minimum` set to the real alembic head
(`20260816_0008`, measured inside the container, not assumed); `backend_code_version` set to the
real default (`0.1.0-be1.3`, `app/core/config.py`). `_BUNDLE_PATH` repointed in both files.
`resolve_c_bundle_and_catalogue` confirmed end-to-end inside the container: schema valid, no
checksum mismatch, `approval_status` reads `APPROVED`, 30 templates loaded.

Two judgment calls, both surfaced to and confirmed by the owner rather than decided silently:
`catalogue.approval_status` mapping (above), and `activation_date: "2026-08-26T00:00:00Z"` (the
schema requires a non-null value once `publication_state: PUBLISHED`; grepped the codebase and
confirmed nothing gates on its actual value).

### The residue, and its root cause

Repointing `_BUNDLE_PATH` alone (before the checksum fix) surfaced 35 failures beyond the pinned
baseline -- not a regression in the code, but `assert_family_usable`/checksum verification working
correctly: the committed bundle fixture declared the OLD catalogue's checksum
(`55709112...`) while `_CATALOGUE_PATH` now served the real one (`82004a5f...`), so
`resolve_c_bundle_and_catalogue` 409'd every session before any test's own assertions ran. Root
cause diagnosed by the owner directly (`bundle_resolution.py:77`), not guessed at. Fixed by
recomputing `catalogue.checksum` against the vendored file in the new approved bundle -- at which
point 29 of the 35 cleared. The remaining 6, all in
`tests/test_c4b_routes_and_bundle_config.py`, were a genuine, distinct test-seam gap: that file's
autouse fixture monkeypatches `_BUNDLE_PATH` to `all_usable_for_tests_bundle_c.json` but had never
needed to patch `_CATALOGUE_PATH`, because until this batch `_CATALOGUE_PATH` WAS the fixture
pointer -- no test ever needed to override it. Fixed by patching `_CATALOGUE_PATH` alongside
`_BUNDLE_PATH` in the same fixture (both `c_session_service` and `task_service` modules), paired
with `test_catalogue_c.md` -- verified its checksum (`55709112...`) matches exactly what
`all_usable_for_tests_bundle_c.json` already declared. No test assertion, expected value, or
template expectation was changed; 11 additive lines total.

Final state, rebuilt container: **650 passed, 1 failed, 76 skipped** -- the failing node id is
exactly and only `tests/test_auth.py::test_invalid_tokens_fail_closed[expired]`, the pinned Step 0
baseline, unchanged. Verified twice more after the schema/note addition above; identical both
times.

### Noted for Step 4, not resolved now

The three bundle-data families in the new bundle carry per-field `status: "APPROVED"` but
`parameter_source_status: "TEST_FIXTURE_ONLY"` at the block level. Nothing gates on that field for
these three families (bundle-data families are gated per-field, not by `parameter_source_status`),
so it is not why anything currently passes or fails -- but a bundle stamped `APPROVED` whose
config blocks still read `TEST_FIXTURE_ONLY` is internally inconsistent and could be resolved the
wrong way by a later reader. Owner asked for a proposal at Step 4 planning, not a change now.

## 2026-08-26 -- CONNECT Step 4: the probes replaced, the two adapter methods, the import-guard fix, and two authorized test inversions

The largest code change in the CONNECT work order, previously undocumented here -- written up now
under owner instruction, since the Component_C_Frontend/ documents are not in git and this file is
the only durable copy.

**Generation.** `PRODUCTION_GENERATION_CONFIG_PROBE` (deliberately empty, `per_template={}`,
always-refused) replaced with `PRODUCTION_GENERATION_CONFIG`: a real, populated `GenerationConfig`
covering all 30 templates, tagged `APPROVED_FOR_PROVISIONAL_IMPLEMENTATION` under
`APPROVAL-2026-08-26-seven-families.md` Family 4. Template-id coverage verified 1:1 against the
vendored real catalogue -- no missing id either direction, checked, not assumed.

**The route it took to get there.** A first attempt read
`component_c_generator.generation_config.DEFAULT_TEMPLATE_GENERATION_PARAMS` directly in
`task_service.py` and tripped `test_component_c_generator_full_dotted_path_enforcement`
(`test_be2_architecture_guards.py:504`) -- a real, correctly-firing guard restricting
`component_c_generator` as an import root to `app/infrastructure/live_engine_c/adapter.py` alone.
Per supervisor ruling, the guard was not exempted; two new adapter methods were added instead --
`LiveEngineCAdapter.production_generation_params_by_template()` and
`.production_generation_config_version()` -- the same shape `supported_template_ids()` already
uses to expose package data to the application layer. `task_service.py` no longer imports
`component_c_generator` at all; the guard now passes because the violation is gone, not because it
was weakened. A full sweep of every other guard in `test_be2_architecture_guards.py` (not just the
one the docstring pointed at, a miss from the first pass, corrected before implementing) found
nothing else implicated by this step's changes.

**Policy.** `PRODUCTION_POLICY_CONFIG_PROBE` (deliberately implausible, edge-pinned values, a
supervisor ruling preserved verbatim in the code comment rather than deleted) replaced with
`PRODUCTION_POLICY_CONFIG`: the real `default_policy_config()` values (0.80/1.30/0.30/0.40/3/0.60,
`config_version: "c4.1-policy-1.0.0"`), hardcoded as literals (never calling the factory, S8-a's
guard unchanged), under Family 5. Both ordering constraints `CPolicyConfig`'s own model_validator
enforces checked by hand against the real values (0.40 < 0.80; 0.30 < 0.60 -- both hold).

**Scaffold.** Status only, as planned -- `PRODUCTION_SCAFFOLD_CONFIG_PROBE` renamed to
`PRODUCTION_SCAFFOLD_CONFIG`; its four numeric fields already matched `default_scaffold_config()`
and were not touched.

**The provenance question.** `_NOT_LIVE_PARAMETER_SOURCE_STATUS` renamed in place to
`_APPROVED_CODE_GATED_PARAMETER_SOURCE_STATUS` (value changed to
`APPROVED_FOR_PROVISIONAL_IMPLEMENTATION`), kept as a hardcoded constant rather than moved into the
bundle -- the bundle schema carries no blocks for the four code-gated families at all, and building
them would collapse two deliberately distinct gate mechanisms (per-field bundle-data whitelist vs.
code-gated status check) into one, a redesign this step was not authorized to make. Written up as
its own architectural question in `Component_C_Frontend/ESCALATIONS.md`, no recommendation.

**TWO AUTHORIZED TEST INVERSIONS, under supervisor ruling, the one exception to "change no
assertion" this work order grants, and only for these two:**

1. `tests/test_batch2_adaptation_live_caller.py::test_production_policy_config_probe_does_not_mirror_the_real_defaults`
   -- renamed to `test_production_policy_config_matches_the_approved_real_defaults`. Its old
   premise (the probe must NOT resemble a real calibration) was a tripwire against a SILENT
   promotion; Step 4's promotion is authorized and disclosed, not silent, so the tripwire is
   inverted rather than retired: it now asserts the values DO match `default_policy_config()`,
   `config_version` IS `"c4.1-policy-1.0.0"`, and `parameter_source_status` is the approved
   literal, never `TEST_FIXTURE_ONLY` -- it still fires red on either an invented-value regression
   or a status promoted ahead of real values.
2. `tests/test_c5_task_serve_and_evaluate.py::test_p6_next_task_real_http_route_refuses_because_no_governed_generation_config_exists`
   -- renamed to
   `test_p6_next_task_real_http_route_serves_a_real_catalogue_task_with_no_leaked_answer`. Its old
   premise (the real HTTP route always refuses) was retired BY NAME by this same step. Inverted to
   assert, at the same real HTTP boundary: 201 not 409; the served template id is a real member of
   the catalogue (membership check, never a hardcoded id); the response key set is exactly
   `CNextTaskResponse`'s declared set; and no answer-bearing value leaks -- checked
   `test_s5_full_30_template_leak_loop`'s own way (leaf-value comparison excluding
   known-public-collision fields), not a naive substring scan, after a first attempt using one
   false-positived on `C-CC-03`'s own legitimately-public `set_size` value colliding with its
   secret answer -- caught and fixed before reporting, not left in.

Both authorities: supervisor ruling, CONNECT Step 4, both individually granted, both recorded in
each test's own updated docstring naming the old premise, why it retired, and what the test now
protects.

Full backend suite after this step: pinned baseline held exactly
(`tests/test_auth.py::test_invalid_tokens_fail_closed[expired]`, the only failure, predicted).

## 2026-08-26 -- CONNECT Step 6: the bundle registered, then found missing, then the mechanism

`backend/scripts/register_c_runtime_bundle.py` written -- importable core / side-effects-under-
`__main__` shape (mirrors `generate_c_template_registry.py`); idempotent (re-run with an unchanged
manifest is a no-op, same `c_runtime_bundle_record_id`); refuses loudly, never silently overwrites,
if a `bundle_version` is already registered with a manifest_checksum that disagrees with the file
on disk (`BundleRegistrationConflictError`) -- proved with a deliberately modified copy of the
manifest, confirmed the real row was untouched by the refused attempt. `manifest_checksum` computed
via `hashlib.sha256(path.read_bytes()).hexdigest()`, the same method every other artifact checksum
in this codebase already uses. Run as `python -m scripts.register_c_runtime_bundle`, never
`python scripts/...`.

Precedent correction, recorded in the script's own docstring: the work order named
`scripts/dev_fixture_learner.py` as this script's "DB-writing precedent." That file's own docstring
states the opposite -- "HTTP-DRIVEN, ZERO DIRECT DATABASE WRITES" -- and a dedicated test asserts it
never imports a SQL toolkit. No script anywhere in `scripts/` wrote to the database directly before
this one; only `generate_c_template_registry.py`'s importable-core/`__main__`-only shape was
actually followed.

Registered, then exercised the real HTTP route end to end for the first time in this project's
history: `POST /api/v1/c/sessions` -> 201 (`c_session_id b6fc81cf-...`, state active, session_mode
c_only, grade 2); `POST .../tasks/next` -> 201 (`C-CC-02`, `C-GF-01`, counting, difficulty 1,
scaffold_state C0, `prompt_text` "Put this many objects in the box."). Method: `TestClient` against
the fully-wired `app` with only the `get_authenticated_principal` dependency overridden -- the same
mechanism this suite already treats as "the real HTTP boundary" throughout `test_c5`/`test_c6a`/
etc.; not a separate network round-trip against the live `uvicorn` process with a real Supabase JWT
-- that is what Step 8's browser walk is for. `C-CC-02` has a registered frontend archetype
(grouped with `C-CC-01`), not one of the three held templates. Worth carrying into Step 8: this is
exactly the template `ESCALATIONS.md` §5 already names as having deictic wording -- the live
response shows `prompt_payload.target_n: 2` present and not woven into `prompt_text`. Not new, not
this step's to fix; now reachable by an actual first task rather than theoretical.

Full backend suite re-run after registration: 651 passed, 1 failed (the pinned
`test_auth.py::test_invalid_tokens_fail_closed[expired]`), 76 skipped -- reported and predicted
correctly.

**Then the owner queried the database directly and found zero rows for `bundle_version =
'c-approved-1.0'`.** The suite's own green result said nothing about it -- no test in the suite
reads `c_runtime_bundle_records`' contents, so nothing could have caught this from inside the
suite.

**Root cause, first reported wrong, then corrected under owner challenge -- the correction matters
as much as the finding.** First pass claimed "the ONLY such downgrade anywhere in the suite... one
hit" against a grep the owner had not seen the output of. The owner ran the same grep and got six:

    grep -rn 'alembic("downgrade"' tests/*.py
    tests/test_be2_persistence.py:148          downgrade 20260722_0001
    tests/test_be4a_opportunity_persistence.py:123   downgrade 20260723_0001
    tests/test_be4b_adaptive_selection.py:170        downgrade 20260727_0001
    tests/test_be4c_attempt_submission.py:232        downgrade 20260727_0002
    tests/test_be4d_hint_events.py:234               downgrade 20260728_0001
    tests/test_be4e_session_completion.py:228        downgrade 20260728_0002

Re-run and confirmed directly, not taken on the owner's word: six matches. Every backend phase has
its own migration-reversibility test. Checked against `migrations/versions/20260816_0001_c2_
runtime_bundle_record.py` (the migration that creates `c_runtime_bundle_records`): all six
downgrade targets (dated 20260722 through 20260728) predate it, so all six -- not five, not one --
drop the table on the way down and recreate it empty on the way back up. This is systemic to how
the migration suite verifies reversibility, not incidental to one test's collection-order position.
Any registered bundle row does not survive a full suite run, regardless of when it was registered
or which of the six tests happens to run "first" among them. The 49 rows the owner originally found
were every one a `test-<uuid>`/`DRAFT`/`UNRESOLVED` fixture row written by a test that ran later
than all six downgrade/upgrade tests in pytest's deterministic (no randomization plugin configured)
collection order.

**The miss itself, recorded because it is the second of its kind this work order (the first was
the Step 4 architecture-guard sweep):** a grep was run against a narrower scope than the claim made
about its result, and the narrow result was reported as a global one -- "the only," "one hit" --
without showing the command or its raw output. Both misses share the same shape: a negative claim
("nothing else references this," "only one test does this") asserted from a search that had not
actually covered what the claim implied. Standing correction, applying from here forward: a
negative result gets the command and its raw output shown, not just the conclusion.

**Consequence, written down here and in the script's own docstring so it is discoverable rather
than only known:** register this bundle AFTER the last full backend suite run intended before
relying on a live session, never before it. A full `pytest -q` run silently un-registers it with no
failing test to say so. Re-registered; verified this time with a direct SQL query against the real
`db` service (`select ... where bundle_version = 'c-approved-1.0'` -- 1 row, matching checksum,
`APPROVED`/`PUBLISHED`), not the script's own printed output. Re-ran both live HTTP calls: 201/201
again (`c_session_id 9c7608d4-...`; task `C-JB-03`, addition, `prompt_text` "Add the two numbers.").

**`--check` mode, built per owner ruling:** read-only, shares `_lookup` (checksum + query) with the
write path so the two can never independently drift on "does this match" -- three states
(`NOT_REGISTERED`/`MATCHING`/`DISAGREEING`), distinct exit codes (1/0/2), `DISAGREEING` reported as
loud as the write path's own `BundleRegistrationConflictError`. All three states demonstrated with
raw output and exit codes: `MATCHING` against the real registered bundle (exit 0); `NOT_REGISTERED`
against a manifest with a never-registered `bundle_version` (exit 1); `DISAGREEING` against the
same modified-content, same-`bundle_version` file the write-path refusal was proved against earlier
(exit 2). Confirmed by direct SQL query after the `DISAGREEING` check that it wrote nothing -- same
row id, same checksum, unchanged.

Second instance this work order of a step reporting green while the artifact it was meant to
produce was absent -- the first was the .gitignore'd catalogue (CONNECT Steps 2/3). Both invisible
to their respective test suites for the same reason: the suite exercises code; neither artifact is
code. Carried into Step 8 planning, where most of what is being verified is also not code.

## 2026-08-26 -- CONNECT Step 7: the frontend cut over

Small, stayed small, as the work order asked. `python -m scripts.register_c_runtime_bundle --check`
run first (MATCHING, exit 0) to establish the habit before touching anything, per supervisor
instruction -- every step touching the live app depends on that row from here on.

`frontend/.env.local`: the five `EXPO_PUBLIC_COMPONENT_C_DEV_FIXTURE*` vars removed.
`EXPO_PUBLIC_SUPABASE_URL`, `EXPO_PUBLIC_SUPABASE_PUBLISHABLE_KEY`, `EXPO_PUBLIC_API_BASE_URL`,
`EXPO_PUBLIC_APP_ENV` untouched, same order. This file is gitignored (`.env.local`), so the change
never shows in `git status` -- recorded here for exactly that reason, since it is otherwise
invisible to anyone reading the tree.

No frontend code changed. The fixture code (`component-c-api.ts`'s fixture branch,
`dev-fixture-exemplars.ts`) and all four `src/api/__tests__/c-dev-fixture-*.test.ts` files left in
place, per instruction -- they remain the only coverage of that branch.

Pre-flight check, done before removing the vars: grepped every reference to the five var names
across the whole frontend tree (six files total -- the two real source files plus the four
fixture test files, confirmed exhaustively, no others). Each of the four test files saves the
ambient value (including `undefined`), overwrites it with its own explicit value, and restores the
original in an `afterEach` -- none of them reads the ambient `.env.local` value as an input to what
they assert. Predicted the reconciled count would not move.

Gate: `npx tsc --noEmit` -- exit 0. `npm run test:contract` -- **1324 tests, 1324 pass, 0 fail** --
exactly the predicted, reconciled count, unmoved. `npx expo export --platform ios` -- succeeded,
`dist/` removed after.

## 2026-08-26 -- CONNECT Step 8 (in progress): the stale-container trap recurs, and a real validator defect found live, by a real submission, on a real browser walk

Two findings during the browser-driven verification walk, neither from the automated backend-only
rehearsal -- both from the owner actually playing the app.

### Finding 1: the running api-1 container was serving a stale image, again

`docker inspect upadya-be1-api-1` showed the long-running service container (`Up 4 hours`, created
2026-08-25 23:12) was still running image `sha256:4e45af0f9b2d...` -- built well before today's
CONNECT Steps 3-6 (bundle/catalogue repointing, the real probes, attempt_number, bundle
registration). `docker compose build api` during those steps updated the `upadya-backend:be1-batch3`
image tag's underlying layers, but never restarted the already-running container to pick it up --
`docker compose build` does not recreate a running service on its own. The owner's browser had been
talking to this stale process the entire time, producing a genuine `409 Conflict` on
`POST /api/v1/c/sessions` (one of the seven family gates almost certainly still pointed at the old,
pre-Step-3 bundle path). Root-caused by comparing `docker inspect`'s image id against
`docker images upadya-backend:be1-batch3`'s latest build, not guessed. Fixed with
`docker compose up -d --force-recreate api`; confirmed healthy and running the current image
immediately after; the owner's next attempt through the browser succeeded. Same class of trap
HANDOVER.md §6.1 already names for `docker compose run`, recurring here against the persistent
service container instead -- worth widening that section's own wording to cover both.

### Finding 2: `list[str]` action-space fields are unconditionally rejected -- a real, live defect

While playing `C-CC-01` ("Count and Collect"), the owner submitted a genuinely correct answer
(`selected_object_ids: ["obj-0","obj-1","obj-2"]`, `submitted_total: 3`, matching the task's own
`correct_answer_payload` exactly -- `expected_total: 3`, `valid_object_ids` the same three ids) and
got a real `422 ACTION_PAYLOAD_REJECTED`, `details: [{"location": ["selected_object_ids"],
"type": "type_mismatch"}]`.

Root cause, reproduced directly against the real validator, not guessed:
`app/domain/live_engine_c/action_payload_validation.py`'s `_value_matches_declared_type` has
branches for `int`, `bool`, `number`, pipe-string enums, and `list[X]` (which recurses into
`_value_matches_declared_type(inner_type, element)` for each element) -- but **no branch for bare
`"str"`**. For `list[str]`, every element's inner check falls through to the function's own
documented fail-closed default (`return False`, "Unrecognized declaration"). Confirmed directly:

    validate_action_payload(
        {'submitted_total': 'int', 'selected_object_ids': 'list[str]'},
        {'selected_object_ids': ['obj-0', 'obj-1', 'obj-2'], 'submitted_total': 3},
    )
    -> ActionPayloadValidationError: ((('selected_object_ids',), 'type_mismatch'),)

**Every `list[str]` field is unconditionally rejected, for any content, always** -- not a
correctness question (the evaluator is never reached; this is the structural gate ahead of it).

**Why the existing suite never caught it:** the one positive-control test for this validator,
`test_c12_positive_control_valid_payload_reaches_evaluate`
(`tests/test_c5_task_serve_and_evaluate.py:789-799`), builds its payload with
`if declared_type.startswith("list["): return []` -- an EMPTY list for every list-typed field.
`all(...)` over an empty list is vacuously true, so the inner per-element type check
(`_value_matches_declared_type("str", element)`) was never actually exercised by the only test
positioned to catch it. The gap in the test is what let the gap in the validator ship -- the same
shape as the C-BT-04/C-SF-01 answer-key naming gaps found while building the held-template walk
script, and the same shape the module's OWN docstring warns about for a genuinely new type-string
vocabulary ("this will surface as a loud rejection during that phase's own testing, not a silent
gap") -- except it was not caught during any phase's testing, because the one test built to catch
it was itself built with a value that could never trigger the check.

**Affected templates, checked against all 30 templates' `valid_action_space` declarations (pulled
directly from `component_c_generator.tasks.registry` while building the held-template walk
script's answer-key overrides):** exactly two use `list[str]` -- `C-CC-01` (`selected_object_ids`)
and `C-CC-02` (`placed_object_ids` -- the same template already flagged for the deictic
`target_n`/`prompt_text` finding, ESCALATIONS.md §5). No other template's `list[...]` field uses
anything but `list[int]`, which the validator handles correctly.

**Consequence:** both templates are currently unplayable for any submission that selects at least
one object -- the normal path, not an edge case. Neither template is one of the three held ids;
both are supposed to be fully live and reachable today.

Reported and held for owner ruling before fixing, per standing discipline -- this is exactly the
class of defect a live browser walk exists to catch that the test suite's own construction missed,
found live, by a real correct submission, not by inspection.

**RULED: fix now, not held** -- two of thirty templates unplayable, one (`C-CC-02`) the first task
the live route ever served, `C-CC-01` sitting in the exact grade-2 `number_sense` pool the held-
template walk needs. Continuing the walk around it would have corrupted the evidence for
conditions 3, 5, and 6 (every draw of either template reading as a spurious wrong-answer failure).

**Fix, exactly as ruled, nothing else touched:** one new branch added to
`action_payload_validation.py`'s `_value_matches_declared_type` --
`if declared_type == "str": return isinstance(value, str)`. No other type touched.

**The fixture that hid it, fixed too:** `test_c5_task_serve_and_evaluate.py`'s
`test_c12_positive_control_valid_payload_reaches_evaluate::valid_value` no longer returns `[]` for
a `list[...]` declaration -- it now returns `[valid_value(inner_type)]`, a real, non-empty element
recursed through the same function, so the per-element check is actually exercised rather than
vacuously passed.

**New test, exhaustive, negative-claim rule applied (command and raw output, not the
conclusion):** `test_c12_list_str_accepted_and_negative_controls_still_fire`, added directly above
the positive control it corrects. Enumerated every declared type string that actually appears in
`contract/c-template-registry.json` first, not assumed:

    docker compose run --rm --no-deps api python -c "..." (types = set of every valid_action_space value)
    <|>|=
    bool
    int
    left|right|equal
    list[int]
    list[str]
    number
    same|changed

-- exactly the eight types the owner named. All eight asserted both ways (one valid instance, one
invalid instance) in the new test, plus the two owner-specified negative controls
(`list[str]` containing a non-string element; `list[int]` containing a string element) proving the
fix did not convert either fail-closed default into fail-open. Full run, raw:

    docker compose run --rm --no-deps api python -m pytest -q tests/test_c5_task_serve_and_evaluate.py -k "c12" -v
    collected 17 items / 11 deselected / 6 selected
    tests/test_c5_task_serve_and_evaluate.py ......                          [100%]
    6 passed, 11 deselected, 1 warning in 7.32s

Then reproduced the ORIGINAL real failing payload directly, not a synthetic stand-in:

    validate_action_payload(
        {'submitted_total': 'int', 'selected_object_ids': 'list[str]'},
        {'selected_object_ids': ['obj-0', 'obj-1', 'obj-2'], 'submitted_total': 3},
    )
    -> VALIDATION PASSED

**Frontend checked, per owner instruction, before declaring this closed:** `field-kinds.ts`'s own
`isValidForKind` for `id-set-collection` was already correct
(`Array.isArray(value) && value.every((element) => typeof element === 'string')`,
`field-kinds.ts:95-96`) -- no equivalent bug on the frontend side. Its own test
(`c-archetype-resolution.test.ts`) does NOT share the backend fixture's vacuous-empty-list blind
spot: `sampleValueFor`'s `id-set-collection` case already returns a real, non-empty
`['obj-1', 'obj-2']` (line 49-50), and a dedicated negative control already exists
(`isValidForKind(binding, ['a', 1])` -> `false`, line 154). Nothing to fix on the frontend; the
defect was backend-only.

**The asymmetry itself, worth more than the one-line fix (owner's own framing, on independent
verification of the frontend claim above):** the frontend's positive controls cover BOTH shapes --
`['obj-0','obj-1']` / `['obj-0','obj-1','obj-2']` (non-empty, real strings) AND, deliberately, an
empty-list case at `c-object-set-action-key-set-proof.test.ts:34` ("an empty selected_object_ids
list still encodes -- the client never enforces a minimum selection"). The backend's positive
control covered ONLY the empty case -- never the non-empty one. Both suites were green for the
entire life of this code; both sides disagreed about what a real `list[str]` submission looks like
for that whole time; and neither suite could see it, because neither side's test ever asked the
other side's actual shape. The defect was not the missing branch -- anyone could have written that
once shown the gap. The defect was that the two suites tested complementary halves of the same
question and neither one covered the half the other side actually exercises in production.

No `ESCALATIONS.md` entry -- ruled unnecessary: a straightforward code defect with an obvious
correct fix and no open question for governance/pedagogy/science does not belong in a document
whose value is that everything in it genuinely needs an owner's ruling. This entry, closed in
place, is the sufficient and correct record.

Full backend suite re-run after the fix -- see this entry's own final section below for the raw
failing-node-id list.

### Held-template reachability -- backend-only script, REACHABILITY EVIDENCE ONLY, explicitly NOT held-template verification

Before the browser walk, a scripted rehearsal (`TestClient` against the real, fully-wired `app`,
real HTTP calls, a throwaway seeded learner -- never the owner's own account) drove a grade-3
`c_only` session forward via real `POST .../tasks/next` + `POST .../tasks/{id}/actions` calls,
answering correctly each time to advance, watching each response's `game_task_template_id`.
`C-SF-02` (p=1/21) observed at advance 16; `C-TC-02` (p=1/14) observed at advance 29 -- both well
inside the 62-advance, 95%-confidence ceiling computed for this pair.

**What this proves:** the backend's real adaptive selector genuinely reaches both held templates
in ordinary play, at rates consistent with the computed probabilities -- retiring the reachability
question outright.

**What this does NOT prove, stated explicitly per owner instruction, because it would be easy to
blur later:** conditions 2 and 4 are claims about what the FRONTEND renders when a held template
arrives -- the fail-closed frame, never a usable surface. A script hitting the API directly never
loads `planTask`, never calls `resolveArchetypeSurface`, never renders anything at all. This
rehearsal is backend-side reachability evidence ONLY. It does not, and cannot, stand in for the
browser walk that conditions 2 and 4 actually require. That evidence is recorded separately below,
paired with the response body at the moment each screenshot was taken.

### Step 8 evidence table -- browser walk, live, in progress. Slots empty until filled from the actual session; no slot pre-filled with a prediction.

| Condition | What it claims | Evidence | Status |
|---|---|---|---|
| 3/7 -- attempt_number increments | Retry a task with wrong answers; `attempt_number` reads 1,1,2,2,3,3 via DB query, never 1,1,1,1,1,1 | DB-CONFIRMED (not yet screenshot-paired): two retried instances in the owner's grade-2 session, `f68c716d-...` (C-BT-01) and `c951b2d7-...` (C-NP-01), both show `answer_submitted`/`answer_evaluated` at `attempt_number` 1 then 2 (never 1,1) -- raw `c_gameplay_events` query, task_index 2 and 3 | CONFIRMED (DB) |
| 5 -- retry returns to same task, empty surface | Wrong answer -> feedback -> "Try again" -> surface empty, not stale | Owner reports a deliberate wrong answer worked as expected; DB confirms the retry cycle happened (attempt 1 -> 2 on both instances above) -- screenshot sequence of the empty-surface behavior itself still pending | DB-CONFIRMED; screenshot PENDING |
| 6 -- scaffold_level escalates, backend-controlled | Repeated wrong answers on one task; `scaffold_state` visibly changes, matches response body | DB-CONFIRMED: `c_scaffold_events` for both retried instances above shows `scaffold_level: C1`, `event_type: shown`, `consecutive_incorrect_current_task: 1` -- response-body pairing still pending | DB-CONFIRMED; response-body pairing PENDING |
| 1 -- frontend never sends template/family id, selection varies | Network tab across several tasks: no template/family field ever sent; ids vary | Session so far: C-TC-01, C-BT-01, C-NP-01, C-TC-03, C-TC-02 -- five distinct templates across five draws, confirming variance; Network-tab confirmation of no template/family field sent still pending | Variance CONFIRMED (DB); Network tab PENDING |
| 2/4 -- C-SF-02 fail-closed | Held template arrives; fail-closed frame renders, never a usable surface | Not yet reached -- requires a Grade-3 session | PENDING |
| 2/4 -- C-TC-02 fail-closed | Same | **CONFIRMED live.** Owner hit the fail-closed frame in the grade-2 session; support code `cc01411d-2ce0-4874-8515-542a56579ec5` resolved (by `request_id`, not instance id) to `c_task_instance_id 38ad214f-...`, template `C-TC-02`, family `C-GF-06`, skill subtraction, difficulty 1, task_index **5** -- self-pairing: the response the frame is unattributable without is the same response this lookup found | CONFIRMED |
| 2/4 -- C-CC-04 fail-closed | Same (grade-2 session) | Not yet drawn in this session (5 draws so far, none C-CC-04) | PENDING |

**Supplementary, not one of the five conditions but flagged by the owner to look at while live:**

| Item | What to look at | Evidence | Status |
|---|---|---|---|
| C-CC-01 first real completion | First-ever genuine end-to-end pass through object-set-action, now that the validator fix is live | *(screenshot, pending)* | PENDING |
| C-CC-02 first real completion | Same | *(screenshot, pending)* | PENDING |
| C-CC-02 deictic wording | `prompt_payload.target_n` present, absent from `prompt_text` ("Put this many objects in the box.") -- to see, not to fix | *(screenshot, pending)* | PENDING |
| Mid-task refresh | Refresh the page mid-task (real children will do this by accident on their first session). Tests ESCALATIONS.md §7 (abandoned-instance) directly -- what does the app show, and does `next_task` serve a fresh task silently or surface anything about the abandoned one? | Owner reports refresh worked -- first live observation of the resume-instead-of-mint fix outside a synthetic test. Screenshot + paired response body still pending for the durable record | OBSERVED (verbal); screenshot PENDING |

**Advance log (browser session `26ff52bb-e143-48cf-a341-63e2f398d5f8`, grade 2, running count, filled in as reported):**

| task_index | Template | Notes |
|---|---|---|
| 1 | C-TC-01 | Completed correct, attempt 1 |
| 2 | C-BT-01 | Wrong then correct -- attempt_number 1,2 confirmed; scaffold C0->C1 confirmed |
| 3 | C-NP-01 | Wrong then correct -- attempt_number 1,2 confirmed; scaffold C0->C1 confirmed |
| 4 | C-TC-03 | Completed correct, attempt 1 |
| 5 | C-TC-02 | **HELD -- fail-closed frame confirmed live** (support code = request_id `cc01411d-...`) |

## 2026-08-27 -- NOT a CONNECT step: the entire test suite shares the dev database, and one test cycle wipes it completely

Traced from a real symptom the owner reported: a real onboarding account
(`yassdevnew@gmail.com`), previously assigned to a classroom, no longer had that assignment after
"the server was restarted." The owner's own working theory was a recent, uncommitted frontend
change (`secure-storage.ts`, persisting the web session in `localStorage` in development so a page
refresh doesn't sign the developer out). That theory was checked first and ruled out:
`auth-context.tsx:139`'s `authorizeSession` calls the backend live on every load
(`getAuthorizedLearner`) -- classroom membership is never cached client-side in any form the
persisted session could make stale. The persisted session affects only whether the browser
remembers a JWT across a refresh; it cannot be the cause of a stale classroom answer, because
there is no classroom answer read from anywhere but a live query.

**The real cause, verified directly, not inferred:**

`tests/test_be2_persistence.py:148` downgrades the schema to migration `20260722_0001` --
`empty_infrastructure_baseline`, confirmed by reading the migration file directly: its `upgrade()`
creates nothing. Every real table in this project -- `app_user` (created at `0004`), `classroom`
and `classroom_membership` (`0723_0001`), every Component B table, every Component C table -- is
created strictly AFTER `0001`. So this one test's downgrade-then-reupgrade cycle drops and
recreates the ENTIRE application schema empty. This is the same mechanism CONNECT Step 6 already
found and documented for `c_runtime_bundle_records` specifically -- the blast radius is not one
table, it is every table in the project.

And it does not run against an isolated test database. Checked exhaustively: every one of the 13
test files defining an `isolated_database()` helper (`test_be2_bundle_integrity.py`,
`test_be2_persistence.py`, `test_be4a` through `test_be4f`, `test_c3a`, `test_c3b`, `test_c4`,
`test_c4b`, `test_learner_activation_path.py`) reads `get_settings().database_url` -- the
application's own connection string, not a distinct test database. `app/core/config.py`'s default
(`postgresql://upadya:local-development-only@db:5432/upadya`) and `compose.yaml`'s `DATABASE_URL`
default are identical. There is no `conftest.py` anywhere under `tests/`, no `.env.test`, no
docker-compose test override, no environment-variable seam of any kind separating test runs from
the dev database. Checked for one directly; none exists. This is not a CONNECT-introduced defect --
it appears to be true of this test suite's design from its first migration onward.

**Consequence, stated plainly:** any full `pytest` run against the dev environment -- including
several run during CONNECT itself, and by extension any run before it -- destroys every real
account, every classroom membership, every learner profile, and all Component B/C runtime data in
the shared database, then leaves behind whatever residue that same run's own fixtures wrote (the
`c_runtime_bundle_records` table alone was found holding 49 `test-<uuid>` rows earlier in CONNECT).
`yassdevnew@gmail.com`'s lost classroom assignment is consistent with this, not with the auth
change.

**Not fixed this entry.** This is materially larger in scope than anything CONNECT's seven-family
ruling covers, and deserves its own remediation plan rather than a fix folded into an unrelated
work order. Options for a real fix, not evaluated further here: point test runs at a distinct
`DATABASE_URL` (same Postgres server, a separate database name -- since `get_settings()` already
just reads an env var, this may need zero Python changes) versus something more invasive; either
way, the six migration-reversibility tests themselves are proving something real (migrations
reverse cleanly) and should not be altered or removed -- the defect is which database they prove it
against, not that they exist.

**Operational note for anyone running this suite before this is fixed:** a full `pytest` run
against the dev environment will destroy any real account or classroom data currently in it. This
happened multiple times during CONNECT's own verification steps.

**Also done this entry (unrelated, owner-ruled, mechanical):** `frontend/src/auth/secure-storage.ts`
reverted to its exact pre-change (memory-only) content -- confirmed via `git diff` showing zero
difference against `HEAD`. The refresh-persistence tradeoff was reconsidered on its own terms and
ruled out; it was not implicated in the finding above, but held pending a decision per `HANDOVER.md`
§7, and that decision is now made.

Owner: whoever owns test infrastructure / CI for this project. No recommendation between the
options above; no fix attempted.

## 2026-08-27 (same day, follow-up) -- the fix implemented and verified: `api-test` / `upadya_test`

The finding above stopped short of a fix, pending an owner decision on scope. The owner then
reported the actual symptom directly: signing in to a real, previously-onboarded account
(`yassdevnew@gmail.com`) produced a request to join a classroom again, as if the account were new.
Traced to this same defect, not to any login/signup code: `signInWithEmail` (`auth-context.tsx:254`)
only ever calls `auth.signInWithPassword` -- it cannot silently create an account -- and the
onboarding routing (`:158`, `if (!authorizedUser.learnerProfile || !membershipApproved) status =
'onboarding'`) is a live, unconditional read of the backend's current classroom-membership state on
every load; nothing is cached client-side that a session-persistence change could make stale.
Confirmed directly: at the time this was investigated, every row in `app_users` (160 total, "REAL"
and "TEST" `source_class` alike) carried a `created_at_utc` inside the same four-minute window --
proof the table had been wholly repopulated by test runs, not by organic use across sessions. The
account's original membership was destroyed by a full suite run, most likely one of CONNECT's own.

**Fixed.** `backend/compose.yaml` gained a second service, `api-test` -- identical to `api` except
`DATABASE_URL` points at a new, separate database, `upadya_test` (same Postgres server, created once
via `CREATE DATABASE upadya_test OWNER upadya;`). No Python code changed: every `isolated_database()`
helper and Alembic's own `env.py` already read `get_settings().database_url`, which reads
`DATABASE_URL` from the environment, so pointing that one variable elsewhere was sufficient.
`profiles: ["test"]` keeps `api-test` from ever starting under a plain `docker compose up`.

**Verified, not asserted:**
- Ran `test_be2_persistence.py` (the deepest-downgrading reversibility test, to `20260722_0001`,
  before every real table exists) against `api-test`: `3 passed`.
- Queried the DEV database (`upadya`) immediately before and after that run:
  `app_users`/`classrooms`/`classroom_memberships`/`c_runtime_bundle_records` counts were
  **160 / 49 / 25 / 51, bit-for-bit identical, both times.** The dev database was not touched.
- Queried `upadya_test` afterward: it had its own independent rows, created fresh by that same
  test run -- proof the isolation is real in both directions, not merely that the dev DB happened
  to be skipped.
- Ran the FULL backend suite (all 654 non-skipped tests, including all six migration-
  reversibility cycles, not just the one deepest-downgrading test above) against `api-test`:
  `1 failed, 654 passed, 76 skipped` -- the failure is the same pinned `auth.py` leeway
  consequence (`test_invalid_tokens_fail_closed[expired]`), unrelated and unchanged. Re-queried the
  dev database immediately afterward: `160 / 49 / 25 / 51`, bit-for-bit identical to before the run
  and to the single-test check above. The fix holds under the full suite, not only a narrow probe.

**The canonical test invocation is now `docker compose run --rm --no-deps api-test python -m
pytest -q`.** `HANDOVER.md` §6.1 and a new §6.7 record this; the old `--no-deps api` form was left
working deliberately (nothing errors if someone types it from habit) but now runs against the dev
database again, with the same consequence as before. `CONNECT-work-order.md` and
`CONNECT-builder-prompt.md` were given dated correction notes rather than silently rewritten --
those documents' own historical instructions genuinely used `api`, and that is what actually ran.

Not touched, and outside this fix's scope: re-provisioning `yassdevnew@gmail.com`'s classroom
membership itself. That is a one-time data restoration, not a defect; the owner can re-run the
join-code flow for that account whenever convenient.

## 2026-08-27 -- Component B start/resume was live-broken by the same shared-database defect, in a different table

Traced from a real symptom: pressing "Resume Adventure" produced a 409 on `POST
.../opportunities`, reproducibly, for a specific session. Root-caused, not guessed:

`app/application/opportunity_selection.py`'s `resolve_bundle_and_catalogue` raises
`ConflictError` (-> 409) unless the session's pinned `runtime_bundle_record_id` resolves to a
`bundle_version` present in the hardcoded `_ENGINEERING_TEST_BUNDLES` map -- which recognizes
exactly one value, `"be3b-test-fixture-1.0"`. The stuck session's bundle_version was
`bundle-120c8ad3-dc45-4272-be82-dbea6147ef1a` -- a synthetic, test-generated name.

**This is not one bad session -- it was live-blocking every new Component B session.**
`b_runtime_bundle_records` held 16 rows: one real (`be3b-test-fixture-1.0`) and 15 test-residue
rows (`bundle-<uuid>`/`unmapped-bundle-<uuid>`, created in the same few-minute window as the
`app_users`/`classroom_memberships` residue documented in this file's 2026-08-27 entry above --
same defect, different table). 14 of those 15 residue rows carried `approval_status: APPROVED`,
`publication_state: PUBLISHED` -- identical to the real bundle -- and
`RuntimeBundleRecordRepository.find_current_approved_published()` (`app/infrastructure/
repositories.py:63-78`) explicitly tie-breaks on **most recently created**. Since residue rows
were created after the real one, **any session started from this point forward would have been
pinned to a fake bundle and 409ed on its first question** -- confirmed by checking: 14 separate
`b_sessions` rows, all still `state=active`, each referencing a different one of the 15 residue
bundles.

**Fixed, not deleted** -- provenance rows stay, only their eligibility changed:
1. Abandoned all 15 `b_sessions` rows (the originally-reported one plus 14 more) that referenced
   a non-real bundle -- confirmed test churn, not real use (same abandoned-in-bulk judgement as
   the account/classroom residue).
2. `UPDATE b_runtime_bundle_records SET publication_state='DRAFT', approval_status='UNRESOLVED'`
   for every row except `be3b-test-fixture-1.0` -- blocked once by
   `enforce_b_runtime_bundle_integrity()` (a real, correct guard: "runtime bundle referenced by an
   active session must remain eligible") until step 1 completed, which is the right order and
   confirms the guard is doing its job.
3. Verified: exactly one row now satisfies `publication_state='PUBLISHED' AND
   approval_status='APPROVED'`, and zero active sessions reference anything else.

**Not yet done, and worth naming:** this is a data-hygiene fix on the CURRENT shared dev database,
not a schema or code change. It stops the bleeding for existing residue, but does not itself
prevent new residue from appearing -- that prevention is `api-test`/`upadya_test` (this file's
prior 2026-08-27 entry), which should mean tests stop writing here going forward. If this
recurs, the first thing to check is whether some test run still executed against `api` (the dev
DB) rather than `api-test`.

Owner: same as the prior finding -- whoever owns test infrastructure/CI. No code changed; this
entry is a cleanup record, not a fix to review.

## 2026-08-27 -- Production branch cleaned: process docs removed, two spec docs relocated

On the new `Production` branch (cut from `C_backend`), on owner instruction: removed the
process/status documentation that had accumulated at the repo root and stopped being current the
moment it was written (matching this file's own repeated finding about status documents decaying
-- HANDOVER.md's Component C equivalent, §6.5). Removed, not relocated (all tracked, all
superseded by this file and its Component C counterpart):
`Component_B_BE4_Sequencing_Plan.md`, `Component_B_Backend_Overview.md`,
`Component_B_Backend_Work_Order.md`, `Component_B_Measurement_And_Parity_Review.md`,
`Component_B_Build_Structure.html`. Also removed, untracked planning drafts and stray artefacts
that had never been part of any commit: `Component_B_Build_Plan.md`, `Component_B_Item_Review.md`,
`backend/BEplan.md`, `hub.png` (unreferenced, per HANDOVER's own note), `.playwright-mcp/`
(browser-automation logs), and an empty stray directory literally named `backend;C`.

**`backend.md` and `frontend.md` (1585 and 1310 lines) were MOVED, not deleted** -- owner ruling:
these are substantial, still-referenced technical specs (frontend.md's own content was read
directly during this session to resolve a real behaviour question), not stale status documents,
so they do not belong in the same removal bucket as the Component B planning docs above. They now
live one directory up, in `Upadya/` (outside this git repository, exactly where `Upadya/`'s own
non-repo planning documents already live), and remain fully intact there.

**Deliberately kept, checked individually rather than swept up by "remove .md files":**
`buildLog.md`/`buildLog1.md`/`buildLog2.md` (this file and its predecessors -- the durable record
itself, explicit owner instruction); `backend/packaging/component_{b,c}_internal/IMPORT_POLICY.md`
(a real, enforced architecture-boundary rule, not process documentation); `backend/scripts/README.md`
and `backend/migrations/README.md` (functional usage docs for those folders); `frontend/README.md`,
`frontend/CLAUDE.md`, `frontend/AGENTS.md` (the last two are active AI-tool configuration, not
documentation about the product, and `AGENTS.md`'s Expo-v54 instruction is genuinely followed
during this project's own work); `backend/tests/fixtures/runtime_bundle/test_catalogue.md`,
`backend/tests/fixtures/runtime_bundle_c/test_catalogue_c.md`, and
`backend/provenance/R26-IT-138_Component_C_Game_Task_Catalogue_v1.0.md` -- all three are DATA the
test suite and the live Component C bundle actually parse at runtime despite the `.md` extension;
deleting any of them would have broken the test suite or the production gate CONNECT spent seven
steps opening.

Root `README.md` rewritten from a one-line description into a real project README: architecture
overview, the two-component split, how to run backend (docker compose, including the `api-test`
isolation from this file's own prior entry) and frontend (npm/expo), and a pointer to this file and
its predecessor as the durable project history.

Owner: Yasindu. No code changed; this is a documentation/repository-hygiene entry only.

## 2026-08-27 -- README expanded; `requirements.txt` found stale and wrong, not yet removed

Added to `README.md`, on owner instruction: the two `dev_fixture_learner.py` commands (mint-invite,
approve-pending) with the host-not-container / port note already established in this file; a
no-Docker backend setup path (venv, `requirements.lock`, local Postgres, `alembic upgrade head`,
`uvicorn` directly); and Expo SDK version (`~54.0.35`, confirmed from `frontend/package.json`) as
an explicit prerequisite.

**Checked, on request, whether `requirements.txt` and `package.json` are correct before pointing
the README at them.** `package.json` is clean: 31 dependencies, 5 dev dependencies, zero
local/relative/`file:`/`link:` paths -- `npm install` alone is a complete, reproducible setup.

**`requirements.txt` is stale and wrong**, confirmed against what actually ships: it pins
`upadya_component_b_live_engine-0.1.0+be3...`, while `requirements.in`/`requirements.lock` (and
`Dockerfile`'s own `COPY`) pin `+bf5` -- an older engine build. It is missing the Component C
engine wheel (`prabathi_component_c_live_engine...+c3...`) entirely, and missing `alembic`,
`asyncpg`, `sqlalchemy[asyncio]`, and `pyjwt[crypto]` outright -- a install from this file cannot
open a database connection, run a migration, or import Component C's adapter. The README now
points explicitly at `requirements.lock` (hash-verified, matches the Docker image exactly) and
names `requirements.txt` as the one not to use, rather than silently working around it.

**Not removed.** This is a from-scratch abandoned file, not the kind of stale status document the
2026-08-27 cleanup entry above already reasoned through -- flagging rather than deleting, since
removing a dependency manifest is a different class of change than removing a planning document,
and it wasn't asked for. Owner: confirm whether `requirements.txt` should be deleted outright or
regenerated from `requirements.in` to match `requirements.lock`.

## 2026-08-27 -- Component C submit UX: an in-flight gate, and `task_already_terminal` treated as benign

Two frontend-only fixes, raised by the owner after playing a real session against the Supabase-
hosted database. Neither touches the backend; `git diff --stat` over `app/application`,
`app/domain`, `app/api` and `migrations/` is empty for this batch.

### What was actually wrong -- measured, not guessed

Against the hosted database, submitting felt dead for several seconds and then frequently showed
the technical-block screen ("Something changed on our end"). Latency, measured from inside the api
container against both databases in the same run:

| | connect | `select 1` median | min | max |
|---|---:|---:|---:|---:|
| Supabase (`ap-southeast-1`, session pooler) | 1754.4 ms | **203.2 ms** | 156.3 | 334.5 |
| Local Docker Postgres | 41.3 ms | **0.2 ms** | 0.1 | 0.5 |

`submit_action` performs on the order of 15-25 queries (row lock, event count, payload validation,
evaluation, three-to-four event writes, summary derivation, policy decision, scaffold event). At
~200 ms per round trip that is several seconds of an apparently unresponsive SUBMIT, so the child
taps again; the second request is refused by the T1-4 guard with `task_already_terminal`
(`task_service.py:664-666`), a 409, which `classifySessionFailure` routes to the technical-block
screen.

**The data was never corrupted, and the backend was never wrong.** The gameplay tables for that
session were checked directly: 26 events across 6 instances (5 complete x 5 events + 1 offered),
`attempt_number` 1 throughout, five `completed_correct` terminal events, five summaries -- exactly
consistent, with no duplicate writes. The duplicate submissions wrote nothing, which is the guard
working as designed. What was wrong was that a correct backend refusal was being shown to a child
as an application failure.

### Fix 1 -- the submit-in-flight gate

`createSubmitGate()` (`c-session-logic.ts`): a one-slot mutual-exclusion cell, `tryEnter` /
`release` / `isBusy`. `c-session-screen.tsx` holds one per mounted screen in a `useRef` and takes
it in `submitFromSurface` **before the first `await`**, releasing in `finally`.

**It is a ref, not `useState`, and the placement is load-bearing.** `setState` is asynchronous and
batched: two taps dispatched in the same frame both read the pre-update value, both pass a
`if (submitting) return` check, and both submit. A guard taken after any `await` reopens the same
race at the suspension point. A `useState` implementation passes a naive sequential test and fails
the concurrent one, which is why the test drives two overlapping callers rather than two sequential
calls.

A separate `submitting` state drives an overlay inside the task panel (`ActivityIndicator` in the
family accent, over a translucent scrim). The overlay does two jobs: it tells the child the answer
is being processed, and it absorbs taps -- covering the card means no archetype's own SUBMIT is
reachable while a request is out, **without this file reaching into eight surfaces to disable eight
separate buttons**. The gate alone still guarantees single submission if the overlay were removed.

### Fix 2 -- `task_already_terminal` handled as the benign duplicate

`isDuplicateSubmissionConflict(error)` (`c-session-logic.ts`), consulted at exactly one call site:
the catch in `handleSubmit`. On a match the existing `feedback` field is set to
`{ matched: true, scaffoldLevel: prev.task.scaffold_state }` -- the same field, the same
`AnswerFeedbackPanel`, the same child-initiated "Next" to advance. No parallel flow.

**`classifySessionFailure` was NOT widened, deliberately.** Its own header states it reads
`error.kind` and nothing else so that two differently-caused 409s cannot reach the screen
differently; teaching it to sniff envelopes would dismantle the property it exists to guarantee.
The narrowing therefore lives at the call site, and every 409 the predicate does not positively
recognise still falls through to `classifySessionFailure` unchanged. A test asserts that function
still routes *every* 409 -- including this one -- to `technical-block`, so a later "simplification"
of the two into one fails loudly.

**Why the detail is trustworthy here, when the gate refusals' 409s are not:** the unsigned-parameter
and non-active-session refusals raise a BARE `ConflictError` with no details at all
(`task_service.py:375`, `:389`); this one is raised with an explicit structured body,
`[{"location": ["c_task_instance_id"], "type": "task_already_terminal"}]`. The distinction is a
real difference in what the server sends, not an inference from a message string. A test pins the
bare-409 case to `technical-block` precisely so the two never blur.

**The assumption `matched: true` rests on, recorded because it is load-bearing and could silently
break:** `completed_correct` is the ONLY wired terminal reason (Phase 6a T1; the other eight are
explicitly fail-closed and documented as not built in `terminal_event.py`'s own header, T1-1/T1-5).
An instance can therefore only be terminal because the child already answered correctly. **If a
second terminal reason is ever wired, this inference breaks and `isDuplicateSubmissionConflict`'s
call site must be revisited before that lands.**

### Verification

- `npx tsc --noEmit` -- exit 0.
- `npm run test:contract` -- **1341 tests, 1341 pass, 0 fail.**
- **Reconciled by measurement, not by arithmetic on a documented number.** The suite was re-run
  with the two new files removed, giving **1327**; 1327 + 6 (gate) + 8 (duplicate) = 1341.
  `HANDOVER.md`'s long-standing `1324` was stale -- measured at `4916d04`, before the
  sign-in/welcome/adventure-charge batches -- and has been corrected there with a note, since §6.5
  had already warned about exactly this row.
- Backend logic untouched: `git diff --stat` over `app/application`, `app/domain`, `app/api`,
  `migrations/` is empty. `task_already_terminal` is still raised at `task_service.py:665`.
- Fix 1 intact after Fix 2: the gate take/release and the overlay are all still present and
  covered.

### Not done, deliberately

The fail-closed frame's own wording is still engineer-facing ("This one isn't ready" plus a visible
UUID), and the technical-block screen's copy is unchanged. Both remain child-facing copy questions
routed to pedagogical sign-off per `ESCALATIONS.md` section 4, not to whoever is holding the
builder pen. Nothing in this batch changes any wording shown to a child.

## 2026-09-21 -- Play prep card bars now show real BKT mastery, as bar length only (product-owner ruling)

**The ruling.** The Play prep card's seven skill bars were a staged animation to fixed targets
(62/48/55/71/44/37/29) -- a warm-up cue, deliberately not a report, because no B response exposed
mastery. The product owner (Yasindu Kularathne) asked for the bars to reflect the child's actual
values and, on being shown the governance below, ruled: **mastery may be shown to the child as the
length of a bar only -- never as a number, label, percentage, or spoken value.**

**What this crosses, stated plainly.** `provenance/component-b-be2-governance-authorization.json`
carries the blocker "safe-progress and descriptive summary policy", status UNRESOLVED, required
approver "product owner and academic/research approver", permitted behaviour while unresolved:
"Expose no session summary, progress label, mastery, certification, readiness, recommendation, or
provisional scientific result." `app/domain/b_completion.py` cites it as the reason no B DTO
carries `p_l`. This entry records the product owner's side of that two-party approval. **The
academic/research approver's sign-off is NOT on file** as of this entry; the product owner
proceeded knowing that. If that sign-off is later refused, the revert is one route and one prop.

**What it does not cross.** The C-4 boundary (`live_engine_c/mastery_fixture.py`: Component C
must not consume B's estimate as engine input) is untouched -- Component C still receives the
fixture. This is Component B reading its own table for its own learner over its own route. The
BE3c private/public split (no mastery on any task-presentation DTO) is untouched.

**Backend.** New `GET /api/v1/b/learner/skill-states` (`app/api/routes/b_learner.py`,
`app/application/learner_skill_states.py`, `app/domain/b_skill_state.py`): the caller's own
`b_learner_skill_states` rows as `{skill_id, p_l, observation_count}`, sorted by skill_id, learner
role only (teacher 403, unlinked/unknown 404, no token 401). Read-only: a learner with no B
history gets `[]`, and the read never seeds priors (unlike `load_or_init_skill_states`, which is a
session-start side effect). Route added to `EXPECTED_ROUTES`; `contract/openapi.v1.json`
regenerated inside the Docker image (Git Bash, LF), checksum `fe153061...486635` into the meta
file; diff is purely additive (+70/-0). `tests/test_learner_skill_states.py`: 4 tests.

**Frontend.** `src/features/home/skill-bar-fill.ts` is the ONE place a probability becomes a
width, and encodes the two honesty rules: a skill with no row draws empty, and a row with
`observation_count` 0 ALSO draws empty -- that row's `p_l` is the bundle's P(L0) prior seeded at
first session start, not evidence about this child (a Grade 2 learner's "Division" sits at the
prior forever). `play-prep-card.tsx` takes `skillStates`, feeds `fills[skill.key]` to exactly one
place (the animated width), and marks the track `accessible={false}` with no progressbar role and
no `accessibilityValue`, so a screen reader cannot announce the number the child must not get.
`adventure-charge-context.tsx` fetches fresh on every Play press (never cached across presses; a
stale response from a dismissed card is dropped by a request counter), best-effort and independent
of the game prefetch -- "Start Game" never waits on it, and any failure leaves the bars empty.
`tests/prep-card-skill-bar-fill.test.ts` pins the fill rule, the validator bounds, and -- by
source scan -- that the card prints no numeric mastery anywhere.

**Verified.** Backend: `test_be5a_contract_freeze`, `test_be2_architecture_guards`,
`test_c4b_routes_and_bundle_config`, `test_learner_skill_states` -- 80 passed; full suite through
`api-test`: 666 passed, 0 failed, 76 skipped. Frontend: `tsc --noEmit` clean, `test:contract` 1350 passed. Live: the endpoint on
the Supabase-backed API answers 401 unauthenticated. On Supabase today 14 of 144 learners have any
skill-state rows (the rest have never started a B session), so most accounts will see empty bars
until they complete a Component B session -- that is the design working, not a fault.

Owner: Yasindu. Academic/research approver: not recorded.

## 2026-09-27 -- the answering clock now starts at the render, not at selection (owner ruling)

**The problem prefetching exposed.** `timeout_deadline_utc` was fixed in `open_opportunity` as
`now + DEFAULT_TIMEOUT` (5 minutes) at SELECTION. Once Home's hero/resume press and the preparation
screen began prefetching the first question, selection moved to before the child is looking at
anything, so server and network time was being spent from the child's answering budget. Overrunning
it is not cosmetic: no server sweep records timeouts, so one is written only when the client submits
after the deadline, and `attempt_submission.py` then sets `submitted_value = None` and never grades
the answer. A slow prefetch could silently discard a child's first real answer.

**Governance.** `provenance/component-b-closure-decisions.json`'s `timeout policy` entry
(`SEMANTICS_PROVISIONAL_NUMERIC_THRESHOLD_UNRESOLVED`) already rules: *"Infrastructure failure is
never learner failure; numeric server timeout is not approved."* Charging prefetch and network time
to the learner is exactly that failure mode, so this is a correction TOWARD the standing ruling, not
a new policy. **The numeric threshold is untouched and remains unapproved** -- only the moment the
clock starts moves. Owner chose this over simply not enforcing the deadline (the other option put).

**Backend.** New route `POST /api/v1/b/sessions/{session_id}/opportunities/{item_opportunity_id}/presented`
(`app/api/routes/b_session.py`, `app/application/presentation_ack.py`, `app/domain/b_presentation_ack.py`).
No idempotency key and no body, for the same reason `select_opportunity` has neither: the operation
is intrinsically once-only. 200, not 201 -- nothing is created. `open_opportunity` now writes
`presented_at_utc=None` (the column is nullable and had no readers; no migration), keeping the
selection-time deadline only as a fail-safe bound for an opportunity that is never acknowledged.
`OpportunityPersistenceService.anchor_presentation` takes a row lock, returns `(record, anchored)`,
and **anchors once**: the first acknowledgement sets `presented_at_utc = now` and
`timeout_deadline_utc = now + timeout`; every later one is a no-op returning the same deadline, so a
remount, relaunch, retry or deliberate reload can neither extend nor shorten what the child has. A
CLOSED opportunity is 409; another learner's is 404; unauthenticated is 401 and anchors nothing.

**Contract and guards.** Route added to `EXPECTED_ROUTES` plus its own
`AUTHORIZED_B_PRESENTATION_ACK_OPERATIONS` set -- needed because the path contains "session", a
prohibited scientific path term that is exempt only for routes in an authorized set; widening the
term list instead would have weakened the guard for every route. `contract/openapi.v1.json`
regenerated in the Docker image (Git Bash, LF, 0 CR bytes verified), checksum `d0d2c8cf...96d9c1`;
diff purely additive (+154/-0).

**Frontend.** `live-session-screen.tsx` fires the acknowledgement from the `'question'` phase only
-- acknowledging a loading or failed phase would start the clock on something the child cannot see
-- guarded by `ackedOpportunityRef` so a re-render does not re-send, and adopts the returned
deadline in place of the selection-time one. Best-effort and silent: a failure leaves the fail-safe
deadline, which is the pre-route behaviour, so there is nothing to show the child.

**Tests.** `tests/test_presentation_ack.py` (7): selection leaves the question un-presented; the
first acknowledgement moves the deadline LATER and by the governed span; repeats are no-ops that
change neither timestamp; CLOSED is 409; cross-learner is 404 and anchors nothing; unknown ids 404;
unauthenticated 401. Frontend: validator bounds plus a source scan pinning the once-per-opportunity
guard and the deadline adoption. Full suites through `api-test`: backend 681 passed, 0 failed,
76 skipped; frontend `tsc --noEmit` clean and `test:contract` 1365 passed.

Owner: Yasindu. Academic/research approver: not recorded (threshold unchanged, so unaffected).

## 2026-09-28 -- "equally" restored, and a localisation seam for Sinhala

**"equally" put back into B-DIV01.** The 2026-09-27 ESL pass shortened "Share 22 equally between 2"
to "Share 22 between 2", which was a mistake and is now reverted. Equal sharing IS the mathematical
content of that item: without the word, "share 22 between 2" permits 21 and 1 and the question
stops being the question. `prompt_wording.py`'s rule 2 now states the distinction it should have
had from the start -- a word is removed only when it is REGISTER; a word that carries the
mathematics stays even when it is long. "equally" joins "tens", "ones", "hundreds" and "groups" in
the kept vocabulary.

**Why a localisation seam at all.** Asked whether the questions are now suitable for Sri Lankan
children, the honest answer was no -- the English is simpler, which is real, but simpler English is
a MITIGATION and not a solution for children who read Sinhala first. Even "How many do you see?" is
five English words to decode before any mathematics starts. For a study that means to measure
mathematical ability that is a validity problem, not only a usability one: a wrong answer cannot be
read as "could not do the maths" when it may mean "could not read the question". Confirmed by
inspection that the product had NO localisation of any kind before this entry -- no i18n library,
no locale handling, every string hard-coded English, front and back.

**Backend.** New `app/domain/live_engine/locales.py`: a `Locale` of `en`/`si`, `resolve_locale`
(accepts `si`, `si-LK`, and a full `Accept-Language` with quality values; anything unrecognised
resolves to English rather than raising), and `DEFAULT_LOCALE = "en"`. `prompt_wording.py` and
`prompt_instructions.py` gain per-locale tables, and both resolvers FALL BACK PER STRING: a
template with no Sinhala serves its English wording, never a gap, a placeholder or a crash. That
per-string rule is the point -- it lets translations land one reviewed item at a time instead of
needing all 29 before any can ship. The locale is threaded through
`project_task_instance_to_presentation` -> `open_adaptive_opportunity` /
`reissue_presentation_for_open_opportunity` -> `select_next_opportunity`, and the route reads it
from `Accept-Language`: the standard way to say this, CORS-safelisted (so no allow-list change),
and needing no migration or contract field. Contract regenerated in the image (LF, 0 CR bytes
verified), checksum `4a0fa610...f73e`; diff purely additive (+171/-0).

**Frontend.** `src/config/locale.ts` reads `EXPO_PUBLIC_LEARNER_LOCALE` and sends
`Accept-Language` on every request. Sinhala is sent as `si-LK,si;q=0.9,en;q=0.5` so the server can
negotiate down per item rather than being told Sinhala-or-nothing. The app never translates
anything itself -- it says which language it wants and relays what the server sends, exactly as it
never composes a stem itself.

**THE SINHALA STRINGS ARE A FIRST DRAFT AND ARE NOT REVIEWED.** Six stems and three instructions,
written to prove the path end to end by someone who is not a Sinhala-speaking primary teacher. They
are marked as such in both modules, the tables are deliberately PARTIAL, and English is the default
at every level (`DEFAULT_LOCALE`, `DEFAULT_LEARNER_LOCALE`, and an unset env var), so nothing
unreviewed can reach a child by accident. Setting the variable to `si` is a conscious act, which is
what makes the draft testable without shipping it to a classroom.

**Open, and owner's to close:** get the English wording AND the Sinhala in front of a Grade 2
teacher who teaches these children. Specific English strings flagged as doubtful: "Break N into
tens and ones" ("break" everyday means damage), "Pick the right sign" (assumes "sign" and the
meaning of < > =), "Count on N more" (English-medium pedagogical jargon), "Is it the same or
changed?" ("it" has no referent), "Tap N things" ("things" is vague).

**Tests.** `tests/test_locales.py` (19): resolution across real `Accept-Language` values including
a preferred-unsupported-then-supported case; English default; per-string fallback in both
directions; no half-rendered sentence in any locale for any template across 6 seeds; Sinhala tables
are a subset of English and contain no stale template id; Sinhala strings are actually Sinhala
script and keep digits as digits. Frontend: locale defaulting and header negotiation.
Full suites: backend 708 passed, 0 failed, 76 skipped; frontend 1374 contract + 18 render
passed, `tsc --noEmit` clean, lint 0 errors.

Owner: Yasindu. Sinhala wording: NOT reviewed. Academic/research approver: not recorded.

## 2026-09-28 -- Component C: wording simplified for Sinhala-first learners, and the big task card removed

**Wording.** All 30 Component C templates (32 strings, two carry variants) rewritten to the rules
Component B's wording follows, and deliberately to the SAME PHRASES where the question is the same,
so a child moving between the two components meets one vocabulary rather than two: "Which number
shows how many?", "Put the two groups together. How many?", "Take away this many. How many are
left?", "Put these in order. Small to big.", "What comes next?" are now shared across both.

Register words removed: "array", "column", "select", "object", "subtract", "trade", "smallest"/
"largest". "Build the array shown." -> "Make the rows of squares shown."; "Select every object one
time." -> "Tap each thing one time." "Change X into Y" replaces both "trade" (commerce) and "break"
(damage), and since C-BT-03/04 are the same idea in opposite directions they now read as a matched
pair. "equally" KEPT in the sharing items, same ruling as Component B's: it carries the mathematics.

**Artefacts.** `contract/c-prompt-wording.json` regenerated (checksum `a576dd61...ee95f`). The
backend suite then caught a THIRD artefact this touches: the prompt exemplars embed `prompt_text`,
so `contract/c-prompt-exemplars.json` (checksum `a4318795...cae73`) and the frontend's generated
mirror were regenerated too. All generated in the image, LF, 0 CR bytes verified.

**A new guard, and three kinds of fallout it did not cover.** `ESL_BANNED_WORDS` added to
`tests/test_c_prompt_wording_freeze.py`, mirroring Component B's list, plus a per-sentence
nine-word bound; it caught two of this batch's own over-long sentences (C-MCL-03 at 11 words,
C-MCL-04 at 10), both shortened. Separately, twelve existing tests failed, in three classes worth
recording:
  1. The exemplars artefact above.
  2. FOUR negative-control tests went VACUOUS. Each altered a prompt by replacing its last
     character with "?" -- but several new prompts now END in "?", so the "altered" string was
     identical to the original and the control passed while testing nothing. That is precisely the
     failure those controls exist to rule out, happening to them. They now swap the final character
     for a genuinely different one.
  3. Two tests named for a MECHANISM (C-EG-02 variant resolution, C-EG-01 exemplar integrity)
     asserted literal copy, as did two on the backend side. All four now assert the mechanism; the
     copy is pinned once, authoritatively, by the checksummed artefact rather than duplicated as
     literals in four places.

**A mistake worth recording.** The first rewrite used a regex over the wording literal; its
non-greedy span crossed template boundaries and silently dropped 9 of the 30 templates. Caught by
checking the template count against the original, restored from backup (verified zero diff), and
redone as exact per-string replacement with a uniqueness assertion for each. Final diff: a clean
31-for-31 swap, 30 templates intact.

**The task card.** Owner instruction: Component C drew ONE big accent-bordered panel around the
entire task -- exit control, family pill, level chip, question, manipulatives, answer controls and
SUBMIT. That panel is no longer a card (it survives as the layout frame that owns the 90% height
the content spacers are proportioned against and the relative positioning the floating chrome rows
sit in; only border, ground and shadow are gone). In its place, `task-prompt-card.tsx` -- Component
B's `promptCard` reproduced value-for-value -- now wraps the question and its items inside each
archetype surface.

ONE LINE DRAWN CONSISTENTLY ACROSS ALL EIGHT ARCHETYPES: inside the card goes what the child LOOKS
AT (object set, payload tokens, number line, array); outside goes what they ACT ON (option rows,
keypads, steppers, toggles) and SUBMIT. That is the same line Component B draws, and it is what
makes the card mean "here is the question" rather than "here is the task". For `object-set-action`
and `ordered-value-sequence` the manipulative IS the answer surface, so those cards hold the
question alone. Two surfaces already wrapped exactly the right content in a `promptBlock`, so they
take the card's exported style rather than gaining a component around JSX whose closing tag was
ambiguous -- same card, defined once.

**Verified.** Backend 711 passed, 0 failed, 76 skipped. Frontend `tsc --noEmit` clean, lint 0
errors, 1381 contract + 21 render passed.

Owner: Yasindu. Wording: CANDIDATE, not owner-reviewed and not reviewed by a Sinhala-speaking
primary teacher. Component C has no Sinhala table yet -- the locale seam exists on the B side only.

## 2026-09-28 (later) -- the big card restored with a shared gradient, and unplayable templates excluded at selection

**The card, reversed back.** The Component C task panel removed earlier the same day is restored:
accent border, warm ground, shadow. What survives from the removal is the inner card --
`TaskPromptCard` in each archetype surface -- so the two components now nest identically: outer
task panel, inner question card, answer controls on the panel's ground.

**The gradient, shared rather than copied.** Component C's task screen now sits on the same slowly
rotating wash Component B does. `RotatingGradientBackground` (plus `withAlpha` and the shared
`GRADIENT_WASH_ALPHA`) was EXTRACTED from live-session-screen.tsx into
`features/session/rotating-gradient-background.tsx` rather than reproduced. Component C's standing
convention is to reproduce B's shapes rather than import private symbols, and that convention is
right for styles -- but a 45-second rotation, an easing, and the diagonal-sizing trick (a square
sized to the screen's diagonal, so a rotating gradient never sweeps its own corners into view)
copied into a second file is a pair that drifts. Two screens that must look IDENTICAL share the
component; two screens that merely rhyme keep their own styles. C re-picks two of the five
game-type colours per task, always excluding that task's own family accent so the panel's border
never blends into the background behind it. `gradientColors` is computed ABOVE the screen's five
early returns because `useMemo` is a Hook -- the same constraint, and the same note, B carries.

**Templates the app cannot draw are no longer served.** Owner instruction: a task with no
renderable surface must not reach a child as "This one isn't ready" mid-game; reject it at
selection and pick another.

MEASURED, NOT ASSUMED. All 150 frozen exemplars (30 templates x 5 difficulty levels) were run
through the app's own pure resolvers. Exactly three never render: `C-TC-02` (value-report refuses),
`C-CC-04` (option-select refuses), and `C-SF-02` -- whose refusal is PERMANENT by the 2026-08-26
ruling, because the template declares no bin-count payload key, so the number of groups IS the
answer and no fixed-slot scene can show the bins without showing it. Two of the three refusals
protect the answer; the app is not failing, it is declining to leak.

`app/domain/live_engine_c/client_support.py` holds the three ids WITH a reason each, and
`task_service` passes `selectable_template_ids(adapter.supported_template_ids())` to `select_task`.
No retry loop is needed: a template outside the pool is simply never chosen. Order is preserved,
because selection is seeded and deterministic and re-ordering would change which task a seed
produces. Live pool verified: 30 -> 27.

RECORDED AS A CLIENT-CAPABILITY CONSTRAINT, NOT A SCIENTIFIC ONE. Nothing here says those tasks are
pedagogically wrong; it says the app has no screen for them. It does narrow the adaptive pool from
30 to 27, which is a real effect on what a child meets, and that belongs in the record rather than
in a silent denylist. Ship a surface and the entry goes away.

**Drift guarded in both directions.** `frontend/.../c-unrenderable-templates.test.ts` runs every
exemplar through the real resolvers and asserts the unrenderable set is EXACTLY those three, with a
failure message naming the backend file to update -- so shipping a surface fails, and breaking a
resolver fails. It also guards against a PARTIALLY renderable template (working at some difficulty
levels and not others), which could neither be excluded nor served safely and would need an owner
decision rather than a denylist entry. `tests/test_c_client_support.py` (6) asserts every excluded
id is a real template, that the filter removes without rearranging, that it is idempotent, that the
remaining pool clears a floor of 20, and that every entry states a reason.

**Verified.** Backend 717 passed, 0 failed, 76 skipped. Frontend `tsc --noEmit` clean, lint 0
errors, 1385 contract + 21 render passed. API restarted, live selectable pool 27 of 30.

Owner: Yasindu.

## 2026-10-10 -- Component C difficulty level: the chip is honest, the progression is not wired (gap recorded, not fixed)

**The chip was showing the wrong axis.** The C game card's top-right "Lv N" pill was rendering
`scaffold_state` -- the SUPPORT ladder, `C0`-`C4` -- which reads to a user as the game's level but
is a different quantity entirely. It now renders the server's `difficulty_level`, which
`09_API_AND_INTEGRATION_GUIDE.md` §2 explicitly marks "Displayed or ignored, never acted on". The
scaffold level was not lost: it still appears in the wrong-answer feedback panel, where it belongs.

NO DENOMINATOR, DELIBERATELY. The approved bundle declares no maximum difficulty -- it carries
`familiarization_difficulty_level: 1`, `fallback_difficulty_level: 1` and caps of 2, and no
catalogue template carries a difficulty field at all. "Lv 2 of 3" would be the client asserting a
ceiling the governed configuration does not define, the same class of mistake as rendering a prior
as evidence. If a ceiling is ever approved it belongs in the bundle and must be read from the
server. `difficultyLevelLabel` fails to a MISSING chip for anything that is not a positive integer
-- never a crash, never a raw value on screen. Locked by
`frontend/src/api/__tests__/c-difficulty-level-chip.test.ts`.

**A premise worth correcting in the record.** "Three levels per game type" is the CURRICULUM
taxonomy (`L1`-`L3`), not this field. `07_GAME_CATALOGUE_AND_TASK_TEMPLATES.md`: "Curriculum level
is not C difficulty level" -- Component C's own `1`-`5` "describes a calibrated configuration
within a template". Separately, a `c_only` session takes `fallback_difficulty_level = 1` capped at
2 (`06_ADAPTIVE_POLICY_SAFETY_AND_SCAFFOLDING.md` Part 1), and the app only ever opens `c_only`
(`adventure-charge-context.tsx` hardcodes it). So even a fully wired progression would show Lv 1
and Lv 2 here, never 3 to 5.

**THE GAP: the difficulty decision is computed, persisted, and then never applied.** Recorded here
rather than fixed, because it needs the Component C owner's ruling.

MEASURED against the dev database, not inferred:

| Table | Observation |
| --- | --- |
| `c_task_opportunities` | 112 rows, `initial_difficulty_level = 1` on every one |
| `c_policy_decisions` | 37 rows `1 -> 1`; **35 rows `difficulty_before = 1 -> difficulty_after = 2`** |
| `c_task_instances` | 112 rows, `difficulty_level = 1` on every one |

The policy has decided "increase to 2" thirty-five times. No task has ever been built above 1.
Three findings close the loop:

1. `task_service.py:930,941` passes `current_difficulty_level=instance_record.difficulty_level`
   into evidence -- which is always 1, because every instance is built at 1. The policy therefore
   never observes a state other than "currently 1", and the most it can conclude is `1 -> 2`.
2. Nothing reads `difficulty_after` back. It is written to `c_policy_decisions` (and to
   `c_safety_event_records`) and consumed by no one.
3. The engine's `selection.selector.select_task` takes NO current-difficulty parameter -- verified
   by `inspect.signature` against the installed wheel, not read from a doc. The next task's level
   is whatever `SelectionResult.initial_difficulty_level` says, which in `c_only` is the fallback.

So this is not a wiring omission in `adapter.py`; the adapter already passes everything
`select_task` accepts.

NOT PRESENTED AS INTENDED BEHAVIOUR. `15_KNOWN_LIMITATIONS_AND_STATUS.md` does not list this as a
limitation -- it lists the difficulty policy under VERIFIED / BUILT, and §10a asserts the opposite
of fixed: the policy and scaffold ladder "are all real, running code -- but they adapt to what the
child does within the current session only". The schema models application explicitly too:
`c_policy_decisions` carries both `selected_action` AND `applied_action` ("proposed and applied
difficulty action"), and `applied_action` means nothing if nothing applies it. This reads as an
unclosed gap, not a deliberate design.

**The candidate fix, and why it is not being taken unilaterally.** The engine does expose
`component_c_generator.selection.selector.build_task_instance(template, seed_lineage, grade,
difficulty_level, student_id, c_session_id, task_index, catalogue_version, config, ...)` with an
explicit `difficulty_level: int` -- the same entry point `scaffolds.recovery` uses. Carrying the
most recent `CPolicyDecisionRecord.difficulty_after` into that call, and persisting the level
actually used on both `c_task_opportunities.initial_difficulty_level` and
`c_task_instances.difficulty_level`, would close the loop without any arithmetic in app code: the
safety controller has already produced `difficulty_after = clamp(target, floor, ceiling)` with the
`c_only` cap applied.

The governance gate is NOT the blocker. `assert_generation_config_permitted` refuses
`TEST_FIXTURE_ONLY` / `SMOKE_ONLY` configs outside smoke mode, but the live config in `adapter.py`
(233, 252, 302) is built with `_APPROVED_CODE_GATED_PARAMETER_SOURCE_STATUS`. Verified.

What blocks it is scientific authority, which is not ours to assume. The docs never name a consumer
for `difficulty_after`, and `06` leaves the step rule undefined -- it gives
`difficulty_after = clamp(target, floor, ceiling)` and never defines `target`. Having the
orchestration layer construct C tasks directly, at a level it selected, is the orchestration layer
making an adaptive choice. This codebase refuses that everywhere else and it should refuse it here
until the Component C owner rules.

OWNER QUESTION, stated so it can be answered in one pass: should the next task be built at the most
recent decision's `difficulty_after`, and should `current_difficulty_level` into
`build_policy_evidence` be that carried value rather than the previous instance's level? If yes,
what is `target` in the clamp?

**Consequence, stated plainly.** Until that ruling lands the chip reads `Lv 1` for an entire
session, every session. That is ACCURATE -- it genuinely is the task's difficulty -- but it does
not move, and it should not be described as adaptive difficulty in a demo.

**Verified.** Frontend 1473 contract tests passed, 0 failed. Backend 717 passed, 0 failed, 76
skipped (unchanged -- this entry adds documentation and one pointer comment, no behaviour). Engine
signature and parameter-source status both confirmed by introspection against the installed wheel.

Owner: Yasindu.

## 2026-10-10 (later) -- Component C difficulty progression WIRED: the decision is now applied to the next task

Closes the gap the entry above recorded. Owner instruction: start the dedicated backend
progression task, keep the UI data-driven, do not fake level changes, and do not implement an
arbitrary escalation formula in `task_service.py`.

**What changed, in one sentence.** `next_task` now builds the task at the most recently persisted
`CPolicyDecisionRecord.difficulty_after` instead of always at `select_task`'s own
`initial_difficulty_level`.

NO FORMULA WAS ADDED, and that is the point. The engine already bounds its own output -- its
hard-safety controller step ends in `difficulty_after = max(floor, min(ceiling, target))`, with the
`c_only` ceiling applied from `selection_config.fallback_difficulty_cap` (VERIFIED by reading the
installed wheel's source, not the docs). This batch carries that integer and computes nothing.
Stepping, flooring or capping in app code would be the orchestration layer implementing adaptive
science, which this codebase refuses everywhere else.

PRECEDENT, NOT A NEW PATHWAY. `CPolicyDecisionRecordRepository.most_recent_for_session` already
existed and its own docstring already establishes that the most recently written decision is what
feeds the NEXT task -- `increase_block_remaining` has been read exactly this way since Phase 6b.
This adds a second field to that same established read. Construction goes through
`LiveEngineCAdapter.build_task_instance(..., difficulty_level=...)`, the governed entry point the
recovery path already uses -- same template, same skill, same seed lineage `select_task` chose,
only the difficulty differs. The frozen instance the engine returned is never mutated.

**Why two causes had to be fixed by one change.** The circle was closed in both directions: the
policy's evidence reads the PREVIOUS INSTANCE's level (`current_difficulty_level=
instance_record.difficulty_level`), so while every instance was built at 1 the policy could only
ever observe "currently 1" and could only ever conclude `1 -> 2`. Persisting the carried level on
the instance fixes the evidence input as a consequence -- no second edit was needed at the
evidence call site, and none was made.

**A validity guard that REJECTS rather than clamps.** `difficulty_level` carries no database CHECK
of its own, while the policy evidence's own `current_difficulty_level` is annotated `Le(5)` -- so an
out-of-domain level would persist cleanly here and then fail LATER, on the child's next submission,
as a validation error. An out-of-domain carried value is therefore discarded in favour of the level
the engine just selected. Clamping it would silently manufacture a level no policy chose;
discarding falls back to a value the engine DID choose. `_ENGINE_DIFFICULTY_MIN/MAX` are the
engine's own annotations (`Ge(1), Le(5)` on both its selection result and its evidence model), and
a test reads them off the installed wheel so they cannot drift from production silently.

**Fail-safe on construction.** If a template cannot be built at the carried level the child keeps
the task the engine already produced rather than meeting an error -- and the rows then record the
level ACTUALLY served, never the one intended, so the audit trail stays honest about what the child
met. Expected never to fire (all 30 templates are frozen at all five levels -- the 150-exemplar
sweep in the 2026-09-28 entry). Both exceptions the adapter can raise here,
`UnsupportedTemplateError` and `TaskGenerationTechnicalError`, were CONFIRMED to be
`LiveEngineCError` subclasses by introspection, so the fallback genuinely covers both paths rather
than appearing to.

**Tests: `tests/test_c_difficulty_progression.py` (4).** The behavioural one drives the real path --
a real session, a real `next_task`, a real terminal event stream so the resume-instead-of-mint path
correctly finds nothing to resume, and a real persisted decision row -- and asserts the second task
is BUILT at the carried level, with the opportunity row, the instance row and the response all
agreeing. PROVEN TO BE A REAL TRIPWIRE, not merely passing: the carry was disabled and the test was
confirmed to FAIL, then restored. The structural test enforces the owner constraint (no arithmetic
or clamping applied to a difficulty expression) and cannot pass by the feature having been deleted
-- it also asserts the carry is still present. It strips whole-line comments before matching,
because the comments in that method legitimately discuss clamping in order to rule it out.

**C-17's GUARD FIRED DURING THIS BATCH, AND IT WAS RIGHT.** The first full run came back
`1 failed, 720 passed`:
`test_c17_3_initial_difficulty_path_does_not_consume_prior_session_end_state` asserts
`apply_safety` and the policy's observable-evidence type appear NOWHERE in this module -- not even
in prose -- and the new explanatory comments had spelled both. The module already carried a note
saying an identifier was "deliberately not spelled out here so this in-line comment does not itself
trip" that check; the convention was documented and not followed. Both comments now describe those
things instead of naming them, with the reason recorded inline so the next person does not
rediscover it. No behaviour was involved -- this was comment text only -- but the earlier
"guards clear" check had been taken BEFORE the validity guard was written, so it did not cover
them. Recorded because a guard that fires and gets quietly worked around is worth less than one
whose firing is written down.

**Verified.** Backend **721 passed, 0 failed, 76 skipped** (717 baseline + 4 new) against the
isolated `upadya_test` database. Frontend untouched: no file changed, and its 1473 contract tests
were already green, including the chip's own `c-difficulty-level-chip.test.ts`.

A NOTE ON THE TEST INVOCATION, because it invalidated a run in this batch: `api-test` declares no
volumes and runs the baked `upadya-backend:be1-batch3` image, so `docker compose build api` is not
optional -- a suite run without it tests the previous code while looking entirely normal. The
compose file says this; it is repeated here because the failure mode is silent. Separately, the
`db` service had been `Exited` for 15 hours at the start of this batch, and because the canonical
command passes `--no-deps`, nothing started it: the suite ran with no database and produced
hundreds of connection failures that looked like real test failures.

**STILL NOT VERIFIED, and not claimed:** the live end-to-end. Nobody has yet played a `c_only`
session through the running API until the policy escalates and confirmed a `c_task_instances` row
appears at level 2, where all 112 existing rows are level 1. The tests prove the mechanism; they do
not prove the running deployment. The dev API container was deliberately NOT rebuilt or restarted
for this check, because doing that mid-session previously broke a question a child-facing screen
was in the middle of (the "Time's up" incident, 2026-10-10).

**Scope note.** `c_only` sessions remain capped at 2 by the approved bundle, so this makes the chip
read Lv 1 -> Lv 2 and nothing higher. Reaching 3-5 needs `combined` mode and a real B->C mastery
feed, which is a separate piece of work: `15` §10a records that mastery is currently a fixed
constant, so deriving a level from it today would be a fabricated difficulty wearing a real one's
clothes.

**Owner question from the entry above is NOT resolved by this batch and still stands:** the docs
name no consumer for `difficulty_after`, and `06` never defines `target` in its clamp. This batch
implements the reading that the schema's own `applied_action` column implies and that
`most_recent_for_session` already set a precedent for. If the Component C owner rules differently,
the change is one function's worth of code to revise and the tests name exactly what would have to
change.

Owner: Yasindu.


---

## 2026-10-20 — LIVE-01: the frozen Q-learning policy replaces the rule policy in production

**What changed.** Component C's live difficulty decision is now proposed by the FROZEN, trained Q-learning policy
(RL notebooks NB02/NB04, `component_c_rl/`); the pinned safety controller still disposes. `PRODUCTION_POLICY_MODE` is
`"frozen_q_evaluation"` (was `"rule_based_baseline"`). The rule policy no longer decides anything in production; its
code path (`decide_adaptation_with_safety_flags`) is untouched and still tested.

**Approval (as reported).** Prabathi (Component C owner), reported by Yasindu, 2026-10-20 — recorded in
`provenance/component-c-q-policy-approval.json`. `evidence_reference` is `"TO BE SUPPLIED BY YASINDU"`; no forum or
document name was invented.

**Decisions applied as given.** Frozen only (no per-child learning; `internal_reward` stays NULL). Fail closed: a missing
or hash-mismatched table raises `QPolicyArtifactError` and the session refuses at start — there is no fallback to the rule.
No DB migration (`frozen_q_evaluation` was already allowed by the `c_policy_decisions` CHECK and by `PolicyMode`). No
frontend change. The c_only difficulty cap of 2 (approved bundle) is unchanged.

**Files.**
- `provenance/c_policy/` — `q_c_only.json`, `q_main.json`, `golden_vectors.json`, `MANIFEST.json` (sha256 of every
  file), `.gitattributes` (`* -text`, so line-ending conversion cannot change a hash). Produced by
  `component_c_rl/notebooks/NB04_live_policy_export.ipynb`. `Dockerfile` copies the directory; `.dockerignore` re-includes it.
- `app/application/live_engine_c/q_policy.py` (new; imports nothing from `component_c_generator`): `load_q_policy`
  (sha256-verified, cached after the first load), `state_of` (same buckets as `rl_core.agent`, plus mastery bucket 3 =
  unknown for c_only), `QPolicy.propose`.
- `app/infrastructure/live_engine_c/adapter.py` (still the ONLY importer of the generator): `preview_allowed_actions`,
  `decide_with_proposed_action`, `safety_controller_version`; ports declared in `app/domain/live_engine_c/ports.py`.
- `adaptation_service.decide_and_persist_adaptation`: optional `proposed_action / policy_version / rl_state`; without them it
  takes the unchanged rule path.
- `task_service.submit_action`: builds the Q observation from persisted data (first-try = mean `first_attempt_correct` over
  the last 5 summaries, 0.5 if none; strain = `rolling_strain_score`; mastery = the selected skill's fixture mastery for
  combined, `None` for c_only; tasks_done = number of summaries), previews the allowed actions, proposes, then
  `decide_with_proposed_action`. `policy_version = "c-rl-q-v1+<SAFETY_CONTROLLER_VERSION>"`; `rl_state` JSONB holds
  `{state, q_values, allowed, artifact_file, artifact_sha256}`.
- `c_session_service.create` loads the table before any session row exists, so a bad artifact refuses the session up front.

**Gate membership.** The Q policy is a new config consumer and was NOT covered by the session-start gate (the existing
`policy_config` family gates the rule thresholds only). It is now wired in the same way as the other code-gated families:
`create_session` gained a required `q_policy_parameter_source_status` argument and calls
`assert_code_gated_family_usable(family_name="q_policy_config", ...)`; the status comes from the hash-verified
`MANIFEST.json` (`APPROVED_FOR_PROVISIONAL_IMPLEMENTATION`, the same status the other code-gated families carry). A seam
(`assert_q_policy_matches_session_gate`) re-checks at `submit_action` that the loaded artifact's status equals the
session-gated one, mirroring `assert_policy_config_matches_session_gate`.

**Equivalence proof.** `decide_with_proposed_action` composes the `AdaptationDecision` itself because the pinned
`decide_adaptation` raises `QLearningDisabledError` for Q modes. `tests/test_live01_q_adapter.py` proves that for the same
applied action the composed decision equals the pinned rule path field-for-field (decision_id, applied/overridden/reason,
difficulty_after, strain bucket, increase block, session-start bucket, seed lineage) and the two safety flags match — except
`policy_mode`, `policy_version`, `rl_state` — over 11 evidence cases; that safety still wins whatever Q proposes (checked
against an independent call of the pinned `apply_safety`); and that Q never leaves the allowed set.

**Tests.** Baseline before any change (full suite, rebuilt image, db running): 2 failed, 720 passed, 76 skipped — both
failures are in `tests/test_be4f_transactional_sweep.py` (Component B, `'RESPONSE' == 'TIMEOUT'`), present before this
change and untouched. After: 2 failed (the same two), 796 passed, 76 skipped. New: `tests/test_live01_q_policy.py`,
`tests/test_live01_q_adapter.py` (76 tests incl. golden vectors, fail-closed, HTTP session refusal, gate, E2E).
Existing tests changed deliberately: `test_c4_session_lifecycle.py`, `test_c5_task_serve_and_evaluate.py`,
`test_c7_scaffolds_and_rewards.py` (+ `test_c6b_policy_and_safety.py` helper): pass the new required
`q_policy_parameter_source_status` to `create_session`; `test_batch3_safety_forces_recovery_column.py::
test_correct_answer_persists_the_real_safety_forces_recovery_flag`: its spy moved from the rule-path method to
`decide_with_proposed_action`, the method production now calls. `test_c6b` ~L703 / ~L1022 needed no change — they test the
adapter's pinned `decide_adaptation`, which still refuses Q modes.

**Known limits (not fixed here).**
- c_only is capped at level 2 by the approved bundle, so live Q chooses only between levels 1 and 2 until combined mode
  with real B->C mastery exists. In simulation c_only leaves little room: greedy Q vs rule +0.0125 reward, +0.0345
  first-try, −0.038 safety events; there is no mastery growth or boredom dropout in c_only.
- Adaptation still runs only after a correct completion (`task_service.py`, the `is_correct` branch); in training Q decided
  after every task. The first Q decisions of a session are forced holds (`min_tasks = 3`), so with correct-only adaptation
  Q starts choosing once the session has 3 task summaries (tasks_done >= 3).
- B mastery in combined mode is still the fixed fixture (`mastery_fixture.py`).
- In the training simulation a forced hold (tasks_done < 3) is returned even if `hold` is not in the allowed set and safety
  then disposes; `QPolicy.propose` keeps that behaviour so it matches the golden vectors.
- The live container was not rebuilt or restarted (see the 2026-10-10 "Time's up" entry); a running dev API must be rebuilt
  to pick this up.

Owner: Yasindu.


---

## 2026-10-20 — LIVE-02: c_only oscillation fixed by retraining (q_c_only_v2)

**Problem (live database after LIVE-01).** The c_only Q table bounced between levels for a child who succeeds:
state `1,2,0,3` -> increase (1->2), state `2,2,0,3` -> decrease (2->1). Diagnosis from the table: Q(2,2,0,3) =
[2.714, 2.076, 0] (decrease beat hold by 0.637), Q(1,2,0,3) = [0, 2.306, 3.126]; 179k / 251k visits, i.e. converged values.

**Fix: training, not a hand-written rule.** In the simulator (`component_c_rl/rl_core/env.py`) boredom dropout was
combined-only, so staying at a level the child masters was never costed in c_only. It now also runs in c_only on the
learner's LATENT mastery (policy still sees mastery unknown); growth stays combined-only; DROP_A/B/C, reward weights, tau,
state buckets, the safety controller and `q_main.json` are unchanged. Combined mode is pinned identical by a digest test. Rule
c_only early-end rate with the change: 14.8%. Retrained with the NB04 settings (3,000 x 25, seed base 50,000, 16.0 min).
Offline result (100 new c_only learners x 10 sessions, seeds 9,400,000+): v2 greedy at (2,2,0,3) = hold; flip rate (decisions that
reverse the previous move) 0.747 (v1) -> 0.162 (v2), rule 0.003; level-2 share when first-try is high and strain low 0.49 -> 0.83
(rule 0.89); reward v1 0.5071 / v2 0.5014 / rule 0.4973. Gate passed. v2 is NOT oscillation-free: about half of its moves still
reverse the previous move.

**Shipped.** `provenance/c_policy/q_c_only_v2.json` (sha256 `5893e91f8917cdabc72a5a9b737c93267f9a55b1b4acbea03353b491218f0e6b`,
`artifact_version: "v2"`). `MANIFEST.json`: `q_c_only` -> v2; the v1 entry is kept as `q_c_only_v1` with
`superseded_by: "q_c_only_v2.json"` and its file stays on disk (audit trail; no fallback to it); `q_main` untouched. Golden vectors
regenerated for c_only (new sha256 `79df790f5ca21e1712f13922786e046d782e193fe6fabf9a85ee5d817ccaff1b`), combined rows
byte-identical. No backend logic change: `load_q_policy("c_only")` resolves v2 through the manifest, so `rl_state.artifact_file /
artifact_sha256` now show v2. `policy_version` stays `c-rl-q-v1+<safety version>` (the policy family); the artifact version
is in `rl_state` and the manifest.

**Tests.** New `tests/test_live02_c_only_v2.py`: manifest points c_only at v2 and keeps v1 as superseded; the greedy action at
`2,2,0,3` is not decrease; v1 file kept only as the audit record; a tampered v2 fails closed (and there is no fallback to v1);
backend E2E through `TaskService.submit_action`, every answer correct, 8 tasks: difficulty sequence **[1, 1, 1, 2, 2, 2, 2, 2]**
(decisions: hold, hold, increase, then hold x5) — no alternation. `tests/test_live01_q_policy.py` updated for the v2 file name.
Full suite after `docker compose build api` (db running): 2 failed, 801 passed, 76 skipped; the 2 failures are the same
Component B `test_be4f_transactional_sweep` ones present before LIVE-01 (LIVE-01 result: 2 failed, 796 passed, 76 skipped).

**Not done / not claimed.** The running dev API was NOT restarted or rebuilt — it still serves v1 until the Lead restarts it.
The live database was not touched by the tests (they use `studentapp_test`).

Owner: Yasindu.


---

## 2026-10-20 — PERF-01: fewer database round trips on Component C submit / next_task

**Problem.** Against the remote dev database (~50 ms per round trip) submit took 1-3 s and next_task 1-1.6 s: the cost was the
number of sequential statements, not computation. Goal: fewer round trips with IDENTICAL behaviour (same rows, same
responses, same errors, same commit boundaries).

**Measured first.** `tests/perf_helpers.py` (statement counter via `before_cursor_execute`, origin = the calling app/ frame,
optional real sleep per statement) and `tests/perf_scenario.py` (a scripted c_only session through the real services: 8
tasks, odd tasks a wrong answer then correct, even tasks correct first time; each call in its own session + commit like the
routes). `tests/test_perf01_submit_benchmark.py` (`PERF=1`, `PERF_LATENCY_MS=50` to really sleep).
Statements per call (BEGIN/COMMIT not counted), simulated at 50 ms each:

| call | BEFORE | AFTER |
|---|---|---|
| submit, correct answer | 24 (min 24, max 25) = 1,225 ms | **11 = 550 ms** (-54 %) |
| submit, wrong answer | 14 = 700 ms | **6 = 300 ms** (-57 %) |
| next_task | 11 (10-11) = 550 ms | **9 = 450 ms** (-18 %) |

Run with a real 50 ms sleep per statement the correct submit measured 606 ms wall (550 ms of sleeping plus ~55 ms of local
CPU and profiler overhead); the simulated figure at 50 ms/statement is 550 ms. The baseline's biggest origins were
`repositories.py:34` (every `add` = one INSERT round trip, 5.5 per correct submit), four separate counting queries over
`c_gameplay_events` for the same instance, the session history read twice (3 queries each time:
`telemetry_validation.py:297-299`), a repeat event-stream read by summary derivation and by the scaffold step, a separate
instance lock, a separate user lookup and session read.

**Changes (what each removed).**
- `repositories.py` `CSessionRecordRepository.get_owned_for_subject` (new): user -> learner link -> owned session in ONE query
  (was the user/link query + session read; the three not-found cases already were one `ResourceNotFoundError`). Used by
  `submit_action` and `next_task`. -1 (submit), -2 (next_task, with the lock below).
- `next_task`: `get_owned_for_subject(..., for_update=True)` takes the same session-row lock in the same query (was a separate
  `SELECT ... FOR UPDATE`; now taken before the state check, which only matters for a request about to be refused).
- `CTaskInstanceRecordRepository.get_owned(..., for_update=True)`: reads AND locks the instance row (was a read, then
  `lock_for_update`). The lock is the same row lock, now taken before the terminal / validation checks instead of after them;
  sequential behaviour is identical, a concurrent duplicate waits one step earlier. -1.
- `submit_action`: ONE `list_ordered_for_instance` read replaces four queries (terminal check, max index / timestamp,
  answer_submitted count, started check); all four values are derived from it in Python under the instance lock. -3.
- `submit_action`: the started / submitted / evaluated (and, for a correct answer, terminal) events are queued and inserted in
  ONE statement (was one INSERT each). The terminal event is built by `write_completed_correct_terminal_event` (new optional
  `known_max_index / known_max_timestamp / known_not_terminal / defer_flush`; defaults keep the old behaviour and the old
  tests) and added AFTER the answer events (insert order = add order, which the Phase 3b consecutive-event_index trigger
  needs). The unique-terminal-index backstop (T1-3) is translated to the same `ConflictError` around that one flush. -2 (wrong),
  -4 (correct, with the two terminal-event re-reads).
- `derive_and_persist_summary(records=...)` and `decide_and_persist_scaffold_level(events=...)` (new optional): reuse the
  stream `submit_action` already holds (its events plus the ones it just wrote) instead of re-reading it. -1 each.
- `build_evidence_for_session(history_records=...)` (new optional) and `submit_action`: the session's derivable history is read
  ONCE (through the same guarded `get_derivable_history_for_session`) and shared by the evidence builder and the Q observation
  (it was read twice). -3.
- `bundle_resolution.resolve_c_bundle_and_catalogue`: per-process cache (below); `next_task` reuses the catalogue that
  resolution already loaded instead of parsing it a second time. Local CPU for next_task 193 ms -> 90 ms.

**Caching.** Cached per process: the result of a SUCCESSFUL `resolve_c_bundle_and_catalogue` (runtime-bundle schema validation,
every artifact checksum incl. the catalogue's, catalogue parse + checksum), keyed by the arguments and by each input file's
(path, size, mtime). The first call after start-up does the full validation; a file that changes or goes missing is
re-validated from scratch on the next call (stricter than "hash once"); a failure is never cached. The Q policy manifest and
tables were already cached after the first sha256-verified load (LIVE-01): a tampered file present at start-up still raises
`QPolicyArtifactError` and the session refuses (existing tamper tests unchanged and passing). The per-request gates are all
still evaluated (`assert_generation_config_permitted`, the policy seam, the Q-policy status seam). The next_task comment that
says the bundle resolution on the resume path "must not be optimized away" is honoured in intent: the resolution still runs on
every call, it is now served from the validated cache unless a file changed.

**Proof nothing changed.** `tests/fixtures/perf01_golden_session.json` was captured from the code BEFORE any change
(`PERF_CAPTURE=1`; two further pre-change runs reproduced it) and `tests/test_perf01_row_equivalence.py` compares the same
scripted session after the change: every row of every c_* table the session writes (c_task_opportunities, c_task_instances,
c_gameplay_events 48 rows, c_task_opportunity_summaries, c_policy_decisions, c_safety_events, c_scaffold_events,
c_task_opportunity_verdicts; UUID / timestamp / request-id columns excluded, UUIDs inside values renumbered) and all 20 API
response bodies are identical. `tests/test_perf01_round_trips.py` keeps a statement budget per call type (<= 12 / 7 / 10) and
tests the cache (same object on a hit, tampered catalogue fails closed, failures not cached). Full suite after
`docker compose build api` (db running): 2 failed, 805 passed, 78 skipped; the 2 failures are the same Component B
`test_be4f_transactional_sweep` ones present before LIVE-01 (LIVE-02 result: 2 failed, 801 passed, 76 skipped; the added
tests are the 4 new PERF-01 tests that run by default plus 2 perf-marked ones skipped without `PERF=1`).

**Remaining hotspots (left deliberately).** Correct submit (11): user+session join, instance read+lock, event stream, ONE INSERT
for the events, INSERT summary, learner local state, the guarded history (opportunities, summaries, verdicts = 3 reads that the
telemetry validator needs), latest decision, INSERT decision. Different tables cannot share an INSERT; the 3-read history is
the validated accessor (J1-2/J1-4) and was left alone; the user lookup is the authorization step. Not measured here: the JWT /
JWKS verification, connection acquisition and BEGIN / COMMIT, which are per request outside these services. The running dev API
was NOT restarted or rebuilt; it needs a rebuild to pick this up.

Owner: Yasindu.

## 2026-10-20 — The session results screen now shows per-skill mastery bars (owner decision, reversing a recorded rule)

**This reverses a rule, deliberately, and the reversal is the entry.** `live-session-logic.ts`'s
`resultsView` stated that the results surface carries "no score, no percentage, no stars, no
streak, no per-skill breakdown, no mastery figure", and that "a child who got everything wrong and
a child who got everything right see the identical screen, by design". It went further: the
function takes an `outcomeHistory` parameter it never reads, with a comment saying the parameter
exists SO THAT ignoring it is testable, and a note ending "If you are here to 'fix' the missing
score, this comment is the answer: it is not missing."

The owner has ruled that the screen may show what moved. The two costs below were put to them
before the work started and accepted.

**WHAT WAS KEPT.** The reversal is narrower than it looks, and the narrowing is enforced:

* `resultsView`'s own guarantee is UNCHANGED and still tested -- the COPY (headline and detail) is
  byte-identical for every possible outcome history, carries no score, and still never reads
  `outcomeHistory` (`session-results.test.ts`).
* The bars are drawn from the SERVER's own `p_l` values (`GET /b/learner/skill-states`), never from
  the `response_matched` values this client happened to observe. That distinction is what keeps the
  original objection intact: the client is not synthesising a summary that was withheld, it is
  rendering one the server already serves to the Play prep card under its own 2026-09-21 ruling.
* No number is printed and none is announced. The bar's length is the whole message; a test asserts
  no `accessibilityValue`, no percentage text, and no formatted number in the component.

**TWO PROTECTIONS, because the audience is seven.**

* A BAR NEVER SHRINKS. BKT lowers `p_l` on a wrong first attempt, and a bar visibly shrinking at
  the end of a session is exactly the "you did badly" message the original rule existed to prevent.
  A fall is clamped to flat and is never flagged as improvement. The stored value is untouched;
  only the drawing is.
* NO SNAPSHOT MEANS NO MOVEMENT. The server has no "before" to give -- the endpoint returns current
  `p_l` only -- so the starting state is photographed client-side at session start. A reload
  mid-session, a direct link, or a session begun before this shipped leaves nothing to compare, and
  the screen then draws current mastery with no movement. Rendering `before: 0` instead would sweep
  every bar from nothing to everything and invent a result.

**THE SNAPSHOT IS IN MEMORY, KEYED BY SESSION, AND NEVER PERSISTED.** Three reasons, each
load-bearing: a snapshot is meaningless outside its own session; this app runs on shared classroom
devices and one child's mastery must never be drawn against another's (the rule
`home-session-state-cache.ts` already follows); and the results screen is documented as not
surviving a reload, which persisting would quietly undo. First write wins, so a remount or a
crash-recovery resume cannot re-baseline the snapshot to a mid-session state and erase the child's
own progress from the screen.

**TWO KNOWN COSTS, accepted rather than solved.**

1. **The bars are driven by TEST_FIXTURE_ONLY parameters.** `p_l0=0.2, p_t=0.15, p_g=0.2, p_s=0.1`
   saturate `p_l` toward 1.0 after roughly four or five correct answers. After a five-question
   session the bars move dramatically -- because the parameters are uncalibrated placeholders, not
   because the child learned that much. The movement a child sees is partly an artefact.
2. **A child who did not progress watches their bars stay still.** The clamp stops a bar falling,
   but it cannot manufacture growth. This is the case the original rule was written to avoid, and
   it is now reachable.

**Navigation changed with it (owner request).** Home is an icon in the top-left; the primary
action at the bottom is PLAY AGAIN, routing to preparation. Leaving is still one tap away but is
no longer what the screen offers.

**A FOURTH ARTEFACT EMBEDS THE PROMPT WORDING, found by the frontend suite.** Changing Component C
wording earlier the same day required regenerating `c-prompt-wording.json`,
`c-prompt-exemplars.json` and the `perf01` golden -- and then the frontend's own generated
`src/api/generated/c-prompt-exemplars.ts`, which cross-checks against the backend artefact
(`npm run generate:c-prompt-exemplars`). Targeted backend runs passed while this was stale. A
wording change touches FOUR generated files, not one; the cross-check test is what catches it.

**Verified.** Frontend 1516 contract + 22 render passed, 0 failed; `tsc` clean; lint 0 errors.
Nine new tests cover the pure comparison logic and three structural guards (no printed number, the
width rule shared with the prep card rather than re-derived, and the snapshot never persisted).

**NOT VERIFIED, and not claimed:** nobody has yet played a session end-to-end and watched the bars
animate. The logic is tested; the animation is not.

Owner: Yasindu.
