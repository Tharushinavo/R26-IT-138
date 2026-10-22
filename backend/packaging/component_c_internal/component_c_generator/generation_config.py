"""Per-template generation-parameter config (Phase C2.1) -- TEST_FIXTURE_ONLY.

The frozen catalogue (Component_C_v1.0/...Game_Task_Catalogue_v1.0.md, Section 5) names each
template's "Main difficulty levers" in PROSE ("set size", "number range", "addend sizes", ...)
but supplies **no numeric bound and no action-space enumeration** for any of the 30 templates
-- confirmed during Phase C2.0's catalogue transcription (see that phase's build report). The
authoritative Component C Empirical/Statistical Parameters do not fix these values either
(CALIBRATION_PENDING). Every numeric value in this module is therefore an
**ENGINEERING_ASSUMPTION, tagged `parameter_source_status = "TEST_FIXTURE_ONLY"`** -- picked
only to be small, deterministic, and mathematically valid for structural generation/testing.
None of it is written into the catalogue or any governance document, and none of it should be
read as a calibrated difficulty curve. The authoritative per-template bounds remain
CALIBRATION_PENDING pending Component C Parameters sign-off.

``TemplateGenerationParams`` uses a small set of GENERIC, level-indexed fields
(``magnitude_a_by_level`` / ``magnitude_b_by_level`` / ``count_a_by_level`` /
``count_b_by_level`` / ``choice_set`` / ``max_generation_attempts``) reused with a
**per-template documented meaning** (see the comment on each entry in
``DEFAULT_TEMPLATE_GENERATION_PARAMS`` and the corresponding ``tasks/*.py`` generator) rather
than one bespoke schema per template -- kept generic deliberately so this file stays a single
auditable table. Structural minimums that are DEFINITIONAL to a task's own mathematical shape
(e.g. a "two-digit number" is >=10, a single-digit addend is <=9, trading a ten requires >=10
ones) are NOT calibration parameters and are fixed directly in the relevant ``tasks/*.py``
generator function, not here -- see each generator's inline comment.

No field has a silent default: every ``TemplateGenerationParams`` value used by a given
template's generator must be present, and ``CGenerationConfig`` requires an explicit
``parameter_source_status`` like every other Component C config (mirrors
``component_c_generator.config.CGeneratorConfig`` / ``component_b_generator.bkt.config``).
"""

from __future__ import annotations

from typing import Annotated, Optional, Tuple

from pydantic import BaseModel, ConfigDict, Field, field_validator

Level5Tuple = Tuple[int, int, int, int, int]

GENERATION_CONFIG_VERSION = "c2.1-generation-1.0.0"


class TemplateGenerationParams(BaseModel):
    """Generic, level-indexed generation bounds for ONE template. Fields are optional because
    different templates need different subsets; each ``tasks/*.py`` generator documents which
    fields it reads and what they mean for that specific template."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    magnitude_a_by_level: Optional[Level5Tuple] = None
    magnitude_b_by_level: Optional[Level5Tuple] = None
    count_a_by_level: Optional[Level5Tuple] = None
    count_b_by_level: Optional[Level5Tuple] = None
    choice_set: Optional[Tuple[int, ...]] = None
    max_generation_attempts: Annotated[int, Field(ge=1)] = 8


class CGenerationConfig(BaseModel):
    """Versioned, no-defaults wrapper over the per-template generation params."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    config_version: str
    parameter_source_status: str  # MUST be "TEST_FIXTURE_ONLY" for this table (see module docstring)
    per_template: dict[str, TemplateGenerationParams]

    @field_validator("config_version", "parameter_source_status")
    @classmethod
    def _non_empty(cls, v: str) -> str:
        if not str(v).strip():
            raise ValueError("version / source-status strings must be non-empty")
        return v

    def params_for(self, game_task_template_id: str) -> TemplateGenerationParams:
        if game_task_template_id not in self.per_template:
            raise KeyError(f"no generation params configured for template {game_task_template_id!r}")
        return self.per_template[game_task_template_id]


