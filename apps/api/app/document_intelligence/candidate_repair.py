"""Constrained candidate repair (Phase D3-9): a *proposal*, never a confirmation.

An OCR value that fails its checksum may be one recogniser error away from the printed number. The
repair enumerates the single-error alternatives from the explicit, versioned confusion table, keeps
those that pass the validator, and proposes a value only when

* exactly one alternative validates, and
* that alternative equals the value another document of the submission carries (an independent
  source: different file, different pixels).

The proposal is attached to the decision (provenance `REPAIRED_FROM_OCR`); the machine value is
never replaced and the field still goes to a human.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass

from app.document_intelligence.ocr_confusions import CONFUSION_TABLE_VERSION, alternative_readings

PROVENANCE = "REPAIRED_FROM_OCR"


@dataclass(frozen=True)
class RepairProposal:
    value: str
    peer_count: int
    confusion_table_version: str = CONFUSION_TABLE_VERSION
    provenance: str = PROVENANCE


def propose_repair(
    value: str, validator: Callable[[str], bool], peer_values: Iterable[str]
) -> RepairProposal | None:
    if validator(value):
        return None
    valid = {candidate for candidate in alternative_readings(value) if validator(candidate)}
    if len(valid) != 1:
        return None
    (candidate,) = valid
    peers = [peer for peer in peer_values if peer == candidate]
    if not peers:
        return None
    return RepairProposal(candidate, len(peers))
