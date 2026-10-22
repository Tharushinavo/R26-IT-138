// The shared tappable object pool (10e), built once for both `object-set-action` scenes: C-CC-01's
// select-and-count scene and C-CC-02's place-into-box scene both compose over this, following §5A's
// "build the primitive once, thin per-scene composition over it" doctrine -- the same shape
// `unit-stepper.tsx` was built for both `line-traversal` and 10d's `line-position`.
//
// GEOMETRY IS TOKEN_TOUCH_TARGET_SIZE / TOKEN_SPACING, DELIBERATELY NOT
// `object-quantity-display.tsx`'s OBJECT_TOKEN_SIZE / OBJECT_TOKEN_SPACING. That primitive's own
// header justifies its smaller (28px) size explicitly as "a PASSIVE, READ-ONLY display, never
// pressed" -- an exemption from SPEC section 10's 48px interactive-touch-target floor that applies
// only because nothing there is tappable. Every object in THIS pool is a press target (toggled for
// selection, or moved between pool and box), so the passive exemption does not apply and the floor
// governs. This is a deliberate divergence from that file's own "what 10e should reuse" list, which
// only ever offered its SIZE constants, not this component -- do not "unify" this pool down to
// OBJECT_TOKEN_SIZE later; that would put a below-floor touch target behind a real gesture.
//
// WRAP, NOT SCROLL, AND NEVER AT A FIXED COUNT PER ROW -- inherits `object-quantity-display.tsx`'s
// own representation-neutrality discipline verbatim (that file's header has the full reasoning: row
// length must be purely a function of container width and fixed object size, never a chosen number
// like 5 or 10, since either would silently build a base-ten or subitizing representation this
// codebase has repeatedly ruled is a scientific choice, not a builder's or layout one). Unlike that
// primitive, THIS one is also interactive, so uniformity additionally matters for fairness: every
// object is the same shape/size regardless of selected state, distinguished only by a border/fill
// change, never by size or position -- a bigger or repositioned selected object would let position
// or size leak information about which had been tapped, to a child scanning the pool rather than
// reading it.
//
// BOUNDED HEIGHT, INTERNAL SCROLL BY DEFAULT (`scrollable` prop, default `true`) --
// `jump-accumulator.tsx`'s exact remedy for the same failure this project has already shipped
// twice (10a's entry slots, 10c's jump chips): an unbounded list pushes SUBMIT further down the
// screen as the pool grows, and this pool can hold up to `MAX_POOL_OBJECTS`
// (object-set-action-logic.ts) objects at once. A fixed maximum height with its own internal
// scroll keeps SUBMIT's position independent of pool size. `scrollable={false}` (2026-08-26,
// added for the select-and-count scene's own two-stage reveal) opts a specific caller OUT of this
// when the pool is the only content on screen while visible -- see the prop's own doc comment.
//
// STATELESS. The surface owns which ids are selected (or which are in the box); this component only
// ever reports "this id was tapped" and renders whatever selection state it is given -- the same
// discipline `UnitStepper` and `DigitKeypad` already follow.
//
// Ids are never rendered as text -- only positional state (selected / not) is visible, matching
// `object-quantity-display.tsx`'s own "no digit, ever" doctrine for the adjacent primitive.

import { useEffect, useRef } from 'react';
import { Pressable, ScrollView, StyleSheet, View } from 'react-native';

import {
  GESTURE_LONG_PRESS_MS,
  HIT_SLOP,
  TOKEN_SPACING,
  TOKEN_TOUCH_TARGET_SIZE,
} from '@/src/features/c-session/motor-constants';
import { AppText } from '@/src/components/app-text';
import { labelForCountableEmoji, pickCountableEmoji } from '@/src/utils/countable-emoji';
import { radius } from '@/src/theme/tokens';

// A LAYOUT bound on how many rows are visible before the pool scrolls internally, not a catalogue
// constraint -- same "bound the display, not the data" doctrine `jump-accumulator.tsx`'s own
// `VISIBLE_ROWS` follows. Four rows keeps a meaningful chunk of the pool visible at once without
// SUBMIT's position ever depending on pool size.
const VISIBLE_ROWS = 4;
const POOL_MAX_HEIGHT = (TOKEN_TOUCH_TARGET_SIZE + TOKEN_SPACING) * VISIBLE_ROWS;

// The un-selected object's own fill: a light tint of the family accent (2026-08-26 request --
// "not only the border but also the fill" of the WHATEVER-family-accent-is-live colour, never a
// fixed literal like the primary brand's own #FF6B68). `accentForGameFamily` only ever returns a
// solid colour meant for text/borders, so this file computes its own low-alpha tint from it rather
// than requiring a second, accent-specific "soft" palette this codebase does not have. Selected
// state uses the SAME accent at full opacity as its fill -- see the `isSelected` branch below.
const UNSELECTED_FILL_ALPHA = 0.16;

function hexToRgba(hex: string, alpha: number): string {
  const match = /^#?([0-9a-fA-F]{6})$/.exec(hex);
  if (match === null) return hex; // not a plain 6-digit hex -- render the colour as given, unmodified.
  const value = match[1]!;
  const r = Number.parseInt(value.slice(0, 2), 16);
  const g = Number.parseInt(value.slice(2, 4), 16);
  const b = Number.parseInt(value.slice(4, 6), 16);
  return `rgba(${r}, ${g}, ${b}, ${alpha})`;
}

