"""Teacher-initiated classroom deletion (2026-09-14, migration 20260914_0009).

A SOFT delete: the classroom disappears from every teacher read and command, its join code
stops working, and each PENDING/APPROVED membership becomes REMOVED -- so the learner is sent
back to enter a classroom code and can join another classroom. The learner's own rows are
never touched.
"""

import asyncio
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.infrastructure.persistence_models import (
    AppUser,
    AppUserLearnerLink,
    Classroom,
    ClassroomInvite,
    ClassroomMembership,
    Learner,
)
from tests.test_classroom_membership import (
    _engine,
    audit_count,
    client_for,
    close_client,
    create_classroom,
    create_invite,
    headers,
    request_membership,
    setup_learner,
    setup_teacher,
    upgrade,
)


def delete(subject: str, classroom_id: UUID, confirmation_name: str, key: str | None = None):
    client = client_for(subject)
    try:
        return client.post(
            f"/api/v1/classrooms/{classroom_id}/delete",
            json={"confirmation_name": confirmation_name},
            headers=headers(key or str(uuid4())),
        )
    finally:
        close_client(client)


def approve(subject: str, membership_id: str):
    client = client_for(subject)
    try:
        return client.post(f"/api/v1/classroom-memberships/{membership_id}/approve", json={}, headers=headers(str(uuid4())))
    finally:
        close_client(client)


def get(subject: str, path: str):
    client = client_for(subject)
    try:
        return client.get(path)
    finally:
        close_client(client)


def joined_learner(teacher: str, token: str, *, approved: bool) -> tuple[str, str]:
    """A learner with a membership via join code `token`; returns (subject, membership id).

    The plaintext code is returned only by the FIRST invite call for a classroom, so callers
    create it once and pass it in."""
    learner = f"learner-del-{uuid4()}"
    setup_learner(learner)
    requested = request_membership(learner, token)
    assert requested.status_code == 201
    membership_id = requested.json()["classroom_membership_id"]
    if approved:
        assert approve(teacher, membership_id).status_code == 200
    return learner, membership_id


async def rows_for(classroom_id: UUID, learner_subject: str) -> tuple[Classroom, list[ClassroomInvite], list[ClassroomMembership], Learner]:
    engine = await _engine()
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        classroom = await session.get(Classroom, classroom_id)
        invites = list(await session.scalars(select(ClassroomInvite).where(ClassroomInvite.classroom_id == classroom_id)))
        memberships = list(await session.scalars(select(ClassroomMembership).where(ClassroomMembership.classroom_id == classroom_id)))
        user = await session.scalar(select(AppUser).where(AppUser.supabase_subject == learner_subject))
        link = await session.scalar(select(AppUserLearnerLink).where(AppUserLearnerLink.user_id == user.user_id))
        learner = await session.get(Learner, link.learner_id)
    await engine.dispose()
    return classroom, invites, memberships, learner


def test_delete_soft_deletes_revokes_code_and_frees_learners() -> None:
    upgrade()
    teacher = f"teacher-del-{uuid4()}"
    setup_teacher(teacher)
    classroom_id = create_classroom(teacher, "Grade 2 Delete")
    token = create_invite(teacher, classroom_id)["invite_token"]
    approved_learner, _ = joined_learner(teacher, token, approved=True)
    pending_learner, _ = joined_learner(teacher, token, approved=False)

    response = delete(teacher, classroom_id, "Grade 2 Delete")
    assert response.status_code == 200, response.text
    assert set(response.json()) == {"classroom_id", "deleted_at_utc", "removed_membership_count", "row_version", "request_id"}
    assert response.json()["removed_membership_count"] == 2

    classroom, invites, memberships, learner = asyncio.run(rows_for(classroom_id, approved_learner))
    assert classroom is not None and classroom.deleted_at_utc is not None and classroom.deleted_by_user_id is not None
    assert invites and all(invite.revoked_at_utc is not None for invite in invites)
    assert {m.state for m in memberships} == {"REMOVED"}
    assert all(m.decided_at_utc is not None and m.decided_by_user_id is not None for m in memberships)
    # The learner row is untouched -- including the grade approval gave it.
    assert learner.name == "Learner" and learner.grade == 2 and learner.status == "ACTIVE"
    assert asyncio.run(audit_count("classroom.deleted", classroom_id)) == 1

    # Gone from every teacher read.
    assert all(c["classroom_id"] != str(classroom_id) for c in get(teacher, "/api/v1/classrooms").json()["classrooms"])
    assert get(teacher, f"/api/v1/classrooms/{classroom_id}").status_code == 404
    assert get(teacher, f"/api/v1/classrooms/{classroom_id}/membership-requests").status_code == 404
    assert get(teacher, f"/api/v1/classrooms/{classroom_id}/learners").status_code == 404

    # Each learner has no classroom any more, so the app asks them for a code again.
    for subject in (approved_learner, pending_learner):
        assert get(subject, "/api/v1/learner/classrooms").json()["memberships"] == []


