"""Gold-label schema (versioned) and manifest structures.

Field vocabulary matches `app.core.domain.EXPECTED_FIELDS` exactly -- this
file does not invent a competing set of field names.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

GOLD_SCHEMA_VERSION = "1.1"

# A. OFFICIAL_PUBLIC_REFERENCE   -- an actual official/public file, stored verbatim (unused so far: none downloaded)
# B. RECREATED_FROM_PUBLIC_REFERENCE -- from-scratch recreation citing a source_id in source_registry.json
# C. SYNTHETIC_REALISTIC         -- purely generated from data pools, no specific external source cited
# D. NEGATIVE_OUT_OF_SCOPE       -- an UNKNOWN-gold sample (real-terminology or synthetic)
SOURCE_CLASSES = (
    "OFFICIAL_PUBLIC_REFERENCE",
    "RECREATED_FROM_PUBLIC_REFERENCE",
    "SYNTHETIC_REALISTIC",
    "NEGATIVE_OUT_OF_SCOPE",
)


@dataclass
class GoldField:
    value: str | None
    required: bool = True


@dataclass
class GoldLabel:
    sample_id: str
    source: str  # "synthetic" | "real"
    document_type: str
    input_format: str  # "text_pdf" | "scanned_pdf" | "png" | "jpg"
    quality: (
        str  # "clean" | "compressed" | "blurred" | "low_contrast" | "rotated" | "low_resolution"
    )
    layout_variant: str
    split: str  # "dev" | "held_out"
    fields: dict[str, GoldField]
    expected_validation_status: str | None
    notes: str = ""
    schema_version: str = GOLD_SCHEMA_VERSION
    verified: bool = True  # False until a human confirms a real-sample label
    source_class: str = "SYNTHETIC_REALISTIC"  # one of SOURCE_CLASSES
    source_id: str | None = None  # references evaluation/sources/source_registry.json

    def to_json(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["fields"] = {name: asdict(f) for name, f in self.fields.items()}
        return payload

    @staticmethod
    def from_json(payload: dict[str, Any]) -> GoldLabel:
        fields = {
            name: GoldField(value=data["value"], required=data.get("required", True))
            for name, data in payload["fields"].items()
        }
        return GoldLabel(
            sample_id=payload["sample_id"],
            source=payload["source"],
            document_type=payload["document_type"],
            input_format=payload["input_format"],
            quality=payload["quality"],
            layout_variant=payload["layout_variant"],
            split=payload["split"],
            fields=fields,
            expected_validation_status=payload.get("expected_validation_status"),
            notes=payload.get("notes", ""),
            schema_version=payload.get("schema_version", GOLD_SCHEMA_VERSION),
            verified=payload.get("verified", True),
            source_class=payload.get("source_class", "SYNTHETIC_REALISTIC"),
            source_id=payload.get("source_id"),
        )


@dataclass
class ManifestEntry:
    sample_id: str
    source: str
    document_type: str
    gold_text_path: str
    rendered_file_path: str
    gold_label_path: str
    split: str


@dataclass
class Manifest:
    manifest_version: str
    generator_seed: int
    entries: list[ManifestEntry] = field(default_factory=list)

    def to_json(self) -> dict[str, Any]:
        return {
            "manifest_version": self.manifest_version,
            "generator_seed": self.generator_seed,
            "sample_count": len(self.entries),
            "entries": [asdict(e) for e in self.entries],
        }
