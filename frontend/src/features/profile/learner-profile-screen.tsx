// The learner's own profile: the four facts about their account this app can actually show (name,
// classroom, grade, gender) and a way to sign out. Nothing here is invented — every field comes
// straight from `useAuth()`, the same sources session-preparation-screen.tsx and
// learner-home-screen.tsx already read (`me.learnerProfile.name`, `me.classroomMembership`), plus
// `profileGender` (new: auth-context.tsx's own gender is captured at sign-up into Supabase's
// user_metadata, since the backend's LearnerProfileResponse carries no gender field at all — see
// that file's readGender for why it's read from the session rather than from `me`).
//
// A field with nothing to show renders neither a fabricated value nor an error: a classroom only
// renders once an APPROVED membership actually exists (mirroring the prep screen's own
// `classroom` derivation exactly), and gender only renders once a value was actually captured.
// There is no "Not set" placeholder row for either — an absent fact is not itself a fact worth
// display space.

import { Ionicons } from '@expo/vector-icons';
import { useEffect, useState } from 'react';
import { Modal, Pressable, StyleSheet, useWindowDimensions, View } from 'react-native';

import { fetchTeacherNextStep, type TeacherNextStep } from '@/src/api/teacher-next-step-api';
import { useAuth } from '@/src/auth/auth-context';
import { AppText } from '@/src/components/app-text';
import { LearnerHeaderBar } from '@/src/features/navigation/learner-header-bar';
import { colors, radius, spacing, typography } from '@/src/theme/tokens';
import { firstNameOf } from '@/src/utils/display-name';

const gradeLabels: Record<'GRADE_2' | 'GRADE_3', string> = {
  GRADE_2: 'Grade 2',
  GRADE_3: 'Grade 3',
};

const genderLabels: Record<'female' | 'male', string> = {
  female: 'Girl',
  male: 'Boy',
};

type ProfileRow = {
  icon: React.ComponentProps<typeof Ionicons>['name'];
  color: string;
  label: string;
  value: string;
};

