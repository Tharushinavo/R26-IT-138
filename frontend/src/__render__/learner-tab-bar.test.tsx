/* eslint-disable import/first --
   The imports below sit AFTER the jest.mock blocks on purpose. ES imports are hoisted above const
   declarations, so moving them to the top would make the module under test load -- and its mock
   factory run -- before the `mock*` consts those factories close over are initialised, which is a
   temporal-dead-zone crash rather than a style question. */
import { fireEvent, render } from '@testing-library/react-native';

const mockRequestPlay = jest.fn();
const mockCharge = {
  awardForSession: jest.fn(),
  dismissPill: jest.fn(),
  dismissPlayPrep: jest.fn(),
  level: 0,
  maxLevel: 4,
  pillVisible: false,
  playPrepReady: false,
  preparingPlay: false,
  requestPlay: mockRequestPlay,
  startPreparedGame: jest.fn(),
};
jest.mock('@/src/features/navigation/adventure-charge-context', () => ({
  useAdventureCharge: () => mockCharge,
}));
// The compD tab reads the signed-in learner's subject to pick its destination from the cache.
jest.mock('@/src/auth/auth-context', () => ({
  useAuth: () => ({ me: { principal: { user_id: 'subject-1' } } }),
}));

import { router } from 'expo-router';

import { clearCompdLearnerStates, writeCompdLearnerState } from '@/src/features/compd/compd-state-cache';
import { LearnerTabBar } from '@/src/features/navigation/learner-tab-bar';

describe('LearnerTabBar', () => {
  beforeEach(() => jest.clearAllMocks());

  it('renders all three tabs', async () => {
    const { getByLabelText } = await render(<LearnerTabBar activeTab="home" playEnabled />);
    expect(getByLabelText(/^Play tab/)).toBeTruthy();
    expect(getByLabelText(/^Home tab/)).toBeTruthy();
    // Labelled "Learn", the word drawn into its brain artwork (owner request, 2026-10-21). It opens
    // Component D (compD) rather than the learner profile, which the header greeting still opens.
    expect(getByLabelText(/^Learn tab/)).toBeTruthy();
  });

  it('sends a learner with no known compD state to the compD gate', async () => {
    clearCompdLearnerStates();
    const { getByLabelText } = await render(<LearnerTabBar activeTab="home" playEnabled />);
    fireEvent.press(getByLabelText(/^Learn tab/));
    expect(router.replace).toHaveBeenCalledWith('/(learner)/compd');
  });

  it('goes straight to compD home once this session knows the intro is done', async () => {
    clearCompdLearnerStates();
    writeCompdLearnerState('subject-1', { intro_completed: true, language: 'en' });
    const { getByLabelText } = await render(<LearnerTabBar activeTab="home" playEnabled />);
    fireEvent.press(getByLabelText(/^Learn tab/));
    expect(router.replace).toHaveBeenCalledWith('/(learner)/compd/home');
  });

  it('lets a current compD tab be pressed to return to compD home when enabled', async () => {
    clearCompdLearnerStates();
    writeCompdLearnerState('subject-1', { intro_completed: true, language: 'en' });
    const { getByLabelText } = await render(<LearnerTabBar activeCompdPressEnabled activeTab="compd" playEnabled />);
    fireEvent.press(getByLabelText(/^Learn tab, selected/));
    expect(router.replace).toHaveBeenCalledWith('/(learner)/compd/home');
  });

  it('shows no tab as selected on the learner profile', async () => {
    const { queryByLabelText } = await render(<LearnerTabBar activeTab={null} playEnabled />);
    expect(queryByLabelText(/selected/)).toBeNull();
  });

  it('marks the active tab as selected and does not navigate away from it', async () => {
    const { getByLabelText } = await render(<LearnerTabBar activeTab="home" playEnabled />);
    const home = getByLabelText(/^Home tab, selected/);
    fireEvent.press(home);
    expect(router.replace).not.toHaveBeenCalled();
  });

  it('routes Play through the charge context rather than navigating itself', async () => {
    // Play is gated on the adventure battery, so the bar must not know the destination -- that
    // decision belongs to requestPlay.
    const { getByLabelText } = await render(<LearnerTabBar activeTab="home" playEnabled />);
    fireEvent.press(getByLabelText(/^Play tab/));
    expect(mockRequestPlay).toHaveBeenCalledTimes(1);
    expect(router.replace).not.toHaveBeenCalled();
  });

  it('reports Play as unavailable when it is disabled', async () => {
    const { getByLabelText } = await render(<LearnerTabBar activeTab="home" playEnabled={false} />);
    const play = getByLabelText(/^Play tab, unavailable/);
    fireEvent.press(play);
    expect(mockRequestPlay).not.toHaveBeenCalled();
  });

  it('no longer renders the Play Adventure pill, which is now the global popup', async () => {
    // It briefly lived here; blurring the page is not something the bar can do to what is drawn
    // above it, so it moved to AdventureChargeProvider. This guards against it coming back twice.
    const { queryByText } = await render(<LearnerTabBar activeTab="home" playEnabled />);
    expect(queryByText('Play Adventure')).toBeNull();
  });
});
