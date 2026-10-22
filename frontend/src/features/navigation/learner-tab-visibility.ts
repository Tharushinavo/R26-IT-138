import type { LearnerTab } from '@/src/features/navigation/learner-tab-bar';

export type LearnerTabBarState =
  | { visible: false }
  | {
      visible: true;
      activeTab: LearnerTab;
      /** Pressing the already-current tab still navigates (back to that tab's root). */
      activePressEnabled: boolean;
    };

/**
 * Whether the learner layout shows the tab bar for `pathname`, and which tab is current.
 *
 * `pathname` is expo-router's group-free path (`/(learner)/compd/home` arrives as `/compd/home`).
 *
 * HIDDEN on screens that must not be left by accident: the two game surfaces (any path not listed
 * here) and compD's quiz WHILE QUESTIONS ARE SHOWING (`compdQuizRunning`), which has its own
 * confirm-before-leaving control. Its Start/Resume page shares the route and keeps the bar: that
 * page has no Back control, so the bar is the child's way out.
 *
 * compD's gate and first-run intro (Logo -> Splash -> Language) keep the bar, with compD current:
 * they open INSIDE the app's chrome, between the header and the bar (owner request, 2026-10-21).
 * Pressing compD there does nothing -- the intro is already compD's entry, and re-pressing it must
 * not restart the intro from the logo.
 */
export function tabBarFor(pathname: string, compdQuizRunning = false): LearnerTabBarState {
  if (pathname.startsWith('/compd/activity')) {
    return compdQuizRunning ? { visible: false } : { visible: true, activeTab: 'compd', activePressEnabled: true };
  }
  if (pathname === '/compd' || pathname === '/compd/' || pathname.startsWith('/compd/intro')) {
    return { visible: true, activeTab: 'compd', activePressEnabled: false };
  }
  if (pathname.startsWith('/compd/')) {
    // From any compD page other than its home, pressing compD returns to compD's home.
    return { visible: true, activeTab: 'compd', activePressEnabled: !pathname.startsWith('/compd/home') };
  }
  // The learner profile, opened from the header greeting: the bar stays, with no tab current.
  if (pathname.startsWith('/profile')) return { visible: true, activeTab: null, activePressEnabled: false };
  // The preparation screen is part of the Home journey and shows Home as current; pressing Home
  // there must still go back to Home, which is what that screen asked for.
  if (pathname.startsWith('/prepare')) return { visible: true, activeTab: 'home', activePressEnabled: true };
  if (pathname.startsWith('/home')) return { visible: true, activeTab: 'home', activePressEnabled: false };
  return { visible: false };
}

/**
 * Whether compD's layout draws MathMingo's header above the page. Every compD page has it --
 * gate, intro, home, result, history -- except the quiz, which stays full-focus like the bar.
 */
export function compdHeaderVisible(pathname: string): boolean {
  return !pathname.startsWith('/compd/activity');
}
