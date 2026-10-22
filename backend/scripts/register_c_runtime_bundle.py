"""CONNECT Step 6 -- registers the owner-approved Component C runtime bundle manifest
(``provenance/c-runtime-bundle-approved-1.0.json``) as a real ``c_runtime_bundle_records`` row.

This is the DB-backed anchor ``CSessionService.create`` already requires and has always required
(``CRuntimeBundleRecordRepository.find_by_version(bundle.bundle_version)``,
``c_session_service.py:153-155``): ``resolve_c_bundle_and_catalogue`` reads the manifest FILE, it
never touches the database, and the FK column on ``c_sessions`` needs a real row. Every prior
CONNECT step made the manifest file itself correct; this step is the first to touch the database.

Run as ``python -m scripts.register_c_runtime_bundle`` from ``backend/`` -- NEVER
``python scripts/register_c_runtime_bundle.py`` (HANDOVER.md §6.3: the latter breaks provenance).

IMPORTABLE CORE / SIDE-EFFECTS-UNDER-__main__ (mirrors ``generate_c_template_registry.py``'s own
split): ``register_bundle`` takes an already-open session and does the one write; it opens no
engine and reads no environment itself, so nothing is written to any database merely by importing
this module. Engine/session construction and CLI wiring live in ``main``, under ``__main__`` only.

PRECEDENT NOTE, RECORDED BECAUSE THE WORK ORDER'S OWN CITATION WAS WRONG AND IT IS WORTH KNOWING
WHY: the work order names ``scripts/dev_fixture_learner.py`` as this script's "DB-writing
precedent." Read directly: that script's own docstring states "HTTP-DRIVEN, ZERO DIRECT DATABASE
WRITES" and a dedicated test (``test_dev_fixture_isolation.py``) asserts its source never imports a
SQL toolkit at all -- deliberately, because it exists to get ProvenanceMixin/constraints "for free"
through the real routes rather than hand-reimplementing them. No script anywhere in this directory
writes to the database directly (verified: grepped every file in ``scripts/`` for
``AsyncSession``/``session.add``/``session.commit`` -- zero matches before this file). This script
is the first to do so, because registering a runtime bundle has no HTTP route to drive through --
it is a provenance/ops action, not a user-facing flow, the same reason
``generate_c_template_registry.py`` writes a contract artefact directly rather than going through
an API. Only ``generate_c_template_registry.py``'s importable-core/side-effects-under-``__main__``
shape is actually followed here; the "DB-writing precedent" is this script itself, not an
inheritance from ``dev_fixture_learner.py``.

IDEMPOTENCY: re-running with an unchanged manifest is a no-op -- ``register_bundle`` finds the
existing row by ``bundle_version``, confirms its ``manifest_checksum`` still matches what the file
on disk hashes to, and returns it unmodified (``created=False``). A ``bundle_version`` already
registered with a DIFFERENT ``manifest_checksum`` than the file currently declares is refused
loudly (``BundleRegistrationConflictError``), never silently overwritten and never inserted as a
second row for the same version -- this table records what was actually approved and registered;
silently updating it to match a changed file would mean the row no longer testifies to what it once
recorded, and the schema's own ``uq_c_runtime_bundle_records_version`` constraint would reject a
blind second INSERT anyway (this check exists to give a legible error first, not to work around
that constraint).

RUN THIS SCRIPT *AFTER* A FULL BACKEND PYTEST RUN, NEVER ASSUME IT SURVIVES ONE -- A PROPERTY OF
THE ENVIRONMENT, FOUND THE HARD WAY (CONNECT Step 6, owner-caught -- and the mechanism below was
MISREPORTED once before being corrected, see buildLog2.md for the full account of that miss):
every backend phase has its own migration-reversibility test, and each one downgrades to a
revision, then upgrades back to head, as part of what it legitimately verifies. Confirmed by raw
grep, not a single-file spot check --

    grep -rn 'alembic("downgrade"' tests/*.py
    tests/test_be2_persistence.py:148          downgrade 20260722_0001
    tests/test_be4a_opportunity_persistence.py:123   downgrade 20260723_0001
    tests/test_be4b_adaptive_selection.py:170        downgrade 20260727_0001
    tests/test_be4c_attempt_submission.py:232        downgrade 20260727_0002
    tests/test_be4d_hint_events.py:234               downgrade 20260728_0001
    tests/test_be4e_session_completion.py:228        downgrade 20260728_0002

six tests, six downgrades. ``c_runtime_bundle_records`` is created by migration
``20260816_0001_c2_runtime_bundle_record.py`` -- every one of the six downgrade targets above
(dated 20260722 through 20260728) predates that migration, so EVERY ONE of the six drops
``c_runtime_bundle_records`` on its way down and recreates it empty on its way back up, not one
of six. This is systemic to how the migration suite verifies reversibility, not an artifact of a
single test's ordering. Any registered bundle row, registered at any point before ANY of these six
tests runs in a given ``pytest`` invocation, is gone once it does; every row surviving in the table
afterward was written by a test that happened to run later than all six in pytest's deterministic
(alphabetical, no randomization plugin configured) collection order. THE CONSEQUENCE: a full
``pytest -q`` run silently un-registers this bundle. Registering it, then running the suite, then
walking away leaves the database gated shut again with no test failure to say so -- no test in the
suite reads this table's contents. Register this bundle AFTER the last full suite run you intend to
make before relying on a live session, not before it, and re-verify with a direct SQL query
(``select ... from c_runtime_bundle_records where bundle_version = 'c-approved-1.0'``) or this
script's own ``--check`` mode (below) rather than trusting a bare registration run's printed
output, which only proves what happened at the moment it ran.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.infrastructure.database import session_factory
from app.infrastructure.persistence_models import CRuntimeBundleRecord

BACKEND_DIR = Path(__file__).resolve().parent.parent
DEFAULT_BUNDLE_PATH = BACKEND_DIR / "provenance" / "c-runtime-bundle-approved-1.0.json"

# Pinned literal, same convention every other application-layer module in this codebase uses for
# this field (e.g. app/application/live_engine_c/session_lifecycle.py's own SCHEMA_REVISION) --
# the real alembic head measured at CONNECT Step 0/3 (backend/buildLog2.md), not re-derived live.
SCHEMA_REVISION = "20260816_0008"


class BundleRegistrationConflictError(RuntimeError):
    """Raised when ``bundle_version`` is already registered with a manifest_checksum that
    disagrees with what the manifest file on disk currently hashes to."""


def compute_manifest_checksum(bundle_path: Path) -> str:
    """The SAME method every other artefact checksum in this codebase already uses --
    ``hashlib.sha256(path.read_bytes()).hexdigest()`` (see
    ``app/infrastructure/runtime_bundle_c/loader.py``'s own ``_sha256_of`` and
    ``component_c_generator.catalogue.loader.catalogue_file_checksum``) -- never a second, ad hoc
    hashing convention invented for this one script."""
    return hashlib.sha256(bundle_path.read_bytes()).hexdigest()


def _provenance(resource_id: UUID, *, environment: str) -> dict[str, object]:
    return {
        "system_actor": "register-c-runtime-bundle-script",
        "request_id": f"script-{uuid4()}",
        "operation_or_event_type": "c_runtime_bundle.registered",
        "reason_code": "APPROVAL_2026_08_26_SEVEN_FAMILIES",
        "resource_type": "c_runtime_bundle_record",
        "resource_id": resource_id,
        "source_class": "REAL",
        "source_system": "upadya-api",
        "environment": environment,
        "schema_revision": SCHEMA_REVISION,
    }


async def _lookup(
    session: AsyncSession, bundle_path: Path
) -> tuple[dict, str, CRuntimeBundleRecord | None]:
    """THE ONE lookup, shared by ``register_bundle`` and ``check_bundle`` -- both the write path
    and the read-only ``--check`` path answer "does the DB row match the file on disk" through
    this single function, never two independently-maintained copies of the same checksum-and-query
    logic (supervisor ruling, CONNECT Step 6: "two ways to answer 'does this match' is how they
    drift into disagreeing"). Returns ``(manifest_dict, manifest_checksum, existing_row_or_None)``.
    """
    manifest = json.loads(bundle_path.read_text(encoding="utf-8"))
    bundle_version = manifest["bundle_version"]
    manifest_checksum = compute_manifest_checksum(bundle_path)
    existing = await session.scalar(
        select(CRuntimeBundleRecord).where(CRuntimeBundleRecord.bundle_version == bundle_version)
    )
    return manifest, manifest_checksum, existing


class BundleCheckState(str, Enum):
    NOT_REGISTERED = "NOT_REGISTERED"
    MATCHING = "MATCHING"
    DISAGREEING = "DISAGREEING"


# Exit codes for --check, distinct from register's own 0/1 (success/conflict) so a caller can
# script against any of the three states without parsing stdout.
CHECK_EXIT_CODES: dict[BundleCheckState, int] = {
    BundleCheckState.MATCHING: 0,
    BundleCheckState.NOT_REGISTERED: 1,
    BundleCheckState.DISAGREEING: 2,
}


@dataclass(frozen=True)
class BundleCheckResult:
    state: BundleCheckState
    bundle_version: str
    manifest_checksum: str
    existing: CRuntimeBundleRecord | None


async def check_bundle(session: AsyncSession, *, bundle_path: Path = DEFAULT_BUNDLE_PATH) -> BundleCheckResult:
    """Read-only. Writes nothing, ever -- answers "is this bundle currently registered and does it
    match the manifest on disk?" (the question Step 8 will actually have, previously answerable
    only by raw SQL). Uses the SAME ``_lookup`` the write path uses, so this can never drift from
    what ``register_bundle`` itself would decide. A DISAGREEING result is reported exactly as loud
    as the write path's own ``BundleRegistrationConflictError`` -- a mismatch found by looking is
    the same finding as one found by writing, not a lesser one (supervisor ruling)."""
    manifest, manifest_checksum, existing = await _lookup(session, bundle_path)
    bundle_version = manifest["bundle_version"]
    if existing is None:
        state = BundleCheckState.NOT_REGISTERED
    elif existing.manifest_checksum == manifest_checksum:
        state = BundleCheckState.MATCHING
    else:
        state = BundleCheckState.DISAGREEING
    return BundleCheckResult(
        state=state, bundle_version=bundle_version, manifest_checksum=manifest_checksum, existing=existing
    )


async def register_bundle(
    session: AsyncSession, *, bundle_path: Path = DEFAULT_BUNDLE_PATH, environment: str
) -> tuple[CRuntimeBundleRecord, bool]:
    """The importable core. Returns ``(record, created)`` -- ``created=False`` means a matching
    row already existed and was returned unmodified; this function never mutates an existing row,
    only inserts a new one or refuses. Raises ``BundleRegistrationConflictError`` on a
    checksum-disagreeing re-run -- see this module's own docstring for why that is the only
    correct response, never a silent overwrite."""
    manifest, manifest_checksum, existing = await _lookup(session, bundle_path)
    bundle_version = manifest["bundle_version"]
    if existing is not None:
        if existing.manifest_checksum == manifest_checksum:
            return existing, False
        raise BundleRegistrationConflictError(
            f"bundle_version {bundle_version!r} is already registered "
            f"(c_runtime_bundle_record_id={existing.c_runtime_bundle_record_id}) with "
            f"manifest_checksum {existing.manifest_checksum!r}, but {bundle_path} currently "
            f"hashes to {manifest_checksum!r}. Refusing to overwrite the existing row -- if the "
            f"manifest genuinely changed, publish it under a new bundle_version rather than "
            f"mutating what an already-registered checksum attested to."
        )

    record_id = uuid4()
    record = CRuntimeBundleRecord(
        c_runtime_bundle_record_id=record_id,
        bundle_version=bundle_version,
        manifest_checksum=manifest_checksum,
        publication_state=manifest["publication_state"],
        approval_status=manifest["approval_status"],
        immutable_after_publication=manifest["immutable_after_publication"],
        **_provenance(record_id, environment=environment),
    )
    session.add(record)
    await session.flush()
    return record, True


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Register the approved Component C runtime bundle manifest as a real "
        "c_runtime_bundle_records row. Idempotent: re-running with an unchanged manifest is a "
        "no-op; a changed manifest under an already-registered bundle_version is refused."
    )
    parser.add_argument(
        "--bundle-path",
        type=Path,
        default=DEFAULT_BUNDLE_PATH,
        help=f"Path to the bundle manifest JSON (default: {DEFAULT_BUNDLE_PATH}).",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Read-only: report whether the bundle is currently registered and matches the "
        "manifest on disk, without writing anything. Exit codes: 0 MATCHING, 1 NOT_REGISTERED, "
        "2 DISAGREEING (distinct from the write path's own 0/1 success/conflict codes).",
    )
    return parser.parse_args(argv)


async def _run_check(bundle_path: Path) -> int:
    async with session_factory() as session:
        result = await check_bundle(session, bundle_path=bundle_path)

    if result.state is BundleCheckState.NOT_REGISTERED:
        print(
            f"NOT_REGISTERED: bundle_version={result.bundle_version!r} "
            f"(manifest_checksum={result.manifest_checksum}) has no c_runtime_bundle_records row."
        )
    elif result.state is BundleCheckState.MATCHING:
        assert result.existing is not None
        print(
            f"MATCHING: c_runtime_bundle_record_id={result.existing.c_runtime_bundle_record_id} "
            f"bundle_version={result.bundle_version!r} manifest_checksum={result.manifest_checksum} "
            f"publication_state={result.existing.publication_state} "
            f"approval_status={result.existing.approval_status}"
        )
    else:
        assert result.existing is not None
        # DISAGREEING is reported exactly as loud as the write path's own
        # BundleRegistrationConflictError -- a mismatch found by looking is the same finding as
        # one found by writing (supervisor ruling, CONNECT Step 6).
        print(
            f"ERROR: DISAGREEING: bundle_version={result.bundle_version!r} is registered "
            f"(c_runtime_bundle_record_id={result.existing.c_runtime_bundle_record_id}) with "
            f"manifest_checksum={result.existing.manifest_checksum!r}, but {bundle_path} "
            f"currently hashes to {result.manifest_checksum!r}."
        )
    return CHECK_EXIT_CODES[result.state]


async def _main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    if args.check:
        return await _run_check(args.bundle_path)

    settings = get_settings()
    async with session_factory() as session:
        try:
            record, created = await register_bundle(
                session, bundle_path=args.bundle_path, environment=settings.app_env
            )
        except BundleRegistrationConflictError as exc:
            print(f"ERROR: {exc}")
            return 1
        await session.commit()

    if created:
        print(
            f"Registered c_runtime_bundle_record_id={record.c_runtime_bundle_record_id} "
            f"bundle_version={record.bundle_version!r} "
            f"manifest_checksum={record.manifest_checksum}"
        )
    else:
        print(
            f"Already registered (no-op): c_runtime_bundle_record_id="
            f"{record.c_runtime_bundle_record_id} bundle_version={record.bundle_version!r} "
            f"manifest_checksum={record.manifest_checksum} matches the manifest file on disk."
        )
    return 0


def main() -> None:
    raise SystemExit(asyncio.run(_main()))


if __name__ == "__main__":
    main()
