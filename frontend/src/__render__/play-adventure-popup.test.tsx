import { fireEvent, render } from '@testing-library/react-native';

import { PlayAdventurePopup } from '@/src/features/navigation/play-adventure-popup';

// RNTL 14 `render` is ASYNC -- it returns a Promise because React 19 renders concurrently -- so
// every test awaits it and reads the queries off the resolved result. Calling it synchronously
// looks like it works (no throw) and then fails with "getByText is not a function", or, via the
// module-level `screen`, with "`render` function has not been called" on a render that did in
// fact happen. Awaiting is what makes both go away.

describe('PlayAdventurePopup', () => {
  it('renders the prompt', async () => {
    const { getByText } = await render(<PlayAdventurePopup onDismiss={jest.fn()} />);
    expect(getByText('Play Adventure')).toBeTruthy();
  });

  it('dismisses when the X is pressed', async () => {
    const onDismiss = jest.fn();
    const { getByLabelText } = await render(<PlayAdventurePopup onDismiss={onDismiss} />);
    fireEvent.press(getByLabelText('Dismiss'));
    expect(onDismiss).toHaveBeenCalledTimes(1);
  });

  it('the X is a real control, not decoration', async () => {
    // It was added so a child learns the popup is dismissible; an icon that looks pressable but is
    // not would be worse than no icon at all.
    const { getByLabelText } = await render(<PlayAdventurePopup onDismiss={jest.fn()} />);
    const close = getByLabelText('Dismiss');
    expect(close.props.accessibilityRole ?? close.props.role).toBe('button');
    expect(close.props.accessibilityState?.disabled).toBeFalsy();
  });

  it('shows a close icon, not some other glyph', async () => {
    const { getByText } = await render(<PlayAdventurePopup onDismiss={jest.fn()} />);
    expect(getByText('Ionicons:close')).toBeTruthy();
  });
});
