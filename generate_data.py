"""Generate a synthetic industrial data landscape for a fictional pump maker.

Four source systems (PLM, ERP, MES, CRM) describe the same parts, suppliers and
products, each in its own format and with its own mistakes. The true links are
written to data/truth.json BEFORE the sources are scrambled, so the evaluation
can score any resolution method against what is actually true.

All companies, products and people here are invented.
"""
import csv
import json
import random
import sys
from pathlib import Path

OUT = Path(__file__).parent / "data"
rng = random.Random(int(sys.argv[1]) if len(sys.argv) > 1 else 7)

# supplier -> the part categories it makes; every category has at least two possible sources
SPECIALISMS = {
    "Vortex Seals GmbH": ["O-ring", "Seal"], "Tampere Seal Systems Oy": ["Seal", "O-ring"],
    "Rhone Polymers SAS": ["O-ring"], "Nordic Castings AB": ["Casing", "Impeller"],
    "Nordic Coatings AB": ["Impeller", "Shaft"], "Baltic Impellers OU": ["Impeller"],
    "Ligure Valvole S.p.A.": ["Casing", "Seal"], "Silesia Steel Sp. z o.o.": ["Shaft", "Fasteners", "Casing"],
    "Lombardia Shafts S.p.A.": ["Shaft"], "Ardennes Bearings S.A.": ["Bearing"],
    "Midlands Fasteners Ltd": ["Fasteners", "Bearing"], "Brabant Motorworks B.V.": ["Motor"],
    "Twente Elektro B.V.": ["Motor", "Electronics"], "Bavaria Sensorik AG": ["Electronics"],
    "Kempen Electronics B.V.": ["Electronics"],
}
SUPPLIERS = list(SPECIALISMS)
DEFECTS = {"O-ring": ["leak at seal face", "swelling after chemical exposure"],
           "Seal": ["leak at seal face", "face wear"], "Bearing": ["bearing noise", "overheating"],
           "Impeller": ["porosity in casting", "imbalance", "cavitation erosion"],
           "Casing": ["porosity in casting", "corrosion"], "Shaft": ["dimension out of tolerance", "corrosion"],
           "Motor": ["winding insulation fault", "overheating"], "Fasteners": ["thread damage", "corrosion"],
           "Electronics": ["PCB solder fault", "sensor drift"]}

# (category, description templates, sizes); {s} is filled with a size
PART_TYPES = [
    ("O-ring", ["O-ring {s}mm NBR", "O-ring {s}mm FKM", "O-ring {s}mm EPDM"], [20, 32, 45, 60, 75, 90]),
    ("Bearing", ["Ball bearing 62{s}-2RS", "Ball bearing 63{s}-ZZ"], [3, 4, 5, 6, 7, 8, 9, 10]),
    ("Impeller", ["Impeller {s}mm cast iron", "Impeller {s}mm bronze", "Impeller {s}mm stainless"], [120, 150, 180, 220, 250, 300]),
    ("Seal", ["Mechanical seal {s}mm carbon/SiC", "Mechanical seal {s}mm SiC/SiC"], [25, 35, 45, 55, 65]),
    ("Motor", ["Motor {s}kW IE3 4-pole", "Motor {s}kW IE4 2-pole"], [4, 7, 11, 15, 22, 30, 45]),
    ("Shaft", ["Shaft {s}mm stainless", "Shaft {s}mm duplex"], [25, 35, 45]),
    ("Casing", ["Volute casing DN{s} cast iron", "Volute casing DN{s} stainless"], [50, 80, 100, 125, 150, 200]),
    ("Fasteners", ["Fastener kit M{s} A4", "Fastener kit M{s} galvanised"], [6, 8, 10, 12, 16, 20]),
    ("Electronics", ["Controller PCB rev {s}", "Pressure sensor 0-{s} bar", "Frequency drive {s}kW"], [6, 10, 16, 25, 40]),
]

