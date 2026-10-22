// The startup gate: what the splash waits for, and what it no longer waits for.
// FE-015 (critical vs deferred artwork) and FE-016 (the splash waits for auth), 2026-10-09.
//
// Before: `app/_layout.tsx` awaited `allArtwork` -- eleven images, ~7.6 MB -- and hid the splash
// the moment fonts and artwork had settled, with `status` never consulted. Two separate problems
// followed, and the second was the worse one:
//
//   1. ~2.8 MB of that preload is artwork no screen a cold start can land on ever draws.
//   2. `RootLayout` returned `null` until that preload finished, and `AuthProvider` was one of the
//      children `null` withheld -- so session restoration did not START until every image had
//      decoded. The two costs added up instead of overlapping, and then the splash lifted onto
//      `app/index.tsx`'s "Checking secure access…" text because auth was still running.
//
// These are structural guards rather than a render test on purpose: the properties worth pinning
// are "which list is passed to the preloader", "no image fell out of either list", and "the ready
// flag latches". A mounted-component test would assert the first and miss the other two.

import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';

const LAYOUT_PATH = 'app/_layout.tsx';
const ARTWORK_PATH = 'src/utils/artwork.ts';
const layoutSource = readFileSync(LAYOUT_PATH, 'utf8');
const artworkSource = readFileSync(ARTWORK_PATH, 'utf8');

// artwork.ts cannot be IMPORTED here: it is a registry of `require('*.png')` calls, which only
// Metro resolves. So the lists are read out of the source instead. That is not a workaround for a
// weaker test -- the thing worth guarding is the classification itself, which is a source-level
// fact about which key appears in which list.
function sliceAfter(marker: string): string {
  const start = artworkSource.indexOf(marker);
  if (start === -1) return '';
  const end = artworkSource.indexOf('];', start);
  return end === -1 ? '' : artworkSource.slice(start, end);
}

function keysOf(declaration: string): string[] {
  return [...sliceAfter(declaration).matchAll(/artwork\.(\w+)/g)].map((match) => match[1]);
}

