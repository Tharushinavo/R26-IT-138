"""BE3 packaging-only boundary tests for upadya-component-b-live-engine.

This batch is packaging + import-boundary work only: no adapter wiring, no live learner
flow, no application import of the package. These tests verify (1) the package itself never
reaches a prohibited Yass research/synthetic module, (2) the application's own import graph
still does not reach any prohibited module (unchanged from BE2 — this package is not imported
by app code yet), and (3) a live-safe deterministic function is in fact deterministic under
fixed inputs. See backend/provenance/component-b-live-engine-manifest.json and
backend/provenance/component-b-live-engine-reuse-map.json.
"""

import ast
import importlib
from pathlib import Path

import pytest

component_b_generator = pytest.importorskip(
    "component_b_generator",
    reason="upadya-component-b-live-engine is not installed; see backend/requirements.in",
)

PROHIBITED_MODULES = (
    "component_b_generator.cohort",
    "component_b_generator.cohort.builder",
    "component_b_generator.behaviour.first_attempt",
    "component_b_generator.behaviour.latency",
    "component_b_generator.behaviour.attempt_loop",
    "component_b_generator.behaviour.initialization",
    "component_b_generator.behaviour.wrong_answers",
    "component_b_generator.behaviour.derivation",
    "component_b_generator.behaviour.seeds",
    "component_b_generator.behaviour.validation",
    "component_b_generator.pipeline",
    "component_b_generator.pilot",
    "component_b_generator.runner",
    "component_b_generator.audits",
    "component_b_generator.audits.fidelity",
    "component_b_generator.audits.leakage",
    "component_b_generator.audits.population_neutrality",
    "component_b_generator.generation.item_opportunities",
)


@pytest.mark.parametrize("module_name", PROHIBITED_MODULES)
def test_prohibited_module_is_not_importable_from_the_package(module_name: str) -> None:
    with pytest.raises(ModuleNotFoundError):
        importlib.import_module(module_name)


def test_thirteen_prohibited_capabilities_are_unreachable() -> None:
    """Cross-check against the 13-item exclusion list in the reuse map: cohort/*, hidden
    learner truth, synthetic learner traits, behaviour.first_attempt, behaviour.latency,
    behaviour.attempt_loop, pipeline, pilot, synthetic audits, dataset-generation entry
    points, experiment runners, simulated answers, simulated timing/latency."""
    assert len(PROHIBITED_MODULES) >= 10  # cohort, 3x behaviour.*, pipeline, pilot, runner, 3x audits
    for module_name in PROHIBITED_MODULES:
        with pytest.raises(ModuleNotFoundError):
            importlib.import_module(module_name)

    import component_b_generator.models.behaviour as mb

    hidden_truth_and_synthetic_classes = {
        "AuditOnlyModel",
        "BLearnerSkillTruth",
        "BAttemptEvent",
        "BoundedBetaSpec",
        "BoundedNormalSpec",
        "BTruthInitializationConfig",
        "BInitialLearnerSkillTruth",
        "LognormalLatencySpec",
        "BFirstAttemptBehaviourConfig",
        "BAttemptLoopConfig",
        "BOpportunityAttemptResult",
    }
    assert not (hidden_truth_and_synthetic_classes & set(dir(mb)))

    assert not any(Path("app").rglob("*cohort*")), "no dataset-generation/cohort surface in app code"


def test_no_dataset_generation_or_experiment_runner_entry_point_in_package() -> None:
    """generate_task_instances/build_task_instance are deterministic single-instance
    construction (SPEC-scoped, per real opportunity), not a dataset-generation batch entry
    point or experiment runner."""
    import component_b_generator.generation.task_instances as ti

    forbidden_symbols = {"run_phase_b1", "run_phase_b2a", "PhaseB2AResult"}
    assert not (forbidden_symbols & set(dir(ti)))

    package_root = Path(component_b_generator.__file__).parent
    for path in package_root.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                assert not node.module.split(".")[-1] == "runner", (path, node.module)
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                names = (
                    {a.name for a in node.names}
                    if isinstance(node, ast.Import)
                    else {node.module or ""}
                )
                assert "cohort" not in " ".join(names), (path, names)


def test_only_the_live_engine_adapter_module_imports_the_package() -> None:
    """BE3b wires the adapter, so ``component_b_generator`` (and the standalone
    ``upadya_component_b_live_engine`` name, ``yass``, or a bare-root ``pipeline``/``pilot``
    import) may now legitimately appear under ``app/`` — but ONLY in
    ``app/infrastructure/live_engine/adapter.py``, the one reviewed binding point. Every other
    file in the app import graph must still be completely disjoint from these roots. This
    replaces the BE3a version of this guard, whose docstring said "this batch does not wire
    any application adapter" — BE3b is that next batch.
    """
    prohibited_import_roots = {
        "component_b_generator",
        "upadya_component_b_live_engine",
        "yass",
        "bkt",
        "sequencing",
        "certification",
        "guess_guard",
        "pipeline",
        "pilot",
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


def test_app_import_graph_never_reaches_the_thirteen_prohibited_submodules() -> None:
    """Regardless of the top-level package now being a legitimate dependency of the adapter,
    every one of the 13 explicitly-prohibited submodules (cohort/*, the synthetic
    ``behaviour.*`` generators, ``pipeline``, ``pilot``, ``runner``, ``audits`` + its
    submodules, and ``generation.item_opportunities``) must stay unreachable from the entire
    ``app/`` import graph — including from the adapter itself."""
    for path in Path("app").rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                full_module = node.module
            elif isinstance(node, ast.Import):
                full_module = ";".join(alias.name for alias in node.names)
            else:
                continue
            for prohibited in PROHIBITED_MODULES:
                assert prohibited not in full_module, (path, full_module, prohibited)


def test_bkt_update_is_deterministic_under_fixed_provenance() -> None:
    """Live-safe determinism smoke test: bkt_predict/bkt_posterior/bkt_update (the reviewed
    BKT prediction/posterior/update capability) return byte-identical output for identical
    fixed inputs, repeated in the same process."""
    from component_b_generator.bkt.update import bkt_posterior, bkt_predict, bkt_update

    def run() -> tuple:
        predicted = bkt_predict(p_l=0.3, p_g=0.2, p_s=0.1)
        posterior = bkt_posterior(p_l=0.3, correct=True, p_g=0.2, p_s=0.1)
        updated = bkt_update(p_l=0.3, correct=True, p_g=0.2, p_s=0.1, p_t=0.15)
        return predicted, posterior, updated

    first_run = run()
    second_run = run()
    assert first_run == second_run
    assert all(0.0 <= value <= 1.0 for value in first_run)


def test_guess_guard_is_deterministic_under_fixed_provenance() -> None:
    """Live-safe determinism smoke test for the Guess-Guard capability."""
    from component_b_generator.bkt.guess_guard import plausibility_floor

    observations = (0.2, 0.25, 0.3, 0.35, 0.4, 0.45, 0.5, 0.55, 0.6, 0.65)
    first_run = plausibility_floor(observations, 0.1, 5)
    second_run = plausibility_floor(observations, 0.1, 5)
    assert first_run == second_run
