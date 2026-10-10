"""Field-level readings of the same documents by method A (current OCR / embedded text) and
method B (PaddleOCR-VL page parse), scored with the frozen scorer's `score_field`.

  PYTHONPATH=<app checkout>/apps/api python analysis/compare_fields.py --corpus dev \
      --synth <evaluation/datasets/synthetic> --harness <evaluation/harness> --a-cache <ocr cache dir> \
      --pages results/pages_test_variants --scored <scored json with decisions> --out results/fields_dev.json
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import fmt, guard, input_type, load_manifest, sha256  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", required=True)
    ap.add_argument("--synth", type=Path, required=True)
    ap.add_argument("--harness", type=Path, required=True)
    ap.add_argument("--a-cache", type=Path, required=True)
    ap.add_argument("--pages", type=Path, required=True)
    ap.add_argument("--scored", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    guard(args.corpus)
    sys.path.insert(0, str(args.harness))
    import score_v2  # type: ignore[import-not-found]  # frozen scorer
    from harness_core import page_from_dict  # type: ignore[import-not-found]

    from adapter import page_from_blocks
    from app.core.domain import DocumentType
    from app.document_intelligence.extraction.registry import ExtractorRegistry
    from app.document_intelligence.ocr.models import OCRDocumentResult
    from app.document_intelligence.ocr.text_assembly import assemble_document_text, assemble_page_text
    from app.document_intelligence.preprocessing.processor import PdfProcessor

    registry = ExtractorRegistry()
    root = args.synth / {"dev": "test_variants"}.get(args.corpus, args.corpus)
    scored = json.loads(args.scored.read_text(encoding="utf-8"))["scored"]
    decisions: dict[tuple[str, str], str] = {}
    for block in (scored["sets"], scored["format_sets"]):
        for entry in block.values():
            groups = [v.get("files", []) for v in entry["versions"].values()] if "versions" in entry else [entry.get("files", [])]
            for items in groups:
                for item in items:
                    for name, fs in (item.get("fields") or {}).items():
                        decisions[(item["file"], name)] = fs.get("decision") or ""

    def extract(doc_type: str, pages) -> dict[str, str | None]:
        source = OCRDocumentResult("replay", pages, assemble_document_text(pages))
        return {v.field_name: v.normalized_value for v in registry.extract(DocumentType(doc_type), source)}

    rows, missing = [], {"a": 0, "b": 0}
    for entry in load_manifest(args.synth, args.corpus):
        rel = entry["file"]
        path = root / rel
        itype = input_type(rel, entry.get("style"))
        doc_type = entry["expected_classification"]
        if doc_type in (None, "n/a", "UNKNOWN"):
            continue
        # method A
        if itype == "digital":
            a_pages = PdfProcessor().extract_text(path).pages
        else:
            cache = args.a_cache / f"{sha256(path)}.json"
            if not cache.exists():
                missing["a"] += 1
                continue
            a_pages = [page_from_dict(p) for p in json.loads(cache.read_text(encoding="utf-8"))["pages"]]
            for page in a_pages:
                page.metadata.setdefault("source", "ocr")
                if page.lines:
                    page.text = assemble_page_text(page.lines)
        a = extract(doc_type, a_pages)
        # method B
        b_file = args.pages / f"{sha256(path)}.json"
        b = None
        if b_file.exists():
            payload = json.loads(b_file.read_text(encoding="utf-8"))
            if "pages" in payload:
                b = extract(doc_type, [page_from_blocks(p) for p in payload["pages"]])
        else:
            missing["b"] += 1
        printed = [str(v) for v in (entry.get("other_printed_values") or {}).values() if v]
        for spec in entry["expected_fields"].values():
            printed += [str(x) for x in (spec.get("printed"), spec.get("value")) if x]

        def on_page(field: str, value) -> bool | None:
            """Is the produced value one of the values printed on the (synthetic) page?"""
            if value is None:
                return None
            key = score_v2.normalize(field, value)
            if any(score_v2.normalize(field, p) == key for p in printed):
                return True
            return bool(key) and key in score_v2.text_key(" ".join(printed))

        for name, spec in entry["expected_fields"].items():
            ra = score_v2.score_field(name, spec, {"value": a.get(name), "machine_value": a.get(name)}, itype != "digital")
            rb = score_v2.score_field(name, spec, {"value": b.get(name), "machine_value": b.get(name)}, itype != "digital") if b is not None else None
            rows.append({
                "corpus": args.corpus, "file": rel, "input": itype, "doc_type": doc_type, "field": name,
                "state": spec.get("state"), "expected": ra.get("expected"),
                "a_value": a.get(name), "a_outcome": ra["outcome"],
                "b_value": None if b is None else b.get(name), "b_outcome": None if rb is None else rb["outcome"],
                "a_on_page": on_page(name, a.get(name)), "b_on_page": on_page(name, None if b is None else b.get(name)),
                "a_decision": decisions.get((rel, name), ""),
                "b_seconds": None,
            })
    meta = {"corpus": args.corpus, "scorer_sha256": sha256(args.harness / "score_v2.py"), "rows": len(rows), "missing": missing}
    args.out.write_text(json.dumps({"meta": meta, "rows": rows}, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(meta))


if __name__ == "__main__":
    main()
