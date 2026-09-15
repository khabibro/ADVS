"""Generates the P1.5+ evaluation benchmark: purely synthetic samples plus a
small set of RECREATED_FROM_PUBLIC_REFERENCE samples motivated by real
source research (see evaluation/reports/source_research.md).

Deterministic: re-running this script with the same GENERATOR_SEED produces
byte-identical gold labels and text (rendered file bytes may differ only in
incidental metadata such as PDF creation timestamps -- content is
deterministic). No LLM or network call is used.

Usage:
    cd apps/api && .venv/bin/python scripts/eval_generate.py
"""

import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from eval_lib import paths
from eval_lib.generate import (
    CaseSpec,
    generate_business_cases,
    generate_career_cases,
    generate_graduation_cases,
    generate_recreated_cases,
    generate_sme_cases,
    generate_submission_documents,
    generate_unknown_cases,
    to_gold_label,
)
from eval_lib.render import render
from eval_lib.schema import Manifest, ManifestEntry

GENERATOR_SEED = 42
COUNTS = {
    "graduation": 24,
    "career": 24,
    "business_registration": 24,
    "sme_confirmation": 24,
    "unknown": 24,
}

_TYPE_DIR = {
    "GRADUATION_CERTIFICATE": "graduation",
    "CAREER_CERTIFICATE": "career",
    "BUSINESS_REGISTRATION_CERTIFICATE": "business_registration",
    "SME_CONFIRMATION_CERTIFICATE": "sme_confirmation",
    "UNKNOWN": "unknown",
}


def _dataset_dir_for(case: CaseSpec) -> Path:
    root = paths.DATASETS_RECREATED if case.source_class == "RECREATED_FROM_PUBLIC_REFERENCE" else paths.DATASETS_SYNTHETIC
    return root / _TYPE_DIR[case.document_type]


def _gold_dir_for(case: CaseSpec) -> Path:
    return paths.GOLD_RECREATED if case.source_class == "RECREATED_FROM_PUBLIC_REFERENCE" else paths.GOLD_SYNTHETIC


def main() -> None:
    for directory in (paths.DATASETS_SYNTHETIC, paths.GOLD_SYNTHETIC, paths.DATASETS_RECREATED, paths.GOLD_RECREATED):
        if directory.exists():
            shutil.rmtree(directory)
    paths.GOLD_SYNTHETIC.mkdir(parents=True, exist_ok=True)
    paths.GOLD_RECREATED.mkdir(parents=True, exist_ok=True)
    for subdir in _TYPE_DIR.values():
        (paths.DATASETS_SYNTHETIC / subdir).mkdir(parents=True, exist_ok=True)
        (paths.DATASETS_RECREATED / subdir).mkdir(parents=True, exist_ok=True)

    all_cases = (
        generate_graduation_cases(COUNTS["graduation"])
        + generate_career_cases(COUNTS["career"])
        + generate_business_cases(COUNTS["business_registration"])
        + generate_sme_cases(COUNTS["sme_confirmation"])
        + generate_unknown_cases(COUNTS["unknown"])
        + generate_recreated_cases()
        + generate_submission_documents()
    )

    manifest = Manifest(manifest_version="1.1", generator_seed=GENERATOR_SEED)
    split_counts = {"dev": 0, "held_out": 0}
    type_counts: dict[str, int] = {}
    source_class_counts: dict[str, int] = {}

    for index, case in enumerate(all_cases):
        case_dir = _dataset_dir_for(case)
        gold_text = "\n".join(case.lines)
        text_path = case_dir / f"{case.sample_id}.txt"
        text_path.write_text(gold_text, encoding="utf-8")

        rendered = render(case.lines, case.input_format, case.quality, rng_seed=GENERATOR_SEED + index)
        rendered_path = case_dir / f"{case.sample_id}.{rendered.extension}"
        rendered_path.write_bytes(rendered.content)

        gold_label = to_gold_label(case)
        gold_path = _gold_dir_for(case) / f"{case.sample_id}.json"
        gold_path.write_text(
            json.dumps(gold_label.to_json(), ensure_ascii=False, indent=2), encoding="utf-8"
        )

        manifest.entries.append(
            ManifestEntry(
                sample_id=case.sample_id,
                source="recreated" if case.source_class == "RECREATED_FROM_PUBLIC_REFERENCE" else "synthetic",
                document_type=case.document_type,
                gold_text_path=str(text_path.relative_to(paths.REPO_ROOT)),
                rendered_file_path=str(rendered_path.relative_to(paths.REPO_ROOT)),
                gold_label_path=str(gold_path.relative_to(paths.REPO_ROOT)),
                split=case.split,
            )
        )
        split_counts[case.split] += 1
        type_counts[case.document_type] = type_counts.get(case.document_type, 0) + 1
        source_class_counts[case.source_class] = source_class_counts.get(case.source_class, 0) + 1

    paths.MANIFEST_PATH.write_text(
        json.dumps(manifest.to_json(), ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print(f"Generated {len(all_cases)} samples (seed={GENERATOR_SEED}).")
    for doc_type, count in type_counts.items():
        print(f"  {doc_type}: {count}")
    print(f"Split: dev={split_counts['dev']} held_out={split_counts['held_out']}")
    print(f"Source class: {source_class_counts}")
    print(f"Manifest: {paths.MANIFEST_PATH.relative_to(paths.REPO_ROOT)}")


if __name__ == "__main__":
    main()
