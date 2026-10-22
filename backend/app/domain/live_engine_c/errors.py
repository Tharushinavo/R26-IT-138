"""Stable internal/application errors for the Component C live-engine adapter (Phase 1 batch 1b).

The adapter never lets a package-internal exception type cross into
``app.application``/``app.api``. Every failure from the vendored package is translated into one
of these instead. The nine package exceptions translated here were verified present in the
installed wheel by direct inspection (not assumed): ``CatalogueValidationError``,
``SelectionInputError``, ``TaskGenerationTechnicalError``, ``UnsupportedTemplateError``,
``UnknownTemplateError``, ``NoEligibleRecoveryTemplateError``, ``RecoveryPreconditionError``,
``QLearningDisabledError``, ``UnknownPolicyModeError``.

VALIDATORS BATCH adds a tenth: ``MasteryPayloadContractValidationError``, translating
``validators.contract_validators.ContractValidationError`` (now shipped in B's wheel at
0.1.0+bf5.09267ab; see backend/provenance/component-b-live-engine-manifest.json's
validators_widened_closure). Same translation pattern as the nine above -- a package exception
type must never cross the X-3 boundary into app.domain.
"""

from __future__ import annotations

from typing import Sequence, Tuple


class LiveEngineCError(Exception):
    """Base type for every stable error raised by the Component C live-engine adapter."""


class CatalogueUnavailableError(LiveEngineCError):
    """The governed catalogue could not be loaded or failed a load-time invariant.

    Translates ``component_c_generator.catalogue.loader.CatalogueValidationError``.
    """


class SelectionInputError(LiveEngineCError):
    """Translates ``component_c_generator.selection.selector.SelectionInputError`` — a fail-closed
    rejection of a wrong or missing ``session_phase``, a B payload supplied in ``c_only`` mode, a
    ``mastery_driven`` phase without a payload, or a ``student_id`` mismatch (v3.0 §7.1)."""


class TaskGenerationTechnicalError(LiveEngineCError):
    """Translates ``component_c_generator.generation.TaskGenerationTechnicalError``."""


class UnsupportedTemplateError(LiveEngineCError):
    """Translates ``component_c_generator.generation.UnsupportedTemplateError``."""


class UnknownTemplateError(LiveEngineCError):
    """Translates ``component_c_generator.evaluation.UnknownTemplateError``."""


class NoEligibleRecoveryTemplateError(LiveEngineCError):
    """Translates ``component_c_generator.scaffolds.recovery.NoEligibleRecoveryTemplateError``."""


class RecoveryPreconditionError(LiveEngineCError):
    """Translates ``component_c_generator.scaffolds.recovery.RecoveryPreconditionError``."""


class QLearningDisabledError(LiveEngineCError):
    """Translates ``component_c_generator.policy.rule_based.QLearningDisabledError`` — raised by
    ``decide_adaptation`` for any ``policy_mode`` other than ``rule_based_baseline`` (v3.0 §7.3:
    Q-learning stays ``EXPERIMENTAL_ONLY``)."""


class UnknownPolicyModeError(LiveEngineCError):
    """Translates ``component_c_generator.policy.rule_based.UnknownPolicyModeError``."""


class MasteryPayloadContractValidationError(LiveEngineCError):
    """Translates ``validators.contract_validators.ContractValidationError`` — raised by
    ``validate_payload(payload, "b_to_c")`` when a mastery payload carries a prohibited field or
    fails the frozen ``BToCMasteryPayload`` contract's own validation (VALIDATORS BATCH).

    Phase 4 work order, Q2: mastery values are exactly what C must never expose to a client, and
    a raw ``str(exc)`` of a pydantic ``ValidationError`` echoes the rejected INPUT VALUE back
    (verified: pydantic's ``errors()`` entries carry an ``input`` key, and its default ``__str__``
    renders it). This type therefore never carries ``str(exc)`` in its message and instead carries
    ``field_errors`` — a tuple of ``(loc_path, error_type_code)`` pairs extracted from the
    package's chained ``pydantic.ValidationError`` (via ``__cause__``), or an empty tuple when no
    such chain exists (e.g. a prohibited-field rejection, which is caught by exact field NAME
    already, no reconstruction needed). ``loc_path`` is a tuple of field-path segments (strings/
    ints); ``error_type_code`` is pydantic's short type string (e.g. ``"string_pattern_mismatch"``,
    ``"float_parsing"``) — NEVER the human-readable ``msg`` (which can itself embed the input for
    some error types) and NEVER the ``input`` value itself."""

    def __init__(self, field_errors: Sequence[Tuple[Tuple[object, ...], str]] = ()) -> None:
        self.field_errors: Tuple[Tuple[Tuple[object, ...], str], ...] = tuple(field_errors)
        rendered = ", ".join(f"{list(loc)}: {code}" for loc, code in self.field_errors) or "b_to_c payload rejected"
        super().__init__(rendered)


