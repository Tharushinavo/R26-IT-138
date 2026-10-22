import { render } from '@testing-library/react-native';
import { Animated } from 'react-native';

import { PlayPrepCard } from '@/src/features/home/play-prep-card';

// The mastery bars are the one place a raw BKT value reaches a child, and the ruling is that it
// reaches them as bar LENGTH only -- never as a number, a label, or anything a screen reader would
// read out. The logic suite pins the probability-to-width rule and scans the source; this mounts
// the real card and checks what actually renders.

const skillState = (skill_id: string, p_l: number, observation_count: number) => ({
  skill_id,
  p_l,
  observation_count,
});

describe('PlayPrepCard', () => {
  it('mounts and shows its heading', async () => {
    const { getByText } = await render(
      <PlayPrepCard onDismiss={jest.fn()} onStart={jest.fn()} ready={false} skillStates={null} />,
    );
    expect(getByText('Ready to Play')).toBeTruthy();
  });

  // REGRESSION, 2026-10-10: the bars popped into place instead of sweeping.
  //
  // Both animations lived in one mount-only effect, but `skillStates` is null at mount and arrives
  // a round trip later. The stagger therefore ran against fills of all zeroes, animated every bar
  // from 0% to 0%, and finished -- so when the data landed, each interpolation was rebuilt with a
  // new outputRange while its driver already sat at 1, and the widths JUMPED.
  //
  // The fix starts the sweep when the data arrives, so this asserts the ORDERING that makes the
  // animation visible: no bar animation may be started while skillStates is still null.
  it('does not start the bar sweep until skill states have arrived', async () => {
    const staggerSpy = jest.spyOn(Animated, 'stagger');
    staggerSpy.mockClear();

    const view = await render(
      <PlayPrepCard onDismiss={jest.fn()} onStart={jest.fn()} ready={false} skillStates={null} />,
    );
    expect(staggerSpy).not.toHaveBeenCalled();

    // The response lands; only now may the bars sweep.
    await view.rerender(
      <PlayPrepCard
        onDismiss={jest.fn()}
        onStart={jest.fn()}
        ready
        skillStates={[skillState('counting', 0.62, 4)]}
      />,
    );
    expect(staggerSpy).toHaveBeenCalledTimes(1);

    // And it is single-shot: a later re-render must not restart a sweep mid-flight.
    await view.rerender(
      <PlayPrepCard
        onDismiss={jest.fn()}
        onStart={jest.fn()}
        ready
        skillStates={[skillState('counting', 0.62, 4)]}
      />,
    );
    expect(staggerSpy).toHaveBeenCalledTimes(1);

    staggerSpy.mockRestore();
  });

  it('lists all seven skills whether or not the server sent any state', async () => {
    const { getByText } = await render(
      <PlayPrepCard onDismiss={jest.fn()} onStart={jest.fn()} ready skillStates={null} />,
    );
    for (const label of [
      'Counting',
      'Number Sense',
      'Place Value',
      'Addition',
      'Subtraction',
      'Multiplication',
      'Division',
    ]) {
      expect(getByText(new RegExp(label))).toBeTruthy();
    }
  });

  it('never renders a mastery number, even when it has real values', async () => {
    // The ruling, checked against the rendered tree rather than the source: p_l 0.73 must produce
    // a longer bar and NO "73", "73%", or spoken value anywhere.
    const { queryByText, toJSON } = await render(
      <PlayPrepCard
        onDismiss={jest.fn()}
        onStart={jest.fn()}
        ready
        skillStates={[skillState('counting', 0.73, 12), skillState('division', 0.2, 0)]}
      />,
    );
    expect(queryByText(/73/)).toBeNull();
    expect(queryByText(/%/)).toBeNull();
    const tree = JSON.stringify(toJSON());
    // Not a blanket ban on the prop: React Native puts an empty `accessibilityValue: {}` on every
    // Pressable, so the Close and Start buttons carry one harmlessly. What must not exist is a
    // POPULATED one -- now/min/max/text is the shape a screen reader would read as a number.
    expect(tree).not.toMatch(/"accessibilityValue":\{"(now|min|max|text)"/);
    expect(tree).not.toContain('progressbar');
    // The bar tracks themselves are hidden from assistive tech outright.
    expect(tree).toContain('"importantForAccessibility":"no-hide-descendants"');
  });

  it('waits for the game before offering Start', async () => {
    const { getByText, queryByText } = await render(
      <PlayPrepCard onDismiss={jest.fn()} onStart={jest.fn()} ready={false} skillStates={null} />,
    );
    expect(getByText('Preparing…')).toBeTruthy();
    expect(queryByText('Start Game')).toBeNull();
  });

  it('offers Start once the game is ready', async () => {
    const { getByText } = await render(
      <PlayPrepCard onDismiss={jest.fn()} onStart={jest.fn()} ready skillStates={null} />,
    );
    expect(getByText('Start Game')).toBeTruthy();
  });
});
