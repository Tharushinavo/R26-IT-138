// The rendered heights of the learner chrome: the header bar at the top, the tab bar at the
// bottom. Anything that must sit against one of them measures from here.
//
// WHY THEY LIVE IN THEIR OWN MODULE. They used to be exported from the components that draw them,
// which is the obvious place until something that is NOT those components needs them: the
// "Play Adventure" popup positions itself inside the header band, so it imported
// learner-header-bar.tsx -- which imports the adventure-charge context -- which renders the popup.
// A require cycle, and Metro says exactly what is wrong with one: "can result in uninitialized
// values". A module holding two numbers and importing nothing cannot participate in a cycle.
//
// These are plain numbers, deliberately: they are facts about the chrome's own stylesheets, and
// each component asserts them by using them in its own styles rather than by agreeing to them.

/** Rendered height of the learner header bar, per density. Callers that must not scroll subtract it. */
export const LEARNER_HEADER_HEIGHT = 88;
export const LEARNER_HEADER_HEIGHT_COMPACT = 63;

/** Rendered geometry of the learner tab bar, per density, plus the margin it floats above. */
export const LEARNER_TAB_BAR_HEIGHT = 73;
export const LEARNER_TAB_BAR_HEIGHT_COMPACT = 61;
export const LEARNER_TAB_BAR_MARGIN_BOTTOM = 11.75;