# --------------------------------------------------------------------------------------
# TEST_FIXTURE_ONLY default table -- every value below is an ENGINEERING_ASSUMPTION picked
# only to be small, valid, and deterministic. NOT sourced from Component C Parameters
# (CALIBRATION_PENDING) or the catalogue (no per-template bounds exist there -- Phase C2.0
# gap report). Comments document the per-template MEANING of each generic field.
# --------------------------------------------------------------------------------------

DEFAULT_TEMPLATE_GENERATION_PARAMS: dict[str, TemplateGenerationParams] = {
    # C-GF-01 Count and Collect
    "C-CC-01": TemplateGenerationParams(  # magnitude_a = valid object count by level; count_a = distractor object count by level
        magnitude_a_by_level=(3, 5, 8, 12, 16), count_a_by_level=(0, 1, 2, 3, 4),
    ),
    "C-CC-02": TemplateGenerationParams(  # magnitude_a = target N (objects to place) by level
        magnitude_a_by_level=(2, 4, 7, 11, 15),
    ),
    "C-CC-03": TemplateGenerationParams(  # magnitude_a = set cardinality by level; count_a = numeral-distractor count by level
        magnitude_a_by_level=(3, 5, 8, 12, 16), count_a_by_level=(1, 2, 2, 3, 3),
    ),
    "C-CC-04": TemplateGenerationParams(  # magnitude_a = object count shown by level (flavor only, not a correctness input)
        magnitude_a_by_level=(3, 4, 6, 8, 10),
    ),
    # C-GF-02 Number Path and Order
    "C-NP-01": TemplateGenerationParams(  # magnitude_a = start-value upper bound by level; count_a = shown length; count_b = blanks to fill
        magnitude_a_by_level=(10, 20, 40, 70, 100), count_a_by_level=(3, 3, 4, 4, 5), count_b_by_level=(1, 1, 2, 2, 2),
    ),
    "C-NP-02": TemplateGenerationParams(  # same roles as C-NP-01, backward sequence
        magnitude_a_by_level=(10, 20, 40, 70, 100), count_a_by_level=(3, 3, 4, 4, 5), count_b_by_level=(1, 1, 2, 2, 2),
    ),
    "C-NP-03": TemplateGenerationParams(  # magnitude_a = start-value upper bound; count_a = shown length; count_b = blanks; choice_set = allowed skip steps
        magnitude_a_by_level=(10, 20, 30, 50, 80), count_a_by_level=(3, 3, 4, 4, 5), count_b_by_level=(1, 1, 2, 2, 2),
        choice_set=(2, 5, 10),
    ),
    "C-NP-04": TemplateGenerationParams(  # magnitude_a = value upper bound by level; count_a = card-list length by level
        magnitude_a_by_level=(20, 40, 60, 90, 150), count_a_by_level=(3, 3, 4, 4, 5),
    ),
    # C-GF-03 Match, Compare and Locate
    "C-MCL-01": TemplateGenerationParams(  # magnitude_a = value upper bound; count_a = distractor-option count; max_generation_attempts covers option-uniqueness retries
        magnitude_a_by_level=(10, 20, 30, 50, 80), count_a_by_level=(2, 2, 3, 3, 4), max_generation_attempts=20,
    ),
    "C-MCL-02": TemplateGenerationParams(magnitude_a_by_level=(10, 20, 30, 50, 80)),  # magnitude_a = quantity upper bound by level
    "C-MCL-03": TemplateGenerationParams(magnitude_a_by_level=(20, 50, 100, 300, 999)),  # magnitude_a = numeral upper bound by level
    "C-MCL-04": TemplateGenerationParams(  # magnitude_a = interval (number-line) upper bound; magnitude_b = tolerance by level
        magnitude_a_by_level=(10, 20, 50, 100, 200), magnitude_b_by_level=(2, 2, 1, 1, 1),
    ),
    # C-GF-04 Build and Trade
    "C-BT-01": TemplateGenerationParams(magnitude_a_by_level=(2, 3, 5, 7, 9)),  # magnitude_a = tens-digit upper bound by level (ones is always canonical 0-9, structural)
    "C-BT-02": TemplateGenerationParams(magnitude_a_by_level=(1, 2, 4, 6, 9)),  # magnitude_a = hundreds-digit upper bound by level (tens/ones canonical 0-9, structural)
    "C-BT-03": TemplateGenerationParams(magnitude_a_by_level=(1, 2, 3, 5, 8)),  # magnitude_a = pre-trade tens-digit upper bound by level (pre-ones fixed 10-19, structural -- see tasks/build_and_trade.py)
    "C-BT-04": TemplateGenerationParams(magnitude_a_by_level=(2, 3, 4, 6, 9)),  # magnitude_a = pre-trade tens-digit upper bound by level (>=1 structural minimum enforced in code)
    # C-GF-05 Join and Bridge
    "C-JB-01": TemplateGenerationParams(magnitude_a_by_level=(3, 5, 8, 12, 18)),  # magnitude_a = each addend's upper bound by level
    "C-JB-02": TemplateGenerationParams(magnitude_a_by_level=(3, 5, 8, 12, 18)),  # magnitude_a = each addend's upper bound by level (jump_unit_size fixed = 1, structural configured-strategy choice)
    "C-JB-03": TemplateGenerationParams(magnitude_a_by_level=(4, 6, 7, 8, 9)),  # magnitude_a = single-digit addend upper bound by level (<=9 structural)
    "C-JB-04": TemplateGenerationParams(magnitude_a_by_level=(29, 39, 49, 69, 98)),  # magnitude_a = two-digit addend upper bound by level (>=10 structural minimum in code)
    # C-GF-06 Take Away and Compare
    "C-TC-01": TemplateGenerationParams(magnitude_a_by_level=(3, 6, 10, 15, 20)),  # magnitude_a = initial quantity upper bound by level
    "C-TC-02": TemplateGenerationParams(magnitude_a_by_level=(5, 8, 12, 18, 25)),  # magnitude_a = each compared quantity's upper bound by level
    "C-TC-03": TemplateGenerationParams(),  # a<=9, b in [0,a] -- fully structural (definitional "within 9"), no config value needed
    "C-TC-04": TemplateGenerationParams(magnitude_a_by_level=(29, 39, 49, 69, 98)),  # magnitude_a = two-digit minuend upper bound by level (>=10 structural minimum in code)
    # C-GF-07 Equal Groups and Arrays
    "C-EG-01": TemplateGenerationParams(count_a_by_level=(2, 3, 3, 4, 5), count_b_by_level=(2, 2, 3, 3, 4)),  # count_a = number_of_groups by level; count_b = group_size by level
    "C-EG-02": TemplateGenerationParams(count_a_by_level=(2, 3, 3, 4, 5), count_b_by_level=(2, 2, 3, 4, 5)),  # count_a = rows by level; count_b = cols by level
    "C-EG-03": TemplateGenerationParams(magnitude_a_by_level=(5, 6, 8, 10, 12), choice_set=(2, 5, 10)),  # magnitude_a = multiplicand upper bound by level; choice_set = approved multipliers
    # C-GF-08 Share Fairly
    "C-SF-01": TemplateGenerationParams(count_a_by_level=(2, 2, 3, 4, 5), magnitude_a_by_level=(2, 3, 4, 5, 6)),  # count_a = recipient_count by level; magnitude_a = per-recipient upper bound by level
    "C-SF-02": TemplateGenerationParams(count_a_by_level=(2, 3, 3, 4, 5), magnitude_a_by_level=(2, 2, 3, 3, 4)),  # count_a = group_count by level; magnitude_a = group_size by level
    "C-SF-03": TemplateGenerationParams(magnitude_a_by_level=(6, 10, 16, 24, 40)),  # magnitude_a = dividend upper bound by level (even dividend enforced in code)
}


def default_generation_config() -> CGenerationConfig:
    """The Phase C2.1 TEST_FIXTURE_ONLY generation config -- explicit builder (mirrors B's
    ``default_b1_config()``), never applied as a silent fallback."""
    return CGenerationConfig(
        config_version=GENERATION_CONFIG_VERSION,
        parameter_source_status="TEST_FIXTURE_ONLY",
        per_template=dict(DEFAULT_TEMPLATE_GENERATION_PARAMS),
    )