const registryBody = artworkSource.slice(
  artworkSource.indexOf('export const artwork = {'),
  artworkSource.indexOf('} as const;'),
);
const registryKeys = [...registryBody.matchAll(/^ {2}(\w+): require\(/gm)].map((match) => match[1]);
const critical = keysOf('export const criticalArtwork');
const deferred = keysOf('export const deferredArtwork');

test('every image is in exactly one of the two lists', () => {
  // The registry exists so a preload list cannot drift from what is actually rendered
  // (src/utils/artwork.ts's own header). Splitting it into two lists reintroduces exactly that
  // drift risk, so this is the check that closes it: add an image and forget to classify it, and
  // this fails rather than the image quietly never preloading.
  assert.ok(registryKeys.length > 0, 'the artwork registry must be parseable');
  const combined = [...critical, ...deferred];
  assert.deepEqual(
    [...combined].sort(),
    [...registryKeys].sort(),
    'criticalArtwork + deferredArtwork must together cover every entry in `artwork`, with no ' +
      'image in both lists or missing from both',
  );
});

test('the two heroes a cold start cannot show are deferred', () => {
  // `prepareHero` belongs to the preparation screen and `startGame` to the Play prep card. Neither
  // is reachable without a tap, so neither can be on the first frame after a splash.
  assert.ok(deferred.includes('prepareHero'), 'prepareHero must not block first paint');
  assert.ok(deferred.includes('startGame'), 'startGame must not block first paint');
  assert.ok(!critical.includes('prepareHero'));
  assert.ok(!critical.includes('startGame'));
});

test('the home hero IS critical, despite showHero sometimes being false', () => {
  // `learner-home-screen.tsx` skips the hero once `heroDismissedThisAppSession` is set -- but that
  // flag is module-scoped and resets with the JS runtime, so it cannot already be set on a launch
  // that shows a splash. A cold start always draws the hero, which makes it first-frame artwork.
  assert.ok(
    critical.includes('heroSection'),
    'heroSection is on the first frame of a cold start and must be awaited',
  );
});

test('the chrome shared by every learner route is critical', () => {
  // The header and tab bar live in app/(learner)/_layout.tsx, so they are on screen for every
  // learner destination the bootstrap can redirect to -- not just Home.
  for (const name of [
    'mathmingoHeader',
    'learningPath',
    'tabHome',
    'tabHomeSelected',
    'tabGame',
    'tabGameSelected',
    'tabLearn',
    'tabLearnSelected',
  ]) {
    assert.ok(critical.includes(name), `${name} is persistent chrome and must be critical`);
  }
});

test('the preloader awaits criticalArtwork, not allArtwork', () => {
  assert.match(
    layoutSource,
    /Asset\.loadAsync\(\[\.\.\.criticalArtwork\]\)/,
    `${LAYOUT_PATH} must gate the splash on criticalArtwork only`,
  );
  assert.doesNotMatch(
    layoutSource,
    /Asset\.loadAsync\(\[\.\.\.allArtwork\]\)/,
    'awaiting allArtwork is the regression this split exists to prevent',
  );
  assert.match(
    layoutSource,
    /runAfterInteractions\([\s\S]{0,200}?warmArtworkInOrder\(artworkWarmUpOrder/,
    'the deferred artwork must be warmed after interactions, not eagerly alongside first paint',
  );
});

// Owner request, 2026-10-21: artwork is decoded into the image cache one screen at a time, in the
// order a child reaches them, so each is instant when opened.
const warmUpSteps = [...sliceAfter('export const artworkWarmUpOrder').matchAll(/^ {2}(criticalArtwork|\[[^\]]*\]),$/gm)].map(
  (match) => (match[1] === 'criticalArtwork' ? ['criticalArtwork'] : [...match[1].matchAll(/artwork\.(\w+)/g)].map((key) => key[1])),
);

test('artwork is warmed in order: Home, B prep, C prep, C prep 2, then B results', () => {
  assert.deepEqual(warmUpSteps, [
    ['criticalArtwork'],
    ['prepareHero'],
    ['startGame'],
    ['cTaskBackground'],
    ['heroSection', 'learningPath', 'startGame'],
  ]);
});

test('every deferred image is in the warm-up, so none is left to load on first view', () => {
  const warmed = new Set(warmUpSteps.flat());
  for (const name of deferred) {
    assert.ok(warmed.has(name), `${name} is deferred but never warmed`);
  }
});

test('AuthProvider is mounted above the splash gate, so auth runs under the splash', () => {
  const providerIndex = layoutSource.indexOf('<AuthProvider>');
  const gateIndex = layoutSource.indexOf('<SplashGate');

  assert.notEqual(providerIndex, -1, 'AuthProvider must still be mounted');
  assert.notEqual(gateIndex, -1, 'the splash gate must exist');
  assert.ok(
    providerIndex < gateIndex,
    'AuthProvider must WRAP the gate. Inverting these puts session restoration behind the ' +
      'asset preload again, which is what made the two costs serial instead of overlapping',
  );
  assert.doesNotMatch(
    layoutSource,
    /const ready = fontsSettled && artworkSettled;[\s\S]{0,200}?if \(!ready\) return null;/,
    'RootLayout must not return null before AuthProvider mounts',
  );
});

test('the splash gate consults auth status, with a bounded ceiling', () => {
  assert.match(
    layoutSource,
    /status !== 'checking'/,
    'the gate must treat only "checking" as not-yet-routable; every other status is a destination',
  );
  assert.match(
    layoutSource,
    /SPLASH_AUTH_CEILING_MS = \d+/,
    'waiting on auth requires a ceiling, or a dead network traps the child on the splash',
  );
});

test('the splash-gate ready flag latches', () => {
  // `status` returns to 'checking' in normal use -- `authorizeSession` sets it on every sign-in and
  // `retryAuthorization` sets it again. Without the latch the gate would re-engage long after
  // startup and unmount the entire navigator mid-session.
  assert.match(
    layoutSource,
    /const ready = shown \|\|/,
    'ready must latch on `shown`, or a later "checking" status unmounts the navigator',
  );
});
