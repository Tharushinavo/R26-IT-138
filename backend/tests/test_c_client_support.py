"""The templates the app cannot draw are never offered to the selector.

Owner instruction, 2026-09-28: a template with no renderable surface must not reach a child as
"This one isn't ready" in the middle of a game -- the backend rejects it at selection and picks
something else. See app/domain/live_engine_c/client_support.py for which three and why.
"""

from app.domain.live_engine_c.client_support import (
    CLIENT_UNRENDERABLE_TEMPLATE_IDS,
    MINIMUM_SELECTABLE_TEMPLATES,
    selectable_template_ids,
)
from app.infrastructure.live_engine_c.adapter import LiveEngineCAdapter


def supported() -> tuple[str, ...]:
    return LiveEngineCAdapter().supported_template_ids()


def test_every_excluded_id_is_a_real_template() -> None:
    """A typo here would silently exclude nothing and leave the dead end in place -- the failure
    this list exists to prevent, wearing the costume of a working denylist."""
    unknown = set(CLIENT_UNRENDERABLE_TEMPLATE_IDS) - set(supported())
    assert unknown == set(), unknown


def test_the_excluded_templates_are_removed_from_the_pool() -> None:
    pool = selectable_template_ids(supported())
    for template_id in CLIENT_UNRENDERABLE_TEMPLATE_IDS:
        assert template_id in supported(), template_id
        assert template_id not in pool, template_id


def test_everything_else_survives_in_its_original_order() -> None:
    """Selection is seeded and deterministic, so re-ordering the pool would change which task a
    given seed produces. The filter removes; it must not rearrange."""
    full = supported()
    pool = selectable_template_ids(full)
    assert list(pool) == [t for t in full if t not in CLIENT_UNRENDERABLE_TEMPLATE_IDS]
    assert len(pool) == len(full) - len(CLIENT_UNRENDERABLE_TEMPLATE_IDS)


def test_the_remaining_pool_is_still_big_enough_to_adapt_over() -> None:
    """A floor to trip on, not a target. If this fails, an exclusion has gone wrong -- a bad id, or
    a wheel whose template set changed underneath this list."""
    pool = selectable_template_ids(supported())
    assert len(pool) >= MINIMUM_SELECTABLE_TEMPLATES, len(pool)


def test_filtering_is_idempotent_and_safe_on_an_already_clean_pool() -> None:
    pool = selectable_template_ids(supported())
    assert selectable_template_ids(pool) == pool
    assert selectable_template_ids(()) == ()


def test_each_exclusion_states_why() -> None:
    """The mapping is a record, not a bare denylist: an entry with no reason is an entry nobody can
    review or remove later."""
    for template_id, reason in CLIENT_UNRENDERABLE_TEMPLATE_IDS.items():
        assert template_id.startswith("C-"), template_id
        assert len(reason.strip()) > 20, (template_id, reason)
