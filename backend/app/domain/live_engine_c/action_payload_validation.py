"""Component C Phase 5, C-12: structural validation of a submitted ``action_payload`` against a
task instance's own ``valid_action_space`` declaration.

OWNER-RULED GOVERNING PRINCIPLE (Phase 5 work order, quoted verbatim): "THE DECLARATION IS THE
SCHEMA. NOTHING BEYOND THE DECLARATION IS STRUCTURAL." This module checks exactly two things and
nothing else: the submitted key set equals the declared key set, and each value's Python type
matches its declared type string. Ranges, counts, non-emptiness, uniqueness, and cross-field
consistency are CORRECTNESS properties and stay with the evaluator (``evaluation.evaluate`` /
each template's own ``_evaluate_*`` function) -- this module never reads ``correct_answer_payload``
and has no way to.

This module imports NOTHING from ``component_c_generator`` -- it operates purely on the plain
``Mapping[str, str]`` ``valid_action_space`` declaration already carried by ``TaskInstance``
(itself already translated at the X-1 adapter boundary), and the plain ``Mapping[str, Any]``
learner-submitted payload. It is therefore not adapter code and is not subject to X-1.

THE TWO OWNER INTERPRETIVE DECISIONS (both disclosed here, in one place, per the work order's own
instruction):
  1. The declared type string ``"number"`` means int OR float (ambiguous in the 30 templates'
     source; resolved here, not silently).
  2. Where ``"int"`` is declared, ``bool`` is explicitly REJECTED, even though
     ``isinstance(True, int)`` is ``True`` in Python -- a naive check would silently admit
     ``{"submitted_total": true}``. Every numeric check below excludes ``bool`` explicitly.

PIPE-STRING DECLARATIONS ARE PARSED PROGRAMMATICALLY. ``"left|right|equal"``, ``"<|>|="``, and
``"same|changed"`` are declarations of an allowed string-literal SET, encoded as a
pipe-separated string because the package's ``valid_action_space`` has no other vocabulary for
"one of these exact strings" (confirmed: no template's declared type is any OTHER form containing
``"|"``). This module detects that shape by the presence of ``"|"`` and splits on it at
validation time -- it never hand-transcribes a per-template enum table, so a future template
whose prose changes (e.g. a fourth comparison outcome added to ``"<|>|="``) is validated
correctly without this module being touched.

FAIL-CLOSED ON AN UNRECOGNIZED DECLARATION (BUILDER JUDGMENT — UNRATIFIED): no work order text
says what to do if a template's ``valid_action_space`` ever declares a type string this module
does not recognize (not one of ``int``/``bool``/``number``/``list[X]``/a pipe-string). Every
other unknown-shape situation in this codebase fails closed (unknown template, absent
selection_configuration, ...); this module does the same -- an unrecognized declaration makes
EVERY value for that key invalid, never silently accepted. If Phase 10 introduces a genuinely new
type-string vocabulary, this will surface as a loud rejection during that phase's own testing,
not a silent gap.
"""

from __future__ import annotations

import re
from typing import Any, Mapping, Sequence, Tuple

_LIST_TYPE_RE = re.compile(r"^list\[(\w+)\]$")


class ActionPayloadValidationError(Exception):
    """Raised when a submitted ``action_payload`` fails structural validation against its task
    instance's own ``valid_action_space``. Carries ``field_errors`` in the same
    ``(loc_path, error_type_code)`` shape as ``MasteryPayloadContractValidationError`` (Phase 4),
    for the same reason: safe to translate into ``[{"location": [...], "type": ...}]`` without
    ever carrying a human-readable message or the rejected input value itself."""

    def __init__(self, field_errors: Sequence[Tuple[Tuple[str, ...], str]]) -> None:
        self.field_errors: Tuple[Tuple[Tuple[str, ...], str], ...] = tuple(field_errors)
        super().__init__(f"action_payload rejected: {len(self.field_errors)} field error(s)")


def _value_matches_declared_type(declared_type: str, value: Any) -> bool:
    """Structural-only: does ``value``'s Python type/shape match ``declared_type``? Never reads
    or considers whether the value is CORRECT."""
    if "|" in declared_type:
        allowed = set(declared_type.split("|"))
        return isinstance(value, str) and value in allowed
    if declared_type == "int":
        return isinstance(value, int) and not isinstance(value, bool)
    if declared_type == "bool":
        return isinstance(value, bool)
    if declared_type == "number":
        # Owner interpretive decision 1: "number" means int or float.
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if declared_type == "str":
        return isinstance(value, str)
    list_match = _LIST_TYPE_RE.match(declared_type)
    if list_match:
        inner_type = list_match.group(1)
        if not isinstance(value, list):
            return False
        return all(_value_matches_declared_type(inner_type, element) for element in value)
    # Unrecognized declaration -- fail closed (BUILDER JUDGMENT — UNRATIFIED, module docstring).
    return False


def validate_action_payload(
    valid_action_space: Mapping[str, str], action_payload: Mapping[str, Any]
) -> None:
    """Raises ``ActionPayloadValidationError`` collecting EVERY violation (not just the first) if
    ``action_payload``'s key set does not exactly equal ``valid_action_space``'s key set, or if
    any present value's type does not match its declaration. Raises nothing on success."""
    declared_keys = set(valid_action_space)
    submitted_keys = set(action_payload)

    field_errors: list[Tuple[Tuple[str, ...], str]] = []

    for missing_key in sorted(declared_keys - submitted_keys):
        field_errors.append(((missing_key,), "missing"))
    for extra_key in sorted(submitted_keys - declared_keys):
        field_errors.append(((extra_key,), "extra_forbidden"))

    for key in sorted(declared_keys & submitted_keys):
        declared_type = valid_action_space[key]
        if not _value_matches_declared_type(declared_type, action_payload[key]):
            field_errors.append(((key,), "type_mismatch"))

    if field_errors:
        raise ActionPayloadValidationError(field_errors)
