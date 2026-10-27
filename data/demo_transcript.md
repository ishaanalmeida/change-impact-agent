  -> find_entity({'query': 'Vortex Seals', 'entity_type': 'Supplier'})
  -> change_impact({'entity_id': 'SUP-vortex-seals-gmbh'})
  -> sparql({'query': 'SELECT ?nc ?defect ?status ?target WHERE { VALUES ?nc { fx:NC-5001 fx:NC-5030 fx:NC-5033 fx:NC-5040 fx:NC-5042 fx:NC-5047 fx:NC-5056 fx:NC-5058 fx:NC-5070 } OPTIONAL { ?nc fx:defect ?defect } OPTIONAL { ?nc fx:status ?status } OPTIONAL { ?nc fx:concerns ?target } }'})
  -> sparql({'query': 'SELECT ?p ?a ?prod WHERE { VALUES ?p { fx:PRT-10003 fx:PRT-10006 fx:PRT-10028 fx:PRT-10035 fx:PRT-10036 fx:PRT-10045 } ?a fx:hasComponent ?p . OPTIONAL { ?prod fx:hasComponent ?a . ?prod a fx:Product } }'})
I matched "Vortex Seals" to **SUP-vortex-seals-gmbh** ("VORTEX SEALS GMBH"). It was a name match with a score of 95, not an exact ID match. I can pull the ERP, MES and CRM records behind it with `source_evidence` if you want to check it.

## 1. Parts affected
Vortex supplies 12 parts. **6 have no second source, so they're the real risk for the 8 weeks:**

| Part | What it is | Goes into |
|---|---|---|
| PRT-10028 | Mechanical seal 35mm carbon/SiC | ASM-0006 → **FX-200** |
| PRT-10006 | O-ring 20mm NBR | ASM-0006 → **FX-200** |
| PRT-10036 | Mechanical seal 45mm SiC/SiC | ASM-0013 → **HD-400, CB-50**; also used directly in **FX-250** |
| PRT-10035 | Mechanical seal 55mm carbon/SiC | ASM-0010 → **SW-300** |
| PRT-10045 | O-ring 32mm FKM | ASM-0003 → **CB-90** |
| PRT-10003 | Mechanical seal 25mm carbon/SiC | ASM-0020 (I couldn't link it to a product directly; it may sit inside another assembly) |

The other 6 parts have a second source: PRT-10020, -10021, -10025, -10055, -10069, -10096.

## 2. What it reaches
- **10 products:** AL-80, AL-120, CB-50, CB-90, FX-150, FX-200, FX-250, HD-400, HD-600, SW-300
- **20 assemblies and 20 customers**, including Maasvlakte Chemicals, Zeeland Desalination, Brabant Pharma Fill and Amstel Water Board
- **150 installed units.** This matters for spare seals, not just new builds.

## 3. Open quality issues that make it worse
There are 9 open issues on Vortex parts:
- **NC-5058** (face wear) is on **PRT-10036**, a part with no second source. That's the worst case: no backup supplier and a known defect. HD-400, CB-50 and FX-250 are exposed.
- **NC-5033** (leak at seal face) is on **PRT-10006**, also no second source (FX-200).
- **PRT-10025** has 3 open seal-face leaks (NC-5030, -5042, -5056). It has a second source, so move volume there.
- Also open: NC-5001 and NC-5070 (face wear, PRT-10096), NC-5040 (leak, PRT-10069), NC-5047 (swelling, PRT-10021).

## 4. What to do first
1. **Today: secure stock for the 6 parts with no second source.** Check stock on hand and open orders against 8 weeks of demand. Start with PRT-10036 and PRT-10028, because they cover 5 products (FX-200, FX-250, HD-400, CB-50). Set aside spare seals for the 150 installed units.
2. **This week: find a second supplier.** Tampere Seal Systems Oy (SUP-tampere-seal-systems-oy) is in the system as a seal supplier, but I haven't confirmed it can make these parts. Ask for quotes and samples for PRT-10036, -10028 and -10035 first.
3. **Warn customers and move volume.** Tell sales and service which customers on FX-200, FX-250, HD-400, CB-50, CB-90 and SW-300 to warn about longer lead times. For the parts that do have a second source, shift orders there now, starting with PRT-10025 because of its 3 open leak issues.

Next, I can work out where PRT-10003 ends up (which product ASM-0020 feeds), or list which customers own each exposed product.
