// Types for the prompt-visual registry (FE-3g).
//
// `prompt` arrives as an open `Record<string, unknown>` carrying `stem` plus per-template content
// keys. FE-3b rendered `stem` and discarded the rest — a deliberate scope call that turned out to
// leave questions unanswerable: measured against the live generator, 7 of 14 Grade 2 templates and
// 1 of 16 Grade 3 either cannot be answered or measure nothing, so a Grade 2 learner meets roughly
// two unanswerable questions in every five-question session.
//
// A spec here says "this payload can be drawn". It never says what the answer is: the visual
// presents the quantity the server sent, and the server alone judges what the child does with it.

export type PromptVisualKind =
  | 'object-set'
  | 'two-sets'
  | 'selectable-pool'
  | 'place-value-chart'
  | 'base-ten-blocks'
  | 'take-away'
  | 'before-after';

export type PlaceName = 'hundreds' | 'tens' | 'ones';

// `layout` is carried through from the payload (currently always "scattered") but is deliberately
// NOT branched on for anything that affects what the child must work out. It is a presentation hint
// only, and an unknown value degrades to the default arrangement rather than failing.
export type ObjectSetVisual = {
  kind: 'object-set';
  count: number;
  layout: string | null;
};

export type TwoSetsVisual = {
  kind: 'two-sets';
  setA: number;
  setB: number;
};

// An answer *surface*, not a passive illustration — see selectable-pool handling in
// live-session-screen.tsx and renderers/count-selection.tsx. `target` is intentionally absent from
// this spec: the pool is all the child needs to see, the stem already states the instruction, and
// carrying the target into the visual layer would invite drawing a progress cue against it, which
// is the measurement the item exists to take.
export type SelectablePoolVisual = {
  kind: 'selectable-pool';
  poolSize: number;
};

// B-PV01 / B-PV03 — `place_value_chart`. `askedPlace` is carried so the chart can be *described*
// accurately, never to highlight that column: which place is being asked about is already in the
// stem, and highlighting it would answer the question.
export type PlaceValueChartVisual = {
  kind: 'place-value-chart';
  value: number;
  places: readonly PlaceName[];
  askedPlace: PlaceName;
};

// B-PV02 / B-PV04 — `base_ten_blocks`. This visual necessarily shows the decomposition, because the
// decomposition IS what base-ten blocks are; that is the catalogue's intended scaffold for these
// items, not a leak of the answer.
export type BaseTenBlocksVisual = {
  kind: 'base-ten-blocks';
  value: number;
  places: readonly PlaceName[];
};

// B-SUB01 — `total` objects with `removed` of them shown as taken away, so the remainder stays
// countable. The remainder is deliberately never shown as a number: counting what is left is the
// task.
export type TakeAwayVisual = {
  kind: 'take-away';
  total: number;
  removed: number;
};

// B-NS07 — two panels. `delta` reached the wire in FE-3h Part 0; before it did, only the delta-0
// case was drawable, and a visual that appeared for exactly one answer value would have been a
// perfect non-mathematical cue.
export type BeforeAfterVisual = {
  kind: 'before-after';
  before: number;
  after: number;
};

export type PromptVisualSpec =
  | ObjectSetVisual
  | TwoSetsVisual
  | SelectablePoolVisual
  | PlaceValueChartVisual
  | BaseTenBlocksVisual
  | TakeAwayVisual
  | BeforeAfterVisual;