class SelectionConfigurationMissingError(LiveEngineCError):
    """Phase 4b, owner condition 1: "If the loader structurally requires a field to be present,
    it is labelled and the code path consuming W must refuse to run rather than proceed on a
    placeholder. Fail-closed means halt, not default." Raised when a code path needs
    ``SelectionConfig`` and the resolved ``CRuntimeBundle.selection_configuration`` is ``None``
    (additive-only means this is a real, expected state for any bundle not yet republished with
    the block, B1-b) -- never defaulted, never substituted."""


class SafetyConfigurationMissingError(LiveEngineCError):
    """Phase 6b, S2-a/X4: raised when a code path needs ``SafetyConfig`` and the resolved
    ``CRuntimeBundle.safety_configuration`` is ``None`` (a real, expected state for any bundle
    not yet republished with the block) -- never defaults, never substitutes a placeholder.
    Mirrors ``SelectionConfigurationMissingError`` exactly, one family later."""


class EvidenceWindowConfigurationMissingError(LiveEngineCError):
    """SEVENTH-FAMILY GATE batch: raised when a code path needs ``EvidenceWindowConfig`` and the
    resolved ``CRuntimeBundle.evidence_window_configuration`` is ``None`` (a real, expected state
    for any bundle not yet republished with the block, additive-only) -- never defaults, never
    substitutes a placeholder. Mirrors ``SafetyConfigurationMissingError`` exactly, one family
    later."""


class ConfigurationFamilyNotUsableError(LiveEngineCError):
    """Phase 6b, X1/X4: raised when ANY field of a parameter family's per-field status is not in
    the USABLE whitelist ({"APPROVED"} only -- X1-a, a whitelist, never a deny-list on specific
    known-bad values). W2's own trap, quoted: "mark enough fields as something-other-than-pending
    and the block reads as usable... Per-field status is for accuracy of the record, never for
    partial enablement." One unusable field makes the WHOLE family unusable. Carries the family
    name and the specific unusable field names -- never which VALUE they held (S1: no threshold
    value may appear in an error message any more than in a source file)."""

    def __init__(self, family_name: str, unusable_fields: tuple[str, ...]) -> None:
        self.family_name = family_name
        self.unusable_fields = unusable_fields
        super().__init__(
            f"{family_name}: {len(unusable_fields)} field(s) not in the usable whitelist: "
            f"{', '.join(unusable_fields)}"
        )


class TelemetryStreamRejectedError(LiveEngineCError):
    """Phase 8 (v3.0 §11 Phase 8, "Treat the client's event stream as untrusted input"): raised by
    ``telemetry_validation`` when a task opportunity's event stream fails a STRUCTURAL check
    (monotonicity, index continuity, terminal uniqueness, pause pairing/overlap, the structural
    half of inactivity plausibility, or the ordinal half of clock discipline) -- never for a
    plausibility judgment, since no threshold for any of those is governed (I4 and its three
    siblings stay BLOCKED, unbuilt). K1: raising this means derivation and scoring are refused for
    this stream -- the already-persisted ``c_gameplay_events`` rows themselves are untouched,
    never deleted, never nulled. Carries the specific structural check name, never a threshold
    value (none exists to carry)."""

    def __init__(self, check: str, detail: str) -> None:
        self.check = check
        self.detail = detail
        super().__init__(f"telemetry stream rejected ({check}): {detail}")


class DistrustedHistoryGapError(LiveEngineCError):
    """Phase 8, J1-4: raised by ``telemetry_validation.get_derivable_history_for_session`` when a
    session's history contains a GAP -- a task opportunity that was offered and reached a terminal
    gameplay event but has no ``c_task_opportunity_summary_id`` row (i.e. Phase 8's own validator
    refused it). Never returns a truncated history silently: a gap makes the WHOLE session history
    request refuse, by the same inversion principle already governing this register (fail-closed
    means refuse the protected activity -- here, the adaptation decision that would otherwise be
    computed over an unusable window -- never refuse the check itself by returning a shorter list
    unremarked)."""

    def __init__(self, c_session_id: object, gap_task_indices: tuple[int, ...]) -> None:
        self.c_session_id = c_session_id
        self.gap_task_indices = gap_task_indices
        super().__init__(
            f"session {c_session_id} history has a gap at task_index(es) {gap_task_indices} -- "
            "refusing rather than returning a truncated history"
        )


