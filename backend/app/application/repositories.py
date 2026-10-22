"""Repository contracts for neutral BE2 persisted facts only."""

from typing import Protocol, TypeVar
from uuid import UUID


ModelT = TypeVar("ModelT")


class NeutralRepository(Protocol[ModelT]):
    async def add(self, record: ModelT) -> None: ...
    async def get_by_id(self, record_id: UUID) -> ModelT | None: ...
    async def exists(self, record_id: UUID) -> bool: ...


class IdempotencyRepository(NeutralRepository[ModelT], Protocol[ModelT]):
    async def find_scoped(
        self,
        actor_user_id: UUID,
        http_method: str,
        operation_identifier: str,
        idempotency_key: str,
    ) -> ModelT | None: ...


class AuditRepository(NeutralRepository[ModelT], Protocol[ModelT]):
    """Append/read contract; no update or delete operation is authorized."""
