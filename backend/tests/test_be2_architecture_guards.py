"""Static guards for the BE2 Limited authorization boundary, extended (Phase 1 batch 1b) with
Component C's full-dotted-path import boundary and column-guard mechanism proof."""

import ast
import dataclasses
import re
from pathlib import Path

from sqlalchemy import Column, Integer, MetaData, String, Table

from app.domain.live_engine_c.types import (
    AggregationConfig,
    EvidenceWindowConfig,
    GenerationConfig,
    PolicyConfig,
    RecoveryConfig,
    SafetyConfig,
    ScaffoldConfig,
    SelectionConfig,
    TemplateGenerationParams,
)
from app.infrastructure.persistence_models import AUTHORIZED_TABLES, Base
from app.main import app
from tests.test_c1a_wheel_provenance import NEVER_SHIP_MODULES


EXPECTED_TABLES = {
    "app_users",
    "b_learners",
    "app_user_learner_links",
    "b_runtime_bundle_records",
    "b_sessions",
    "b_session_events",
    "b_idempotency_records",
    "b_audit_events",
    "teacher_profiles", "classrooms", "classroom_invites", "classroom_memberships",
    "teacher_profiles", "classrooms", "classroom_invites", "classroom_memberships",
    # BE4a (BEplan §9 BE4.1) — private opportunity/task-instance/presentation-token tables.
    "b_item_opportunities", "b_task_instances", "b_presentation_tokens",
    # BE4b (BEplan §9 BE4.2) — private per-learner, per-skill BKT state.
    "b_learner_skill_states",
    # BE4c (BEplan §9 BE4.3 + BE4.4) — private attempt events + immutable BKT transitions.
    "b_attempts", "b_skill_state_transitions",
    # BE4d (BEplan §9 BE4.5) — private governed hint events, separate from attempts/transitions.
    "b_hint_events",
    # BE4e (BEplan §9 BE4.6) — private, immutable session-aggregate + skill-certification results.
    "b_session_aggregate_results", "b_skill_certification_results",
    # Component C Phase 2 — mirrors b_runtime_bundle_records for Component C's own wheel pin.
    "c_runtime_bundle_records",
    # Component C Phase 3a (v3.0 §11 Phase 3) — the ten tables, created by their own migration
    # (20260816_0002), not BE2's 0002.
    "c_sessions", "c_task_opportunities", "c_task_instances", "c_gameplay_events",
    "c_task_opportunity_summaries", "c_session_aggregate_results", "c_learner_local_state",
    "c_policy_decisions", "c_safety_events", "c_scaffold_events",
    # Component C backend remediation, batch 4 (Amendment A-1) — the durable exclusion-reason /
    # supersession-chain table, created by its own migration (20260816_0007), not BE2's 0002.
    "c_task_opportunity_verdicts",
    # Component D (Component D authorization, owner decision D-011 A1, 2026-10-21) — the three
    # cognitive-profiling tables, created by their own migration (20261021_0010), not BE2's 0002.
    "d_learner_state", "d_interactions", "d_cognitive_profiles",
    # Component C batch 9c-1a (Master Build Plan v3.0 §11 Phase 9; 9b_9c plan Track 9c, "9c-1 —
    # the tables and the routing") — the two shared B/C outbox tables, deliberately unprefixed
    # (shared infrastructure, not shared ownership — owner condition 1), created by their own
    # migration (20260816_0008), not BE2's 0002.
    "outbox_events", "contract_deliveries",
}
BE2_BASE_TABLES = EXPECTED_TABLES - {
    "teacher_profiles", "classrooms", "classroom_invites", "classroom_memberships",
    "b_item_opportunities", "b_task_instances", "b_presentation_tokens",
    "b_learner_skill_states",
    "b_attempts", "b_skill_state_transitions",
    "b_hint_events",
    "b_session_aggregate_results", "b_skill_certification_results",
    # Component C Phase 2 — created by its own migration (20260816_0001), not BE2's 0002.
    "c_runtime_bundle_records",
    # Component C Phase 3a — created by their own migration (20260816_0002), not BE2's 0002.
    "c_sessions", "c_task_opportunities", "c_task_instances", "c_gameplay_events",
    "c_task_opportunity_summaries", "c_session_aggregate_results", "c_learner_local_state",
    "c_policy_decisions", "c_safety_events", "c_scaffold_events",
    # Component C backend remediation, batch 4 — created by its own migration (20260816_0007),
    # not BE2's 0002.
    "c_task_opportunity_verdicts",
    # Component C batch 9c-1a — created by its own migration (20260816_0008), not BE2's 0002.
    "outbox_events", "contract_deliveries",
    # Component D (Component D authorization, D-011 A1) — created by their own migration
    # (20261021_0010), not BE2's 0002.
    "d_learner_state", "d_interactions", "d_cognitive_profiles",
}
PROHIBITED_COLUMN_TERMS = {
    "mastery", "bkt", "guess_guard", "certif", "sequenc", "hint", "answer",
    "correct", "error_class", "population", "dd_subtype", "true_mastery",
    "simulated", "latency", "off_day", "random_effect", "experiment",
}
# "answer" and "correct" stay in the blanket prohibition above (blocked everywhere by default).
# BEplan §9 BE4.1 authorizes exactly two PRIVATE columns to carry them — behind the BE3c
# private/public split (never read by any public-DTO projection; see
# ``app.domain.b_opportunity.project_task_instance_to_presentation``) — and only those two cells
# are exempted, via this explicit, minimal allow-list rather than a global term removal.
AUTHORIZED_ANSWER_BEARING_COLUMNS = {
    ("b_task_instances", "correct_answer"),
    ("b_task_instances", "allowed_equivalent_answers"),
}


def test_exact_authorized_model_table_set_and_no_scientific_columns() -> None:
    """R-A (Phase 3a work order): this test's exemption sets are now
    AUTHORIZED_ANSWER_BEARING_COLUMNS | AUTHORIZED_C_COLUMN_EXCEPTIONS. Phase 1b's "leave it
    byte-identical" instruction is superseded for this test and this reason only, per the
    Phase 3a work order's binding ruling R-A. AUTHORIZED_ANSWER_BEARING_COLUMNS itself keeps its
    two B entries and its name, unchanged; C's pairs live in the separate, named
    AUTHORIZED_C_COLUMN_EXCEPTIONS so provenance stays legible. Every assertion below stays
    EXACT EQUALITY -- none relaxed to a subset check (R-A binding condition)."""
    assert AUTHORIZED_TABLES == EXPECTED_TABLES
    assert set(Base.metadata.tables) == EXPECTED_TABLES

    exemptions = AUTHORIZED_ANSWER_BEARING_COLUMNS | AUTHORIZED_C_COLUMN_EXCEPTIONS

    # The allow-list itself must not be stale: every exempted column must actually exist on its
    # named table, and no other table may have an answer/correct-bearing column at all.
    table_columns = {
        table.name: {column.name for column in table.columns} for table in Base.metadata.tables.values()
    }
    for table_name, column_name in exemptions:
        assert column_name in table_columns.get(table_name, set()), (table_name, column_name)
    answer_bearing = {
        (table.name, column.name)
        for table in Base.metadata.tables.values()
        for column in table.columns
        if any(term in column.name.lower() for term in ("answer", "correct"))
    }
    answer_bearing_exemptions = {
        pair for pair in exemptions if any(term in pair[1].lower() for term in ("answer", "correct"))
    }
    assert answer_bearing == answer_bearing_exemptions

    offenders = {
        (table.name, column.name)
        for table in Base.metadata.tables.values()
        for column in table.columns
        if any(term in column.name.lower() for term in PROHIBITED_COLUMN_TERMS)
        and (table.name, column.name) not in exemptions
    }
    assert not offenders, offenders


EXPECTED_ROUTES = {
    ("/health/live", ("GET",)),
    ("/health/ready", ("GET",)),
    ("/api/v1/me", ("GET",)),
    ("/api/v1/teacher/profile", ("GET", "POST")),
    ("/api/v1/learner/profile", ("GET", "POST")),
    ("/api/v1/classrooms", ("GET", "POST")),
    ("/api/v1/classrooms/{classroom_id}", ("GET",)),
    # 2026-09-14 -- teacher-initiated classroom soft delete (migration 20260914_0009).
    ("/api/v1/classrooms/{classroom_id}/delete", ("POST",)),
    ("/api/v1/classrooms/{classroom_id}/invites", ("POST",)),
    ("/api/v1/classroom-invites/{classroom_invite_id}/revoke", ("POST",)),
    ("/api/v1/classroom-invites/resolve", ("POST",)),
    ("/api/v1/classroom-memberships/requests", ("POST",)),
    ("/api/v1/classrooms/{classroom_id}/membership-requests", ("GET",)),
    ("/api/v1/classroom-memberships/{membership_id}/approve", ("POST",)),
    ("/api/v1/classroom-memberships/{membership_id}/reject", ("POST",)),
    ("/api/v1/classrooms/{classroom_id}/learners", ("GET",)),
    ("/api/v1/learner/classrooms", ("GET",)),
    ("/api/v1/b/sessions", ("POST",)),
    ("/api/v1/b/sessions/active", ("GET",)),
    ("/api/v1/b/sessions/{session_id}/complete", ("POST",)),
    ("/api/v1/b/sessions/{session_id}/abandon", ("POST",)),
    # BE4b (BEplan §9 BE4.2) — the one authorized adaptive-selection route.
    ("/api/v1/b/sessions/{session_id}/opportunities", ("POST",)),
    # 2026-09-27 — the learner-presentation acknowledgement that anchors the answering clock at
    # the render rather than at selection (owner ruling; app/domain/b_presentation_ack.py).
    ("/api/v1/b/sessions/{session_id}/opportunities/{item_opportunity_id}/presented", ("POST",)),
    # BE4c (BEplan §9 BE4.3 + BE4.4) — the one authorized attempt-submission route.
    ("/api/v1/b/sessions/{session_id}/opportunities/{item_opportunity_id}/responses", ("POST",)),
    # BE4d (BEplan §9 BE4.5) — the one authorized governed-hint-request route.
    ("/api/v1/b/sessions/{session_id}/opportunities/{item_opportunity_id}/assists", ("POST",)),
    # BE4e (BEplan §9 BE4.6) — the two authorized next-or-complete / SAFE-standing routes.
    ("/api/v1/b/sessions/{session_id}/opportunities/{item_opportunity_id}/complete", ("POST",)),
    ("/api/v1/b/sessions/{session_id}/summary", ("GET",)),
    # 2026-09-21 -- the learner's own per-skill BKT state, read-only, for the Play prep card
    # (product-owner ruling; app/domain/b_skill_state.py).
    ("/api/v1/b/learner/skill-states", ("GET",)),
    # Phase 4b — the four authorized Component C session-lifecycle routes (create/start, resume,
    # abandon, complete). See AUTHORIZED_C_SESSION_LIFECYCLE_OPERATIONS below.
    ("/api/v1/c/sessions", ("POST",)),
    ("/api/v1/c/sessions/active", ("GET",)),
    ("/api/v1/c/sessions/{c_session_id}/abandon", ("POST",)),
    ("/api/v1/c/sessions/{c_session_id}/complete", ("POST",)),
    # Phase 5 -- the two task-serving routes. See AUTHORIZED_C_TASK_SERVING_OPERATIONS below.
    ("/api/v1/c/sessions/{c_session_id}/tasks/next", ("POST",)),
    ("/api/v1/c/sessions/{c_session_id}/tasks/{c_task_instance_id}/actions", ("POST",)),
    # Component D (Component D authorization, owner decision D-011 A2, 2026-10-21) -- the six
    # authorized student-side cognitive-profiling routes. The two carrying "session" are
    # additionally carved out of the path-term prohibition by A3; see
    # AUTHORIZED_D_PROFILING_OPERATIONS below.
    ("/api/v1/d/learner/state", ("GET", "POST")),
    ("/api/v1/d/learner/profiles", ("GET",)),
    ("/api/v1/d/learner/profiles/latest", ("GET",)),
    ("/api/v1/d/sessions/{session_id}/profile", ("GET", "POST")),
}
AUTHORIZED_INVITE_MEMBERSHIP_OPERATIONS = {
    ("/api/v1/classrooms/{classroom_id}/invites", ("POST",)),
    ("/api/v1/classroom-invites/resolve", ("POST",)),
    ("/api/v1/classroom-memberships/requests", ("POST",)),
    ("/api/v1/classrooms/{classroom_id}/membership-requests", ("GET",)),
    ("/api/v1/classroom-memberships/{membership_id}/approve", ("POST",)),
    ("/api/v1/classroom-memberships/{membership_id}/reject", ("POST",)),
    ("/api/v1/classrooms/{classroom_id}/learners", ("GET",)),
    ("/api/v1/learner/classrooms", ("GET",)),
    ("/api/v1/classroom-invites/{classroom_invite_id}/revoke", ("POST",)),
}
AUTHORIZED_B_SESSION_LIFECYCLE_OPERATIONS = {
    ("/api/v1/b/sessions", ("POST",)),
    ("/api/v1/b/sessions/active", ("GET",)),
    ("/api/v1/b/sessions/{session_id}/complete", ("POST",)),
    ("/api/v1/b/sessions/{session_id}/abandon", ("POST",)),
}
AUTHORIZED_B_OPPORTUNITY_SELECTION_OPERATIONS = {
    ("/api/v1/b/sessions/{session_id}/opportunities", ("POST",)),
}
AUTHORIZED_B_PRESENTATION_ACK_OPERATIONS = {
    ("/api/v1/b/sessions/{session_id}/opportunities/{item_opportunity_id}/presented", ("POST",)),
}
AUTHORIZED_B_ATTEMPT_SUBMISSION_OPERATIONS = {
    ("/api/v1/b/sessions/{session_id}/opportunities/{item_opportunity_id}/responses", ("POST",)),
}
AUTHORIZED_B_HINT_REQUEST_OPERATIONS = {
    ("/api/v1/b/sessions/{session_id}/opportunities/{item_opportunity_id}/assists", ("POST",)),
}
AUTHORIZED_B_SESSION_COMPLETION_OPERATIONS = {
    ("/api/v1/b/sessions/{session_id}/opportunities/{item_opportunity_id}/complete", ("POST",)),
    ("/api/v1/b/sessions/{session_id}/summary", ("GET",)),
}
# Phase 4b — the four authorized Component C session-lifecycle routes, mirroring
# AUTHORIZED_B_SESSION_LIFECYCLE_OPERATIONS' own role for B exactly.
AUTHORIZED_C_SESSION_LIFECYCLE_OPERATIONS = {
    ("/api/v1/c/sessions", ("POST",)),
    ("/api/v1/c/sessions/active", ("GET",)),
    ("/api/v1/c/sessions/{c_session_id}/abandon", ("POST",)),
    ("/api/v1/c/sessions/{c_session_id}/complete", ("POST",)),
}
# Phase 5 -- mirrors AUTHORIZED_C_SESSION_LIFECYCLE_OPERATIONS' own role, for the two task-serving
# routes (select_task -> build_task_instance -> persist -> public DTO; evaluate on submit).
AUTHORIZED_C_TASK_SERVING_OPERATIONS = {
    ("/api/v1/c/sessions/{c_session_id}/tasks/next", ("POST",)),
    ("/api/v1/c/sessions/{c_session_id}/tasks/{c_task_instance_id}/actions", ("POST",)),
}
# Component D (Component D authorization, owner decision D-011 A3, 2026-10-21): the "session" path
# term is carved out for the TWO profile routes only, on the same pattern B's and C's lifecycle
# routes already use. Component D's other four routes are learner-scoped and carry no prohibited
# term at all, so they are deliberately NOT in this set -- a carve-out that covered them would
# grant more than was asked for. Every other prohibited term still applies to these two paths.
AUTHORIZED_D_PROFILING_OPERATIONS = {
    ("/api/v1/d/sessions/{session_id}/profile", ("GET", "POST")),
}
PROHIBITED_SCIENTIFIC_PATH_TERMS = (
    "session", "attempt", "hint", "progress", "bkt", "mastery", "sequenc", "certif", "guess",
)


