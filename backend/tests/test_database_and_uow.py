"""Database URL and unit-of-work lifecycle tests."""

import asyncio
from unittest.mock import AsyncMock, MagicMock

from app.infrastructure.database import async_database_url
from app.infrastructure.unit_of_work import SqlAlchemyUnitOfWork


def test_database_url_requires_postgresql_and_selects_asyncpg() -> None:
    assert async_database_url("postgresql://user:pass@db/name") == "postgresql+asyncpg://user:pass@db/name"
    try:
        async_database_url("sqlite:///local.db")
    except ValueError:
        pass
    else:
        raise AssertionError("SQLite fallback must not be accepted")


def test_uow_commits_and_closes() -> None:
    session = MagicMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.close = AsyncMock()
    factory = MagicMock(return_value=session)

    async def exercise() -> None:
        async with SqlAlchemyUnitOfWork(factory) as uow:
            await uow.commit()

    asyncio.run(exercise())
    session.commit.assert_awaited_once()
    session.rollback.assert_not_awaited()
    session.close.assert_awaited_once()


def test_uow_rolls_back_failed_transaction_and_closes() -> None:
    session = MagicMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.close = AsyncMock()
    factory = MagicMock(return_value=session)

    async def exercise() -> None:
        try:
            async with SqlAlchemyUnitOfWork(factory):
                raise RuntimeError("failed transaction")
        except RuntimeError:
            pass

    asyncio.run(exercise())
    session.rollback.assert_awaited_once()
    session.close.assert_awaited_once()
