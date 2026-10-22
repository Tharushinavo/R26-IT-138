"""Enforce active bundle eligibility and published checksum immutability.

Revision ID: 20260722_0003
Revises: 20260722_0002
"""

from collections.abc import Sequence

from alembic import op


revision: str = "20260722_0003"
down_revision: str | Sequence[str] | None = "20260722_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


ACTIVE_BUNDLE_ELIGIBILITY_FUNCTION = """
CREATE FUNCTION enforce_b_session_active_bundle_eligibility()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    bundle_publication_state text;
    bundle_approval_status text;
    bundle_is_immutable boolean;
BEGIN
    IF NEW.state <> 'active' THEN
        RETURN NEW;
    END IF;

    SELECT publication_state, approval_status, immutable_after_publication
      INTO bundle_publication_state, bundle_approval_status, bundle_is_immutable
      FROM b_runtime_bundle_records
     WHERE runtime_bundle_record_id = NEW.runtime_bundle_record_id
     FOR UPDATE;

    IF NOT FOUND
       OR bundle_publication_state <> 'PUBLISHED'
       OR bundle_approval_status <> 'APPROVED'
       OR bundle_is_immutable IS NOT TRUE THEN
        RAISE EXCEPTION 'active session requires an eligible published, approved, immutable runtime bundle'
            USING ERRCODE = '23514', CONSTRAINT = 'ck_b_sessions_active_bundle_eligible';
    END IF;

    RETURN NEW;
END;
$$
"""


BUNDLE_INTEGRITY_FUNCTION = """
CREATE FUNCTION enforce_b_runtime_bundle_integrity()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    IF OLD.publication_state = 'PUBLISHED'
       AND OLD.immutable_after_publication IS TRUE
       AND NEW.manifest_checksum IS DISTINCT FROM OLD.manifest_checksum THEN
        RAISE EXCEPTION 'published immutable runtime bundle checksum cannot change'
            USING ERRCODE = '23514', CONSTRAINT = 'ck_b_runtime_bundle_published_checksum_immutable';
    END IF;

    IF (NEW.publication_state <> 'PUBLISHED'
        OR NEW.approval_status <> 'APPROVED'
        OR NEW.immutable_after_publication IS NOT TRUE)
       AND EXISTS (
           SELECT 1
             FROM b_sessions
            WHERE runtime_bundle_record_id = OLD.runtime_bundle_record_id
              AND state = 'active'
       ) THEN
        RAISE EXCEPTION 'runtime bundle referenced by an active session must remain eligible'
            USING ERRCODE = '23514', CONSTRAINT = 'ck_b_runtime_bundle_active_reference_eligible';
    END IF;

    RETURN NEW;
END;
$$
"""


def upgrade() -> None:
    op.execute(ACTIVE_BUNDLE_ELIGIBILITY_FUNCTION)
    op.execute(
        """
        CREATE TRIGGER trg_b_sessions_active_bundle_eligible
        BEFORE INSERT OR UPDATE OF state, runtime_bundle_record_id
        ON b_sessions
        FOR EACH ROW
        EXECUTE FUNCTION enforce_b_session_active_bundle_eligibility()
        """
    )
    op.execute(BUNDLE_INTEGRITY_FUNCTION)
    op.execute(
        """
        CREATE TRIGGER trg_b_runtime_bundle_integrity
        BEFORE UPDATE OF manifest_checksum, publication_state, approval_status, immutable_after_publication
        ON b_runtime_bundle_records
        FOR EACH ROW
        EXECUTE FUNCTION enforce_b_runtime_bundle_integrity()
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER trg_b_runtime_bundle_integrity ON b_runtime_bundle_records")
    op.execute("DROP FUNCTION enforce_b_runtime_bundle_integrity()")
    op.execute("DROP TRIGGER trg_b_sessions_active_bundle_eligible ON b_sessions")
    op.execute("DROP FUNCTION enforce_b_session_active_bundle_eligibility()")
