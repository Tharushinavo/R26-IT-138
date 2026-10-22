import { Asset } from 'expo-asset';
import { Image } from 'expo-image';
import { Image as ReactNativeImage, Platform } from 'react-native';

/**
 * Puts artwork into expo-image's cache ONE STEP AT A TIME, in the order given (owner request,
 * 2026-10-21): each step is fully downloaded and decoded before the next one starts, so the screen
 * a child is most likely to open next is always the one that is ready first.
 *
 * WHY TWO CALLS PER STEP. `Asset.loadAsync` only makes the file local (in Expo Go it is fetched
 * from Metro; in a release build it is already on disk). The visible pop-in is the DECODE, which
 * happens when expo-image first draws the picture. `Image.prefetch` with `memory-disk` does that
 * decode up front on iOS/Android, and on web loads the image through the browser's own cache, so
 * the screen that later draws it gets it instantly.
 *
 * WHY THE URI MUST BE RESOLVED THIS WAY. expo-image keys its cache by URI, so the prefetch has to
 * ask for exactly the URI the screen will draw:
 *   - native: expo-image resolves a `require()` through React Native's `resolveAssetSource`, which
 *     expo-asset hooks to return the downloaded local file once `Asset.loadAsync` has run -- hence
 *     resolving AFTER the load, never before;
 *   - web: expo-image and expo-asset build the same relative `/assets/...?platform=web&hash=...`
 *     URL from the same asset registry entry.
 *
 * Best-effort throughout: a failed step costs that picture a later on-demand load, never the app,
 * and never stops the steps after it.
 */
export async function warmArtworkInOrder(
  steps: readonly (readonly number[])[],
  isCancelled: () => boolean = () => false,
): Promise<void> {
  for (const step of steps) {
    if (isCancelled()) return;
    await Asset.loadAsync([...step]).catch(() => undefined);
    if (isCancelled()) return;
    const uris = step.map(cacheUriFor).filter((uri): uri is string => Boolean(uri));
    if (uris.length > 0) await Image.prefetch(uris, 'memory-disk').catch(() => false);
  }
}

function cacheUriFor(module: number): string | undefined {
  if (Platform.OS === 'web') return Asset.fromModule(module).uri || undefined;
  return ReactNativeImage.resolveAssetSource(module)?.uri;
}
