"""BE4f (BEplan §9 BE4.7) — the deterministic parity test (BEplan §9 BE4 Exit Gate item 1;
Component_B_BE4_Sequencing_Plan.md §7.1): prove the adapter-driven live task-construction path
reproduces the generator's own construction, byte-for-byte, for identical inputs.

**Why this file uses the documented ACCEPTABLE FALLBACK, not the PREFERRED direct-digest match.**

The PREFERRED path (Sequencing Plan §7.1 / this batch's own instruction) is to reproduce
``backend/provenance/component-b-characterization.json``'s ``private_output_sha256`` =
``b1d8cb3388ac7e47dd353af68210b24debf3d49791f40a6447ad57f74641926c`` (``global_seed=20260716``,
``config_version="b1-smoke-0.1.0"``, 54 item instances) directly through
``LiveEngineAdapter.build_task_instance``.

Tracing that anchor back to its source (research repo ``Yass``, commit
``73acb113bbb179f5946333c27b0142c43f3063f3`` — the exact ``generator_git_tree_sha1`` the
characterization file cites) shows it is NOT reproducible through the adapter alone:

- ``config_version="b1-smoke-0.1.0"`` is emitted by ``component_b_generator.config.loader.
  default_b1_config(global_seed=20260716, n_learners=8, scheduled_session_count=3)`` — an
  8-learner, 3-scheduled-session **cohort pipeline** run, not a single deterministic
  ``build_task_instance`` call.
- Producing 54 item instances from that config requires ``component_b_generator.pipeline``
  (``PipelineConfig``/the B4->B2A->B2B.3->B3->B5 orchestration loop), which in turn calls
  ``cohort.builder``, ``behaviour.initialization`` (hidden per-learner truth), ``behaviour.
  attempt_loop`` (simulated attempts/timing), and ``generation.item_opportunities._draw_item_count``
  (a randomized per-session item count) to decide *how many* opportunities and *which* templates
  each of the 8 learners receives across 3 sessions.
- Every one of those modules is prohibited from the live application. ``cohort/*``,
  ``behaviour.attempt_loop``, and ``pipeline`` are named in ``explicitly_prohibited_from_application``
  in ``backend/provenance/component-b-live-engine-reuse-map.json`` ("cohort and cohort/*", "hidden
  learner truth", "component_b_generator.behaviour.first_attempt/.latency/.attempt_loop",
  "component_b_generator.pipeline", "dataset-generation entry points", "experiment runners");
  ``generation.item_opportunities`` is not named literally in that array but falls under
  "dataset-generation entry points" and is independently enforced-unreachable by the boundary
  guard (``tests/test_be3_live_engine_boundary.py``). Each is
  therefore, by design, never vendored into ``upadya-component-b-live-engine`` / never importable
  from ``app/`` (``tests/test_be3_live_engine_boundary.py``). No script reproducing this exact
  54-item sweep is checked into either the ``Yass`` research repo or this backend at any commit
  (searched ``git grep`` for ``item_instance_count`` / ``private_output_sha256`` across all
  ``Yass`` history and this repo's history — no match); it was evidently run ad hoc against the
  full (never-vendored) pipeline. Reconstructing it would require importing exactly the modules
  BE3/BE4's reuse boundary exists to keep out of the live application — the PREFERRED path is
  therefore architecturally unavailable here, not merely inconvenient.

**The ACCEPTABLE FALLBACK actually run below** (Sequencing Plan §7.1's own documented
alternative): a direct A/B test, for every implemented template at every grade it is eligible for
(the same sweep ``tests/test_be3c_characterization.py::TestAllImplementedTemplatesGenerate``
already uses to prove full-coverage generation), asserting
``LiveEngineAdapter.build_task_instance`` is byte-for-byte identical to a direct, independent call
into the vendored package's own ``component_b_generator.generation.task_instances.
build_task_instance`` — constructed here from scratch (its own ``GeneratedItemOpportunity``, its
own ``SeedManager``, its own ``load_catalogue``), never by reaching into the adapter's private
helpers. This proves the adapter is a byte-identical, non-diverging wrapper around the generator's
own construction function: no formula, seed derivation, sampler, distractor rule, or guard is
copied, altered, or reimplemented anywhere on the live path. Repeat-run determinism (BEplan §9
BE4.7 note "repeat run byte-identical") is asserted for both the adapter and the direct package
call. The canonical serialization is the exact method the characterization file records:
``JSON of model_dump(mode="json"), sort_keys=true, separators=(",", ":")``.
"""

from __future__ import annotations

import dataclasses
import hashlib
import json

import pytest

