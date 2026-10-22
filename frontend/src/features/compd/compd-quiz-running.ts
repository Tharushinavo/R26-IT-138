// Whether compD's quiz is showing questions right now, for the learner layout's tab bar.
//
// The Start/Resume page and the running quiz share one route (`/compd/activity`), so the pathname
// alone can't tell them apart. The quiz screen sets this flag; the layout reads it. The bar is
// hidden only while questions are on screen -- on the Start/Resume page it stays, because that
// page has no Back control of its own (owner request, 2026-10-21) and a child must be able to leave.

import { useSyncExternalStore } from 'react';

let running = false;
const listeners = new Set<() => void>();

export function setCompdQuizRunning(next: boolean): void {
  if (running === next) return;
  running = next;
  listeners.forEach((listener) => listener());
}

function subscribe(listener: () => void): () => void {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
}

const read = () => running;

export function useCompdQuizRunning(): boolean {
  return useSyncExternalStore(subscribe, read, read);
}
