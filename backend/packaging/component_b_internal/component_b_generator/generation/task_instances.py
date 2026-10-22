"""Deterministic mathematical task-instance engine (Phase B2A).

Builds :class:`GeneratedItemInstance` records on top of Phase-B1 ``GeneratedItemOpportunity``
records: sample operands -> recompute correct answer -> equivalents -> distractor candidates
-> run hard guards -> emit a validated instance. Content is seeded from a **task-instance
child lineage** branched off the opportunity seed, so instance content is reproducible and
independent of learner/cohort order.

Unsupported templates are never fabricated: :func:`build_task_instance` raises
``UnsupportedTemplateError``; the batch :func:`generate_task_instances` reports the set of
unimplemented templates it skipped.

PACKAGING NOTE (upadya-component-b-live-engine): this file is a reviewed live-safe subset of
the pinned Yass source file at the same relative path. ``build_task_instance`` and
``generate_task_instances`` are byte-identical to the pinned commit. The offline smoke-path
entry point ``run_phase_b2a`` (and its module-level ``from ..runner import run_phase_b1``
import, which reaches the prohibited synthetic/offline pipeline) and its provenance-only
helpers were removed because they are not part of the reviewed live-safe capability closure
in ``backend/provenance/component-b-live-engine-reuse-map.json`` and are unreachable from any
retained function. See ``backend/provenance/component-b-live-engine-manifest.json`` for the
pinned source commit and manifest.
"""

from __future__ import annotations

from typing import List, Tuple

from ..answers.registry import allowed_equivalent_answers, correct_answer_raw
from ..answers.rules import normalize_answer
from ..distractors.registry import generate_distractors
from ..models.catalogue import ItemTemplate, LoadedCatalogue
from ..models.opportunity import GeneratedItemOpportunity
from ..models.task_instance import GeneratedItemInstance
from ..samplers.registry import get_sampler, supported_template_ids
from ..seeds import derive_child_lineage, rng_from
from .activation import decide_activation
from .errors import TaskInstanceValidationError, UnsupportedTemplateError
from .guards import GuardContext, run_guards

PHASE_B2A = "B2A.2"


def build_task_instance(
    opportunity: GeneratedItemOpportunity,
    template: ItemTemplate,
    catalogue_version: str,
    catalogue_status: str,
    catalogue_checksum: str,
) -> GeneratedItemInstance:
    """Build one validated task instance for a supported, active template.

    Raises ``UnsupportedTemplateError`` if no strategy is implemented for the template, and
    ``TaskInstanceValidationError`` if the template is not active for the opportunity's grade
    or any hard guard fails.
    """
    sampler = get_sampler(opportunity.item_template_id)
    if sampler is None:
        raise UnsupportedTemplateError(
            f"no Phase-B2A strategy for template {opportunity.item_template_id!r}"
        )

    decision = decide_activation(template, supported_template_ids(), opportunity.grade, catalogue_status)
    if not decision.active:
        raise TaskInstanceValidationError(f"template not active: {decision.reason}")

    # Content seed = child lineage branched off the opportunity seed (traceable, order-free).
    instance_lineage = derive_child_lineage(opportunity.seed_lineage, "item_instance", "1")
    rng = rng_from(instance_lineage)

    content = sampler.sample(rng, opportunity.grade)
    correct_raw = correct_answer_raw(opportunity.item_template_id, content.operands)
    correct_norm = normalize_answer(correct_raw)
    equivalents = allowed_equivalent_answers(opportunity.item_template_id, content.operands)
    distractors, distractor_rule_ids = generate_distractors(
        opportunity.item_template_id, content.operands, correct_raw,
        required=sampler.required_distractors,
    )

    ctx = GuardContext(
        item_template_id=opportunity.item_template_id,
        task_type=sampler.task_type,
        skill_id=sampler.skill_id,
        grade=opportunity.grade,
        eligible_grades=template.eligible_grades,
        operands=content.operands,
        correct_raw=correct_raw,
        correct_norm=correct_norm,
        distractors=distractors,
    )
    applied_guard_ids = run_guards(sampler.guard_ids, ctx)

    return GeneratedItemInstance(
        item_instance_id=f"{opportunity.item_opportunity_id}-X001",
        item_opportunity_id=opportunity.item_opportunity_id,
        learner_id=opportunity.student_id,
        scheduled_session_index=opportunity.scheduled_session_number,
        item_index=opportunity.item_index,
        item_template_id=opportunity.item_template_id,
        task_type=sampler.task_type,
        skill_id=sampler.skill_id,
        curriculum_node_id=opportunity.curriculum_node_id,
        grade=opportunity.grade,
        difficulty_level=template.difficulty_level,
        representation_type=template.representation_type,
        response_format=sampler.response_format,
        generated_operands=dict(content.operands),
        prompt=dict(content.prompt),
        correct_answer=correct_norm,
        allowed_equivalent_answers=tuple(equivalents),
        distractor_candidates=distractors,
        distractor_rule_ids=distractor_rule_ids,
        generation_seed=instance_lineage.seed,
        seed_lineage=instance_lineage,
        catalogue_version=catalogue_version,
        catalogue_checksum=catalogue_checksum,
        validity_status="VALID",
        applied_guard_ids=applied_guard_ids,
        generation_phase=PHASE_B2A,
    )


def generate_task_instances(
    opportunities: List[GeneratedItemOpportunity],
    catalogue: LoadedCatalogue,
    catalogue_checksum: str,
    strict: bool = False,
) -> Tuple[List[GeneratedItemInstance], Tuple[str, ...], Tuple[str, ...]]:
    """Generate instances for every opportunity whose template is implemented.

    Returns ``(instances, implemented_template_ids, unsupported_template_ids)``. In ``strict``
    mode the first unsupported template raises ``UnsupportedTemplateError`` (no fabrication);
    otherwise unsupported opportunities are skipped and reported (still no fabrication).
    """
    instances: List[GeneratedItemInstance] = []
    implemented: set[str] = set()
    unsupported: set[str] = set()

    for opp in opportunities:
        template = catalogue.by_id(opp.item_template_id)
        if template is None:
            raise TaskInstanceValidationError(f"opportunity references unknown template {opp.item_template_id!r}")
        if get_sampler(opp.item_template_id) is None:
            if strict:
                raise UnsupportedTemplateError(
                    f"no Phase-B2A strategy for template {opp.item_template_id!r}"
                )
            unsupported.add(opp.item_template_id)
            continue
        instances.append(
            build_task_instance(
                opp, template, catalogue.catalogue_version, catalogue.catalogue_status, catalogue_checksum
            )
        )
        implemented.add(opp.item_template_id)

    return instances, tuple(sorted(implemented)), tuple(sorted(unsupported))