def _current_routes() -> set[tuple[str, tuple[str, ...]]]:
    return {
        (path, tuple(sorted(method.upper() for method in operations)))
        for path, operations in app.openapi()["paths"].items()
    }


def test_no_new_api_route_or_lifecycle_service() -> None:
    assert _current_routes() == EXPECTED_ROUTES
    # Phase 4b work order (B2) explicitly authorizes Component C's own session-lifecycle
    # application-service layer, behind the four AUTHORIZED_C_SESSION_LIFECYCLE_OPERATIONS
    # routes above -- app/application/live_engine_c/c_session_service.py is that one, named
    # exemption; every OTHER *session*service*.py file anywhere under app/ stays prohibited.
    matches = {str(path) for path in Path("app").rglob("*session*service*.py")}
    assert matches == {"app/application/live_engine_c/c_session_service.py"}, matches


def test_openapi_contains_exactly_the_nine_authorized_invite_membership_operations() -> None:
    assert len(AUTHORIZED_INVITE_MEMBERSHIP_OPERATIONS) == 9
    assert AUTHORIZED_INVITE_MEMBERSHIP_OPERATIONS <= _current_routes()
    assert _current_routes() - AUTHORIZED_INVITE_MEMBERSHIP_OPERATIONS == {
        route for route in EXPECTED_ROUTES if route not in AUTHORIZED_INVITE_MEMBERSHIP_OPERATIONS
    }


def test_no_session_question_answer_or_scientific_route_exists() -> None:
    """The blanket "session" path prohibition is carved out only for the four
    authorized BE2.3-BE2.4 neutral session-lifecycle routes plus the one BE4b adaptive-
    selection route (BEplan §9 BE4.2) plus the one BE4c attempt-submission route (BEplan §9
    BE4.3 + BE4.4) plus the one BE4d hint-request route (BEplan §9 BE4.5) plus the two BE4e
    next-or-complete / SAFE-standing routes (BEplan §9 BE4.6) plus the four Phase 4b Component C
    session-lifecycle routes (AUTHORIZED_C_SESSION_LIFECYCLE_OPERATIONS); every other prohibited
    scientific term remains prohibited unconditionally, including on those routes themselves — in
    particular every route must never contain "attempt", "hint", "progress", "bkt", "mastery",
    "sequenc", "certif", or "guess" (the BE4e routes spell completion as "complete"/"summary",
    never "progress"; the C routes spell it the same way)."""
    for route in _current_routes():
        path, _ = route
        lowered = path.lower()
        terms = PROHIBITED_SCIENTIFIC_PATH_TERMS
        if (
            route in AUTHORIZED_B_SESSION_LIFECYCLE_OPERATIONS
            or route in AUTHORIZED_B_OPPORTUNITY_SELECTION_OPERATIONS
            or route in AUTHORIZED_B_PRESENTATION_ACK_OPERATIONS
            or route in AUTHORIZED_B_ATTEMPT_SUBMISSION_OPERATIONS
            or route in AUTHORIZED_B_HINT_REQUEST_OPERATIONS
            or route in AUTHORIZED_B_SESSION_COMPLETION_OPERATIONS
            or route in AUTHORIZED_C_SESSION_LIFECYCLE_OPERATIONS
            or route in AUTHORIZED_C_TASK_SERVING_OPERATIONS
            # D-011 A3.
            or route in AUTHORIZED_D_PROFILING_OPERATIONS
        ):
            terms = tuple(term for term in terms if term != "session")
        assert not any(term in lowered for term in terms), path


def test_openapi_contains_exactly_the_two_authorized_b_session_completion_operations() -> None:
    assert len(AUTHORIZED_B_SESSION_COMPLETION_OPERATIONS) == 2
    assert AUTHORIZED_B_SESSION_COMPLETION_OPERATIONS <= _current_routes()
    non_completion_routes = {route for route in EXPECTED_ROUTES if route not in AUTHORIZED_B_SESSION_COMPLETION_OPERATIONS}
    assert _current_routes() - AUTHORIZED_B_SESSION_COMPLETION_OPERATIONS == non_completion_routes


def test_openapi_contains_exactly_the_one_authorized_b_presentation_ack_operation() -> None:
    """The clock-anchoring route is one route, and adding a second would fail here first."""
    assert len(AUTHORIZED_B_PRESENTATION_ACK_OPERATIONS) == 1
    assert AUTHORIZED_B_PRESENTATION_ACK_OPERATIONS <= _current_routes()
    non_ack_routes = {route for route in EXPECTED_ROUTES if route not in AUTHORIZED_B_PRESENTATION_ACK_OPERATIONS}
    assert _current_routes() - AUTHORIZED_B_PRESENTATION_ACK_OPERATIONS == non_ack_routes


def test_openapi_contains_exactly_the_one_authorized_b_attempt_submission_operation() -> None:
    assert len(AUTHORIZED_B_ATTEMPT_SUBMISSION_OPERATIONS) == 1
    assert AUTHORIZED_B_ATTEMPT_SUBMISSION_OPERATIONS <= _current_routes()
    non_attempt_routes = {route for route in EXPECTED_ROUTES if route not in AUTHORIZED_B_ATTEMPT_SUBMISSION_OPERATIONS}
    assert _current_routes() - AUTHORIZED_B_ATTEMPT_SUBMISSION_OPERATIONS == non_attempt_routes


def test_openapi_contains_exactly_the_one_authorized_b_hint_request_operation() -> None:
    assert len(AUTHORIZED_B_HINT_REQUEST_OPERATIONS) == 1
    assert AUTHORIZED_B_HINT_REQUEST_OPERATIONS <= _current_routes()
    non_hint_routes = {route for route in EXPECTED_ROUTES if route not in AUTHORIZED_B_HINT_REQUEST_OPERATIONS}
    assert _current_routes() - AUTHORIZED_B_HINT_REQUEST_OPERATIONS == non_hint_routes


def test_openapi_contains_exactly_the_four_authorized_b_session_lifecycle_operations() -> None:
    assert len(AUTHORIZED_B_SESSION_LIFECYCLE_OPERATIONS) == 4
    assert AUTHORIZED_B_SESSION_LIFECYCLE_OPERATIONS <= _current_routes()
    non_session_routes = {route for route in EXPECTED_ROUTES if route not in AUTHORIZED_B_SESSION_LIFECYCLE_OPERATIONS}
    assert _current_routes() - AUTHORIZED_B_SESSION_LIFECYCLE_OPERATIONS == non_session_routes


def test_openapi_contains_exactly_the_four_authorized_c_session_lifecycle_operations() -> None:
    """Phase 4b: mirrors the B session-lifecycle route-count guard exactly, for C's own four
    routes (create/start, resume, abandon, complete)."""
    assert len(AUTHORIZED_C_SESSION_LIFECYCLE_OPERATIONS) == 4
    assert AUTHORIZED_C_SESSION_LIFECYCLE_OPERATIONS <= _current_routes()
    non_c_session_routes = {
        route for route in EXPECTED_ROUTES if route not in AUTHORIZED_C_SESSION_LIFECYCLE_OPERATIONS
    }
    assert _current_routes() - AUTHORIZED_C_SESSION_LIFECYCLE_OPERATIONS == non_c_session_routes


def test_openapi_contains_exactly_the_two_authorized_c_task_serving_operations() -> None:
    """Phase 5: mirrors the C session-lifecycle route-count guard exactly, for the two
    task-serving routes (next, actions)."""
    assert len(AUTHORIZED_C_TASK_SERVING_OPERATIONS) == 2
    assert AUTHORIZED_C_TASK_SERVING_OPERATIONS <= _current_routes()
    non_c_task_routes = {
        route for route in EXPECTED_ROUTES if route not in AUTHORIZED_C_TASK_SERVING_OPERATIONS
    }
    assert _current_routes() - AUTHORIZED_C_TASK_SERVING_OPERATIONS == non_c_task_routes


def test_b_session_dto_contains_no_scientific_expiry_or_attempt_fields() -> None:
    """Scans actual DTO field identifiers only (via AST), not prose/docstrings, since
    this module's docstring legitimately documents excluded terms by name."""
    tree = ast.parse(Path("app/domain/b_session.py").read_text(encoding="utf-8"))
    field_names = {
        node.target.id.lower()
        for class_def in ast.walk(tree)
        if isinstance(class_def, ast.ClassDef)
        for node in class_def.body
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name)
    }
    forbidden = PROHIBITED_COLUMN_TERMS | {
        "expires_at", "expiry", "timeout", "question", "attempt", "opportunity",
    }
    assert not {name for name in field_names if any(term in name for term in forbidden)}


def test_no_yass_research_or_scientific_imports() -> None:
    """BE3b wires ``app/infrastructure/live_engine/adapter.py`` to the reviewed
    ``component_b_generator`` package (see ``tests/test_be3_live_engine_boundary.py`` for the
    detailed BE3 import-boundary guards). That one file is therefore exempt from the
    ``component_b_generator`` top-level prohibition here, but not from ``yass``/``pipeline``/
    ``pilot`` — every other file in ``app/`` stays fully disjoint from all of these roots."""
    prohibited_import_roots = {
        "component_b_generator", "yass", "bkt", "sequencing", "certification",
        "guess_guard", "pipeline", "pilot",
    }
    allowed_adapter_path = Path("app/infrastructure/live_engine/adapter.py")
    for path in Path("app").rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported = {alias.name.split(".")[0].lower() for alias in node.names}
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported = {node.module.split(".")[0].lower()}
            else:
                continue
            if path == allowed_adapter_path:
                assert imported.isdisjoint({"yass", "pipeline", "pilot"}), (path, imported)
                continue
            assert imported.isdisjoint(prohibited_import_roots), (path, imported)


