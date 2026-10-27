"""Re-run the evaluation on seeds the resolver was never tuned on (21-30) and average.

Seed 7 is the demo dataset and seeds 11-15 were used to find and fix resolver bugs, so neither
counts as a test. Restores seed 7 when done.
"""
import json
import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SEEDS = range(21, 31)


def run(*args):
    subprocess.run([sys.executable, *args], cwd=ROOT, check=True, capture_output=True)


table, misses, counts = defaultdict(list), [], []
for seed in SEEDS:
    run("generate_data.py", str(seed))
    run("eval/run_eval.py")
    report = (ROOT / "eval" / "results.md").read_text(encoding="utf-8")
    counts.append(int(re.search(r"(\d+) change-impact questions", report).group(1)))
    for line in report.splitlines():
        cells = [c.strip() for c in line.strip("|").split("|")]
        if line.startswith("| ") and cells[0] not in ("Method", "Check") and "---" not in line:
            table[cells[0]].append([float(x) for c in cells[1:] for x in c.split(" / ")])
    # which vendor records the resolver failed to join
    truth = json.loads((ROOT / "data" / "truth.json").read_text(encoding="utf-8"))
    sys.path.insert(0, str(ROOT))
    from resolve import build  # noqa: E402
    _, log = build("full")
    by_sup = defaultdict(set)
    for line in log:
        if line["system"] == "ERP" and line["method"] == "vendor name cluster":
            by_sup[truth["vendor_supplier"][line["record"].split()[0]]].add((line["entity"], line["record"].split(" ", 1)[1]))
    for sup, recs in by_sup.items():
        if len({e for e, _ in recs}) > 1:
            misses.append(f"seed {seed}: {sup} split across {sorted(r for _, r in recs)}")

def cell(vals, i):
    col = [v[i] for v in vals]
    return f"{sum(col) / len(col):.2f} ({min(col):.2f})"


out = [f"# Held-out evaluation, seeds {SEEDS.start}-{SEEDS.stop - 1}\n",
       f"{sum(counts)} questions in total, {min(counts)} to {max(counts)} per seed. "
       "Mean over seeds, worst seed in brackets.\n",
       "| Method | Supplier parts P | R | Products P | R | Customers P | R | Open issues P | R |",
       "|---|---|---|---|---|---|---|---|---|"]
checks = ["\n| Resolver check | Score |", "|---|---|"]
for name, vals in table.items():
    target, sep = (out, " | ") if len(vals[0]) == 8 else (checks, " / ")  # checks hold one score or a P / R pair
    target.append(f"| {name} | " + sep.join(cell(vals, i) for i in range(len(vals[0]))) + " |")
out += checks
out += ["\n## Resolver misses\n"] + [f"- {m}" for m in misses or ["none"]]
(ROOT / "eval" / "held_out.md").write_text("\n".join(out) + "\n", encoding="utf-8")
print("\n".join(out))
run("generate_data.py")
run("resolve.py")
run("eval/run_eval.py")