def test_a_removed_learner_can_join_another_classroom() -> None:
    upgrade()
    teacher = f"teacher-del-{uuid4()}"
    setup_teacher(teacher)
    old_id = create_classroom(teacher, "Old Room")
    learner, _ = joined_learner(teacher, create_invite(teacher, old_id)["invite_token"], approved=True)
    assert delete(teacher, old_id, "Old Room").status_code == 200

    new_id = create_classroom(teacher, "New Room", "GRADE_3")
    new_token = create_invite(teacher, new_id)["invite_token"]
    requested = request_membership(learner, new_token)
    assert requested.status_code == 201
    # Approval would 409 if the old APPROVED membership still held the one-per-learner index.
    assert approve(teacher, requested.json()["classroom_membership_id"]).status_code == 200
    memberships = get(learner, "/api/v1/learner/classrooms").json()["memberships"]
    assert [(m["classroom_id"], m["state"]) for m in memberships] == [(str(new_id), "APPROVED")]


def test_the_deleted_classrooms_code_no_longer_works() -> None:
    upgrade()
    teacher = f"teacher-del-{uuid4()}"
    setup_teacher(teacher)
    classroom_id = create_classroom(teacher, "Code Room")
    token = create_invite(teacher, classroom_id)["invite_token"]
    assert delete(teacher, classroom_id, "Code Room").status_code == 200
    learner = f"learner-del-{uuid4()}"
    setup_learner(learner)
    assert request_membership(learner, token).status_code == 409


def test_confirmation_must_match_the_name_exactly() -> None:
    upgrade()
    teacher = f"teacher-del-{uuid4()}"
    setup_teacher(teacher)
    classroom_id = create_classroom(teacher, "Grade 3B")
    for wrong in ("grade 3b", "Grade 3", "", "Grade 3BB"):
        response = delete(teacher, classroom_id, wrong)
        assert response.status_code == 422 and response.json()["error"]["code"] == "CLASSROOM_NAME_MISMATCH"
    assert get(teacher, f"/api/v1/classrooms/{classroom_id}").status_code == 200
    # Surrounding spaces are forgiven; the name itself is not.
    assert delete(teacher, classroom_id, "  Grade 3B ").status_code == 200


def test_ownership_role_and_replay() -> None:
    upgrade()
    owner = f"teacher-del-{uuid4()}"
    other = f"teacher-del-{uuid4()}"
    setup_teacher(owner)
    setup_teacher(other)
    classroom_id = create_classroom(owner, "Mine")
    learner = f"learner-del-{uuid4()}"
    setup_learner(learner)

    assert delete(other, classroom_id, "Mine").status_code == 404
    assert delete(learner, classroom_id, "Mine").status_code == 403

    key = str(uuid4())
    first = delete(owner, classroom_id, "Mine", key)
    replay = delete(owner, classroom_id, "Mine", key)
    assert first.status_code == 200 and replay.status_code == 200
    assert replay.json()["deleted_at_utc"] == first.json()["deleted_at_utc"]
    # A new key on an already-deleted classroom finds nothing to delete.
    assert delete(owner, classroom_id, "Mine").status_code == 404


def test_a_deleted_name_can_be_used_again() -> None:
    upgrade()
    teacher = f"teacher-del-{uuid4()}"
    setup_teacher(teacher)
    classroom_id = create_classroom(teacher, "Reusable")
    assert delete(teacher, classroom_id, "Reusable").status_code == 200
    assert create_classroom(teacher, "Reusable") != classroom_id
