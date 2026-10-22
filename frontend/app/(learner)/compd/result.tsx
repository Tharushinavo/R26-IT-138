import ProfileResultScreen from '@/src/features/compd/screens/profile-result-screen';
import { withCompdScreen } from '@/src/features/compd/navigation';

/** One cognitive profile: ?sessionId= for a just-finished quiz, otherwise the latest. */
export default withCompdScreen(ProfileResultScreen);
