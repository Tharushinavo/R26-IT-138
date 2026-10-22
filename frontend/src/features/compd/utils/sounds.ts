
/**
 * Sound effects for the MathsMate activity screen.
 *
 * Uses expo-audio to play short, child-friendly sound effects.
 * Sound files are loaded from remote URLs.
 *
 * Features:
 * - Seven sound effects
 * - Cached audio players
 * - Volume control
 * - Replay support
 * - Silent failure if audio is unavailable
 * - Cleanup of cached audio players
 */

import {
  createAudioPlayer,
  setAudioModeAsync,
} from 'expo-audio';

// Royalty-free sound effect URLs
const SOUND_URLS = {
  correct:
    'https://assets.mixkit.co/active_storage/sfx/2000/2000-preview.mp3',

  wrong:
    'https://assets.mixkit.co/active_storage/sfx/2364/2364-preview.mp3',

  tap:
    'https://assets.mixkit.co/active_storage/sfx/2568/2568-preview.mp3',

  hint:
    'https://assets.mixkit.co/active_storage/sfx/2570/2570-preview.mp3',

  complete:
    'https://assets.mixkit.co/active_storage/sfx/1435/1435-preview.mp3',

  nextQuestion:
    'https://assets.mixkit.co/active_storage/sfx/2571/2571-preview.mp3',

  alarm:
    'https://assets.mixkit.co/active_storage/sfx/1647/1647-preview.mp3',
};

export type SoundName = keyof typeof SOUND_URLS;

type AudioPlayer = ReturnType<typeof createAudioPlayer>;

// Cache players to avoid creating a new player on every interaction.
const soundCache: Partial<Record<SoundName, AudioPlayer>> = {};

let audioModeConfigured = false;
let audioModePromise: Promise<void> | null = null;

/**
 * Configure audio playback once.
 *
 * Allows sound effects to play when the device is in silent mode.
 */
async function configureAudioMode(): Promise<void> {
  if (audioModeConfigured) {
    return;
  }

  if (!audioModePromise) {
    audioModePromise = setAudioModeAsync({
      playsInSilentMode: true,
    })
      .then(() => {
        audioModeConfigured = true;
      })
      .finally(() => {
        audioModePromise = null;
      });
  }

  await audioModePromise;
}

/**
 * Get a cached player or create a new one.
 */
function getSoundPlayer(name: SoundName): AudioPlayer {
  let player = soundCache[name];

  if (!player) {
    player = createAudioPlayer({
      uri: SOUND_URLS[name],
    });

    player.volume = 0.7;
    soundCache[name] = player;
  }

  return player;
}

/**
 * Play a sound effect.
 *
 * Example:
 * await playSound('correct');
 * await playSound('wrong');
 * await playSound('complete');
 *
 * Audio errors are ignored because sound effects
 * are not essential to the learning activity.
 */
export async function playSound(name: SoundName): Promise<void> {
  try {
    await configureAudioMode();

    const player = getSoundPlayer(name);

    player.volume = 0.7;

    // Reset playback position before replaying.
    player.seekTo(0);

    // Start playback.
    player.play();
  } catch {
    // Fail silently if audio is unavailable.
  }
}

/**
 * Release all cached audio players.
 *
 * Call this when the screen or application no longer
 * needs the cached sound effects.
 */
export async function unloadAllSounds(): Promise<void> {
  const players = Object.values(soundCache);

  // Clear the cache first to prevent reuse during cleanup.
  for (const key of Object.keys(soundCache) as SoundName[]) {
    delete soundCache[key];
  }

  for (const player of players) {
    try {
      player?.remove();
    } catch {
      // Ignore individual player cleanup errors.
    }
  }

  audioModeConfigured = false;
}
