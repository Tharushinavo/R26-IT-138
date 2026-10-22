import { useWindowDimensions } from 'react-native';

import { useAuth } from '@/src/auth/auth-context';
import { LearnerHeaderBar } from '@/src/features/navigation/learner-header-bar';
import { firstNameOf } from '@/src/utils/display-name';

/**
 * MathMingo's own header on compD's main pages, so compD reads as part of one app. Same name rule
 * and same compact breakpoint as the host's Home (learner-home-screen.tsx).
 */
export function CompdHeader() {
  const { me, profileName } = useAuth();
  const compact = useWindowDimensions().height < 760;
  const displayName = firstNameOf(me?.learnerProfile?.name.trim() || profileName || 'Math Explorer');
  return <LearnerHeaderBar compact={compact} displayName={displayName} />;
}
