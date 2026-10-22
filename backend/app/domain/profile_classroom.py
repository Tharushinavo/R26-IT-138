"""Public contracts for the limited profile and classroom scope."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, field_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ProfileCreateRequest(StrictModel):
    name: str

    @field_validator("name")
    @classmethod
    def valid_name(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized or len(normalized) > 255:
            raise ValueError("name must contain 1 to 255 characters")
        return normalized


class TeacherProfileResponse(StrictModel):
    teacher_profile_id: UUID
    user_id: UUID
    profile_type: Literal["TEACHER"]
    name: str
    email: str | None
    created_at_utc: datetime
    request_id: str


class LearnerProfileResponse(StrictModel):
    learner_id: UUID
    user_id: UUID
    profile_type: Literal["LEARNER"]
    name: str
    email: str | None
    created_at_utc: datetime
    request_id: str


class ClassroomCreateRequest(StrictModel):
    name: str | None = None
    grade: Literal["GRADE_2", "GRADE_3"]

    @field_validator("name")
    @classmethod
    def valid_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        if not normalized or len(normalized) > 255:
            raise ValueError("name must contain 1 to 255 characters when provided")
        return normalized


class ClassroomResponse(StrictModel):
    classroom_id: UUID
    name: str | None
    grade: Literal["GRADE_2", "GRADE_3"]
    teacher_profile_id: UUID
    created_at_utc: datetime
    row_version: int
    request_id: str


class ClassroomListItem(StrictModel):
    classroom_id: UUID
    name: str | None
    grade: Literal["GRADE_2", "GRADE_3"]
    created_at_utc: datetime
    row_version: int


class ClassroomListResponse(StrictModel):
    classrooms: list[ClassroomListItem]
    request_id: str


class ClassroomDeleteRequest(StrictModel):
    """The classroom name, typed by the teacher, as the confirmation for deleting it."""

    confirmation_name: str

    @field_validator("confirmation_name")
    @classmethod
    def valid_confirmation(cls, value: str) -> str:
        if len(value) > 255:
            raise ValueError("confirmation_name must contain at most 255 characters")
        return value


class ClassroomDeleteResponse(StrictModel):
    classroom_id: UUID
    deleted_at_utc: datetime
    removed_membership_count: int
    row_version: int
    request_id: str