class AggregationInputsUnavailableError(LiveEngineCError):
    """Phase 9a, P1 (owner ruling): "AGGREGATION MUST REFUSE AT RUNTIME WHEN ITS INPUTS ARE
    UNAVAILABLE, not merely be documented as unwired... What stops it is code that refuses."
    Raised unconditionally by ``aggregation_service.derive_and_persist_session_aggregate`` while
    ``aggregation_service._AGGREGATION_INPUTS_AVAILABLE`` is ``False`` -- REGARDLESS of what a
    caller passes for ``time_in_target_band_sec``/``safety_override_count``, so a caller supplying
    a real number cannot quietly satisfy this the way a ``None``-check could be satisfied. Carries
    no threshold or invented value -- there is none to carry; this error exists precisely because
    none is sourced yet (see the module docstring's loop-level register entry)."""


class NoRealCSessionError(LiveEngineCError):
    """SF-040 (9b-1): translates ``component_c_generator.c_to_3.emit.NoRealCSessionError``.
    Raised -- and no C->3 payload is built or returned -- when the mapping row's ``c_present`` is
    false or its ``c_session_id`` is null.

    FINDING (recorded per supervisor ruling on the 9b-1 plan): ``SharedInterventionSessionMapping.
    validate_mapping_invariants`` (``packaging/component_b_internal/models/contracts.py:96-107``,
    CD-04) already enforces ``c_present == (c_session_id is not None)`` on every mapping row at
    construction, and ``emit_c_to_3`` validates the mapping row via ``validate_payload(mapping_row,
    "mapping")`` BEFORE testing SF-040 (``component_c_generator/c_to_3/emit.py:58-60``). The two
    disjuncts the vendored SF-040 check tests (``not c_present`` / ``c_session_id is None``) are
    therefore logically equivalent given CD-04, and the second is not independently constructible
    as a mapping-row fixture -- it is defensive redundancy in the vendored source, not a
    separately reachable branch. See ``tests/test_9b1_c_to_3_emission.py`` for the one
    constructible test case."""


class PromptWordingUnavailableError(LiveEngineCError):
    """BE-prompt-text batch. Raised by ``app.domain.live_engine_c.prompt_wording.prompt_text_for``
    in two cases:

    (1) ``game_task_template_id`` has no entry at all in
    ``PROMPT_TEXT_BY_TEMPLATE``. This should be UNREACHABLE in practice: the wording table's own
    coverage test asserts all 30 supported template ids are present, so a real gap would be caught
    before this ever fired. Raised anyway, as defence in depth, so a future template addition that
    outpaces the wording table produces a deliberate, structured refusal instead of an uncaught
    ``KeyError`` that could leak an internal lookup detail into a 500 response.

    (2) the template DOES carry variants (currently ``C-EG-02``, ``C-NP-04``) but the task
    instance's ``prompt_payload`` carries a discriminator value the wording table has no entry
    for. Unlike (1), this IS a reachable, real fail-closed path -- it fires whenever the pinned
    generator's payload for that template diverges from the wording table's variant coverage.
    Wording resolution never falls back to a default string or picks an arbitrary variant: no
    wording is better than wrong wording.

    Both are translated to ``ConflictError`` at the ``next_task`` call site, the same pattern every
    other ``LiveEngineCError`` here uses. Carries the template id only -- never any wording
    content or payload value, since there is none that should be echoed back."""

    def __init__(self, game_task_template_id: str) -> None:
        self.game_task_template_id = game_task_template_id
        super().__init__(f"no prompt wording for template {game_task_template_id!r}")


class SF043OrderingError(LiveEngineCError):
    """Phase 4: the SF-043 ordering gate at session creation -- "B runs -> B completes ->
    B emits seven mastery values -> C validates the same-session payload -> C begins." Raised
    when a ``combined`` session is requested with no mastery payload supplied, or a ``c_only``
    session is requested WITH one (c_only must never receive, query, cache, or infer a B
    payload). Distinct from ``MasteryPayloadContractValidationError`` (a present but
    contract-invalid payload) and from the package's own ``SelectionInputError`` (translated only
    at the ``select_task`` chokepoint, Phase 5) -- this is the ordering check Phase 4 itself owns,
    enforced before any session row is ever created."""