export type ObjectPoolProps = {
  objectIds: readonly string[];
  selectedIds: ReadonlySet<string>;
  onToggle: (id: string) => void;
  disabled?: boolean;
  /** The family's own accent (game-family-accents.ts), read from the wire -- see the surface's
   *  own accent comment. Colours the object's fill/border; never chosen per archetype. */
  accent: string;
  /** Default `true` (the ScrollView-bounded shape above). `false` (2026-08-26 request) renders
   *  every object at once with no internal scroll at all -- for a scene where the pool is the ONLY
   *  thing on screen while it is visible (see object-set-action-surface.tsx's own "two-stage
   *  reveal"), so there is no competing content a scrollbar could be mistaken for hiding, and a
   *  child cannot become unsure whether more objects exist off-screen. This still wraps
   *  (`flexWrap`) rather than compressing -- only the SCROLL behaviour changes, not the layout
   *  discipline above (WRAP, NOT SCROLL, AND NEVER AT A FIXED COUNT PER ROW still applies either
   *  way). Leave `true` for a scene (like the place-into-box scene) where the pool shares the
   *  screen with other controls SUBMIT must stay reachable below. */
  scrollable?: boolean;
};

export function ObjectPool({ accent, disabled = false, objectIds, onToggle, scrollable = true, selectedIds }: ObjectPoolProps) {
  // ONE emoji for the whole pool, seeded from the object ids so it is stable across every
  // re-render -- and this pool re-renders on every tap, since selection lives in state. A
  // `Math.random()` here would reshuffle the fruit each time a child selected one.
  const emoji = pickCountableEmoji(objectIds.join('|'));
  const emojiLabel = labelForCountableEmoji(emoji);
  const scrollRef = useRef<ScrollView>(null);
  const previousCount = useRef(objectIds.length);

  // Keeps a newly-changed pool scrolled to the top when its own membership changes (e.g. an id
  // moves out of this pool into the box in the place-into-box scene) -- not the child's own scroll
  // position while merely toggling selection within a stable pool, which must not be disturbed.
  // Only meaningful when `scrollable`; a no-op ref when it is not.
  useEffect(() => {
    if (objectIds.length !== previousCount.current) {
      scrollRef.current?.scrollTo({ y: 0, animated: false });
      previousCount.current = objectIds.length;
    }
  }, [objectIds.length]);

  const objects = objectIds.map((id, index) => {
    const isSelected = selectedIds.has(id);
    return (
      <Pressable
        accessibilityLabel={`${emojiLabel} ${index + 1}`}
        accessibilityRole="button"
        accessibilityState={{ disabled, selected: isSelected }}
        delayLongPress={GESTURE_LONG_PRESS_MS}
        disabled={disabled}
        hitSlop={HIT_SLOP}
        key={id}
        onPress={() => onToggle(id)}
        style={({ pressed }) => [
          styles.object,
          // SELECTED is carried by a ring AND a tinted ground AND the emoji's own scale -- three
          // cues, because the disc that used to encode it by fill is gone. Selection must never
          // rest on colour alone for a child who may not distinguish two tints of one accent.
          isSelected && { backgroundColor: hexToRgba(accent, UNSELECTED_FILL_ALPHA), borderColor: accent },
          disabled && styles.objectDisabled,
          pressed && !disabled && styles.pressed,
        ]}>
        <View style={isSelected ? styles.glyphSelected : styles.glyph}>
          <AppText style={styles.glyphText}>{emoji}</AppText>
        </View>
      </Pressable>
    );
  });

  if (!scrollable) {
    return <View style={styles.row}>{objects}</View>;
  }

  return (
    <ScrollView ref={scrollRef} style={styles.scrollBound}>
      <View style={styles.row}>{objects}</View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  // Fill and border colour are both applied inline per-object, from the family accent -- see
  // hexToRgba/UNSELECTED_FILL_ALPHA above. No static colour here.
  // NO DISC. The box is the touch target and the selection ring only -- transparent and
  // border-less until selected, so what a child sees is the emoji itself. The full
  // TOKEN_TOUCH_TARGET_SIZE is kept, so reachability is unchanged from the disc version.
  glyph: { alignItems: 'center', justifyContent: 'center' },
  glyphSelected: { alignItems: 'center', justifyContent: 'center', transform: [{ scale: 1.12 }] },
  glyphText: { fontSize: Math.round(TOKEN_TOUCH_TARGET_SIZE * 0.62), lineHeight: Math.round(TOKEN_TOUCH_TARGET_SIZE * 0.78) },
  object: {
    alignItems: 'center',
    borderColor: 'transparent',
    borderRadius: radius.pill,
    borderWidth: 2,
    height: TOKEN_TOUCH_TARGET_SIZE,
    justifyContent: 'center',
    width: TOKEN_TOUCH_TARGET_SIZE,
  },
  objectDisabled: { opacity: 0.55 },
  pressed: { opacity: 0.72 },
  row: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: TOKEN_SPACING,
    justifyContent: 'center',
    paddingVertical: TOKEN_SPACING / 2,
  },
  // `flexShrink: 0` + `minHeight` (2026-08-26 fix): without them, this ScrollView -- nested inside
  // a `justifyContent: 'space-between'` flex column (the surface's own `container` style) -- was
  // observed clipping the pool's objects roughly in half rather than showing them at full height,
  // a React Native Web flex-shrink pitfall where a scrollable child with only `maxHeight` set can
  // be compressed below its own content's natural size. `minHeight` guarantees at least one full
  // row is always visible; `flexShrink: 0` stops the flex parent from compressing this child at
  // all -- `maxHeight` alone still caps it from growing past `POOL_MAX_HEIGHT`.
  scrollBound: {
    flexShrink: 0,
    maxHeight: POOL_MAX_HEIGHT,
    minHeight: TOKEN_TOUCH_TARGET_SIZE + TOKEN_SPACING,
  },
});