def test_dependency_files_exclude_research_generator() -> None:
    dependency_files = [
        path
        for name in ("requirements.in", "requirements.lock", "requirements.txt")
        if (path := Path(name)).exists()
    ]
    assert dependency_files
    dependency_text = "\n".join(path.read_text(encoding="utf-8") for path in dependency_files).lower()
    assert "component-b-generator" not in dependency_text
    assert "component_b_generator" not in dependency_text
    assert "yass" not in dependency_text


def test_migration_introduces_only_authorized_tables_and_no_triggers_or_seed_data() -> None:
    migration = Path("migrations/versions/20260722_0002_be2_neutral_persistence.py").read_text(encoding="utf-8")
    created = set(re.findall(r'op\.create_table\(\s*"([^"]+)"', migration))
    assert created == BE2_BASE_TABLES
    lowered = migration.lower()
    assert "create_trigger" not in lowered
    assert "create trigger" not in lowered
    assert "bulk_insert" not in lowered
    assert "op.execute" not in lowered


def test_corrective_migration_adds_only_the_two_authorized_integrity_guards() -> None:
    migration = Path("migrations/versions/20260722_0003_bundle_integrity_guards.py").read_text(
        encoding="utf-8"
    )
    assert not re.findall(r'op\.create_table\(\s*"([^"]+)"', migration)
    assert "enforce_b_session_active_bundle_eligibility" in migration
    assert "trg_b_sessions_active_bundle_eligible" in migration
    assert "enforce_b_runtime_bundle_integrity" in migration
    assert "trg_b_runtime_bundle_integrity" in migration
    lowered = migration.lower()
    assert "insert into" not in lowered
    assert "component_b_generator" not in lowered
    assert "yass" not in lowered


def test_profile_classroom_migration_and_routes_stay_within_authorization() -> None:
    migration = Path("migrations/versions/20260722_0004_profile_classroom_foundations.py").read_text(encoding="utf-8")
    assert set(re.findall(r'op\.create_table\(\s*"([^"]+)"', migration)) == {"teacher_profiles", "classrooms", "classroom_invites", "classroom_memberships"}
    lowered = migration.lower()
    assert "learner_profiles" not in lowered
    assert "bulk_insert" not in lowered
    assert "component_b_generator" not in lowered
    assert "yass" not in lowered
    # The blanket "no invite/membership path" check from the prior limited batch is
    # superseded by the now-authorized invite/membership batch; see
    # test_invite_membership_migration_adds_only_the_authorized_index and
    # test_openapi_contains_exactly_the_nine_authorized_invite_membership_operations
    # for the current, narrower boundary checks. Session/scientific paths remain
    # prohibited unconditionally; see test_no_session_question_answer_or_scientific_route_exists.


def test_invite_membership_migration_adds_only_the_authorized_index() -> None:
    migration = Path("migrations/versions/20260723_0001_classroom_membership_single_approval.py").read_text(encoding="utf-8")
    assert not re.findall(r'op\.create_table\(\s*"([^"]+)"', migration)
    assert not re.findall(r'op\.add_column\(', migration)
    assert not re.findall(r'op\.drop_column\(', migration)
    assert "uq_classroom_memberships_one_approved_per_learner" in migration
    assert '"classroom_memberships"' in migration
    lowered = migration.lower()
    assert "classroom_invites" not in lowered
    assert "create_trigger" not in lowered
    assert "create trigger" not in lowered
    assert "bulk_insert" not in lowered
    assert "component_b_generator" not in lowered
    assert "yass" not in lowered


def test_no_production_failure_injection_or_debug_mechanism() -> None:
    """The corrective batch injects failure only in tests; production code exposes no such hook."""
    markers = (
        "controlled-test-failure", "_failing_audit", "inject_fail", "injectfailure",
        "fail_flag", "failure_flag", "debug_fail", "force_error", "force_failure",
    )
    for path in Path("app").rglob("*.py"):
        lowered = path.read_text(encoding="utf-8").lower()
        for marker in markers:
            assert marker not in lowered, (path, marker)
    paths = set(app.openapi()["paths"])
    assert not any("debug" in path or "inject" in path or "/test" in path for path in paths)


# =====================================================================================
# Phase 1 batch 1b — Component C full-dotted-path import boundary (C-8).
#
# The B guard above (test_no_yass_research_or_scientific_imports) matches import ROOTS only via
# `.split(".")[0]`, which is correct for B but insufficient for C: both the legitimate
# `component_c_generator.pipeline.evidence` and the prohibited
# `component_c_generator.pipeline.session` share the identical root `component_c_generator` --
# a root-only check cannot distinguish them. B's guard, its prohibited_import_roots set, and its
# exempt path are left completely untouched above; everything below is new, additive, and
# independent.
# =====================================================================================

_ALLOWED_C_ADAPTER_PATH = Path("app/infrastructure/live_engine_c/adapter.py")

# The 16 never-ship C module paths, sourced from 1a's own list rather than hand-copied here --
# see test_prohibited_c_full_dotted_paths_matches_1a_never_ship_modules below, which proves this
# derivation stays correct rather than merely asserting it once at import time.
PROHIBITED_C_FULL_DOTTED_PATHS = frozenset(NEVER_SHIP_MODULES)


def _full_dotted_import_candidates(node: ast.AST) -> set[str]:
    """Every full dotted path a single Import/ImportFrom AST node could bind into scope.

    For `ast.ImportFrom` this includes BOTH the bare `node.module` (covers
    `from component_c_generator.pipeline.session import X`, where the prohibited path is
    already the whole module) AND `f"{node.module}.{alias.name}"` for every imported name
    (covers `from component_c_generator.pipeline import session`, where the prohibited path
    only appears once the imported name is appended)."""
    if isinstance(node, ast.Import):
        return {alias.name for alias in node.names}
    if isinstance(node, ast.ImportFrom) and node.module:
        return {node.module} | {f"{node.module}.{alias.name}" for alias in node.names}
    return set()


def _matches_prohibited_full_path(candidate: str, prohibited: frozenset[str]) -> bool:
    """Exact match or dot-bounded prefix match -- NEVER substring containment. This is what
    lets `component_c_generator.pipeline.evidence` pass (it is neither equal to, nor a
    dot-prefix of, any prohibited entry) while `component_c_generator.pipeline.session` and
    `component_c_generator.audits.leakage` (a dot-prefix of the whole-package entry
    `component_c_generator.audits`) are both caught."""
    return any(candidate == p or candidate.startswith(p + ".") for p in prohibited)


def test_component_c_generator_full_dotted_path_enforcement() -> None:
    """SIGNAL: only app/infrastructure/live_engine_c/adapter.py may have `component_c_generator`
    as an import root anywhere under app/ (root check, same style as B's guard); even inside
    that one exempt file, none of the 16 never-ship full dotted paths may appear among its
    import candidates (full-dotted-path check, matched via
    _matches_prohibited_full_path -- exact-or-dot-prefix, never substring). Would FAIL if any
    other file under app/ imported component_c_generator at all, or if the adapter itself
    imported e.g. `component_c_generator.pipeline.session` or `component_c_generator.audits.*`."""
    for path in Path("app").rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            candidates = _full_dotted_import_candidates(node)
            roots = {c.split(".")[0] for c in candidates}
            if path != _ALLOWED_C_ADAPTER_PATH:
                assert "component_c_generator" not in roots, (path, candidates)
                continue
            for candidate in candidates:
                if candidate.split(".")[0] != "component_c_generator":
                    continue
                assert not _matches_prohibited_full_path(
                    candidate, PROHIBITED_C_FULL_DOTTED_PATHS
                ), (path, candidate)


def test_full_dotted_path_guard_negative_control_catches_same_root_violation() -> None:
    """POSITIVE PROOF the full-dotted-path matcher is doing real work, not merely inheriting B's
    root-only check. Parses SYNTHETIC, in-memory module source -- never a file under app/, which
    would be a real boundary breach waiting to be committed by accident -- containing
    `from component_c_generator.pipeline import session`, a SAME-ROOT, DIFFERENT-FULL-PATH case
    the OLD root-only matcher could not have distinguished from the legitimate
    `from component_c_generator.pipeline import evidence` (both share root
    `component_c_generator`, exempted for the adapter path). Would FAIL (silently) if the
    matcher were reverted to root-only, since both cases share the same root and a root-only
    check cannot discriminate them -- this is the discrimination pair the negative control
    exists to prove."""
    violating_source = "from component_c_generator.pipeline import session\n"
    legitimate_source = "from component_c_generator.pipeline import evidence\n"

    violating_tree = ast.parse(violating_source, filename="<synthetic-negative-control-violation>")
    legitimate_tree = ast.parse(legitimate_source, filename="<synthetic-negative-control-legitimate>")

    def _any_prohibited(tree: ast.AST) -> bool:
        return any(
            _matches_prohibited_full_path(candidate, PROHIBITED_C_FULL_DOTTED_PATHS)
            for node in ast.walk(tree)
            for candidate in _full_dotted_import_candidates(node)
        )

    assert _any_prohibited(violating_tree), "negative control failed to catch a real violation"
    assert not _any_prohibited(legitimate_tree), (
        "guard incorrectly flagged a legitimate sibling import -- it is not discriminating"
    )


def test_prohibited_c_full_dotted_paths_matches_1a_never_ship_modules() -> None:
    """SIGNAL: PROHIBITED_C_FULL_DOTTED_PATHS (this file, used operationally by the guard above)
    stays set-equal to NEVER_SHIP_MODULES (backend/tests/test_c1a_wheel_provenance.py, the
    16-module never-ship list 1a's wheel-content tests assert against). Would FAIL the moment
    the two lists diverge -- e.g. if a future Phase 1a revision adds a 17th never-ship module and
    this file is not updated to match -- rather than silently leaving this guard one module
    weaker than the wheel's own packaging boundary."""
    assert PROHIBITED_C_FULL_DOTTED_PATHS == frozenset(NEVER_SHIP_MODULES)


# =====================================================================================
# VALIDATORS BATCH — T6: only the C adapter may import ``validators`` (now shipped in B's wheel
# at the same pin; see backend/provenance/component-b-live-engine-manifest.json's
# validators_widened_closure). Same root-check style as B's own guard
# (test_no_yass_research_or_scientific_imports) above, extended to a second exempt path rather
# than folded into either existing prohibited_import_roots set -- B's guard's own prohibited set
# and exempt path stay completely untouched (G9: this is additive, not a rewrite of an existing
# assertion).
# =====================================================================================


def test_validators_import_root_restricted_to_the_c_adapter() -> None:
    """SIGNAL: only app/infrastructure/live_engine_c/adapter.py may have `validators` as an
    import root anywhere under app/. Would FAIL if any other file under app/ imported
    `validators` at all, or if the adapter's own import of it were removed (the second assert
    would then vacuously pass on a mistranslated/reverted conversion -- so it also asserts the
    adapter DOES import it, a positive control that this guard is exercising a real, present
    import, not an absent one)."""
    adapter_path = Path("app/infrastructure/live_engine_c/adapter.py")
    adapter_imports_validators = False
    for path in Path("app").rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                roots = {alias.name.split(".")[0] for alias in node.names}
            elif isinstance(node, ast.ImportFrom) and node.module:
                roots = {node.module.split(".")[0]}
            else:
                continue
            if "validators" not in roots:
                continue
            assert path == adapter_path, (path, roots)
            adapter_imports_validators = True
    assert adapter_imports_validators, "adapter no longer imports validators -- guard is vacuous"


# =====================================================================================
# Phase 1 batch 1b — PROHIBITED_COLUMN_TERMS mechanism, proven to fire (X-10), not merely
# present. NEVER touches Base.metadata / EXPECTED_TABLES -- uses a throwaway
# sqlalchemy.MetaData()/Table so test_exact_authorized_model_table_set_and_no_scientific_columns
# above stays byte-identical and its exact-equality assertion is never at risk.
# =====================================================================================