export function LearnerProfileScreen() {
  const compact = useWindowDimensions().height < 760;
  const { getAccessToken, me, profileGender, profileName, signOut } = useAuth();

  // THE TEACHER'S NEXT STEP (spec §4 steps 6-8; owner decision 2026-10-10).
  //
  // COMPONENT STATE ONLY -- no module cache, no storage. §4 step 8: "Never cache it across
  // accounts; never persist it locally." That is not a style preference here: this app runs on
  // shared classroom devices, and a cached decision about one child appearing in another child's
  // profile is the worst failure this feature has. Living in component state means it cannot
  // outlive the screen, let alone the account.
  //
  // `null` covers BOTH "no decision" and "could not ask" -- see fetchTeacherNextStep, which
  // deliberately makes them indistinguishable because they render identically.
  const [nextStep, setNextStep] = useState<TeacherNextStep | null>(null);
  const [parentNotice, setParentNotice] = useState<'message' | 'none' | null>(null);

  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      const accessToken = await getAccessToken();
      if (cancelled || !accessToken) return;
      const result = await fetchTeacherNextStep(accessToken);
      if (cancelled) return;
      setNextStep(result);
    };
    void load();
    return () => {
      cancelled = true;
    };
    // Re-runs when the signed-in learner changes, so one account's decision can never be left on
    // screen for the next.
  }, [getAccessToken, me?.principal.user_id]);
  const displayName = me?.learnerProfile?.name.trim() || profileName || 'Math Explorer';
  // Only an APPROVED membership is a real classroom the learner is in — mirrors
  // session-preparation-screen.tsx's own `classroom` derivation exactly, so the two screens can
  // never disagree about whether a classroom is showing.
  const classroom = me?.classroomMembership?.state === 'APPROVED' ? me.classroomMembership : null;

  const rows: ProfileRow[] = [
    { color: colors.primary, icon: 'person', label: 'Name', value: firstNameOf(displayName) },
    ...(classroom
      ? [
          {
            color: colors.accentBlue,
            icon: 'school' as const,
            label: 'Classroom',
            value: classroom.classroom_name ?? 'Your classroom',
          },
          {
            color: colors.accentGreen,
            icon: 'ribbon' as const,
            label: 'Grade',
            value: gradeLabels[classroom.grade],
          },
        ]
      : []),
    ...(profileGender
      ? [
          {
            color: colors.accentWingPink,
            icon: 'happy' as const,
            label: 'Gender',
            value: genderLabels[profileGender],
          },
        ]
      : []),
  ];

  return (
    <View style={styles.safeArea}>
      <View style={styles.mobileCanvas}>
        <LearnerHeaderBar compact={compact} displayName={firstNameOf(displayName)} />

        <View style={[styles.content, compact && styles.contentCompact]}>
          <View style={styles.avatarWrap}>
            {/* LONG-PRESS, NOT TAP, and that choice is the feature's ethics (owner decision,
                2026-10-10). The spec's §2 worry is that a 7-9 year old reads a teacher's judgement
                about them as a verdict. A long press is a gesture children of this age rarely
                discover by accident, so the message is reachable by an adult sitting with the
                child while not being put in front of the child. There is no tap handler and no
                visible "open" affordance for exactly that reason -- do not add one.
                
                `delayLongPress` is left at the platform default rather than shortened: a shorter
                hold would make accidental discovery likelier, which is the thing being avoided. */}
            <Pressable
              accessibilityHint="Press and hold for a message for a grown-up"
              accessibilityLabel="Profile picture"
              accessibilityRole="button"
              onLongPress={() => setParentNotice(nextStep ? 'message' : 'none')}>
              <View style={styles.avatarCircle}>
                <Ionicons color={colors.primaryForeground} name="person" size={44} />
              </View>
              {/* The dot renders ONLY when a decision exists. §4 step 7: a null next step is
                  "nothing at all -- no empty state, no placeholder", and an always-present grey dot
                  would be precisely the placeholder that invites a child to wonder why. */}
              {nextStep ? <View style={styles.avatarDot} /> : null}
            </Pressable>
            <AppText style={styles.avatarName}>{displayName}</AppText>
          </View>

          {/* FOR THE GROWN-UP, NOT THE CHILD. Both branches are deliberately plain and carry no
              risk status, score, ranking, reason or research vocabulary -- §3.4: "A child sees what
              to do next, never what the system thinks of them." */}
          <Modal
            animationType="fade"
            onRequestClose={() => setParentNotice(null)}
            transparent
            visible={parentNotice !== null}>
            <Pressable style={styles.noticeBackdrop} onPress={() => setParentNotice(null)}>
              <Pressable style={styles.noticeCard} onPress={() => undefined}>
                {parentNotice === 'message' && nextStep ? (
                  <>
                    {/* VERBATIM. §3.3: Component 3 returns finished sentences and this app "must
                        not map proposed_action to text of its own" -- one source of wording, one
                        place to review it. Nothing here reformats, truncates or re-cases them. */}
                    <AppText style={styles.noticeTitle}>{nextStep.headline}</AppText>
                    <AppText style={styles.noticeBody}>{nextStep.detail}</AppText>
                    {nextStep.disclosure ? (
                      <AppText style={styles.noticeDisclosure}>{nextStep.disclosure}</AppText>
                    ) : null}
                  </>
                ) : (
                  <>
                    {/* THE NO-MESSAGE BRANCH IS A DELIBERATE DEVIATION FROM §4 STEP 7, which says a
                        null next step must render "nothing at all". Owner decision, 2026-10-10:
                        the demo learner has no teacher decision, so without this there would be
                        nothing to show at all.
                        
                        It is narrowed to keep the spirit of the rule: it appears only behind the
                        same adult-facing long press, never as a visible empty state, and it says
                        nothing about the child. A passive child never encounters it. If the
                        Component 3 owner declines the deviation, deleting this branch -- so a long
                        press with no dot does nothing -- is the whole change. */}
                    <AppText style={styles.noticeTitle}>No message yet</AppText>
                    <AppText style={styles.noticeBody}>
                      There is nothing from the teacher right now. If they choose a next step, it
                      will appear here.
                    </AppText>
                  </>
                )}
                <Pressable
                  accessibilityLabel="Close"
                  accessibilityRole="button"
                  onPress={() => setParentNotice(null)}
                  style={({ pressed }) => [styles.noticeButton, pressed && styles.noticeButtonPressed]}>
                  <AppText style={styles.noticeButtonText}>CLOSE</AppText>
                </Pressable>
              </Pressable>
            </Pressable>
          </Modal>

          <View style={styles.card}>
            {rows.map((row, index) => (
              <View
                key={row.label}
                style={[styles.row, index === rows.length - 1 && styles.rowLast]}>
                <View style={[styles.rowIcon, { backgroundColor: row.color }]}>
                  <Ionicons color={colors.primaryForeground} name={row.icon} size={20} />
                </View>
                <View style={styles.rowCopy}>
                  <AppText style={styles.rowLabel}>{row.label}</AppText>
                  <AppText style={styles.rowValue}>{row.value}</AppText>
                </View>
              </View>
            ))}
          </View>

          <Pressable
            accessibilityRole="button"
            onPress={() => void signOut()}
            style={({ pressed }) => [styles.logoutButton, pressed && styles.logoutButtonPressed]}>
            <Ionicons color={colors.danger} name="log-out-outline" size={22} />
            <AppText style={styles.logoutText}>LOG OUT</AppText>
          </Pressable>
        </View>

      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  avatarCircle: {
    alignItems: 'center',
    backgroundColor: colors.primary,
    borderColor: colors.surface1,
    borderRadius: radius.pill,
    borderWidth: 4,
    elevation: 4,
    height: 96,
    justifyContent: 'center',
    shadowColor: colors.foreground,
    shadowOffset: { width: 0, height: 3 },
    shadowOpacity: 0.18,
    shadowRadius: 5,
    width: 96,
  },
  avatarName: {
    fontFamily: typography.fonts.display,
    fontSize: typography.fontSize.subtitle,
    lineHeight: typography.lineHeight.subtitle,
  },
  // Top-right of the avatar, overlapping its edge the way a notification badge does. Absolute so
  // it cannot shift the avatar's own layout when it appears or goes.
  avatarDot: {
    backgroundColor: colors.danger,
    borderColor: colors.surface1,
    borderRadius: radius.pill,
    borderWidth: 3,
    height: 22,
    position: 'absolute',
    right: 0,
    top: 2,
    width: 22,
  },
  avatarWrap: { alignItems: 'center', gap: spacing.sm },
  noticeBackdrop: {
    alignItems: 'center',
    backgroundColor: 'rgba(17, 17, 17, 0.45)',
    flex: 1,
    justifyContent: 'center',
    padding: spacing.lg,
  },
  noticeBody: {
    color: colors.textSecondary,
    fontFamily: typography.fonts.body,
    fontSize: typography.fontSize.body,
    lineHeight: typography.lineHeight.body,
    textAlign: 'center',
  },
  noticeButton: {
    alignItems: 'center',
    backgroundColor: colors.primary,
    borderRadius: radius.md,
    justifyContent: 'center',
    marginTop: spacing.sm,
    minHeight: 48,
    paddingHorizontal: spacing.lg,
  },
  noticeButtonPressed: { opacity: 0.85 },
  noticeButtonText: {
    color: colors.primaryForeground,
    fontFamily: typography.fonts.bold,
    fontSize: typography.fontSize.body,
  },
  noticeCard: {
    backgroundColor: colors.surface1,
    borderRadius: radius.lg,
    gap: spacing.sm,
    maxWidth: 420,
    padding: spacing.lg,
    width: '100%',
  },
  // Component 3's own provenance line. Smaller and muted: it is a qualification on the message
  // above, not a second message.
  noticeDisclosure: {
    color: colors.textSecondary,
    fontFamily: typography.fonts.body,
    fontSize: typography.fontSize.xs,
    lineHeight: typography.lineHeight.xs,
    textAlign: 'center',
  },
  noticeTitle: {
    fontFamily: typography.fonts.bold,
    fontSize: typography.fontSize.lg,
    lineHeight: typography.lineHeight.lg,
    textAlign: 'center',
  },
  card: {
    backgroundColor: colors.surface1,
    borderBottomColor: colors.borderStrong,
    borderBottomWidth: 3,
    borderColor: colors.border,
    borderRadius: radius.lg,
    borderWidth: 2,
    padding: spacing.smPlus,
  },
  content: { flex: 1, gap: spacing.lg, paddingHorizontal: spacing.md, paddingTop: spacing.sm },
  contentCompact: { gap: spacing.md },
  logoutButton: {
    alignItems: 'center',
    alignSelf: 'stretch',
    backgroundColor: colors.dangerSoft,
    borderColor: colors.danger,
    borderRadius: radius.md,
    borderWidth: 2,
    flexDirection: 'row',
    gap: spacing.sm,
    justifyContent: 'center',
    minHeight: 56,
  },
  logoutButtonPressed: { opacity: 0.72 },
  logoutText: {
    color: colors.danger,
    fontFamily: typography.fonts.bold,
    fontSize: typography.fontSize.body,
    letterSpacing: typography.letterSpacing.button,
  },
  mobileCanvas: { alignSelf: 'center', backgroundColor: colors.background, flex: 1, maxWidth: 500, width: '100%' },
  row: {
    alignItems: 'center',
    borderBottomColor: colors.border,
    borderBottomWidth: 1,
    flexDirection: 'row',
    gap: spacing.smPlus,
    paddingVertical: spacing.smPlus,
  },
  rowCopy: { flex: 1, gap: 2 },
  rowIcon: {
    alignItems: 'center',
    borderRadius: radius.pill,
    height: 40,
    justifyContent: 'center',
    width: 40,
  },
  rowLabel: { color: colors.textSecondary, fontSize: typography.fontSize.sm },
  rowLast: { borderBottomWidth: 0, paddingBottom: 0 },
  rowValue: {
    fontFamily: typography.fonts.bold,
    fontSize: typography.fontSize.lg,
    lineHeight: typography.lineHeight.lg,
  },
  safeArea: { backgroundColor: colors.background, flex: 1 },
});
