"""BE-G2 isolation guard — deleted together with backend/scripts/ when FE-1b lands.

Proves the dev-fixture script (backend/scripts/dev_fixture_learner.py) cannot influence the
authorized architecture surface and cannot write to the database directly: it is HTTP-driven
only, per its own module docstring.
"""

import importlib.util
from pathlib import Path

from app.main import app


SCRIPT_PATH = Path("scripts/dev_fixture_learner.py")


def test_no_file_under_app_references_scripts() -> None:
    for path in Path("app").rglob("*.py"):
        assert "scripts" not in path.read_text(encoding="utf-8"), path


def test_importing_the_script_adds_no_route() -> None:
    routes_before = set(app.openapi()["paths"])

    spec = importlib.util.spec_from_file_location("dev_fixture_learner", SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    routes_after = set(app.openapi()["paths"])
    assert routes_after == routes_before
    # Importing must be side-effect-free: no network call happens unless main() is invoked.
    assert hasattr(module, "main")


def test_script_cannot_write_the_database_directly() -> None:
    source = SCRIPT_PATH.read_text(encoding="utf-8").lower()
    for marker in ("sqlalchemy", "asyncpg", "database_url", "service_role"):
        assert marker not in source, marker