# Phase 3a: the 13 real collisions, derived term-by-term against PROHIBITED_COLUMN_TERMS from
# the ten new C tables (Phase 3a work order R-B). Two classes, named per pair below:
#   CARRIES-REAL-CONTENT -- a private column legitimately holding scientific content, same
#     reasoning as AUTHORIZED_ANSWER_BEARING_COLUMNS's two B entries.
#   FALSE-POSITIVE-NAME -- the term matches the column NAME but the column's value domain
#     (enforced by a CHECK constraint) never actually contains that kind of content.
AUTHORIZED_C_COLUMN_EXCEPTIONS: frozenset[tuple[str, str]] = frozenset(
    {
        # FALSE-POSITIVE-NAME (R-C): domain is exactly ('same_session_fresh',
        # 'unavailable_fallback'), enforced by ck_c_sessions_mastery_context_mode /
        # ck_c_task_opportunities_mastery_context_mode -- never a mastery scalar.
        ("c_sessions", "mastery_context_mode"),
        ("c_task_opportunities", "mastery_context_mode"),
        # CARRIES-REAL-CONTENT (R-D): SelectionResult's own returned provenance for the governed
        # clamp(round(1 + 4 x mastery), 1, 5) initial-difficulty decision (C-17) -- C auditing
        # its own reviewed calculation, not re-storing B's contract.
        ("c_task_opportunities", "mastery_selected_skill"),
        # CARRIES-REAL-CONTENT: the private, never-public correct answer (mirrors B's
        # AUTHORIZED_ANSWER_BEARING_COLUMNS reasoning exactly).
        ("c_task_instances", "correct_answer_payload"),
        # CARRIES-REAL-CONTENT: not named by v3.0 Section 8 -- found by this batch's own
        # term-by-term derivation (R-B). "correctness_function_id" contains "correct".
        ("c_task_instances", "correctness_function_id"),
        ("c_task_opportunity_summaries", "correct_task"),
        ("c_task_opportunity_summaries", "c_answer_changes"),
        ("c_task_opportunity_summaries", "task_latency_sec"),
        ("c_task_opportunity_summaries", "first_attempt_correct"),
        ("c_task_opportunity_summaries", "final_attempt_correct"),
        ("c_session_aggregate_results", "correct_task_count"),
        ("c_session_aggregate_results", "c_mean_game_task_latency_sec"),
        ("c_session_aggregate_results", "c_median_game_task_latency_sec"),
        # CARRIES-REAL-SCIENTIFIC-CONTENT (R-H): name-identical to
        # component_c_generator.scaffolds.ladder.ScaffoldDecisionContext's
        # consecutive_incorrect_current_task field -- the substring match ("incorrect" contains
        # "correct") is incidental, but the semantics are not: this is a count of incorrect
        # attempts, i.e. correctness-derived learner data, same class as correct_task /
        # first_attempt_correct / final_attempt_correct above. Renaming it to dodge the guard
        # would break parity with the governed scaffold-decision contract (R-H, extending R-B/G9).
        # Do NOT reuse mastery_context_mode's false-positive-name justification for this entry.
        ("c_scaffold_events", "consecutive_incorrect_current_task"),
    }
)


def _offending_columns(tables, prohibited_terms, authorized_exceptions) -> set[tuple[str, str]]:
    """Same offender-derivation LOGIC as
    test_exact_authorized_model_table_set_and_no_scientific_columns's inline check above --
    written as a standalone, independently-callable function so it can be run against a
    throwaway MetaData/Table without touching that test's own code or Base.metadata."""
    return {
        (table.name, column.name)
        for table in tables
        for column in table.columns
        if any(term in column.name.lower() for term in prohibited_terms)
        and (table.name, column.name) not in authorized_exceptions
    }


def test_prohibited_column_terms_mechanism_fires_on_synthetic_metadata() -> None:
    """SIGNAL: against a THROWAWAY sqlalchemy.MetaData()/Table (never Base.metadata), a
    deliberately offending column name (`mastery_score`) is flagged, and a SIBLING column that
    ALSO contains a prohibited term (`mastery_baseline_ok`) but is on the allow-list is
    correctly exempted -- proving both halves of the mechanism (detection AND exemption) fire
    against a real SQLAlchemy structure, not merely that an empty allow-list vacuously passes
    against zero C tables. Would FAIL if the offender-derivation logic stopped matching a
    genuinely prohibited term, or if it flagged an allow-listed column anyway."""
    synthetic_metadata = MetaData()
    Table(
        "c_synthetic_test_table",
        synthetic_metadata,
        Column("id", Integer, primary_key=True),
        Column("mastery_score", String),
        Column("mastery_baseline_ok", String),
    )
    synthetic_exceptions = {("c_synthetic_test_table", "mastery_baseline_ok")}

    offenders = _offending_columns(
        synthetic_metadata.tables.values(), PROHIBITED_COLUMN_TERMS, synthetic_exceptions
    )

    assert offenders == {("c_synthetic_test_table", "mastery_score")}
    assert set(Base.metadata.tables) == EXPECTED_TABLES  # untouched by the synthetic metadata above


def test_prohibited_column_terms_allow_list_matches_the_14_computed_pairs() -> None:
    """SIGNAL: AUTHORIZED_C_COLUMN_EXCEPTIONS is EXACTLY the C-side collision set COMPUTED live
    from real Base.metadata against the real PROHIBITED_COLUMN_TERMS -- not a hand-maintained
    list trusted on its own. R-I (Phase 3a UNBLOCK ruling): the 13-pair hand derivation missed
    ("c_scaffold_events", "consecutive_incorrect_current_task"), found only when the guard ran
    against real metadata. The fix is to compute the collision set from source every time this
    test runs and compare AUTHORIZED_C_COLUMN_EXCEPTIONS against it -- never to hand-maintain the
    count alone. Would FAIL if a future column collides and nobody adds its allow-list entry, or
    if an entry is removed/added without a matching real collision, or if the computed set drifts
    from 14 for any reason."""
    computed_c_collisions = {
        (table.name, column.name)
        for table in Base.metadata.tables.values()
        for column in table.columns
        if any(term in column.name.lower() for term in PROHIBITED_COLUMN_TERMS)
        and (table.name, column.name) not in AUTHORIZED_ANSWER_BEARING_COLUMNS
    }
    assert computed_c_collisions == AUTHORIZED_C_COLUMN_EXCEPTIONS
    assert len(AUTHORIZED_C_COLUMN_EXCEPTIONS) == 14
    assert ("c_task_opportunity_summaries", "consecutive_error_max_within_task") not in (
        AUTHORIZED_C_COLUMN_EXCEPTIONS
    ), "this column does not collide (R-B) and must never need an exemption"


# =====================================================================================
# Phase 1 batch 1b — seed-derivation symbols must never be reachable from the adapter (C3).
# AST-based: a text grep would be defeated by this file's own module docstring, which names
# these four symbols in prose to explain why they are absent.
# =====================================================================================

_PROHIBITED_SEED_DERIVATION_SYMBOLS = frozenset(
    {"derive_child_lineage", "SeedManager", "rng_from", "SUBSTREAMS"}
)


def test_adapter_references_no_seed_derivation_symbol() -> None:
    """SIGNAL: parses app/infrastructure/live_engine_c/adapter.py's AST and asserts none of
    derive_child_lineage, SeedManager, rng_from, SUBSTREAMS appears as an imported name, an
    attribute access, or a bare Name reference anywhere in the file -- checked via
    ast.Import/ast.ImportFrom/ast.Attribute/ast.Name nodes, never a text search, so the
    adapter's own module docstring (which names these four symbols in prose to explain their
    absence) cannot trip this test. Would FAIL if a future edit added
    `from component_c_generator.seeds import derive_child_lineage` (or called
    `seeds.SeedManager(...)`/`seeds.rng_from(...)`/referenced `seeds.SUBSTREAMS`) to work around
    the seed-lineage gap instead of waiting for an explicit future authorization (G3)."""
    adapter_path = _ALLOWED_C_ADAPTER_PATH
    tree = ast.parse(adapter_path.read_text(encoding="utf-8"), filename=str(adapter_path))
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            found |= {alias.name for alias in node.names} & _PROHIBITED_SEED_DERIVATION_SYMBOLS
        elif isinstance(node, ast.Import):
            found |= {
                alias.name.split(".")[-1] for alias in node.names
            } & _PROHIBITED_SEED_DERIVATION_SYMBOLS
        elif isinstance(node, ast.Attribute) and node.attr in _PROHIBITED_SEED_DERIVATION_SYMBOLS:
            found.add(node.attr)
        elif isinstance(node, ast.Name) and node.id in _PROHIBITED_SEED_DERIVATION_SYMBOLS:
            found.add(node.id)
    assert not found, found


# =====================================================================================
# 9c-0 (Component_C_9b_9c_And_Generator_Plan_v1.0 "9c-0 -- resolve the identifier question
# FIRST") -- the identifier-derivation prohibition, as an allow-listed AST guard over the
# WHOLE application tree, not just live_engine_c/. The determination (D1): student_number()
# is sha256(learner_id) % 10_000 (app/application/opportunity_selection.py:151-154); derived
# ids in that 10,000-wide space collide at roughly 50% by ~118 learners and ~12% by 50,
# while assigned ids in the same space collide at zero -- the space is not the defect,
# deriving into it is. Outbound student_id (the frozen C->3 contract's ^STU-[0-9]{4}$,
# models.contracts.StudentId) must come from the shared intervention-session mapping --
# assigned and recorded, never derived from this function. The contract's own ID-05
# invariant (_student_prefix(identifier) != student_id, contracts.py:26-27,96-107) is a
# prefix-consistency check, not a uniqueness check, so it cannot catch a derived-id
# collision -- this guard has to exist in code because the frozen contract offers no
# defence.
#
# The trap (D2), named as a prohibition, not an omission: package_student_id() already
# returns exactly ^STU-[0-9]{4}$ -- the same shape the C->3 contract's student_id wants.
# Reusing it for an outbound payload is one line, looks correct, passes the contract's own
# regex AND ID-05 cleanly, and silently merges two learners who happen to derive the same
# 4-digit number. That collision is invisible to every frozen validator.
#
# Scope of the allow-list, deliberately over app/ as a whole rather than only
# live_engine_c/: the next batch this feeds (9c-1's shared outbox/contract-delivery
# tables) is explicitly shared B/C infrastructure and will NOT live under live_engine_c/,
# which is C-specific. A guard scoped only to live_engine_c/ would go green while staying
# silent about exactly the layer -- the outbox, wherever 9c-1 places it, or 9b-1's emission
# surface, or the route layer -- where a 4-digit key is most tempting to reach for as a
# shard/route key. Scanning the whole app/ tree with an explicit two-file allow-list covers
# all of those regardless of where they land.
# =====================================================================================

_PROHIBITED_IDENTITY_DERIVATION_SYMBOLS = frozenset(
    {"student_number", "package_student_id", "package_item_opportunity_id"}
)

# Every file under app/ that may reference the three symbols above -- exactly these two,
# no others. A third entry may only be added by a batch that justifies the new consumer
# in the same change as the allow-list edit (see buildLog1.md's 9c-0 entry, "Remains
# open" -- 9b-1 and 9c-1 are named as the batches expected to next add code this guard
# covers). Never widen this set just to make a red run green.
_IDENTITY_DERIVATION_ALLOWED_FILES = frozenset(
    {
        # The definition site: student_number(), package_item_opportunity_id(),
        # package_student_id() are all defined here.
        Path("app/application/opportunity_selection.py"),
        # The one legitimate consumer: package_student_id() -> SkillMasteryUpdate.student_id
        # (session_completion.py:424), which stays internal storage (SessionAggregateResultRecord
        # via adapter.aggregate_session) and reaches no outbound contract today.
        Path("app/application/session_completion.py"),
    }
)


def _symbols_referenced_in(tree: ast.AST, symbols: frozenset[str]) -> set[str]:
    """Shared by the real guard and its negative control, so the two can never drift apart --
    unlike the seed-derivation precedent above, which hand-writes its AST walk inline in both
    places. Matches ast.Import / ast.ImportFrom / ast.Attribute / ast.Name exactly as that
    precedent does; never a text search, so a docstring naming these symbols in prose (as this
    very block does, repeatedly, above) cannot trip it."""
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            found |= {alias.name for alias in node.names} & symbols
        elif isinstance(node, ast.Import):
            found |= {alias.name.split(".")[-1] for alias in node.names} & symbols
        elif isinstance(node, ast.Attribute) and node.attr in symbols:
            found.add(node.attr)
        elif isinstance(node, ast.Name) and node.id in symbols:
            found.add(node.id)
    return found


