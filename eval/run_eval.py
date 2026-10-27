"""Score change-impact answers against the generator's ground truth.

Questions: "supplier S stops delivering" for every supplier, and "part P changes" for every part
that has an open quality issue or sits more than one BOM level below a product.
Methods differ in one thing each: entity resolution on/off, and BOM traversal depth.
"""
import json
import sys
from collections import defaultdict
from itertools import combinations
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from impact import ImpactGraph  # noqa: E402
from resolve import build, rows  # noqa: E402

truth = json.loads((ROOT / "data" / "truth.json").read_text(encoding="utf-8"))
children = defaultdict(set)
for parent, child, _ in truth["bom"]:
    children[parent].add(child)


def contains(item, target):
    return target in children[item] or any(contains(c, target) for c in children[item])


def true_answer(parts):
    products = {p for p in truth["products"] if any(contains(p, x) for x in parts)}
    customers = {i["customer"] for i in truth["installations"] if i["product"] in products}
    issues = {q["nc_id"] for q in truth["issues"] if q["part"] in parts and q["status"] == "open"}
    return products, customers, issues


def questions():
    qs = [("supplier", s, {p for p, sups in truth["part_suppliers"].items() if s in sups}) for s in truth["suppliers"]]
    direct = {c for p in truth["products"] for c in children[p]}
    open_parts = {q["part"] for q in truth["issues"] if q["status"] == "open"}
    for part in sorted(truth["part_suppliers"]):
        if part in open_parts or part not in direct:
            qs.append(("part", part, {part}))
    return qs


def prf(pred, gold):
    if not pred and not gold:
        return 1.0, 1.0
    tp = len(pred & gold)
    return (tp / len(pred) if pred else 0.0), (tp / len(gold) if gold else 1.0)


def run(graph, qs):
    scores = defaultdict(list)
    for kind, name, parts in qs:
        products, customers, issues = true_answer(parts)
        hit = graph.find_entity(name, "Supplier" if kind == "supplier" else "Part", limit=1)
        if hit:
            res = graph.change_impact(hit[0]["id"])
            got_p = {d["id"] for d in res["products"]}
            got_c = {d["label"] for d in res["customers"]}
            got_i = {d["id"] for d in res["open_quality_issues"]}
            got_parts = {d["id"] for d in res["parts"]}
        else:
            got_p = got_c = got_i = got_parts = set()
        if kind == "supplier":  # products saturate (10 models); the part list is where a bad merge shows
            scores["supplier parts"].append(prf(got_parts, parts))
        for field, pred, gold in (("products", got_p, products), ("customers", got_c, customers), ("open issues", got_i, issues)):
            scores[field].append(prf(pred, gold))
    return {f: tuple(sum(x) / len(v) for x in zip(*v)) for f, v in scores.items()}


def resolution_quality():
    """How well the full build resolved each source, record by record."""
    _, log = build("full")
    out = {}
    # vendor clustering: pairwise precision/recall over ERP vendor records
    v2s = truth["vendor_supplier"]
    clusters = {}
    for line in log:
        if line["system"] == "ERP" and line["method"] == "vendor name cluster":
            clusters[line["record"].split()[0]] = line["entity"]
    pairs = list(combinations(sorted(clusters), 2))
    same_pred = {p for p in pairs if clusters[p[0]] == clusters[p[1]]}
    same_true = {p for p in pairs if v2s[p[0]] == v2s[p[1]]}
    out["ERP vendor records -> suppliers (pairwise P/R)"] = prf(same_pred, same_true)
    # MES description-only records
    issue_part = {q["nc_id"]: q["part"] for q in truth["issues"]}
    desc_rows = {r["nc_id"] for r in rows("mes_nonconformance.csv") if not r["part_ref"]}
    g, _ = build("full")
    from resolve import FX
    got = {nc: str(g.value(FX[nc], FX.concerns) or "").split("/")[-1] for nc in desc_rows}
    out["MES description-only records matched correctly"] = (
        sum(got[n] == issue_part[n] for n in desc_rows) / len(desc_rows) if desc_rows else 1.0)
    inst = {i["serial"]: i["product"] for i in truth["installations"]}
    got = {s: str(g.value(FX[s], FX.ofProduct) or "").split("/")[-1] for s in inst}
    out["CRM installations matched to the right product"] = sum(got[s] == inst[s] for s in inst) / len(inst)
    return out


if __name__ == "__main__":
    qs = questions()
    n_sup = sum(q[0] == "supplier" for q in qs)
    methods = {"Ontology + entity resolution": ImpactGraph("full", "all"),
               "Key joins only (baseline)": ImpactGraph("keys", "all"),
               "Entity resolution, direct BOM parents only": ImpactGraph("full", "one")}
    lines = [f"# Evaluation\n\n{len(qs)} change-impact questions ({n_sup} supplier losses, {len(qs) - n_sup} part changes), "
             "scored against the generator's ground truth. Mean precision / recall per question.\n",
             "| Method | Supplier parts P / R | Products P / R | Customers P / R | Open issues P / R |", "|---|---|---|---|---|"]
    for name, graph in methods.items():
        s = run(graph, qs)
        lines.append(f"| {name} | " + " | ".join(f"{s[f][0]:.2f} / {s[f][1]:.2f}" for f in ("supplier parts", "products", "customers", "open issues")) + " |")
    lines += ["\n## Entity resolution, record level\n", "| Check | Score |", "|---|---|"]
    for k, v in resolution_quality().items():
        lines.append(f"| {k} | {' / '.join(f'{x:.2f}' for x in v) if isinstance(v, tuple) else f'{v:.2f}'} |")
    report = "\n".join(lines) + "\n"
    (ROOT / "eval" / "results.md").write_text(report, encoding="utf-8")
    print(report)
