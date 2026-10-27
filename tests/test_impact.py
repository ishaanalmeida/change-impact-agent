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
