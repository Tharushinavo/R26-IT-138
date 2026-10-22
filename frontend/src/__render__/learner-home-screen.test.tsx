/* eslint-disable import/first --
   The imports below sit AFTER the jest.mock blocks on purpose. ES imports are hoisted above const
   declarations, so moving them to the top would make the module under test load -- and its mock
   factory run -- before the `mock*` consts those factories close over are initialised, which is a
   temporal-dead-zone crash rather than a style question. */
import { render } from '@testing-library/react-native';

// The hero is a FIRST-RUN welcome: shown on a fresh app start or a fresh login, and never again
// for the rest of that app session. On a return from Profile or Play the screen opens at the path
// card and does not scroll at all -- there is nothing above it to scroll to, because the hero is
// not rendered. These pin both halves, which no logic test can see: whether a component renders
// and whether a ScrollView is enabled are facts about the tree, not about a pure function.

const mockGetAccessToken = jest.fn(async () => 'token');
const mockAuth = {
  getAccessToken: mockGetAccessToken,
  me: { principal: { user_id: 'subject-1' }, learnerProfile: { name: 'Dev' }, classroomMembership: null },
  profileName: 'Dev',
  retryAuthorization: jest.fn(),
  status: 'authorized' as const,
};
jest.mock('@/src/auth/auth-context', () => ({ useAuth: () => mockAuth }));

jest.mock('@/src/config/env', () => ({
  readPublicConfig: () => ({
    config: {
      apiBaseUrl: 'http://localhost:8000',
      appEnvironment: 'development',
      supabasePublishableKey: 'key',
      supabaseUrl: 'http://localhost:54321',
    },
    error: null,
  }),
}));

// No active session: the state a child lands in right after finishing one.
jest.mock('@/src/api/component-b-api', () => ({
  createComponentBApi: () => ({
    getActiveSession: jest.fn(async () => ({ session: null, request_id: 'r' })),
    getSessionSummary: jest.fn(async () => null),
  }),
  getComponentBDevelopmentFixture: () => null,
}));

jest.mock('@/src/features/navigation/adventure-charge-context', () => ({
  useAdventureCharge: () => ({
    awardForSession: jest.fn(),
    dismissPill: jest.fn(),
    dismissPlayPrep: jest.fn(),
    level: 0,
    maxLevel: 4,
    pillVisible: false,
    playPrepReady: false,
    preparingPlay: false,
    requestPlay: jest.fn(),
    startPreparedGame: jest.fn(),
  }),
}));

jest.mock('@/src/features/session/b-session-prefetch', () => ({
  prefetchBSessionBootstrap: jest.fn(() => new Promise(() => {})),
}));

import { LearnerHomeScreen } from '@/src/features/home/learner-home-screen';

const HERO_LABEL = 'MathMingo adventure landscape';

function scrollViewOf(tree: unknown): Record<string, unknown> | null {
  // The screen has exactly one ScrollView. Walk the rendered tree for it rather than reaching for
  // a testID the component does not have.
  const seen: Record<string, unknown>[] = [];
  const walk = (node: unknown) => {
    if (!node || typeof node !== 'object') return;
    const record = node as Record<string, unknown>;
    const type = record.type;
    if (typeof type === 'string' && type.includes('ScrollView')) seen.push(record);
    const children = (record.children ?? []) as unknown[];
    for (const child of children) walk(child);
  };
  walk(tree);
  return seen[0] ?? null;
}

describe('LearnerHomeScreen', () => {
  beforeEach(() => jest.clearAllMocks());

  // The module-level "hero already used" flag lives inside the screen's module, and the catch-all
  // cleanup effect sets it when the screen unmounts. So the FIRST render in this file is the
  // fresh-start case and every later one is a return visit -- which is exactly the sequence a
  // child experiences, and the order these run in.
  it('shows the hero on a fresh start, and the screen scrolls', async () => {
    const { queryByLabelText, toJSON } = await render(<LearnerHomeScreen />);
    expect(queryByLabelText(HERO_LABEL)).not.toBeNull();
    const scroll = scrollViewOf(toJSON());
    expect(scroll).not.toBeNull();
    expect(scroll?.props).toMatchObject({ scrollEnabled: true });
  });

  it('does not render the hero on a return visit, and the screen does not scroll', async () => {
    const { queryByLabelText, toJSON } = await render(<LearnerHomeScreen />);
    expect(queryByLabelText(HERO_LABEL)).toBeNull();
    expect(scrollViewOf(toJSON())?.props).toMatchObject({ scrollEnabled: false });
  });

  it('offers a way into a game from the path itself, with no session in progress', async () => {
    // The dead end this fixes: all five nodes were "Not started" with no play control anywhere, so
    // the only way back into a game was scrolling up to a hero that is now not even rendered.
    const { getByLabelText, getByText } = await render(<LearnerHomeScreen />);
    expect(getByLabelText(/Question 1, up next/i)).toBeTruthy();
    expect(getByText('Start here')).toBeTruthy();
  });
});
