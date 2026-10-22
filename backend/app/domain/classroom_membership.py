"""Public contracts for the authorized classroom invite and membership scope.

The wire field names ``invite_token`` and the ``classroom_invite`` resource identity are
frozen by governance (component-b-invite-membership-authorization.json) and are not
renamed here. Product framing calls the underlying secret a "classroom join code": a
short, human-readable, high-entropy code rather than an opaque token or QR payload.
"""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


# REMOVED (20260914_0009): the membership ended because its classroom was deleted.
MembershipState = Literal["PENDING", "APPROVED", "REJECTED", "REMOVED"]
Grade = Literal["GRADE_2", "GRADE_3"]


class InviteCreateResponse(StrictModel):
    classroom_invite_id: UUID
    invite_token: str | None = Field(
        description=(
            "Plaintext classroom join code (e.g. 'M7KP-4X9D'). Present only in the "
            "first successful response for a given invite; never re-exposed on replay."
        )
    )
    token_already_issued: bool = Field(
        description="True when this response is a replay of an already-committed invite creation."
    )
    expires_at_utc: datetime | None = Field(
        default=None,
        description=(
            "When the code stops resolving. NULL for a classroom join code, which does not "
            "expire: a teacher reads it aloud to a room and children write it down, so it "
            "stays valid until the classroom is deleted."
        ),
    )
    created_at_utc: datetime
    request_id: str


class InviteRevokeResponse(StrictModel):
    classroom_invite_id: UUID
    classroom_id: UUID
    revoked_at_utc: datetime
    row_version: int
    request_id: str


class InviteTokenRequest(StrictModel):
    invite_token: str = Field(
        description=(
            "Classroom join code as displayed to the teacher. Matching is case-insensitive "
            "and ignores optional display separators such as hyphens or spaces."
        )
    )

    @field_validator("invite_token")
    @classmethod
    def bounded(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized or len(normalized) > 64:
            raise ValueError("invite_token must contain 1 to 64 characters")
        return normalized


class InviteResolveResponse(StrictModel):
    invite_resolution_id: UUID
    classroom_name: str | None
    grade: Grade
    request_id: str


class MembershipRequestResponse(StrictModel):
    classroom_membership_id: UUID
    classroom_id: UUID
    classroom_name: str | None
    grade: Grade
    state: MembershipState
    requested_at_utc: datetime
    request_id: str


class MembershipRequestListItem(StrictModel):
    classroom_membership_id: UUID
    learner_id: UUID
    learner_name: str | None
    state: MembershipState
    requested_at_utc: datetime
    decided_at_utc: datetime | None


class MembershipRequestListResponse(StrictModel):
    requests: list[MembershipRequestListItem]
    request_id: str


class MembershipDecisionResponse(StrictModel):
    classroom_membership_id: UUID
    classroom_id: UUID
    learner_id: UUID
    state: MembershipState
    decided_at_utc: datetime
    row_version: int
    request_id: str


class ClassroomLearnerListItem(StrictModel):
    learner_id: UUID
    name: str | None
    membership_id: UUID
    membership_state: MembershipState


class ClassroomLearnerListResponse(StrictModel):
    learners: list[ClassroomLearnerListItem]
    request_id: str


class LearnerMembershipListItem(StrictModel):
    membership_id: UUID
    classroom_id: UUID
    classroom_name: str | None
    grade: Grade
    state: MembershipState
    requested_at_utc: datetime
    decided_at_utc: datetime | None


class LearnerMembershipListResponse(StrictModel):
    memberships: list[LearnerMembershipListItem]
    request_id: str