PRODUCTS = [("FX-150", "FluxaPro 150"), ("FX-200", "FluxaPro 200"), ("FX-250", "FluxaPro 250"),
            ("AL-80", "AquaLine 80"), ("AL-120", "AquaLine 120"), ("HD-400", "HydroDrive 400"),
            ("HD-600", "HydroDrive 600"), ("CB-50", "ChemBoost 50"), ("CB-90", "ChemBoost 90"),
            ("SW-300", "SeaWater 300")]

CUSTOMERS = ["Polder Utilities", "Maasvlakte Chemicals", "Veluwe Dairy Cooperative", "Drenthe Biogas",
             "Schelde Shipyards", "Limburg Paper Mill", "Zeeland Desalination", "Twente Textiles",
             "Flevo Greenhouses", "Haven Terminals", "Kempen Breweries", "IJssel Steelworks",
             "Groningen District Heating", "Delta Fish Processing", "Brabant Pharma Fill",
             "Utrecht Data Cooling", "Waal Gravel Works", "Noord Food Ingredients",
             "Amstel Water Board", "Rijn Chemical Park"]
CITIES = ["Rotterdam", "Eindhoven", "Groningen", "Antwerp", "Duisburg", "Venlo", "Utrecht", "Zwolle"]


def make_parts():
    parts, seen = [], set()
    while len(parts) < 100:  # templates allow ~140 unique descriptions
        cat, templates, sizes = rng.choice(PART_TYPES)
        desc = rng.choice(templates).format(s=rng.choice(sizes))
        if desc in seen:
            continue
        seen.add(desc)
        able = [sup for sup, cats in SPECIALISMS.items() if cat in cats]
        sups = rng.sample(able, 2 if rng.random() < 0.25 else 1)  # a quarter are dual sourced
        parts.append({"id": f"PRT-{10001 + len(parts)}", "desc": desc, "category": cat, "suppliers": sups})
    return parts


def make_bom(parts):
    """Leaf assemblies hold parts; top assemblies hold leaf assemblies; products hold both."""
    edges = []  # (parent, child, qty)
    leaf = [f"ASM-{i:04d}" for i in range(1, 21)]
    top = [f"ASM-{i:04d}" for i in range(21, 31)]
    pids = [p["id"] for p in parts]
    contents = {a: set() for a in leaf}
    for pid in pids:  # every part is used at least once
        contents[rng.choice(leaf)].add(pid)
    for a in leaf:  # plus some reuse
        contents[a].update(rng.sample(pids, rng.randint(1, 3)))
    for a in leaf:
        edges += [(a, c, rng.randint(1, 8)) for c in sorted(contents[a])]
    for a in top:
        edges += [(a, c, 1) for c in rng.sample(leaf, rng.randint(2, 3))]
        edges += [(a, c, rng.randint(1, 4)) for c in rng.sample(pids, rng.randint(0, 2))]
    for code, _ in PRODUCTS:
        edges += [(code, c, 1) for c in rng.sample(top, rng.randint(1, 2))]
        edges += [(code, c, 1) for c in rng.sample(leaf, rng.randint(0, 2))]
        edges += [(code, c, 1) for c in rng.sample(pids, rng.randint(1, 2))]
    labels = {a: f"Assembly {a[-4:]}" for a in leaf + top}
    return edges, labels


# ---- the ways each system gets names wrong -------------------------------------------

def typo(s):
    i = rng.randrange(1, len(s) - 2)
    return s[:i] + s[i + 1] + s[i] + s[i + 2:]


def vendor_variant(name):
    base = name.rsplit(" ", 1)[0] if any(name.endswith(x) for x in (" GmbH", " AB", " Ltd", " SAS", " OU", " AG", " Oy")) else name
    return rng.choice([name, name.upper(), base, name.replace(".", ""), base.upper(), typo(name)])


def desc_variant(desc):
    d = desc
    for a, b in [("stainless", "SS"), ("Mechanical", "Mech."), ("Ball bearing", "Bearing"),
                 ("cast iron", "CI"), ("Volute casing", "Volute"), ("galvanised", "galv.")]:
        if a in d and rng.random() < 0.7:
            d = d.replace(a, b)
    if rng.random() < 0.5:
        d = d.replace("mm", " mm")
    return rng.choice([d, d.lower(), d.upper()])


