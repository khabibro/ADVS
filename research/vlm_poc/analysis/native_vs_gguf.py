"""Agreement between the native Paddle CPU route and the llama.cpp GGUF route on the validation sample."""
import difflib, hashlib, json, re, sys
from pathlib import Path

S = Path("/Users/admin/Documents/ADVS/evaluation/datasets/synthetic/test_variants")
sample = json.loads(Path("results/native_sample_files.json").read_text())
sq = lambda t: re.sub(r"\s+", "", t or "")
rows, exact_pages, total_pages = [], 0, 0
print("| file | pages | identical text | character similarity | blocks identical / total | native s | GGUF s |")
print("|---|---|---|---|---|---|---|")
for rel in sample:
    h = hashlib.sha256((S / rel).read_bytes()).hexdigest()
    n = json.loads(Path(f"results/native_sample/{h}.json").read_text())
    g = json.loads(Path(f"results/pages_test_variants/{h}.json").read_text())
    ident = sims = blocks_same = blocks = 0
    for pn, pg in zip(n["pages"], g["pages"]):
        tn = "".join(sq(b["block_content"]) for b in pn["blocks"]); tg = "".join(sq(b["block_content"]) for b in pg["blocks"])
        total_pages += 1; exact_pages += tn == tg; ident += tn == tg
        sims += difflib.SequenceMatcher(None, tn, tg).ratio()
        bn = [sq(b["block_content"]) for b in pn["blocks"]]; bg = [sq(b["block_content"]) for b in pg["blocks"]]
        blocks += max(len(bn), len(bg)); blocks_same += len(set(bn) & set(bg))
    k = len(n["pages"])
    print(f"| {rel.split('/')[-1]} | {k} | {ident}/{k} | {sims / k:.4f} | {blocks_same}/{blocks} | {n['seconds']} | {g['seconds']} |")
print(f"\nPages with identical text: {exact_pages}/{total_pages}")
