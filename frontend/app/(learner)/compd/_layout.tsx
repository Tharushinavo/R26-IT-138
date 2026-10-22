import { Stack, usePathname } from 'expo-router';
import { StyleSheet, View } from 'react-native';

import { CompdHeader } from '@/src/features/compd/compd-header';
import { LanguageProvider } from '@/src/features/compd/i18n/language-context';
import { compdHeaderVisible } from '@/src/features/navigation/learner-tab-visibility';

/**
 * Component D (compD) pages. No native header and no animation, matching every other learner stack.
 *
 * MathMingo's own header is drawn HERE, once, above the stack -- not by each compD screen -- so it
 * stays mounted while compD pages change and the intro opens inside the app's chrome: header on
 * top, the learner layout's tab bar below, the page in the space between (owner request,
 * 2026-10-21). The quiz is the one page without it (`compdHeaderVisible`).
 *
 * compD's English/Sinhala choice is provided here too, so it is shared by every compD page and by
 * nothing outside compD (plan v5 Q5).
 */
export default function CompdLayout() {
  const pathname = usePathname();
  return (
    <LanguageProvider>
      <View style={styles.page}>
        {compdHeaderVisible(pathname) ? <CompdHeader /> : null}
        <View style={styles.page}>
          <Stack screenOptions={{ animation: 'none', headerShown: false }} />
        </View>
      </View>
    </LanguageProvider>
  );
}

const styles = StyleSheet.create({
  page: { flex: 1 },
});