def product_variant(name):
    word, num = name.rsplit(" ", 1)
    return rng.choice([name, f"{word}{num}", f"{word.upper()}-{num}", f"{name} pump unit",
                       f"{word[:5]} {word[5:]} {num}" if len(word) > 5 else name])


def main():
    OUT.mkdir(exist_ok=True)
    parts = make_parts()
    edges, asm_labels = make_bom(parts)

    # ERP: every supplier has one or two vendor master records, each spelled its own way
    vendors = {}  # vendor_id -> (true supplier, spelling)
    for s in SUPPLIERS:
        for _ in range(2 if rng.random() < 0.5 else 1):
            vendors[f"V{len(vendors) + 1:04d}"] = (s, vendor_variant(s))
    by_supplier = {}
    for vid, (s, _) in vendors.items():
        by_supplier.setdefault(s, []).append(vid)

    erp_rows = []
    for p in parts:
        num = p["id"].split("-")[1]
        for s in p["suppliers"]:
            vid = rng.choice(by_supplier[s])
            mat = f"{num}-00" if rng.random() < 0.85 else num
            erp_rows.append({"erp_material": mat, "vendor_id": vid, "vendor_name": vendors[vid][1],
                             "unit_price_eur": round(rng.uniform(2, 900), 2)})

    # CRM installed base: marketing names typed by hand
    installs, crm_rows = [], []
    for i in range(150):
        code, name = rng.choice(PRODUCTS)
        cust = rng.choice(CUSTOMERS)
        serial = f"SN{24000 + i}"
        installs.append({"serial": serial, "product": code, "customer": cust})
        crm_rows.append({"account": cust, "site_city": rng.choice(CITIES), "product_name": product_variant(name),
                         "serial_no": serial, "install_year": rng.randint(2015, 2026)})

    # MES nonconformance reports: sometimes a clean part id, sometimes only a description
    issues, mes_rows = [], []
    for i in range(70):
        p = rng.choice(parts)
        nc = f"NC-{5001 + i}"
        status = rng.choice(["open", "open", "closed"])
        issues.append({"nc_id": nc, "part": p["id"], "status": status})
        num = p["id"].split("-")[1]
        r = rng.random()
        if r < 0.5:
            ref, desc = p["id"], ""
        elif r < 0.75:
            ref, desc = rng.choice([f"prt{num}", num]), ""
        else:
            ref, desc = "", desc_variant(p["desc"])
        mes_rows.append({"nc_id": nc, "part_ref": ref, "part_desc": desc, "status": status,
                         "defect": rng.choice(DEFECTS[p["category"]])})

    def write(name, rows):
        with open(OUT / name, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0]))
            w.writeheader()
            w.writerows(rows)

    items = ([{"item_id": c, "item_type": "product", "description": n} for c, n in PRODUCTS]
             + [{"item_id": a, "item_type": "assembly", "description": l} for a, l in asm_labels.items()]
             + [{"item_id": p["id"], "item_type": "part", "description": p["desc"]} for p in parts])
    write("plm_items.csv", items)
    write("plm_bom.csv", [{"parent": a, "child": b, "qty": q} for a, b, q in edges])
    write("erp_purchasing.csv", erp_rows)
    write("mes_nonconformance.csv", mes_rows)
    write("crm_installed_base.csv", crm_rows)

    truth = {"part_suppliers": {p["id"]: p["suppliers"] for p in parts},
             "vendor_supplier": {v: s for v, (s, _) in vendors.items()},
             "bom": edges, "installations": installs, "issues": issues,
             "suppliers": SUPPLIERS, "products": dict(PRODUCTS)}
    (OUT / "truth.json").write_text(json.dumps(truth, indent=1), encoding="utf-8")
    print(f"{len(parts)} parts, {len(asm_labels)} assemblies, {len(PRODUCTS)} products, "
          f"{len(vendors)} ERP vendor records for {len(SUPPLIERS)} suppliers, "
          f"{len(installs)} installations, {len(issues)} quality issues")


if __name__ == "__main__":
    main()