def test_identity_derivation_symbols_confined_to_allowed_files() -> None:
    """SIGNAL (D1/D2/D3): asserts student_number, package_student_id and
    package_item_opportunity_id are referenced -- as an import, an attribute access, or a bare
    name -- in NO file under app/ except the two files in
    _IDENTITY_DERIVATION_ALLOWED_FILES. Scans the whole app/ tree (rglob), not just
    live_engine_c/, because the outbound-contract paths this prohibition protects (9c-1's shared
    outbox, 9b-1's emission surface, the route layer) are not guaranteed to live under
    live_engine_c/ -- 9c-1's outbox is explicitly shared B/C infrastructure and will not.
    Non-vacuity: asserts app/ resolves and the scanned file set is non-empty (83 files at this
    commit, not pinned exactly so the guard does not go red on every new module). Would FAIL if
    any third file anywhere under app/ started referencing any of the three symbols -- e.g. a
    future outbox/routing module reaching for the 4-digit derivation as a shard or delivery key
    -- forcing that addition through an explicit, reviewed allow-list edit instead of silently
    passing."""
    app_root = Path("app")
    assert app_root.is_dir()
    scanned_files = sorted(app_root.rglob("*.py"))
    assert scanned_files, "no *.py files found under app/ -- scan set degraded to a no-op"

    violations: dict[Path, set[str]] = {}
    for path in scanned_files:
        relative = path.relative_to(".") if path.is_absolute() else path
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        found = _symbols_referenced_in(tree, _PROHIBITED_IDENTITY_DERIVATION_SYMBOLS)
        if found and relative not in _IDENTITY_DERIVATION_ALLOWED_FILES:
            violations[relative] = found

    assert not violations, violations


def test_identity_derivation_guard_negative_control_catches_synthetic_violation() -> None:
    """POSITIVE PROOF the confinement guard above does real work, not merely observing that no
    file happens to violate it. Parses SYNTHETIC, in-memory module source -- never a file under
    app/, which would be a real boundary breach waiting to be committed by accident -- and
    asserts _symbols_referenced_in (the SAME helper the real test above uses, so this cannot
    silently drift from what it validates) actually fires on it. Would FAIL if the detection
    logic stopped recognising a known-bad reference to package_student_id."""
    violating_source = (
        "from app.application.opportunity_selection import package_student_id\n"
        "\n"
        "def build_outbound_payload(learner_id):\n"
        "    return package_student_id(learner_id)\n"
    )
    violating_tree = ast.parse(violating_source, filename="<synthetic-identity-derivation-violation>")
    found = _symbols_referenced_in(violating_tree, _PROHIBITED_IDENTITY_DERIVATION_SYMBOLS)
    assert found == {"package_student_id"}, found


def test_identity_derivation_allow_list_entries_are_all_minimal() -> None:
    """D5 (batch 9c-1b, carried from 9c-0): asserts every file in
    ``_IDENTITY_DERIVATION_ALLOWED_FILES`` actually references at least one of the three
    prohibited symbols -- so a STALE or SPURIOUS allow-list entry (one added for a file that never
    ends up needing it, or one left behind after its only reference is removed) FAILS instead of
    silently widening the guard's exemption for no reason. Uses the same ``_symbols_referenced_in``
    helper the real confinement guard and its own negative control use, so this cannot drift from
    what it validates."""
    for allowed_path in _IDENTITY_DERIVATION_ALLOWED_FILES:
        tree = ast.parse(allowed_path.read_text(encoding="utf-8"), filename=str(allowed_path))
        found = _symbols_referenced_in(tree, _PROHIBITED_IDENTITY_DERIVATION_SYMBOLS)
        assert found, f"{allowed_path} is allow-listed but references none of the prohibited symbols"


# =====================================================================================
# Phase 1 batch 1b — no domain config field may carry a default (G1: a default on a config
# field is a recorded threshold). Asserted structurally, not reviewed.
# =====================================================================================

_DOMAIN_CONFIG_TYPES = (
    AggregationConfig,
    EvidenceWindowConfig,
    GenerationConfig,
    PolicyConfig,
    RecoveryConfig,
    SafetyConfig,
    ScaffoldConfig,
    SelectionConfig,
    TemplateGenerationParams,
)


def test_no_domain_config_field_carries_a_default() -> None:
    """SIGNAL: every field on every Component C domain config dataclass has no default value
    and no default_factory, asserted via dataclasses.fields() -- not a style review. The pinned
    package carries zero defaults across all eight top-level configs (independently verified);
    a default here would be this codebase recording an unapproved scientific threshold, weight,
    window, or cap (G1), since Component C is PROPOSED, not approved. Would FAIL the moment a
    future edit added so much as one `field: float = 0.8`-style default to any of these nine
    dataclasses."""
    for config_type in _DOMAIN_CONFIG_TYPES:
        for config_field in dataclasses.fields(config_type):
            assert config_field.default is dataclasses.MISSING, (
                config_type.__name__, config_field.name,
            )
            assert config_field.default_factory is dataclasses.MISSING, (
                config_type.__name__, config_field.name,
            )


# =====================================================================================
# Phase 4 — W1/W2/W5: SelectionConfig is INJECTION ONLY, no default anywhere (owner ruling,
# Phase 4 work order, "W — OWNER-RULED. OPTION 1: INJECTION, NO DEFAULT ANYWHERE"). Distinct from
# test_no_domain_config_field_carries_a_default above, which checks the DATACLASS's own fields;
# this checks CALL SITES and FUNCTION SIGNATURES across app/ -- a dataclass with no-default
# fields can still be defaulted at a call site (`selection_config: SelectionConfig =
# default_selection_config()`), which is exactly what this guard exists to catch.
# =====================================================================================


def _config_default_violations(tree: ast.AST, *, param_name: str, factory_name: str) -> list[tuple[str, str]]:
    """Shared scan logic behind both the SelectionConfig (W1/W2, Phase 4) and GenerationConfig
    (S1, Phase 5 work order: "Extend the W5-style AST guard to cover default_generation_config
    exactly as it covers default_selection_config") injection-only guards. Returns
    (kind, node_name) violation markers -- ("defaulted_param", function name) for a defaulted
    parameter, ("factory_call", dumped call) for a call to the named factory -- rather than
    asserting inline, so this same logic can be run against BOTH the real app/ tree and synthetic
    ASTs (the latter proves the mechanism fires at all, not only that it happened to find nothing
    today)."""
    violations: list[tuple[str, str]] = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            args = node.args
            positional = args.posonlyargs + args.args
            defaulted_positional = dict(
                zip(positional[len(positional) - len(args.defaults):], args.defaults)
            )
            defaulted_kwonly = {
                arg: default
                for arg, default in zip(args.kwonlyargs, args.kw_defaults)
                if default is not None
            }
            for arg_node, _default in {**defaulted_positional, **defaulted_kwonly}.items():
                if arg_node.arg == param_name:
                    violations.append(("defaulted_param", node.name))
        if isinstance(node, ast.Call):
            callee = node.func
            name = callee.id if isinstance(callee, ast.Name) else getattr(callee, "attr", None)
            if name == factory_name:
                violations.append(("factory_call", ast.dump(node)[:200]))
    return violations


def test_no_app_code_defaults_or_calls_default_selection_config() -> None:
    """SIGNAL: no function signature anywhere under app/ gives a `selection_config` parameter a
    default value (W1), and no file under app/ calls `default_selection_config` at all (W2 --
    reading the CALIBRATION_PENDING W value out of the wheel at runtime does not change its
    provenance, it only hides the dependency). Would FAIL if a future edit added
    `selection_config: SelectionConfig = default_selection_config()` to any application-layer
    function, or called `default_selection_config()` anywhere in app/ even without assigning a
    default (e.g. inline at a call site)."""
    for path in Path("app").rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        violations = _config_default_violations(
            tree, param_name="selection_config", factory_name="default_selection_config"
        )
        assert not violations, (path, violations)


def test_no_app_code_defaults_or_calls_default_generation_config() -> None:
    """SIGNAL (Phase 5, S1): the same guard, same shape, for GenerationConfig -- "GenerationConfig
    stays INJECTION-ONLY with NO DEFAULT on every path (W1's shape). No production path may call
    default_generation_config()." Governance assigned no values to any of the 30 templates'
    generation parameters (every one is TEST_FIXTURE_ONLY); reading them out of the wheel at
    runtime via its own default_generation_config() would hide that dependency exactly as
    default_selection_config() would have for W. Would FAIL if a future edit added
    `generation_config: GenerationConfig = default_generation_config()` to any application-layer
    function, or called `default_generation_config()` anywhere in app/ even without assigning a
    default."""
    for path in Path("app").rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        violations = _config_default_violations(
            tree, param_name="generation_config", factory_name="default_generation_config"
        )
        assert not violations, (path, violations)


def test_no_app_code_defaults_or_calls_default_safety_config() -> None:
    """SIGNAL (Phase 6b, S8-a/X8-a): the same guard, same shape, for SafetyConfig. No threshold
    value in any source file; default_safety_config() never called from app/. Would FAIL if a
    future edit added `safety_config: SafetyConfig = default_safety_config()` to any
    application-layer function, or called `default_safety_config()` anywhere in app/ even without
    assigning a default."""
    for path in Path("app").rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        violations = _config_default_violations(
            tree, param_name="safety_config", factory_name="default_safety_config"
        )
        assert not violations, (path, violations)


def test_default_config_guard_mechanism_fires_on_synthetic_violations() -> None:
    """SIGNAL: proves _config_default_violations actually DETECTS what it claims to, for ALL
    THREE guards, against synthetic source -- not merely that it found nothing today. Four cases
    per param/factory pair: a positional default, a keyword-only default, a bare (unassigned)
    factory call, and a clean function that uses neither -- the first three must each be caught,
    the fourth must pass clean. Would FAIL if the detection logic stopped matching a real
    violation shape, or started flagging the clean case."""
    for param_name, factory_name in (
        ("selection_config", "default_selection_config"),
        ("generation_config", "default_generation_config"),
        ("safety_config", "default_safety_config"),
    ):
        positional_default_source = (
            f"def f(a, {param_name}={factory_name}()):\n    pass\n"
        )
        kwonly_default_source = (
            f"def f(a, *, {param_name}={factory_name}()):\n    pass\n"
        )
        bare_call_source = (
            f"def f({param_name}):\n    x = {factory_name}()\n    return x\n"
        )
        clean_source = (
            f"def f({param_name}):\n    return {param_name}\n"
        )

        for source in (positional_default_source, kwonly_default_source, bare_call_source):
            tree = ast.parse(source, filename="<synthetic-violation>")
            violations = _config_default_violations(
                tree, param_name=param_name, factory_name=factory_name
            )
            assert violations, (param_name, factory_name, source)

        clean_tree = ast.parse(clean_source, filename="<synthetic-clean>")
        clean_violations = _config_default_violations(
            clean_tree, param_name=param_name, factory_name=factory_name
        )
        assert not clean_violations, (param_name, factory_name, clean_violations)


# =====================================================================================
# Phase 6a — T1-2: completed_correct is the ONLY terminal_reason any CGameplayEventRecord(...)
# construction under app/ may carry (owner ruling T1, "record it as an owner ruling... not an
# engineering default" -- see app/application/live_engine_c/terminal_event.py's module docstring
# for the full nine-reason mapping this guard-tests the single built exception of).
# =====================================================================================


def _terminal_event_write_violations(tree: ast.AST) -> tuple[list[tuple[str, str]], int]:
    """Scans for CGameplayEventRecord(...) calls whose terminal_reason keyword is anything other
    than the literal string "completed_correct" or the literal None. Returns
    (violations, legitimate_site_count) rather than asserting inline, so the same logic drives
    both the real app/ scan and the synthetic positive control below."""
    violations: list[tuple[str, str]] = []
    legitimate_count = 0
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        callee = node.func
        name = callee.id if isinstance(callee, ast.Name) else getattr(callee, "attr", None)
        if name != "CGameplayEventRecord":
            continue
        for kw in node.keywords:
            if kw.arg != "terminal_reason":
                continue
            value = kw.value
            if isinstance(value, ast.Constant) and value.value is None:
                break
            if isinstance(value, ast.Constant) and value.value == "completed_correct":
                legitimate_count += 1
                break
            violations.append(("non_completed_correct_terminal_write", ast.dump(node)[:200]))
            break
    return violations, legitimate_count


def test_only_completed_correct_writes_a_terminal_gameplay_event() -> None:
    """SIGNAL (T1-2): no CGameplayEventRecord(...) construction anywhere under app/ ever sets
    terminal_reason to anything but the literal "completed_correct" or None, and exactly ONE such
    "completed_correct" site exists app-wide (app/application/live_engine_c/terminal_event.py).
    Would FAIL if a future edit added a second terminal-event write site, gave terminal_reason a
    dynamically-computed value this guard cannot prove safe, or set it to any of the other eight
    terminal reasons T1-1 leaves unbuilt -- "Otherwise Phase 8 can wire the client-reported
    reasons in without confronting this ruling, which is the failure mode the fail-closed mapping
    exists to prevent.\""""
    total_violations: list[tuple[Path, tuple[str, str]]] = []
    total_legitimate = 0
    for path in Path("app").rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        violations, legitimate = _terminal_event_write_violations(tree)
        total_violations.extend((path, v) for v in violations)
        total_legitimate += legitimate
    assert not total_violations, total_violations
    assert total_legitimate == 1, (
        "expected exactly one completed_correct terminal-write site", total_legitimate
    )


