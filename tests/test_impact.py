import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from impact import ImpactGraph  # noqa: E402


@pytest.fixture(scope="module")
def g():
    return ImpactGraph()


def test_find_entity_survives_typos_and_case(g):
    assert g.find_entity("vortex seals", "Supplier")[0]["id"].startswith("SUP-vortex")
    assert g.find_entity("Nordic Castings AB", "Supplier")[0]["label"].lower().startswith("nordic cas")


def test_supplier_impact_splits_sole_sourced(g):
    sup = g.find_entity("Vortex Seals GmbH", "Supplier")[0]["id"]
    res = g.change_impact(sup)
    sole = {p["id"] for p in res["sole_sourced_parts"]}
    assert sole <= {p["id"] for p in res["parts"]}
    assert res["products"] and res["installation_count"] > 0


def test_impact_rejects_wrong_start_type(g):
    assert "error" in g.change_impact("FX-200")


def test_sparql_is_read_only(g):
    assert "error" in g.sparql("DELETE WHERE { ?s ?p ?o }")
    assert g.sparql("ASK { fx:FX-200 a fx:Product }") == {"answer": True}


def test_sparql_blocks_federation_and_non_select(g):
    blocked = g.sparql("SELECT * WHERE { service <http://example.com/sparql> { ?s ?p ?o } }")
    assert "SERVICE" in blocked["error"]  # stopped by the guard, before rdflib tries the network
    assert "error" in g.sparql("PREFIX x: <urn:x> CONSTRUCT { ?s ?p ?o } WHERE { ?s ?p ?o }")
    assert "error" in g.sparql("SELECT ?s WHERE { this is not sparql")


def test_unknown_ids_get_a_clear_error(g):
    assert "unknown entity" in g.describe("NOPE-1")["error"]
    assert "unknown entity" in g.change_impact("NOPE-1")["error"]


def test_assembly_impact_lists_its_parts_and_walks_up(g):
    asm = next(r[0] for r in g.sparql("SELECT ?a WHERE { ?p fx:hasComponent ?a . ?a a fx:Assembly }")["rows"])
    res = g.change_impact(asm)
    assert res["parts"] and all(g.describe(p["id"])["type"] == "Part" for p in res["parts"])
    assert asm not in {a["id"] for a in res["assemblies"]}
    assert res["products"]


def test_find_entity_without_type_still_prefers_one_edit_match(g):
    assert g.find_entity("Nordic Castings AB")[0]["label"].lower().startswith("nordic cas")
