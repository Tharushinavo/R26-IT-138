/* eslint-disable import/first --
   The imports below sit AFTER the jest.mock blocks on purpose, the same reason as
   learner-tab-bar.test.tsx: the mock factories close over `mock*` consts that must exist first. */

// Owner request, 2026-10-21: artwork is cached one screen at a time, in order. These tests pin the
// ORDER guarantee -- a step never starts until the previous step's decode has finished -- which the
// source-level check in startup-splash-gate.test.ts (which list, in which order) cannot see.

const mockLog: string[] = [];
const mockLoadAsync = jest.fn();
const mockPrefetch = jest.fn();

// The factories call the mocks LAZILY. The module under test is imported (and so these factories
// run) before the `const`s above are initialised, so capturing `mockLoadAsync` directly would
// capture `undefined`.
jest.mock('expo-asset', () => ({
  Asset: {
    fromModule: (module: number) => ({ uri: `/assets/${module}` }),
    loadAsync: (modules: number[]) => mockLoadAsync(modules),
  },
}));
jest.mock('expo-image', () => ({
  Image: { prefetch: (uris: string[], cachePolicy: string) => mockPrefetch(uris, cachePolicy) },
}));

import { Image as ReactNativeImage } from 'react-native';

import { warmArtworkInOrder } from '@/src/utils/artwork-warm-up';

async function flush() {
  for (let i = 0; i < 10; i += 1) await Promise.resolve();
}

describe('warmArtworkInOrder', () => {
  beforeEach(() => {
    mockLog.length = 0;
    mockLoadAsync.mockReset().mockImplementation(async (modules: number[]) => {
      mockLog.push(`load ${modules.join(',')}`);
    });
    mockPrefetch.mockReset().mockImplementation(async (uris: string[]) => {
      mockLog.push(`decode ${uris.join(',')}`);
      return true;
    });
    jest.spyOn(ReactNativeImage, 'resolveAssetSource').mockImplementation((module) => {
      mockLog.push(`resolve ${String(module)}`);
      return { height: 1, scale: 1, uri: `file:///local/${String(module)}`, width: 1 };
    });
  });

  it('loads, resolves and decodes each step fully before the next, in the given order', async () => {
    await warmArtworkInOrder([[1, 2], [3], [4]]);
    expect(mockLog).toEqual([
      'load 1,2', 'resolve 1', 'resolve 2', 'decode file:///local/1,file:///local/2',
      'load 3', 'resolve 3', 'decode file:///local/3',
      'load 4', 'resolve 4', 'decode file:///local/4',
    ]);
    expect(mockPrefetch).toHaveBeenCalledWith(['file:///local/1', 'file:///local/2'], 'memory-disk');
  });

  it('does not start the next step until the current decode has finished', async () => {
    let finishFirstDecode: (ok: boolean) => void = () => undefined;
    mockPrefetch.mockImplementationOnce(
      (uris: string[]) =>
        new Promise<boolean>((resolve) => {
          mockLog.push(`decode ${uris.join(',')}`);
          finishFirstDecode = resolve;
        }),
    );

    const done = warmArtworkInOrder([[1], [2]]);
    await flush();
    expect(mockLog).toEqual(['load 1', 'resolve 1', 'decode file:///local/1']);

    finishFirstDecode(true);
    await done;
    expect(mockLog).toEqual(['load 1', 'resolve 1', 'decode file:///local/1', 'load 2', 'resolve 2', 'decode file:///local/2']);
  });

  it('keeps going after a failed step, so one bad image never blocks the screens after it', async () => {
    mockLoadAsync.mockImplementationOnce(() => Promise.reject(new Error('offline')));
    mockPrefetch.mockImplementationOnce(() => Promise.reject(new Error('decode failed')));

    await warmArtworkInOrder([[1], [2]]);
    expect(mockLog).toEqual(['resolve 1', 'load 2', 'resolve 2', 'decode file:///local/2']);
  });

  it('stops before the next step once cancelled', async () => {
    let cancelled = false;
    mockPrefetch.mockImplementationOnce(async (uris: string[]) => {
      mockLog.push(`decode ${uris.join(',')}`);
      cancelled = true;
      return true;
    });

    await warmArtworkInOrder([[1], [2]], () => cancelled);
    expect(mockLog).toEqual(['load 1', 'resolve 1', 'decode file:///local/1']);
  });
});