def test_terminal_event_write_guard_fires_on_synthetic_violations() -> None:
    """POSITIVE CONTROL (T1-2): proves _terminal_event_write_violations actually detects a
    non-completed_correct literal terminal_reason and a dynamically-supplied one, and correctly
    distinguishes (never flags) the one legitimate literal shape and the non-terminal None shape."""
    wrong_literal_violations, wrong_literal_legit = _terminal_event_write_violations(
        ast.parse("CGameplayEventRecord(terminal_reason='skipped')\n", filename="<synthetic-violation>")
    )
    assert wrong_literal_violations and wrong_literal_legit == 0

    dynamic_violations, dynamic_legit = _terminal_event_write_violations(
        ast.parse(
            "reason = get_reason()\nCGameplayEventRecord(terminal_reason=reason)\n",
            filename="<synthetic-violation>",
        )
    )
    assert dynamic_violations and dynamic_legit == 0

    legitimate_violations, legitimate_count = _terminal_event_write_violations(
        ast.parse(
            "CGameplayEventRecord(terminal_reason='completed_correct')\n",
            filename="<synthetic-legitimate>",
        )
    )
    assert not legitimate_violations and legitimate_count == 1

    none_violations, none_legit = _terminal_event_write_violations(
        ast.parse("CGameplayEventRecord(terminal_reason=None)\n", filename="<synthetic-clean>")
    )
    assert not none_violations and none_legit == 0


# =====================================================================================
# Phase 6a — T4: the evidence-construction guard, TWO classes, TWO rules, SYMMETRIC (owner:
# "you tightened my rule correctly. My wording named only the package type and would have been
# defeated by constructing the domain mirror and passing it where evidence is expected.").
#
# T4-a was reported BLOCKED in this batch's first implementation pass: the owner's literal
# wording ("NEVER constructed anywhere under app/") collided with app/infrastructure/
# live_engine_c/adapter.py:478's _to_pkg_policy_observable_evidence -- already built, Phase 1b/2,
# unwired until 6b's decide_adaptation is called -- which constructs exactly this package class,
# by design, to cross X-3 back into package form for the AdaptationPort call. That block was
# correct: the owner did not have this file in view when the absolute wording was written.
#
# SUPERVISOR RULING (correcting the owner's literal wording on evidence the owner did not have,
# NOT an owner approval): the package class may be constructed ONLY in
# app/infrastructure/live_engine_c/adapter.py -- the SAME X-1/T4-b shape already ruled for the
# domain mirror, not the absolute "never anywhere under app/" the earlier wording stated.
# _to_pkg_policy_observable_evidence is a pure field-by-field domain -> package translation, the
# same X-3 boundary shape as _to_pkg_mastery_payload (an already-uncontested translation in the
# same file) -- adapter.py is the one file this whole register already trusts to touch both type
# systems (X-1's own dispensation), so both directions of this one class pair belong to the same
# rule, not two different ones.
#
# BOTH classes, BOTH now adapter-only, BOTH proven with a synthetic violation and a clean control:
#   - package CPolicyObservableEvidence  -> app/infrastructure/live_engine_c/adapter.py ONLY
#   - domain  PolicyObservableEvidence   -> app/infrastructure/live_engine_c/adapter.py ONLY (T4-b)
#
# T4-d, restated for both halves: 6b's own criterion-1 positive controls REQUIRE test-side
# construction of either class, and NEITHER guard below may ever be read as forbidding that --
# owner's words: "Test-constructed evidence is a stimulus. It is never persisted, no child's data
# flows from it, and it is the one test shape that would have caught B-1. A builder refusing them
# by over-applying my Phase 5 ruling has made the opposite error." Neither guard scans tests/ (see
# the dedicated proof below).
#
# THE RESIDUAL (recorded, not solved): inside adapter.py itself, nothing structurally prevents
# building a domain (or now package) evidence object FROM NOTHING and translating/passing it on
# -- the guard's boundary is the FILE, not the call's own provenance. This is the identical,
# already-accepted trust model _to_pkg_mastery_payload lives under: one audited file, not a proof
# that every construction inside it is itself fed from build_policy_evidence's real output. Not a
# new gap this batch introduces; a pre-existing property of the X-1/X-3 boundary this guard
# inherits rather than closes.
# =====================================================================================


def _evidence_construction_violations(tree: ast.AST, *, class_name: str) -> list[str]:
    """Shared scan logic for BOTH evidence-class guards (package and domain) -- flags any
    construction of ``class_name`` found in the given tree. The caller is responsible for
    skipping app/infrastructure/live_engine_c/adapter.py, the one file both rulings permit to
    construct either class."""
    violations: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            callee = node.func
            name = callee.id if isinstance(callee, ast.Name) else getattr(callee, "attr", None)
            if name == class_name:
                violations.append(ast.dump(node)[:200])
    return violations


def _domain_policy_observable_evidence_violations(tree: ast.AST) -> list[str]:
    """T4-b: flags any construction of the DOMAIN PolicyObservableEvidence
    (app/domain/live_engine_c/types.py:284)."""
    return _evidence_construction_violations(tree, class_name="PolicyObservableEvidence")


def _package_policy_observable_evidence_violations(tree: ast.AST) -> list[str]:
    """T4-a (supervisor ruling, this batch): flags any construction of the PACKAGE
    CPolicyObservableEvidence (component_c_generator.models.adaptation), found via its import
    ALIAS as used in adapter.py (``_PkgCPolicyObservableEvidence``) -- a plain-name match, same
    mechanism as every other guard in this file; this does not resolve arbitrary aliasing
    elsewhere under app/, only the one alias the adapter's own X-3 translation actually uses."""
    violations = _evidence_construction_violations(tree, class_name="CPolicyObservableEvidence")
    violations += _evidence_construction_violations(tree, class_name="_PkgCPolicyObservableEvidence")
    return violations


def _evidence_guard_result(
    violation_fn, *, real_source_name: str
) -> tuple[list[tuple[Path, str]], bool]:
    """Runs one evidence-construction guard across app/, skipping (and separately recording
    whether) app/infrastructure/live_engine_c/adapter.py itself constructs the class -- shared by
    both the package and domain real-scan tests below so the two guards stay mechanically
    identical, not just similarly worded."""
    adapter_constructs_it = False
    violations: list[tuple[Path, str]] = []
    for path in Path("app").rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        found = violation_fn(tree)
        if path == _ALLOWED_C_ADAPTER_PATH:
            adapter_constructs_it = bool(found)
            continue
        violations.extend((path, v) for v in found)
    return violations, adapter_constructs_it


def test_domain_policy_observable_evidence_constructed_only_in_the_c_adapter() -> None:
    """SIGNAL (T4-b): the domain PolicyObservableEvidence dataclass is constructed ONLY in
    app/infrastructure/live_engine_c/adapter.py, and IS constructed there (a positive-presence
    check, same shape as the validators-import guard's own "adapter DOES import it" assertion --
    a guard whose real exception vanished would otherwise pass vacuously). Would FAIL if any other
    file under app/ constructed PolicyObservableEvidence directly, or if the adapter's own
    construction were ever removed without this guard noticing."""
    violations, adapter_constructs_it = _evidence_guard_result(
        _domain_policy_observable_evidence_violations, real_source_name="domain"
    )
    assert not violations, violations
    assert adapter_constructs_it, "expected the adapter to construct PolicyObservableEvidence at least once"


def test_package_policy_observable_evidence_constructed_only_in_the_c_adapter() -> None:
    """SIGNAL (T4-a, supervisor ruling): the PACKAGE CPolicyObservableEvidence is constructed
    ONLY in app/infrastructure/live_engine_c/adapter.py (via its
    _PkgCPolicyObservableEvidence import alias, adapter.py:478's _to_pkg_policy_observable_evidence
    -- the X-3 domain -> package translation for the AdaptationPort call), and IS constructed
    there. Would FAIL if any other file under app/ constructed the package class directly, or if
    the adapter's own construction were ever removed without this guard noticing."""
    violations, adapter_constructs_it = _evidence_guard_result(
        _package_policy_observable_evidence_violations, real_source_name="package"
    )
    assert not violations, violations
    assert adapter_constructs_it, "expected the adapter to construct CPolicyObservableEvidence at least once"


def test_domain_evidence_guard_fires_on_synthetic_violations() -> None:
    """POSITIVE CONTROL (T4-b/T4-c): proves _domain_policy_observable_evidence_violations actually
    detects a bare construction, and passes clean on source that never constructs it -- this guard
    "will pass trivially today" outside the adapter (T4-c's own words), so this control is what
    stops that from being worthless."""
    violating_tree = ast.parse(
        "PolicyObservableEvidence(session_mode='c_only')\n", filename="<synthetic-violation>"
    )
    assert _domain_policy_observable_evidence_violations(violating_tree)

    clean_tree = ast.parse(
        "build_policy_evidence(session_mode='c_only')\n", filename="<synthetic-clean>"
    )
    assert not _domain_policy_observable_evidence_violations(clean_tree)


def test_package_evidence_guard_fires_on_synthetic_violations() -> None:
    """POSITIVE CONTROL (T4-a): proves _package_policy_observable_evidence_violations actually
    detects a bare construction under either the real class name or the adapter's own import
    alias, and passes clean on source that never constructs it."""
    violating_tree_real_name = ast.parse(
        "CPolicyObservableEvidence(session_mode='c_only')\n", filename="<synthetic-violation>"
    )
    assert _package_policy_observable_evidence_violations(violating_tree_real_name)

    violating_tree_alias = ast.parse(
        "_PkgCPolicyObservableEvidence(session_mode='c_only')\n", filename="<synthetic-violation>"
    )
    assert _package_policy_observable_evidence_violations(violating_tree_alias)

    clean_tree = ast.parse(
        "build_policy_evidence(session_mode='c_only')\n", filename="<synthetic-clean>"
    )
    assert not _package_policy_observable_evidence_violations(clean_tree)


def test_evidence_construction_guards_do_not_scan_tests_directory() -> None:
    """T4-d, both halves (owner's words: "Test-constructed evidence is a stimulus. It is never
    persisted, no child's data flows from it, and it is the one test shape that would have caught
    B-1. A builder refusing them by over-applying my Phase 5 ruling has made the opposite error."):
    proves, by actually running BOTH guards against tests/-shaped trees, that construction there
    is never flagged -- not merely documented as permitted. Would FAIL if either guard were ever
    broadened to scan tests/ (e.g. by changing its caller's glob root), silently forbidding the
    exact positive-control shape 6b's criterion-1 needs."""
    domain_test_side_tree = ast.parse(
        "def test_something():\n"
        "    evidence = PolicyObservableEvidence(session_mode='c_only', current_difficulty_level=3)\n"
        "    assert evidence.session_mode == 'c_only'\n",
        filename="tests/test_synthetic_positive_control.py",
    )
    package_test_side_tree = ast.parse(
        "def test_something():\n"
        "    evidence = CPolicyObservableEvidence(session_mode='c_only', current_difficulty_level=3)\n"
        "    assert evidence.session_mode == 'c_only'\n",
        filename="tests/test_synthetic_positive_control.py",
    )
    # Both guards WOULD flag these trees if handed them -- what protects tests/ is that no caller
    # in this file ever hands either guard a tests/ tree (both real-scan tests above glob
    # Path("app").rglob("*.py") only). Demonstrated here by calling both guards directly against
    # tests/-shaped trees and confirming the CALLER discipline, not the function, is the boundary.
    assert _domain_policy_observable_evidence_violations(domain_test_side_tree)
    assert _package_policy_observable_evidence_violations(package_test_side_tree)
    for path in Path("app").rglob("*.py"):
        assert "tests" not in path.parts


# =====================================================================================
# Phase 8, J1-2 -- THE GUARDED ACCESSOR GUARD, mirroring the T4 evidence-construction guards
# exactly (same AST-attribute-name-match mechanism, same one-allow-listed-file shape, same
# positive-presence assertion so a vanished real call cannot pass vacuously, same tests/
# exemption). Flags the METHOD NAME, not the repository class construction -- unlike T4's guards,
# which flag construction of a whole class, this one must let
# CTaskOpportunitySummaryRecordRepository be constructed and written to (summary_service.py's own
# ``.add(record)`` call) everywhere; only its ``list_ordered_for_session`` READ method is
# restricted to telemetry_validation.get_derivable_history_for_session, the one guarded accessor
# J1-2 designed. Verified unique (grep, planning turn): repositories.py defines
# ``list_ordered_for_session`` exactly once, on CTaskOpportunitySummaryRecordRepository -- the same
# "plain-name match, does not resolve arbitrary aliasing" limitation T4's own guard already
# discloses as a residual, not solved here either.
# =====================================================================================

