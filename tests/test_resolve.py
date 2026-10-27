import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from resolve import best_match, cluster_vendors, norm_desc, norm_vendor  # noqa: E402
from rapidfuzz import fuzz  # noqa: E402


def test_legal_forms_and_case_collapse():
    assert norm_vendor("VORTEX SEALS GMBH") == norm_vendor("Vortex Seals") == norm_vendor("Vortex Seals GbmH")
    assert norm_vendor("Silesia Steel Sp. z o.o.") == "silesiasteel"


def test_typo_joins_but_different_word_does_not():
    c = cluster_vendors({"V1": "Nordic Castings AB", "V2": "Nordic Casitngs AB", "V3": "Nordic Coatings AB"}, "full")
    assert c["V1"] == c["V2"] != c["V3"]


def test_numbers_are_never_fuzzy():
    cands = [("A", norm_desc("O-ring 45mm NBR")), ("B", norm_desc("O-ring 60mm NBR"))]
    assert best_match(norm_desc("o-ring 45 mm nbr"), cands, fuzz.token_sort_ratio, 85)[0] == "A"
    assert best_match(norm_desc("o-ring 50 mm nbr"), cands, fuzz.token_sort_ratio, 85)[0] is None


def test_ambiguous_description_is_left_unresolved():
    cands = [("A", "impeller 150mm bronze"), ("B", "impeller 150mm bronze")]
    key, reason = best_match("impeller 150mm bronze", cands, fuzz.token_sort_ratio, 85)
    assert key is None and reason.startswith("ambiguous")


def test_glossary_expands_shop_floor_abbreviations():
    assert norm_desc("MECH. SEAL 45 MM SIC/SIC") == "mechanical seal 45mm sic/sic"
    assert norm_desc("Volute DN80 CI") == "volute casing dn80 cast iron"


def test_part_key_handles_every_format_and_garbage():
    from resolve import part_key
    assert part_key("PRT-10023") == part_key("prt10023") == part_key("10023-00") == "PRT-10023"
    assert part_key("see drawing") is None
