import type { LearnerMembershipListItem } from '@/src/api/contracts';

export function pickMembership(
  memberships: LearnerMembershipListItem[],
  membershipId?: string,
): LearnerMembershipListItem | null {
  if (membershipId) {
    const match = memberships.find((item) => item.membership_id === membershipId);
    if (match) return match;
  }
  const sorted = [...memberships].sort(
    (a, b) => new Date(b.requested_at_utc).getTime() - new Date(a.requested_at_utc).getTime(),
  );
  return sorted[0] ?? null;
}
