# Change-impact agent over an enterprise ontology

An engineer at an industrial manufacturer asks: *what does this change affect?* Today the answer
is spread across PLM, ERP, MES and CRM, and each system names the same parts, suppliers and products
differently. This repo connects them into one ontology, puts an agent on top through MCP, and
measures how often the answers are right.

```
$ python agent.py "Vortex Seals just told us their seal plant is shut for 8 weeks. What does this change affect?"
  -> find_entity({'query': 'Vortex Seals', 'entity_type': 'Supplier'})
  -> change_impact({'entity_id': 'SUP-vortex-seals-gmbh'})
  -> sparql({'query': 'SELECT ?nc ?defect ?status ?target WHERE { VALUES ?nc { fx:NC-5001 ... } ... }'})
Matched "Vortex Seals" to SUP-vortex-seals-gmbh (fuzzy, score 95). Want the ERP/MES/CRM records behind it?
Vortex supplies 12 parts. 6 have no second source: those are the real risk for 8 weeks.
NC-5058 (face wear) is open on PRT-10036, a sole-sourced 45mm seal: no backup and a known defect.
HD-400, CB-50 and FX-250 are exposed...
```
Full transcript: [`data/demo_transcript.md`](data/demo_transcript.md)

**All data is synthetic** (a fictional pump maker). That is deliberate: the generator records the
true links *before* it scrambles the sources, so every answer can be scored against ground truth.

## How it fits together

```
 PLM  items + BOM  ─┐
 ERP  purchasing   ─┤  resolve.py          ontology/core.ttl        impact.py           mcp_server.py      agent.py
 MES  quality      ─┼─ entity resolution ─▶ OWL classes + RDF  ───▶ SPARQL tools  ───▶ MCP (stdio) ─────▶ Claude
 CRM  installed base┘  + provenance         graph                   (property paths)    any MCP client
```

| Source | What goes wrong in it | How `resolve.py` handles it |
|---|---|---|
| ERP | One supplier has several vendor records, typed differently: `VORTEX SEALS GMBH`, `Vortex Seals`, `Nordic Casitngs AB` | Strip legal forms, then cluster names that are **one edit apart** (Damerau-Levenshtein). A similarity ratio fails here: `castings` vs `coatings` scores 93, and they are different firms. |
| ERP | Material numbers `10023-00` vs PLM `PRT-10023` | Key normalisation |
| MES | A quarter of reports carry no part number, only shop-floor text: `MECH. SEAL 55MM CARBON/SIC` | Domain glossary (SS, CI, mech., galv.), then fuzzy match; **numbers must match exactly** (45mm is never 50mm); ambiguous matches stay unresolved |
| CRM | Product names typed by hand: `FLUXAPRO-200`, `Fluxa Pro 200`, `FluxaPro 200 pump unit` | Normalise, exact match, fuzzy fallback with the same number rule |

Every resolved link keeps its source record and match score (`fx:sourceRecord`), so the agent can
show *why* it believes two records are the same thing before anyone acts on the answer.

## Tools (MCP)

| Tool | Does |
|---|---|
| `find_entity` | Name or ID to entities, across every spelling the sources used |
| `describe` | Type, label, direct links, where-used |
| `change_impact` | From a supplier, part or assembly: parts (and which are **sole sourced**), assemblies, products, customers, installations, open quality issues. Walks the BOM with `fx:hasComponent+`. |
| `source_evidence` | The ERP, MES and CRM records behind an entity, with match method and score |
| `sparql` | Read-only SELECT/ASK for anything else |

Use it from Claude Code: `claude mcp add change-impact -- python mcp_server.py`

## Evaluation

`eval/run_eval.py` asks 108 change-impact questions (every supplier going down, plus every part with
an open quality issue or sitting deeper than one BOM level) and scores three methods that differ in
one thing each.

Held-out results, mean over 10 data seeds (21 to 30) the resolver was never tuned on. Precision / recall per question.

| Method | Supplier's parts | Products | Customers | Open quality issues |
|---|---|---|---|---|
| **Ontology + entity resolution** | **1.00 / 0.99** | **1.00 / 1.00** | **1.00 / 1.00** | **1.00 / 1.00** |
| Key joins only (IDs normalised, names exact) | 0.67 / 0.58 | 0.95 / 0.95 | 0.94 / 0.50 | 0.92 / 0.89 |
| Entity resolution, direct BOM parents only | 1.00 / 0.99 | 0.27 / 0.16 | 0.27 / 0.22 | 1.00 / 1.00 |

Two things carry the result. Entity resolution doubles customer recall: half the installed base is
invisible to a key join because CRM names products by hand. And the BOM has to be walked to the
bottom: looking only one level up finds 16% of affected products. Vendor clustering scores 1.00
pairwise precision and 0.98 recall (`eval/held_out.md`).

**How the numbers got here.** The first resolver scored 1.00 on the seed it was built on and
0.67 pairwise precision on vendor clustering on new seeds: it merged Nordic Castings with Nordic
Coatings, and split suppliers whose typo landed in the legal form ("GbmH"). Seeds 11 to 15 were
used to find and fix those; seeds 21 to 30 were never looked at while changing the resolver.

**Known failure.** When two vendor records carry *different* typos of the same name
(`Votrex Seals GmbH` and `Vortex Seal sGmbH`, seed 23), they are two edits apart and stay split. A customer
engagement would fix this with the procurement team's vendor master, not with a looser threshold,
which would start merging real competitors.

**Limits.** Synthetic data with one kind of noise per system; real landscapes are messier. The glossary
was written knowing which abbreviations the generator uses, so MES and CRM scores are an upper bound.
Product counts are small (10), which is why the supplier-level score is measured on parts.

## Run it

```
pip install -r requirements.txt
python generate_data.py          # data/ (seed 7)
python resolve.py                # data/graph.ttl + data/resolution_log.csv
python eval/run_eval.py          # eval/results.md
python eval/held_out.py          # eval/held_out.md, seeds 21-30
pytest
python agent.py "Vortex Seals is closing its Dutch plant. What is affected?"   # needs ANTHROPIC_API_KEY
```

Built with Claude Code.
