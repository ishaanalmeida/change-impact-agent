"""Map the four source systems onto the ontology as one RDF graph.

mode="full": entity resolution (vendor clustering, description matching, product-name matching).
mode="keys": the baseline. The same IDs are normalised (PRT-10023 == 10023-00), but names must
match exactly apart from case, as in a spreadsheet join. Everything else is the same, so the
evaluation compares entity resolution and nothing more.
"""
import csv
import re
from collections import Counter
from pathlib import Path

from rapidfuzz import fuzz
from rapidfuzz.distance import OSA
from rdflib import RDF, RDFS, Graph, Literal, Namespace
from rdflib.namespace import SKOS

ROOT = Path(__file__).parent
DATA = ROOT / "data"
FX = Namespace("https://example.org/fluxa/")

# Abbreviations shop-floor systems use; in a real engagement this list comes from the customer's engineers.
GLOSSARY = [(r"\bss\b", "stainless"), (r"\bci\b", "cast iron"), (r"\bmech\.?", "mechanical"),
            (r"\bgalv\.?", "galvanised"), (r"\bvolute(?! casing)", "volute casing"),
            (r"(?<!ball )\bbearing\b", "ball bearing"), (r"(\d)\s+(mm|kw)\b", r"\1\2")]


def rows(name):
    with open(DATA / name, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def digits(s):
    return re.findall(r"\d+", s)


def part_key(ref):
    """PRT-10023, prt10023, 10023-00 -> PRT-10023. None when the reference holds no number."""
    d = digits(ref)
    return f"PRT-{d[0]}" if d else None


def norm_vendor(name):
    tokens = re.sub(r"[.,]", " ", name.lower()).split()
    # legal forms are short trailing tokens; dropping any token of <= 4 chars also catches typos like "GbmH"
    while len(tokens) > 2 and len(tokens[-1]) <= 4:
        tokens.pop()
    return "".join(tokens)  # spaces dropped: typos often move a space ("ArdennesB earings")


def norm_desc(d):
    d = d.lower()
    for pat, rep in GLOSSARY:
        d = re.sub(pat, rep, d)
    return " ".join(d.split())


def norm_product(name):
    n = re.sub(r"pump unit", "", name.lower())
    return re.sub(r"[^a-z0-9]", "", n)


def best_match(query, candidates, scorer, cutoff, margin=3):
    """Best candidate whose numbers equal the query's. Numbers are never fuzzy: 45mm is not 50mm.

    Returns (key, score) or (None, reason)."""
    q_digits = digits(query)
    scored = sorted(((scorer(query, text), key) for key, text in candidates if digits(text) == q_digits), reverse=True)
    if not scored or scored[0][0] < cutoff:
        return None, f"no candidate above {cutoff}"
    if len(scored) > 1 and scored[0][0] - scored[1][0] < margin:
        return None, f"ambiguous: {scored[0][1]} vs {scored[1][1]}"
    return scored[0][1], round(scored[0][0])


def cluster_vendors(vendors, mode):
    """vendor_id -> cluster key. Greedy single-pass clustering on normalised names.

    Two names join when one edit (a swapped, changed, added or dropped character) separates them.
    A similarity ratio cannot do this: normalised "Nordic Castings" vs "Nordic Coatings" scores 93 and
    they are different firms; the typo "Nordic Casitngs" is one edit from the first, the other firm two."""
    if mode == "keys":
        return {vid: name.lower() for vid, name in vendors.items()}
    reps, out = [], {}
    for vid, name in sorted(vendors.items()):
        n = norm_vendor(name)
        match = next((r for r in reps if OSA.distance(n, r) <= 1), None)
        if match is None:
            reps.append(n)
            match = n
        out[vid] = match
    return out


def build(mode="full"):
    g = Graph()
    g.parse(ROOT / "ontology" / "core.ttl")
    g.bind("fx", FX)
    log = []

    def note(entity, system, record, method, score=""):
        g.add((entity, FX.sourceRecord, Literal(f"{system}:{record} ({method}{' ' + str(score) if score != '' else ''})")))
        log.append({"entity": str(entity).split("/")[-1], "system": system, "record": record, "method": method, "score": score})

    # PLM is the master for items and structure
    items = rows("plm_items.csv")
    cls = {"product": FX.Product, "assembly": FX.Assembly, "part": FX.Part}
    for it in items:
        e = FX[it["item_id"]]
        g.add((e, RDF.type, cls[it["item_type"]]))
        g.add((e, RDFS.label, Literal(it["description"])))
        g.add((e, FX.sourceRecord, Literal(f"PLM:{it['item_id']} (master record)")))
    for b in rows("plm_bom.csv"):
        g.add((FX[b["parent"]], FX.hasComponent, FX[b["child"]]))
    parts = {it["item_id"]: it["description"] for it in items if it["item_type"] == "part"}
    products = {it["item_id"]: it["description"] for it in items if it["item_type"] == "product"}

    # ERP: vendor records -> suppliers, material numbers -> parts
    erp = rows("erp_purchasing.csv")
    vendors = {r["vendor_id"]: r["vendor_name"] for r in erp}
    clusters = cluster_vendors(vendors, mode)
    spellings = {}
    for vid, key in clusters.items():
        spellings.setdefault(key, []).append(vendors[vid])
    sup_uri = {}
    for key, names in spellings.items():
        # canonical label: most words (keeps the legal form), then not shouted in capitals, then most common
        label = max(names, key=lambda n: (len(n.split()), not n.isupper(), names.count(n), n))
        uri, k = FX["SUP-" + slug(label)], 2
        while uri in sup_uri.values():  # two clusters slugging alike must stay two suppliers
            uri, k = FX[f"SUP-{slug(label)}-{k}"], k + 1
        sup_uri[key] = uri
        g.add((sup_uri[key], RDF.type, FX.Supplier))
        g.add((sup_uri[key], RDFS.label, Literal(label)))
        for n in set(names):
            g.add((sup_uri[key], SKOS.altLabel, Literal(n)))
    for vid, key in clusters.items():
        note(sup_uri[key], "ERP", f"{vid} '{vendors[vid]}'", "vendor name cluster" if mode == "full" else "exact name")
    for r in erp:
        pid = part_key(r["erp_material"])
        if pid in parts:
            g.add((FX[pid], FX.suppliedBy, sup_uri[clusters[r["vendor_id"]]]))
            note(FX[pid], "ERP", r["erp_material"], "material number key")
        else:
            log.append({"entity": "", "system": "ERP", "record": r["erp_material"], "method": "unresolved", "score": "no PLM part"})

    # MES: nonconformance -> part, by id when there is one, else by description
    desc_candidates = [(pid, norm_desc(d)) for pid, d in parts.items()]
    exact_desc = {d.lower(): pid for pid, d in parts.items()}
    for r in rows("mes_nonconformance.csv"):
        qi = FX[r["nc_id"]]
        g.add((qi, RDF.type, FX.QualityIssue))
        g.add((qi, FX.status, Literal(r["status"])))
        g.add((qi, FX.defect, Literal(r["defect"])))
        if r["part_ref"]:
            pid, method, score = part_key(r["part_ref"]), "part number key", ""
        elif mode == "full":
            pid, score = best_match(norm_desc(r["part_desc"]), desc_candidates, fuzz.token_sort_ratio, cutoff=85)
            method = "description match"
        else:
            pid, method, score = exact_desc.get(r["part_desc"].lower()), "exact description", ""
        if pid in parts:
            g.add((qi, FX.concerns, FX[pid]))
            note(qi, "MES", f"{r['nc_id']} '{r['part_ref'] or r['part_desc']}'", method, score)
        else:
            log.append({"entity": r["nc_id"], "system": "MES", "record": r["part_ref"] or r["part_desc"], "method": "unresolved", "score": score})

    # CRM: installations -> product by typed name; accounts -> customers
    prod_norm = {norm_product(n): code for code, n in products.items()}
    for r in rows("crm_installed_base.csv"):
        inst, cust = FX[r["serial_no"]], FX["CUS-" + slug(r["account"])]
        g.add((inst, RDF.type, FX.Installation))
        g.add((inst, RDFS.label, Literal(f"{r['serial_no']} at {r['account']}, {r['site_city']}")))
        g.add((cust, RDF.type, FX.Customer))
        g.add((cust, RDFS.label, Literal(r["account"])))
        g.add((cust, FX.sourceRecord, Literal(f"CRM:account '{r['account']}' (exact name)")))
        g.add((inst, FX.ownedBy, cust))
        if mode == "full":
            code = prod_norm.get(norm_product(r["product_name"]))
            score = "exact after normalising"
            if code is None:
                code, score = best_match(norm_product(r["product_name"]), [(c, norm_product(n)) for c, n in products.items()], fuzz.ratio, cutoff=85)
        else:
            code = next((c for c, n in products.items() if n.lower() == r["product_name"].lower()), None)
            score = "exact name"
        if code:
            g.add((inst, FX.ofProduct, FX[code]))
            note(inst, "CRM", f"{r['serial_no']} '{r['product_name']}'", "product name", score)
        else:
            log.append({"entity": r["serial_no"], "system": "CRM", "record": r["product_name"], "method": "unresolved", "score": score})
    return g, log


if __name__ == "__main__":
    for mode in ("keys", "full"):
        g, log = build(mode)
        c = Counter((l["system"], l["method"] == "unresolved") for l in log)
        print(mode, len(g), "triples |", {f"{s}{' unresolved' if u else ''}": n for (s, u), n in sorted(c.items())})
    g.serialize(ROOT / "data" / "graph.ttl", format="turtle")
    with open(ROOT / "data" / "resolution_log.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["entity", "system", "record", "method", "score"])
        w.writeheader()
        w.writerows(log)
