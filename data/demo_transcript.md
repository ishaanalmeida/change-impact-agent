  -> find_entity({'query': 'Vortex Seals', 'entity_type': 'Supplier'})
  -> change_impact({'entity_id': 'SUP-vortex-seals-gmbh'})
  -> sparql({'query': 'SELECT ?nc ?defect ?status ?target ?tlabel WHERE { VALUES ?nc { fx:NC-5001 fx:NC-5030 fx:NC-5033 fx:NC-5040 fx:NC-5042 fx:NC-5047 fx:NC-5056 fx:NC-5058 fx:NC-5070 } OPTIONAL { ?nc fx:defect ?defect } OPTIONAL { ?nc fx:status ?status } OPTIONAL { ?nc fx:concerns ?target . OPTIONAL { ?target rdfs:label ?tlabel } } }'})
  -> sparql({'query': 'SELECT ?part ?plabel ?sup ?slabel WHERE { VALUES ?part { fx:PRT-10020 fx:PRT-10021 fx:PRT-10025 fx:PRT-10055 fx:PRT-10069 fx:PRT-10096 } ?part fx:suppliedBy ?sup . ?part rdfs:label ?plabel . ?sup rdfs:label ?slabel . FILTER(?sup != fx:SUP-vortex-seals-gmbh) }'})
  -> sparql({'query': 'SELECT ?part ?prod (COUNT(DISTINCT ?inst) AS ?installs) WHERE { VALUES ?part { fx:PRT-10003 fx:PRT-10006 fx:PRT-10028 fx:PRT-10035 fx:PRT-10036 fx:PRT-10045 } ?prod a fx:Product ; fx:hasComponent+ ?part . OPTIONAL { ?inst fx:ofProduct ?prod } } GROUP BY ?part ?prod ORDER BY ?part'})
An 8-week Vortex Seals shutdown hits every product line we have. Six of the 12 parts they supply have no second source, and those six alone appear in all 10 products.

**Supplier match:** "Vortex Seals" matched **SUP-vortex-seals-gmbh** ("VORTEX SEALS GMBH") with a fuzzy score of 95. That's very likely correct, but I can pull the ERP/CRM source records (source_evidence) if you want to confirm it.

**1. Parts affected (12)**

**No second source (6), where the real risk is:**

| Part | What it is | Products | Installs |
|---|---|---|---|
| PRT-10006 | O-ring 20mm NBR | FX-200, FX-250, AL-80, HD-400, CB-50, SW-300 | 93 |
| PRT-10028 | Mech. seal 35mm carbon/SiC | same 6 as above | 93 |
| PRT-10036 | Mech. seal 45mm SiC/SiC | FX-150, FX-250, HD-400, CB-50 | 63 |
| PRT-10003 | Mech. seal 25mm carbon/SiC | AL-120, HD-600, CB-90 | 40 |
| PRT-10045 | O-ring 32mm FKM | FX-250, CB-90 | 31 |
| PRT-10035 | Mech. seal 55mm carbon/SiC | SW-300 | 22 |

**Have a second source (6):**
- **Tampere Seal Systems:** PRT-10020, PRT-10021, PRT-10025, PRT-10055
- **Rhone Polymers:** PRT-10069
- **Ligure Valvole:** PRT-10096

**2. What it reaches**
- **Products (all 10):** FX-150, FX-200, FX-250, AL-80, AL-120, HD-400, HD-600, CB-50, CB-90, SW-300, through 20 assemblies
- **Customers:** 20. The most exposed are the ones running chemical and seawater duty: Maasvlakte Chemicals, Rijn Chemical Park, Zeeland Desalination, Schelde Shipyards and Haven Terminals.
- **Installations:** 150. That number matters for spare seals as well as new builds.

**3. Open quality issues that make it worse (9)**
- **NC-5033:** seal-face leak on PRT-10006, a part with no backup supplier.
- **NC-5058:** face wear on PRT-10036, also no backup. Field failures here will need spares nobody else can supply.
- **NC-5030, NC-5042, NC-5056:** three seal-face leaks on PRT-10025. If the backup is Tampere, check that their part doesn't have the same problem.
- **NC-5001, NC-5070:** face wear on PRT-10096, which switches to Ligure.
- **NC-5040:** seal-face leak on PRT-10069, which switches to Rhone.
- **NC-5047:** swelling after chemical exposure on PRT-10021, which switches to Tampere.

**4. What to do first**
1. **Today, check stock and lock it down.** For the 6 parts with no backup, count on-hand and open-PO quantities against 8 weeks of build demand plus field spares. Start with PRT-10006 and PRT-10028, since together they cover 6 products and 93 installs. Reserve service stock for the NC-5033 and NC-5058 field cases.
2. **This week, start emergency qualification of a second source** for those 6 parts. Tampere already makes our O-rings and 25mm SiC/SiC seals, so they're the obvious first call. Also ask Vortex whether they can make any of these parts at another site.
3. **Move volume to the existing backup suppliers** for the other 6 parts, and run incoming inspection on PRT-10025 and PRT-10096, given their open leak and wear issues. In parallel, send sales a list of at-risk orders and give a heads-up to the chemical and seawater customers above.

Next I can list which customers sit behind each part, or pull the source records behind the Vortex match.
