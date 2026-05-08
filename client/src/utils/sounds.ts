/**
 * Sound effects for the MathsMate activity screen.
 * Uses expo-av Audio to play short child-friendly sounds.
 *
 * Sound files are loaded from free CDN URLs (no local assets needed).
 */
import { Audio } from 'expo-av';

// Free sound effect URLs (royalty-free, child-friendly)
const SOUND_URLS = {
  correct: 'https://assets.mixkit.co/active_storage/sfx/2000/2000-preview.mp3',     // happy ding
  wrong: 'https://assets.mixkit.co/active_storage/sfx/2003/2003-preview.mp3',       // soft wrong buzz
  tap: 'https://assets.mixkit.co/active_storage/sfx/2568/2568-preview.mp3',         // soft click/pop
  hint: 'https://assets.mixkit.co/active_storage/sfx/2570/2570-preview.mp3',        // magic chime
  complete: 'https://assets.mixkit.co/active_storage/sfx/1435/1435-preview.mp3',    // celebration fanfare
  nextQuestion: 'https://assets.mixkit.co/active_storage/sfx/2571/2571-preview.mp3', // whoosh
};

export type SoundName = keyof typeof SOUND_URLS;

// Cache loaded sounds so we don't reload every time
const soundCache: Partial<Record<SoundName, Audio.Sound>> = {};

export async function playSound(name: SoundName): Promise<void> {
  try {
    // Re-use cached sound if possible
    let sound = soundCache[name];

    if (sound) {
      const status = await sound.getStatusAsync();
      if (status.isLoaded) {
        await sound.setPositionAsync(0);
        await sound.playAsync();
        return;
      }
    }

    // Load fresh
    const { sound: newSound } = await Audio.Sound.createAsync(
      { uri: SOUND_URLS[name] },
      { shouldPlay: true, volume: 0.7 },
    );
    soundCache[name] = newSound;
  } catch {
    // Sound is non-critical — fail silently
  }
}

export async function unloadAllSounds(): Promise<void> {
  for (const key of Object.keys(soundCache) as SoundName[]) {
    try {
      await soundCache[key]?.unloadAsync();
    } catch {}
    delete soundCache[key];
  }
}
