"""Component D's learner state: whether the intro has been seen, and the chosen language
(Component D authorization, D-011; API contract v4 rows 1-2).

READING NEVER WRITES. A learner with no row gets ``{intro_completed: false, language: "en"}`` and
no row is created. This matters more than it looks: the gate route calls the GET on every entry to
the compD tab, so a read that created rows would manufacture a ``d_learner_state`` row for every
learner who ever opened the tab, including ones who bounced straight back out -- and ``language``
would then hold "en" for children who never chose it. The default belongs to the READ.
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.application.d_learner_access import provenance, require_learner
from app.core.errors import ConflictError
from app.domain.d_profile import DLearnerStateResponse, Language
from app.domain.principal import AuthenticatedPrincipal
from app.infrastructure.persistence_models import DLearnerStateRecord
from app.infrastructure.repositories import DLearnerStateRepository
from app.infrastructure.unit_of_work import SqlAlchemyUnitOfWork


DEFAULT_LANGUAGE: Language = "en"


class DLearnerStateService:
    def __init__(self, uow_factory=SqlAlchemyUnitOfWork) -> None:
        self._uow_factory = uow_factory

    async def get_for_principal(
        self, principal: AuthenticatedPrincipal, request_id: str
    ) -> DLearnerStateResponse:
        async with self._uow_factory() as uow:
            learner_id = await require_learner(uow.session, principal)
            record = await DLearnerStateRepository(uow.session).find_for_learner(learner_id)
            if record is None:
                return DLearnerStateResponse(
                    intro_completed=False, language=DEFAULT_LANGUAGE, request_id=request_id
                )
            return DLearnerStateResponse(
                # Derived from the TIMESTAMP, not from a stored boolean: the table records when
                # the intro was finished, and the public shape answers whether it was.
                intro_completed=record.intro_completed_at is not None,
                language=record.language,  # type: ignore[arg-type]
                request_id=request_id,
            )

    async def update_for_principal(
        self,
        principal: AuthenticatedPrincipal,
        request_id: str,
        *,
        intro_completed: bool | None,
        language: Language | None,
    ) -> DLearnerStateResponse:
        """Upsert. At least one field is set; the DTO already refused an empty body.

        Concurrency: the host's own ``pg_advisory_xact_lock`` before the existence check, scoped
        to the learner, so two POSTs from the same child (the language toggle tapped twice, or a
        retried request) cannot both decide to INSERT. The ``IntegrityError`` catch is the
        backstop for a real race that slips past the lock -- the primary key on ``learner_id``
        makes the second insert impossible at the database, and translating it to 409 keeps that
        from surfacing as a 500.

        ``intro_completed`` can only ever be ``True`` here (the DTO's ``Literal[True]``), so the
        stamp is set and never cleared. A second POST does NOT move the timestamp: when the intro
        was first completed is a fact, and re-sending the flag is not a new event.
        """
        async with self._uow_factory() as uow:
            learner_id = await require_learner(uow.session, principal)
            await uow.session.execute(
                text("SELECT pg_advisory_xact_lock(hashtextextended(:scope, 0))"),
                {"scope": f"d_learner_state.upsert:{learner_id}"},
            )
            repository = DLearnerStateRepository(uow.session)
            record = await repository.get_for_update(learner_id)
            now = datetime.now(UTC)

            if record is None:
                record = DLearnerStateRecord(
                    learner_id=learner_id,
                    intro_completed_at=now if intro_completed else None,
                    language=language or DEFAULT_LANGUAGE,
                    **provenance(
                        resource_type="d_learner_state",
                        resource_id=learner_id,
                        request_id=request_id,
                        operation="d_learner_state.created",
                    ),
                )
                try:
                    await repository.add(record)
                except IntegrityError as exc:
                    raise ConflictError() from exc
            else:
                if intro_completed and record.intro_completed_at is None:
                    record.intro_completed_at = now
                if language is not None:
                    record.language = language
                record.updated_at_utc = now
                record.request_id = request_id
                record.operation_or_event_type = "d_learner_state.updated"
                await uow.session.flush()

            await uow.commit()
            return DLearnerStateResponse(
                intro_completed=record.intro_completed_at is not None,
                language=record.language,  # type: ignore[arg-type]
                request_id=request_id,
            )
