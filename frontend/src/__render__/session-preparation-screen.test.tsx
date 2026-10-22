/* eslint-disable import/first --
   The imports below sit AFTER the jest.mock blocks on purpose. ES imports are hoisted above const
   declarations, so moving them to the top would make the module under test load -- and its mock
   factory run -- before the `mock*` consts those factories close over are initialised, which is a
   temporal-dead-zone crash rather than a style question. */
import { render, waitFor } from '@testing-library/react-native';

// THE REGRESSION THIS FILE EXISTS FOR. `awaitingQuestion` was declared below the effects that the
// React Compiler hoists, and the screen threw "Cannot access 'awaitingQuestion' before
// initialization" the moment it mounted -- in the browser, for the owner, while `tsc --noEmit` and
// all 1366 contract tests were green. Nothing in the logic suite mounts a component, so nothing
// there could have caught it. Simply rendering this screen would have.
//
// Mocks below are boundaries only: auth, config and the API client. The screen itself, its phase
// machine and its copy are the real thing.

// Every name a jest.mock factory closes over must start with `mock`: the factories are hoisted
// above these declarations, and the prefix is how Jest permits the reference.
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

const mockCheckReadiness = jest.fn(async () => ({ status: 'ready' }));
const mockGetActiveSession = jest.fn(async () => ({ session: null, request_id: 'r' }));
jest.mock('@/src/api/component-b-api', () => ({
  createComponentBApi: () => ({ checkReadiness: mockCheckReadiness, getActiveSession: mockGetActiveSession, startSession: jest.fn(), selectOpportunity: jest.fn() }),
  getComponentBDevelopmentFixture: () => null,
}));

// The screen renders LearnerTabBar, which requires AdventureChargeProvider. Mounting the real
// provider would start a network prefetch this test has no interest in, so the context is supplied
// at its own boundary -- the screen under test is still entirely real.
jest.mock('@/src/features/navigation/adventure-charge-context', () => ({
  AdventureChargeProvider: ({ children }: { children: React.ReactNode }) => children,
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

jest.mock('@/src/features/session/session-command-store', () => ({
  clearPendingStartCommand: jest.fn(async () => undefined),
  loadPendingStartCommand: jest.fn(async () => null),
  saveActiveSessionId: jest.fn(async () => undefined),
  savePendingStartCommand: jest.fn(async () => undefined),
}));

// The prefetch is indirected through a mock the tests can re-point, so both sides of the new
// readiness behaviour are reachable: question still in flight, and question landed.
const mockPrefetch = jest.fn(() => new Promise(() => {}));
jest.mock('@/src/features/session/b-session-prefetch', () => ({
  prefetchBSessionBootstrap: (...args: unknown[]) => mockPrefetch(...(args as [])),
}));

import { dropBSessionPrefetch } from '@/src/features/session/b-session-prefetch-cache';
import { SessionPreparationScreen } from '@/src/features/session/session-preparation-screen';

describe('SessionPreparationScreen', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    // The cache is module-level and keyed by learner, so one test's entry would otherwise decide
    // the next test's readiness.
    dropBSessionPrefetch('subject-1');
    mockPrefetch.mockReturnValue(new Promise(() => {}));
  });

  it('mounts without throwing', async () => {
    // The whole point. A temporal-dead-zone error, a bad hook order or a missing import all fail
    // here, and none of them are visible to the type-checker or the logic suite.
    await expect(render(<SessionPreparationScreen />)).resolves.toBeTruthy();
  });

  it('shows its heading once mounted', async () => {
    const { getByText } = await render(<SessionPreparationScreen />);
    expect(getByText("Let's get ready!")).toBeTruthy();
  });

  it('says the question is still being built while the prefetch is in flight', async () => {
    // The fix for the press-then-wait: "Session ready" with an enabled "Start Adventure" was a
    // lie while the first question had not arrived, and pressing it stalled on the next screen.
    const { getByText, queryByText } = await render(<SessionPreparationScreen />);
    await waitFor(() => expect(getByText('Getting ready…')).toBeTruthy());
    expect(getByText('Building your question')).toBeTruthy();
    expect(queryByText('Start Adventure')).toBeNull();
    expect(queryByText('Session ready')).toBeNull();
  });

  it('offers the real control once the question has landed', async () => {
    mockPrefetch.mockReturnValue(Promise.resolve(null) as never);
    const { getByText } = await render(<SessionPreparationScreen />);
    await waitFor(() => expect(getByText('Start Adventure')).toBeTruthy());
    expect(getByText('Session ready')).toBeTruthy();
  });
});