_ALLOWED_DERIVABLE_HISTORY_ACCESSOR_PATH = Path("app/application/live_engine_c/telemetry_validation.py")


def _derivable_history_raw_read_violations(tree: ast.AST) -> list[str]:
    """Flags any call to a method named ``list_ordered_for_session`` -- the guarded accessor's own
    raw read, J1-2's own text: "the only code under app/ permitted to call
    CTaskOpportunitySummaryRecordRepository.list_ordered_for_session." The caller is responsible
    for skipping telemetry_validation.py, the one file this guard permits."""
    violations: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if node.func.attr == "list_ordered_for_session":
                violations.append(ast.dump(node)[:200])
    return violations


def test_derivable_history_raw_read_permitted_only_in_telemetry_validation() -> None:
    """SIGNAL (J1-2): CTaskOpportunitySummaryRecordRepository.list_ordered_for_session is called
    ONLY in app/application/live_engine_c/telemetry_validation.py (get_derivable_history_for_session),
    and IS called there -- a positive-presence check, same shape as T4's own
    ``adapter_constructs_it`` assertion, so this guard cannot pass vacuously if the real call is
    ever removed. Would FAIL if any other file under app/ called this method directly (the raw read
    J1-2 exists to close -- adaptation_service.py's own build_evidence_for_session used to be that
    file, verified fixed by this same batch) OR if the accessor's own call disappeared."""
    accessor_calls_it = False
    violations: list[tuple[Path, str]] = []
    for path in Path("app").rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        found = _derivable_history_raw_read_violations(tree)
        if path == _ALLOWED_DERIVABLE_HISTORY_ACCESSOR_PATH:
            accessor_calls_it = bool(found)
            continue
        violations.extend((path, v) for v in found)
    assert not violations, violations
    assert accessor_calls_it, "expected telemetry_validation.py to call list_ordered_for_session at least once"


def test_derivable_history_guard_fires_on_synthetic_violation() -> None:
    """POSITIVE CONTROL: proves _derivable_history_raw_read_violations actually detects a raw call
    to list_ordered_for_session, and passes clean on source that never calls it -- this guard
    "will pass trivially today" outside the accessor file, so this control is what stops that from
    being worthless (same reasoning T4-c's own control states)."""
    violating_tree = ast.parse(
        "async def f(session, c_session_id):\n"
        "    return await CTaskOpportunitySummaryRecordRepository(session)."
        "list_ordered_for_session(c_session_id)\n",
        filename="<synthetic-violation>",
    )
    assert _derivable_history_raw_read_violations(violating_tree)

    clean_tree = ast.parse(
        "async def f(session, c_session_id):\n"
        "    return await get_derivable_history_for_session(session, c_session_id=c_session_id)\n",
        filename="<synthetic-clean>",
    )
    assert not _derivable_history_raw_read_violations(clean_tree)


def test_derivable_history_guard_does_not_scan_tests_directory() -> None:
    """Same discipline as T4-d: test-side direct repository construction stays legitimate for
    building fixtures. Demonstrated by calling the guard directly against a tests/-shaped tree
    (which WOULD flag it) and confirming the caller discipline (Path("app").rglob only) is what
    actually protects tests/, not the function itself."""
    test_side_tree = ast.parse(
        "async def test_something(session, c_session_id):\n"
        "    rows = await CTaskOpportunitySummaryRecordRepository(session)."
        "list_ordered_for_session(c_session_id)\n"
        "    assert rows == []\n",
        filename="tests/test_synthetic_positive_control.py",
    )
    assert _derivable_history_raw_read_violations(test_side_tree)
    for path in Path("app").rglob("*.py"):
        assert "tests" not in path.parts


# =====================================================================================
# Batch 9c-1b, D2 -- THE OUTBOX ENQUEUE BYPASS GUARD, mirroring the J1-2
# ``list_ordered_for_session`` guard immediately above (same AST-scan mechanism, same one-
# allow-listed-file shape, same positive-presence assertion so a vanished real call cannot pass
# vacuously, same tests/ exemption).
#
# MECHANISM DEVIATION FROM THE TEMPLATE -- APPROVED (work order v2 ADDENDUM A, "D2 mechanism
# deviation -- approved"). The J1-2 template above flags a METHOD NAME
# (``list_ordered_for_session``). This guard instead flags CONSTRUCTION of the
# ``OutboxEventRecord`` CLASS -- the same shape the earlier T4 evidence-construction guards use,
# not J1-2's method-name shape -- because ``session.add`` is used by every repository in this
# codebase: a guard on the method name "add" would false-positive on every single repository
# write, not just this one. Guarding the class construction itself (``OutboxEventRecord(...)``)
# is the only shape that isolates "something built a row for this specific table" from "something
# called .add()", which the write-side accessor unavoidably still does but which is not this
# guard's concern.
# =====================================================================================

_ALLOWED_OUTBOX_ENQUEUE_ACCESSOR_PATH = Path("app/application/live_engine_c/outbox_enqueue.py")


def _outbox_event_record_construction_violations(tree: ast.AST) -> list[str]:
    """Flags any call constructing ``OutboxEventRecord`` -- D1's own text: "Sole writer to
    outbox_events." The caller is responsible for skipping ``outbox_enqueue.py``, the one file
    this guard permits (the accessor's own construction of the row it writes)."""
    violations: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id == "OutboxEventRecord":
                violations.append(ast.dump(node)[:200])
            elif isinstance(node.func, ast.Attribute) and node.func.attr == "OutboxEventRecord":
                violations.append(ast.dump(node)[:200])
    return violations


def test_outbox_event_construction_permitted_only_in_outbox_enqueue() -> None:
    """SIGNAL (D1/D2): ``OutboxEventRecord`` is constructed ONLY in
    ``app/application/live_engine_c/outbox_enqueue.py`` (``enqueue_outbox_event``), and IS
    constructed there -- a positive-presence check, same shape as J1-2's own
    ``accessor_calls_it`` assertion, so this guard cannot pass vacuously if the real construction
    is ever removed. Would FAIL if any other file under app/ constructed ``OutboxEventRecord``
    directly (the exact bypass this guard exists to close) OR if the accessor's own construction
    disappeared."""
    accessor_constructs_it = False
    violations: list[tuple[Path, str]] = []
    for path in Path("app").rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        found = _outbox_event_record_construction_violations(tree)
        if path == _ALLOWED_OUTBOX_ENQUEUE_ACCESSOR_PATH:
            accessor_constructs_it = bool(found)
            continue
        violations.extend((path, v) for v in found)
    assert not violations, violations
    assert accessor_constructs_it, "expected outbox_enqueue.py to construct OutboxEventRecord at least once"


def test_outbox_enqueue_guard_fires_on_synthetic_violation() -> None:
    """POSITIVE CONTROL (acceptance criterion 1): proves
    ``_outbox_event_record_construction_violations`` actually detects a bypassing construction of
    ``OutboxEventRecord``, and passes clean on source that never constructs it -- mirrors J1-2's
    own ``test_derivable_history_guard_fires_on_synthetic_violation`` exactly, including the
    passing arm on the real accessor's own shape."""
    violating_tree = ast.parse(
        "async def f(session):\n"
        "    row = OutboxEventRecord(owning_component='C', contract_name='c_to_3', payload_json={})\n"
        "    session.add(row)\n",
        filename="<synthetic-violation>",
    )
    assert _outbox_event_record_construction_violations(violating_tree)

    clean_tree = ast.parse(
        "async def f(session, owning_component, contract_name, payload, request_id):\n"
        "    return await enqueue_outbox_event(\n"
        "        session,\n"
        "        owning_component=owning_component,\n"
        "        contract_name=contract_name,\n"
        "        payload=payload,\n"
        "        request_id=request_id,\n"
        "    )\n",
        filename="<synthetic-clean>",
    )
    assert not _outbox_event_record_construction_violations(clean_tree)


def test_outbox_enqueue_guard_does_not_scan_tests_directory() -> None:
    """Same discipline as J1-2's own tests/-exemption test: test-side direct construction of
    ``OutboxEventRecord`` stays legitimate for building fixtures (the 9c-1a constraint tests in
    ``test_9c1b_outbox_enqueue.py`` do exactly this). Demonstrated by calling the guard directly
    against a tests/-shaped tree (which WOULD flag it) and confirming the caller discipline
    (``Path("app").rglob`` only) is what actually protects tests/, not the function itself."""
    test_side_tree = ast.parse(
        "def test_something():\n"
        "    row = OutboxEventRecord(owning_component='C', contract_name='c_to_3', payload_json={})\n"
        "    assert row.owning_component == 'C'\n",
        filename="tests/test_synthetic_positive_control.py",
    )
    assert _outbox_event_record_construction_violations(test_side_tree)
    for path in Path("app").rglob("*.py"):
        assert "tests" not in path.parts


# =====================================================================================
# Phase 6b, final step -- X2-1: a NAMED ALLOW-LIST WITH A STALENESS ASSERTION (supervisor ruling,
# correcting the earlier "only tests/ may pass require_approved=False" wording -- that wording
# collided with four pre-existing, already-shipped app/ call sites the owner did not have in
# view). This is NOT an authorization: each entry below is a KNOWN BYPASS of
# CRuntimeBundleLoader.load_and_validate's own require_approved gate, recorded so it is VISIBLE,
# never blessed. Two are Component B's own call sites (hint_request.py, opportunity_selection.py)
# and are OUT OF THIS COMPONENT'S REMIT entirely -- reported to the owner as a finding, not
# touched by this batch. The other two are Component C's, both Phase 4b/5's own already-disclosed
# "ENGINEERING-ONLY TEST-provenance DRAFT bridge... not a governed bundle-artifact resolution
# mechanism" (c_session_service.py's and task_service.py's own module docstrings) -- no other
# bundle-resolution mechanism exists anywhere in this codebase.
#
# WHY THIS DOES NOT REOPEN X2-3: this batch's own per-field usability gate
# (app.application.live_engine_c.bundle_resolution.assert_family_usable, called from
# session_lifecycle.py:148-149) fires INDEPENDENTLY of require_approved -- it checks
# selection_config/safety_config's own per-field statuses, a completely separate mechanism from
# the bundle-level require_approved flag these four call sites bypass. "Component C's backend
# cannot create a session in production" (X2-3) holds regardless of these four bypasses, because
# the per-field gate was never gated by require_approved in the first place.
# =====================================================================================


KNOWN_REQUIRE_APPROVED_FALSE_BYPASSES: frozenset[str] = frozenset(
    {
        # Component C, Phase 4b -- ENGINEERING-ONLY TEST-provenance DRAFT bridge (own docstring).
        "app/application/live_engine_c/c_session_service.py",
        # Component C, Phase 5 -- same bridge, same reasoning, second call site.
        "app/application/live_engine_c/task_service.py",
        # Component B -- OUT OF THIS COMPONENT'S REMIT. Reported, not touched.
        "app/application/hint_request.py",
        # Component B -- OUT OF THIS COMPONENT'S REMIT. Reported, not touched.
        "app/application/opportunity_selection.py",
    }
)


def _has_require_approved_false(tree: ast.AST) -> bool:
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            for kw in node.keywords:
                if (
                    kw.arg == "require_approved"
                    and isinstance(kw.value, ast.Constant)
                    and kw.value.value is False
                ):
                    return True
    return False


def _require_approved_false_call_sites() -> set[str]:
    found: set[str] = set()
    for path in Path("app").rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        if _has_require_approved_false(tree):
            found.add(path.as_posix())
    return found


def test_x2_1_known_require_approved_false_bypasses_are_exactly_these_four() -> None:
    """SIGNAL: KNOWN_REQUIRE_APPROVED_FALSE_BYPASSES is EXACTLY the set COMPUTED live from a real
    AST scan of app/ -- never a hand-maintained count trusted on its own (same discipline as
    AUTHORIZED_C_COLUMN_EXCEPTIONS's own staleness assertion). Would FAIL if a FIFTH call site
    appeared anywhere under app/ (a new, unenumerated bypass -- "a fifth call site fails the
    build") or if one of these four were removed/renamed without updating the record."""
    found = _require_approved_false_call_sites()
    assert found == KNOWN_REQUIRE_APPROVED_FALSE_BYPASSES, found

    # Staleness half: every enumerated entry must actually exist and actually contain the call --
    # an allow-list entry for a file that no longer bypasses anything is exactly as misleading as
    # a missing one.
    for rel_path in KNOWN_REQUIRE_APPROVED_FALSE_BYPASSES:
        path = Path(rel_path)
        assert path.exists(), rel_path
        assert _has_require_approved_false(ast.parse(path.read_text(encoding="utf-8"))), rel_path