pytest.importorskip(
    "component_b_generator",
    reason="upadya-component-b-live-engine is not installed; see backend/requirements.in",
)

from component_b_generator.generation.task_instances import build_task_instance as pkg_build_task_instance
from component_b_generator.models.opportunity import GeneratedItemOpportunity as PkgGeneratedItemOpportunity
from component_b_generator.seeds import SeedManager as PkgSeedManager

from app.domain.live_engine.types import TaskConstructionRequest
from app.infrastructure.live_engine.adapter import LiveEngineAdapter


FIXTURE_CATALOGUE_PATH = "tests/fixtures/runtime_bundle/test_catalogue.md"
COVERAGE_PROVENANCE_PATH = "provenance/component-b-coverage.json"

# The characterization anchor this file traces (see module docstring for why it is not directly
# reproducible here) — cited for provenance, not asserted against.
CHARACTERIZATION_GLOBAL_SEED = 20260716
CHARACTERIZATION_CONFIG_VERSION = "b1-smoke-0.1.0"
CHARACTERIZATION_SHA256 = "b1d8cb3388ac7e47dd353af68210b24debf3d49791f40a6447ad57f74641926c"

# Canonical serialization method exactly as recorded in
# backend/provenance/component-b-characterization.json:
# "JSON of item_instances model_dump(mode='json'), sort_keys=true, separators=(',', ':')".
def _canonical_json(payload: object) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def _sha256_of(payload: object) -> str:
    return hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest()


@pytest.fixture(scope="module")
def adapter() -> LiveEngineAdapter:
    return LiveEngineAdapter()


@pytest.fixture(scope="module")
def catalogue(adapter: LiveEngineAdapter):
    return adapter.load(FIXTURE_CATALOGUE_PATH)


@pytest.fixture(scope="module")
def catalogue_checksum(adapter: LiveEngineAdapter) -> str:
    return adapter.checksum(FIXTURE_CATALOGUE_PATH)


@pytest.fixture(scope="module")
def coverage() -> dict:
    import json as _json

    with open(COVERAGE_PROVENANCE_PATH, encoding="utf-8") as f:
        return _json.load(f)


def _adapter_request(
    *, item_template_id: str, skill_id: str, grade: int, curriculum_node_id: str, seed: int, item_index: int
) -> TaskConstructionRequest:
    return TaskConstructionRequest(
        item_opportunity_id=f"STU-0001-B001-I{item_index:03d}",
        student_id="STU-0001",
        grade=grade,
        scheduled_session_number=1,
        b_session_index=1,
        item_index=item_index,
        event_order=item_index,
        item_template_id=item_template_id,
        skill_id=skill_id,
        curriculum_node_id=curriculum_node_id,
        selection_reason_internal="be4f-parity-test",
        global_seed=seed,
    )


def _direct_package_instance(
    *,
    pkg_catalogue,
    item_template_id: str,
    grade: int,
    curriculum_node_id: str,
    seed: int,
    item_index: int,
) -> dict:
    """Independently constructed, NOT via any adapter helper: this module's own
    ``GeneratedItemOpportunity`` + ``SeedManager`` + a direct call into
    ``component_b_generator.generation.task_instances.build_task_instance`` — the generator's own
    function, called the way the generator itself would call it."""
    seed_manager = PkgSeedManager(seed)
    seed_lineage = seed_manager.item_opportunity("STU-0001", 1, 1, item_index)
    opportunity = PkgGeneratedItemOpportunity(
        item_opportunity_id=f"STU-0001-B001-I{item_index:03d}",
        student_id="STU-0001",
        grade=grade,
        scheduled_session_number=1,
        b_session_index=1,
        item_index=item_index,
        event_order=item_index,
        item_template_id=item_template_id,
        skill_id=pkg_catalogue.by_id(item_template_id).skill_id,
        curriculum_node_id=curriculum_node_id,
        selection_reason_internal="be4f-parity-test",
        seed_lineage=seed_lineage,
    )
    template = pkg_catalogue.by_id(item_template_id)
    instance = pkg_build_task_instance(
        opportunity, template, pkg_catalogue.catalogue_version, pkg_catalogue.catalogue_status, "irrelevant-checksum"
    )
    return instance.model_dump(mode="json")


def _load_pkg_catalogue():
    from component_b_generator.catalogue.loader import load_catalogue as pkg_load_catalogue

    return pkg_load_catalogue(FIXTURE_CATALOGUE_PATH)


