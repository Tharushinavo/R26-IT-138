"""BE5a (BEplan §10 steps 1-2, 8, 10): the frozen backend<->frontend OpenAPI contract.

Freezes ``app.openapi()`` as ``backend/contract/openapi.v1.json`` and enforces that the live
schema never silently drifts from it, that its route set stays exactly the BE2-S/BE4-authorized
set, and that no private/scientific field name (correct answer, BKT/mastery, hint-guard
internals, generation seed, selection provenance, ...) is reachable from any public request or
response schema.
"""

import hashlib
import json
from pathlib import Path

from app.main import app
from tests.test_be2_architecture_guards import EXPECTED_ROUTES


CONTRACT_DIR = Path(__file__).parent.parent / "contract"
FROZEN_PATH = CONTRACT_DIR / "openapi.v1.json"
META_PATH = CONTRACT_DIR / "openapi.v1.meta.json"

# Mirrors the DB-column guard's PROHIBITED_COLUMN_TERMS (test_be2_architecture_guards.py) at the
# public-schema-field-name layer: independent enforcement that no private/scientific concept
# leaks into a request/response *field name*, even if it never reaches persistence.
FORBIDDEN_FIELD_TERMS = {
    "mastery", "bkt", "guess_guard", "certif", "sequenc", "answer", "correct",
    "error_class", "population", "dd_subtype", "true_mastery", "simulated", "latency",
    "off_day", "random_effect", "experiment", "distractor", "seed", "provenance",
}


def _frozen_schema() -> dict:
    return json.loads(FROZEN_PATH.read_text(encoding="utf-8"))


def _current_routes() -> set[tuple[str, tuple[str, ...]]]:
    return {
        (path, tuple(sorted(method.upper() for method in operations)))
        for path, operations in app.openapi()["paths"].items()
    }


def test_live_openapi_matches_frozen_artefact() -> None:
    """Any unreviewed change to a public request/response/status shape fails this test."""
    assert app.openapi() == _frozen_schema()


def test_frozen_artefact_checksum_matches_meta() -> None:
    meta = json.loads(META_PATH.read_text(encoding="utf-8"))
    digest = hashlib.sha256(FROZEN_PATH.read_bytes()).hexdigest()
    assert digest == meta["checksum_sha256"]
    assert meta["contract_version"] == "v1"


def test_frozen_route_set_matches_expected_authorized_routes() -> None:
    frozen = _frozen_schema()
    frozen_routes = {
        (path, tuple(sorted(method.upper() for method in operations)))
        for path, operations in frozen["paths"].items()
    }
    assert frozen_routes == EXPECTED_ROUTES
    assert frozen_routes == _current_routes()


def test_no_private_or_scientific_field_name_in_frozen_schema() -> None:
    schemas = _frozen_schema().get("components", {}).get("schemas", {})
    offenders = {
        (schema_name, property_name)
        for schema_name, schema in schemas.items()
        for property_name in schema.get("properties", {})
        if any(term in property_name.lower() for term in FORBIDDEN_FIELD_TERMS)
    }
    assert not offenders, offenders