def test_require_approved_false_scan_fires_on_synthetic_violation() -> None:
    """POSITIVE CONTROL: proves _has_require_approved_false actually detects the literal
    ``require_approved=False`` keyword call, and passes clean on ``require_approved=True`` --
    "a fifth call site must fail, and a clean control must not.\""""
    violating_tree = ast.parse("foo(require_approved=False)\n", filename="<synthetic-violation>")
    assert _has_require_approved_false(violating_tree)

    clean_tree = ast.parse("foo(require_approved=True)\n", filename="<synthetic-clean>")
    assert not _has_require_approved_false(clean_tree)


# =====================================================================================
# Phase 7, Z4-c: no reward path writes learner state or imports anything B-owned. The package's
# own rewards.py cannot violate this (verified by direct read, Y4-a/Z4-d) -- this guard is about
# the APPLICATION code calling it, same shape as the T4 evidence-construction guards.
# =====================================================================================

_B_OWNED_IMPORT_ROOTS = frozenset({"models"})  # `models.contracts` -- B's own mastery/identity models
_LEARNER_STATE_WRITE_TARGETS = frozenset({"CLearnerLocalStateRecord", "prior_session_end_state"})


def _reward_path_violations(tree: ast.AST) -> list[str]:
    """Flags, in a reward-named file's own AST: any import whose root is B-owned, or any
    construction/assignment naming a learner-state write target. Returns violation strings, never
    asserts inline, so the same logic drives both the real app/ scan and the synthetic control."""
    violations: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                root = alias.name.split(".")[0]
                if root in _B_OWNED_IMPORT_ROOTS:
                    violations.append(f"import:{alias.name}")
        if isinstance(node, ast.ImportFrom) and node.module:
            root = node.module.split(".")[0]
            if root in _B_OWNED_IMPORT_ROOTS:
                violations.append(f"import_from:{node.module}")
        if isinstance(node, ast.Call):
            callee = node.func
            name = callee.id if isinstance(callee, ast.Name) else getattr(callee, "attr", None)
            if name in _LEARNER_STATE_WRITE_TARGETS:
                violations.append(f"construct:{name}")
        if isinstance(node, ast.Attribute) and node.attr in _LEARNER_STATE_WRITE_TARGETS:
            if isinstance(node.ctx, ast.Store):
                violations.append(f"assign:{node.attr}")
    return violations


def test_z4c_no_reward_path_writes_learner_state_or_imports_b_owned() -> None:
    """SIGNAL: every file under app/ whose path contains "reward" (today: exactly
    reward_service.py) is scanned for a B-owned import root or a learner-state write target.
    Would FAIL if a future reward-related file imported anything B-owned, or constructed/assigned
    CLearnerLocalStateRecord/prior_session_end_state."""
    reward_files = [p for p in Path("app").rglob("*.py") if "reward" in p.name]
    assert reward_files, "expected at least one reward-named file under app/ (reward_service.py)"
    violations: list[tuple[Path, str]] = []
    for path in reward_files:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        violations.extend((path, v) for v in _reward_path_violations(tree))
    assert not violations, violations


def test_z4c_reward_guard_fires_on_synthetic_violations() -> None:
    """POSITIVE CONTROL: proves _reward_path_violations actually detects a B-owned import and a
    learner-state write, and passes clean on legitimate reward-decision code."""
    b_import_tree = ast.parse("from models.contracts import BToCMasteryPayload\n", filename="<synthetic-violation>")
    assert _reward_path_violations(b_import_tree)

    write_tree = ast.parse(
        "def f(record):\n    record.prior_session_end_state = 'overloaded'\n",
        filename="<synthetic-violation>",
    )
    assert _reward_path_violations(write_tree)

    construct_tree = ast.parse(
        "CLearnerLocalStateRecord(student_id=x)\n", filename="<synthetic-violation>"
    )
    assert _reward_path_violations(construct_tree)

    clean_tree = ast.parse(
        "def decide_child_facing_reward(adapter, context):\n    return adapter.decide_child_facing_reward(context)\n",
        filename="<synthetic-clean>",
    )
    assert not _reward_path_violations(clean_tree)


# =====================================================================================
# Phase 7, Z5-e: C scaffolds are not B hints -- no C scaffold path imports, reads, or mirrors
# app/application/hint_request.py.
# =====================================================================================


def test_z5e_no_scaffold_path_imports_hint_request() -> None:
    """SIGNAL: every file under app/ whose path contains "scaffold" (today: exactly
    scaffold_service.py) never imports app.application.hint_request in any form. Would FAIL if a
    future scaffold-related file imported B's hint machinery."""
    scaffold_files = [p for p in Path("app").rglob("*.py") if "scaffold" in p.name]
    assert scaffold_files, "expected at least one scaffold-named file under app/ (scaffold_service.py)"
    for path in scaffold_files:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                assert not node.module.startswith("app.application.hint_request"), (path, node.module)
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert not alias.name.startswith("app.application.hint_request"), (path, alias.name)


def test_z5e_guard_fires_on_synthetic_violation() -> None:
    """POSITIVE CONTROL: proves the hint_request-import check actually detects an import."""
    violating_tree = ast.parse(
        "from app.application.hint_request import HintService\n", filename="<synthetic-violation>"
    )
    found = any(
        isinstance(node, ast.ImportFrom)
        and node.module
        and node.module.startswith("app.application.hint_request")
        for node in ast.walk(violating_tree)
    )
    assert found

    clean_tree = ast.parse("from app.domain.live_engine_c.types import ScaffoldConfig\n", filename="<synthetic-clean>")
    found_clean = any(
        isinstance(node, ast.ImportFrom)
        and node.module
        and node.module.startswith("app.application.hint_request")
        for node in ast.walk(clean_tree)
    )
    assert not found_clean


# =====================================================================================
# C prompt-exemplars batch (D4) -- no module under app/ may read
# backend/contract/c-prompt-exemplars.json. It exists for the frontend development fixture and
# for tests (tests/test_c_prompt_exemplars_freeze.py); a production code path reading it would be
# serving manufactured content to a child, which is the failure the whole gate exists to prevent.
#
# MECHANISM AND ITS STATED LIMIT (supervisor ruling 2): this guard scans every ast.Constant
# string node under app/ for the literal filename "c-prompt-exemplars.json" -- it therefore
# catches open("contract/c-prompt-exemplars.json"), Path(...) / "c-prompt-exemplars.json",
# .read_text() on a path built from that literal, and any other use where the filename appears
# as a string literal in source. IT DOES NOT CATCH a path assembled dynamically -- from a
# variable, a glob pattern, an f-string built from parts, or a config-supplied value -- since no
# such construction would ever contain the literal filename as one AST constant. That is an
# accepted limit of this guard, not an oversight: closing it with heuristics for dynamic
# construction would produce false positives on unrelated string handling and yield a guard
# nobody trusts (supervisor ruling 2, "do NOT try to close the gap"). A later reader should read
# "no app module reads this artefact" as "no app module references it by literal filename" --
# not as a stronger, unconditional guarantee.
# =====================================================================================

_PROMPT_EXEMPLARS_ARTEFACT_FILENAME = "c-prompt-exemplars.json"


def _references_prompt_exemplars_artefact(tree: ast.AST) -> bool:
    """Shared by the real guard and its negative control, so the two can never drift apart.
    Matches ONLY a literal string constant containing the artefact's filename -- see the module
    limit documented above."""
    return any(
        isinstance(node, ast.Constant)
        and isinstance(node.value, str)
        and _PROMPT_EXEMPLARS_ARTEFACT_FILENAME in node.value
        for node in ast.walk(tree)
    )


def test_no_app_module_reads_prompt_exemplars_artefact() -> None:
    """SIGNAL: no file under app/ contains a string-literal reference to
    "c-prompt-exemplars.json" anywhere in its source. Would FAIL if any file under app/ opened,
    built a Path to, or otherwise referenced the artefact by its literal filename -- e.g. a
    future task-serving code path reaching for the frontend's development fixture instead of
    real generation. Does NOT prove the absence of a dynamically-constructed reference -- see the
    module docstring above for that stated limit."""
    app_root = Path("app")
    assert app_root.is_dir()
    scanned_files = sorted(app_root.rglob("*.py"))
    assert scanned_files, "no *.py files found under app/ -- scan set degraded to a no-op"

    offenders = []
    for path in scanned_files:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        if _references_prompt_exemplars_artefact(tree):
            offenders.append(path)
    assert not offenders, offenders


def test_prompt_exemplars_artefact_read_guard_negative_control_fires() -> None:
    """POSITIVE PROOF the detector above does real work, not merely observing that no file
    happens to violate it, AND that it discriminates this specific artefact rather than
    blanket-matching any contract filename. Parses SYNTHETIC, in-memory module source -- never a
    file under app/, which would be a real boundary breach waiting to be committed by accident.
    Would FAIL if the detector stopped recognising a literal reference to the artefact's
    filename, or if it over-matched and flagged an unrelated contract file too."""
    violating_source = 'open("backend/contract/c-prompt-exemplars.json")\n'
    unrelated_contract_source = 'open("backend/contract/c-template-registry.json")\n'

    violating_tree = ast.parse(violating_source, filename="<synthetic-prompt-exemplars-violation>")
    unrelated_tree = ast.parse(unrelated_contract_source, filename="<synthetic-unrelated-contract-file>")

    assert _references_prompt_exemplars_artefact(violating_tree), (
        "negative control failed to catch a real literal-filename reference"
    )
    assert not _references_prompt_exemplars_artefact(unrelated_tree), (
        "guard incorrectly flagged an unrelated contract filename -- it is not discriminating"
    )


# =====================================================================================
# BE-prompt-text batch -- no module under app/ may read backend/contract/c-prompt-wording.json
# BY FILENAME. Unlike the exemplars artefact (D4 above, which nothing under app/ may read at
# all), prompt_text DOES need to reach app/: task_service._task_fields calls
# app.domain.live_engine_c.prompt_wording.prompt_text_for, which reads the authoritative Python
# module PROMPT_TEXT_BY_TEMPLATE directly. This guard keeps that the ONLY path: app/ code must
# never re-open the frozen JSON snapshot directly, which would create a second, divergence-prone
# route to the same content and defeat the point of having one source of truth. Same mechanism
# and same stated limit as the D4 guard: an ast.Constant string-literal scan for the exact
# filename, so a dynamically-assembled path would evade it (accepted limit, not closed here for
# the same reason D4 states its own).
# =====================================================================================

_PROMPT_WORDING_ARTEFACT_FILENAME = "c-prompt-wording.json"


def _references_prompt_wording_artefact(tree: ast.AST) -> bool:
    """Shared by the real guard and its negative control, so the two can never drift apart.
    Matches ONLY a literal string constant containing the artefact's filename."""
    return any(
        isinstance(node, ast.Constant)
        and isinstance(node.value, str)
        and _PROMPT_WORDING_ARTEFACT_FILENAME in node.value
        for node in ast.walk(tree)
    )


def test_no_app_module_reads_prompt_wording_artefact_by_filename() -> None:
    """SIGNAL: no file under app/ contains a string-literal reference to
    "c-prompt-wording.json" anywhere in its source -- app/ reads the authoritative
    ``prompt_wording.PROMPT_TEXT_BY_TEMPLATE`` module, never the derived JSON snapshot. Would
    FAIL if any file under app/ opened, built a Path to, or otherwise referenced the artefact by
    its literal filename. Does NOT prove the absence of a dynamically-constructed reference."""
    app_root = Path("app")
    assert app_root.is_dir()
    scanned_files = sorted(app_root.rglob("*.py"))
    assert scanned_files, "no *.py files found under app/ -- scan set degraded to a no-op"

    offenders = []
    for path in scanned_files:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        if _references_prompt_wording_artefact(tree):
            offenders.append(path)
    assert not offenders, offenders


def test_prompt_wording_artefact_read_guard_negative_control_fires() -> None:
    """POSITIVE PROOF the detector above does real work, AND that it discriminates this specific
    artefact rather than blanket-matching any contract filename. Parses SYNTHETIC, in-memory
    module source only."""
    violating_source = 'open("backend/contract/c-prompt-wording.json")\n'
    unrelated_contract_source = 'open("backend/contract/c-prompt-exemplars.json")\n'

    violating_tree = ast.parse(violating_source, filename="<synthetic-prompt-wording-violation>")
    unrelated_tree = ast.parse(unrelated_contract_source, filename="<synthetic-unrelated-contract-file>")

    assert _references_prompt_wording_artefact(violating_tree), (
        "negative control failed to catch a real literal-filename reference"
    )
    assert not _references_prompt_wording_artefact(unrelated_tree), (
        "guard incorrectly flagged an unrelated contract filename -- it is not discriminating"
    )