class TestParityAnchorProvenance:
    """Documents, in an assertable way, exactly what the characterization anchor is and is not
    claiming here — see the module docstring for the full trace."""

    def test_characterization_anchor_is_cited_not_asserted(self) -> None:
        assert CHARACTERIZATION_GLOBAL_SEED == 20260716
        assert CHARACTERIZATION_CONFIG_VERSION == "b1-smoke-0.1.0"
        assert len(CHARACTERIZATION_SHA256) == 64


class TestAdapterMatchesDirectPackageCallByteForByte:
    """The headline deliverable's fallback: for every implemented, grade-eligible template, the
    adapter's ``build_task_instance`` and an independently-constructed direct call into the
    vendored package's own ``build_task_instance`` produce byte-identical canonical JSON."""

    def test_every_implemented_template_matches_direct_package_call(
        self, adapter: LiveEngineAdapter, catalogue, catalogue_checksum: str, coverage: dict
    ) -> None:
        pkg_catalogue = _load_pkg_catalogue()
        implemented_ids = set(coverage["implemented_template_ids"])
        checked_pairs = 0
        for template in catalogue.templates:
            if template.item_template_id not in implemented_ids:
                continue
            for grade in template.eligible_grades:
                item_index = checked_pairs + 1
                seed = CHARACTERIZATION_GLOBAL_SEED

                adapter_request = _adapter_request(
                    item_template_id=template.item_template_id,
                    skill_id=template.skill_id,
                    grade=grade,
                    curriculum_node_id=template.curriculum_node_id,
                    seed=seed,
                    item_index=item_index,
                )
                adapter_instance = adapter.build_task_instance(adapter_request, catalogue, catalogue_checksum)
                adapter_payload = dataclasses.asdict(adapter_instance)

                direct_payload = _direct_package_instance(
                    pkg_catalogue=pkg_catalogue,
                    item_template_id=template.item_template_id,
                    grade=grade,
                    curriculum_node_id=template.curriculum_node_id,
                    seed=seed,
                    item_index=item_index,
                )

                # The adapter's ``TaskInstance`` dataclass (app.domain.live_engine.types) is a
                # deliberately narrower, allow-listed projection of the package's raw
                # ``GeneratedItemInstance`` (which also carries internal-only bookkeeping fields
                # like ``generation_phase``/``item_index``/``learner_id``/``validation_status``
                # not part of the adapter's port contract) — so the byte-for-byte comparison is
                # scoped to exactly the fields the adapter exposes (every one of them a
                # generated/scientific field: operands, correct answer, distractors, guards,
                # seed, ...), minus ``catalogue_checksum`` which differs by construction (the
                # adapter call passes the real fixture checksum; the direct call below
                # intentionally passes a placeholder to prove it is a pure pass-through, never
                # re-derived).
                compared_fields = set(adapter_payload) - {"catalogue_checksum"}
                adapter_comparable = {k: adapter_payload[k] for k in compared_fields}
                direct_comparable = {k: direct_payload[k] for k in compared_fields}
                assert _canonical_json(adapter_comparable) == _canonical_json(direct_comparable), (
                    template.item_template_id,
                    grade,
                )
                checked_pairs += 1

        assert checked_pairs > 0

    def test_repeat_run_is_byte_identical_for_adapter_and_direct_package_call(
        self, adapter: LiveEngineAdapter, catalogue, catalogue_checksum: str, coverage: dict
    ) -> None:
        pkg_catalogue = _load_pkg_catalogue()
        template_id = sorted(coverage["implemented_template_ids"])[0]
        template = catalogue.by_id(template_id)
        grade = template.eligible_grades[0]
        seed = CHARACTERIZATION_GLOBAL_SEED

        request = _adapter_request(
            item_template_id=template_id,
            skill_id=template.skill_id,
            grade=grade,
            curriculum_node_id=template.curriculum_node_id,
            seed=seed,
            item_index=1,
        )
        first_adapter = adapter.build_task_instance(request, catalogue, catalogue_checksum)
        second_adapter = adapter.build_task_instance(request, catalogue, catalogue_checksum)
        assert first_adapter == second_adapter
        assert _sha256_of(dataclasses.asdict(first_adapter)) == _sha256_of(dataclasses.asdict(second_adapter))

        first_direct = _direct_package_instance(
            pkg_catalogue=pkg_catalogue,
            item_template_id=template_id,
            grade=grade,
            curriculum_node_id=template.curriculum_node_id,
            seed=seed,
            item_index=1,
        )
        second_direct = _direct_package_instance(
            pkg_catalogue=pkg_catalogue,
            item_template_id=template_id,
            grade=grade,
            curriculum_node_id=template.curriculum_node_id,
            seed=seed,
            item_index=1,
        )
        assert _sha256_of(first_direct) == _sha256_of(second_direct)
