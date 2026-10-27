"""Questions the agent can ask of the graph. Every answer is a SPARQL query over the ontology."""
from rapidfuzz import fuzz, process, utils
from rapidfuzz.distance import OSA
from rdflib import RDF, RDFS, URIRef
from rdflib.namespace import SKOS

from resolve import FX, build, norm_vendor

PREFIX = "PREFIX fx: <https://example.org/fluxa/>\nPREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>\n"
TYPES = ["Product", "Assembly", "Part", "Supplier", "Customer", "Installation", "QualityIssue"]


def _id(uri):
    return str(uri).split("/")[-1]


class ImpactGraph:
    def __init__(self, mode="full", bom_depth="all"):
        self.g, self.log = build(mode)
        self.mode = mode
        # "all" follows the BOM through every level; "one" only looks at direct parents (ablation)
        self.path = "fx:hasComponent+" if bom_depth == "all" else "fx:hasComponent"

    def _rows(self, query, **bind):
        return list(self.g.query(PREFIX + query, initBindings={k: FX[v] for k, v in bind.items()}))

    def _type(self, uri):
        return next((_id(t) for t in self.g.objects(uri, RDF.type) if _id(t) in TYPES), None)

    def _named(self, uris):
        return sorted(({"id": _id(u), "label": str(self.g.value(u, RDFS.label) or _id(u))} for u in set(uris)),
                      key=lambda d: d["id"])

    def find_entity(self, query, entity_type=None, limit=5):
        """Match a free-text name or ID to graph entities, across every spelling the sources used."""
        names = {}
        for s, p, o in self.g.triples((None, None, None)):
            if p in (RDFS.label, SKOS.altLabel) and isinstance(s, URIRef):
                if entity_type and self._type(s) != entity_type:
                    continue
                names[f"{_id(s)}|{o}"] = str(o)
                names[f"{_id(s)}|{_id(s)}"] = _id(s)
        if self.mode == "keys":  # baseline: exact text only
            hits = [(k, 100) for k, v in names.items() if v.lower() == query.lower()]
        else:
            hits = [(k, s) for _, s, k in process.extract(query, names, scorer=fuzz.WRatio,
                                                          processor=utils.default_process, limit=limit * 4)]
            # one edit away from the query beats a high fuzzy score: "Castings" must find "Castigns", not "Coatings"
            norm = norm_vendor if entity_type == "Supplier" else (lambda s: utils.default_process(s).replace(" ", ""))
            q = norm(query)
            hits.sort(key=lambda h: (OSA.distance(q, norm(names[h[0]])) > 1, -h[1]))
        out, seen = [], set()
        for key, score in hits:
            eid = key.split("|")[0]
            if eid not in seen:
                seen.add(eid)
                out.append({"id": eid, "type": self._type(FX[eid]), "label": str(self.g.value(FX[eid], RDFS.label)),
                            "score": round(score)})
        return out[:limit]

    def describe(self, entity_id):
        """Type, label and direct neighbours of one entity."""
        e = FX[entity_id]
        out = {"id": entity_id, "type": self._type(e), "label": str(self.g.value(e, RDFS.label) or "")}
        for p, o in self.g.predicate_objects(e):
            name = _id(p)
            if name in ("hasComponent", "suppliedBy", "ofProduct", "ownedBy", "concerns", "status", "defect"):
                out.setdefault(name, []).append(_id(o) if isinstance(o, URIRef) else str(o))
        used_in = [_id(s) for s in self.g.subjects(FX.hasComponent, e)]
        if used_in:
            out["usedIn"] = sorted(used_in)
        return out

    def change_impact(self, entity_id):
        """Everything downstream of a change to a supplier, part or assembly."""
        kind = self._type(FX[entity_id])
        if kind == "Supplier":
            parts = [r.part for r in self._rows("SELECT ?part WHERE { ?part fx:suppliedBy ?s }", s=entity_id)]
            sole = [r.part for r in self._rows(
                "SELECT ?part WHERE { ?part fx:suppliedBy ?s . FILTER NOT EXISTS { ?part fx:suppliedBy ?o . FILTER(?o != ?s) } }",
                s=entity_id)]
        elif kind in ("Part", "Assembly"):
            parts, sole = [FX[entity_id]], []
        else:
            return {"error": f"{entity_id} is a {kind}; change impact starts from a Supplier, Part or Assembly"}

        products, assemblies, installs, customers, issues = set(), set(), set(), set(), set()
        for part in parts:
            for r in self._rows(f"SELECT ?up WHERE {{ ?up {self.path} ?x }}", x=_id(part)):
                (products if (r.up, RDF.type, FX.Product) in self.g else assemblies).add(r.up)
            for r in self._rows("SELECT ?qi WHERE { ?qi fx:concerns ?x ; fx:status 'open' }", x=_id(part)):
                issues.add(r.qi)
        for prod in products:
            for r in self._rows("SELECT ?i ?c WHERE { ?i fx:ofProduct ?p ; fx:ownedBy ?c }", p=_id(prod)):
                installs.add(r.i)
                customers.add(r.c)
        result = {"changed": {"id": entity_id, "type": kind, "label": str(self.g.value(FX[entity_id], RDFS.label))},
                  "parts": self._named(parts), "assemblies": self._named(assemblies), "products": self._named(products),
                  "customers": self._named(customers), "installation_count": len(installs),
                  "open_quality_issues": self._named(issues)}
        if kind == "Supplier":
            result["sole_sourced_parts"] = self._named(sole)
        return result

    def source_evidence(self, entity_id):
        """The source-system records that were resolved onto this entity, and how each match was made."""
        return sorted(str(o) for o in self.g.objects(FX[entity_id], FX.sourceRecord))

    def sparql(self, query, limit=50):
        """Run a read-only SPARQL SELECT. Prefixes fx: and rdfs: are predefined."""
        if not query.lstrip().upper().startswith(("SELECT", "ASK", "PREFIX")):
            return {"error": "only SELECT or ASK queries are allowed"}
        res = self.g.query(PREFIX + query)  # rdflib's query() cannot run SPARQL Update
        if res.type == "ASK":
            return {"answer": bool(res.askAnswer)}
        cols = [str(v) for v in res.vars]
        return {"columns": cols, "rows": [[_id(x) if isinstance(x, URIRef) else (None if x is None else str(x)) for x in row]
                                          for row in list(res)[:limit]]}
