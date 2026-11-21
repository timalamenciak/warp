"""The tolerance group (Phase 5; proposals section 7)."""

import copy
import subprocess
import sys

import pytest
import yaml
from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.namespace import OWL, RDF, RDFS

import check_tolerance
import derive_propositions as dp
import derive_strategies as ds
import export_rdf
import project_owl
import report_tolerance
from conftest import EXAMPLES, ROOT, SCHEMA, SCRIPTS, load_yaml

WARP = Namespace("https://w3id.org/ecoweaver/warp/")
NODE = Namespace("https://w3id.org/causal-mosaic/node/")
RO = Namespace("http://purl.obolibrary.org/obo/RO_")


@pytest.fixture(scope="module")
def derived():
    return load_yaml(EXAMPLES / "tolerance_statements.derived.yaml")


def prop_of(data, sid):
    return next(p for p in data["tolerance_propositions"] if sid in p["derived_from_statements"])


def test_group_has_place_in_the_key():
    g = {x["group"]: x for x in dp.load_groups(SCHEMA)}["tolerance"]
    assert g["extras"] == ["place"]


def test_different_ranges_from_three_sources_are_one_proposition(derived):
    p = prop_of(derived, "stmt:usda-bogr-ph")
    assert sorted(p["derived_from_statements"]) == ["stmt:flora-bogr-ph", "stmt:trial-bogr-ph", "stmt:usda-bogr-ph"]
    assert "predicate_qualifiers" not in p      # ranges are not in the key, nor on the proposition
    assert p["place"] == ["place:northern-great-plains"]


def test_two_regions_are_two_propositions(derived):
    a = prop_of(derived, "stmt:nwpl-spartina-great-plains")
    b = prop_of(derived, "stmt:nwpl-spartina-midwest")
    assert a["id"] != b["id"]
    assert a["subject"] == b["subject"] and a["object"] == b["object"] and a["predicate"] == b["predicate"]


def test_tolerates_and_intolerant_of_are_never_derived_from_each_other(derived):
    source = load_yaml(EXAMPLES / "tolerance_statements.yaml")
    assert len(source["tolerance_statements"]) == len(derived["tolerance_statements"])
    preds = {(p["subject"], p["predicate"], p["object"]) for p in derived["tolerance_propositions"]}
    assert ("node:bouteloua_gracilis", "tolerates", "node:wetness_of_soil") not in preds


def test_explained_by_resolves_to_the_causal_proposition(derived):
    s = next(x for x in derived["tolerance_statements"] if x["id"] == "stmt:flora-bogr-saturation")
    causal = {p["id"] for p in derived["causal_propositions"]}
    assert s["explained_by"][0] in causal


# --- checks ---------------------------------------------------------------------------

def test_examples_pass_check_tolerance(derived):
    assert check_tolerance.check([derived]) == []


def test_has_habitat_needs_a_habitat_node(derived):
    data = copy.deepcopy(derived)
    s = next(x for x in data["tolerance_statements"] if x["id"] == "stmt:flora-spartina-habitat")
    s["object"] = "node:wetness_of_soil"
    errs = check_tolerance.check([data])
    assert len(errs) == 1 and "has_habitat needs a habitat" in errs[0]


def test_other_predicates_need_a_quality_node(derived):
    data = copy.deepcopy(derived)
    s = next(x for x in data["tolerance_statements"] if x["id"] == "stmt:usda-bogr-ph")
    s["object"] = "node:wet_meadow"
    assert any("needs a quality_of_environmental_material" in e for e in check_tolerance.check([data]))


def test_object_without_definition_is_an_error(derived):
    data = copy.deepcopy(derived)
    s = next(x for x in data["tolerance_statements"] if x["id"] == "stmt:usda-bogr-ph")
    s["object"] = "node:root_anoxia_of_bouteloua_gracilis"
    assert any("no node definition" in e for e in check_tolerance.check([data]))


def test_curve_x_must_increase(derived):
    data = copy.deepcopy(derived)
    s = next(x for x in data["tolerance_statements"] if x["id"] == "stmt:hsi-y-temperature")
    s["predicate_qualifiers"]["response_curve"][2]["x"] = 12
    assert any("strictly increasing" in e for e in check_tolerance.check([data]))


def test_suitability_is_bounded_by_the_schema(validator):
    data = load_yaml(EXAMPLES / "tolerance_statements.yaml")
    s = next(x for x in data["tolerance_statements"] if x["id"] == "stmt:hsi-y-temperature")
    s["predicate_qualifiers"]["response_curve"][1]["suitability"] = 1.2
    assert validator.validate(data, "StatementSet").results


def test_registered_scale_needs_its_concept(schemaview):
    from check_values import ValueChecker
    data = load_yaml(EXAMPLES / "tolerance_statements.yaml")
    s = next(x for x in data["tolerance_statements"] if x["id"] == "stmt:eive-taxon-r")
    s["predicate_qualifiers"]["class_value"].pop("concept")
    c = ValueChecker(schemaview)
    c.check_set("t", data)
    assert any("concept is required" in e for e in c.errors)


# --- the node template ----------------------------------------------------------------

@pytest.fixture(scope="module")
def nodes_graph(tmp_path_factory, derived):
    d = tmp_path_factory.mktemp("tol")
    src = d / "t.yaml"
    src.write_text(yaml.safe_dump(derived), encoding="utf-8")
    out = d / "nodes.ttl"
    subprocess.run([sys.executable, str(SCRIPTS / "expand_nodes.py"), str(ROOT / "templates" / "node_templates.yaml"),
                    str(src), "--owl", str(out)], check=True, capture_output=True)
    return Graph().parse(out)


def test_quality_of_material_is_an_equivalent_class(nodes_graph):
    assert nodes_graph.value(NODE.temperature_of_water, OWL.equivalentClass) is not None
    assert str(nodes_graph.value(NODE.temperature_of_water, RDFS.label)) == "temperature of liquid water"


def test_depth_refinement_makes_a_subclass_not_an_equivalent(nodes_graph):
    refined = NODE.ph_of_soil_0_15cm
    assert nodes_graph.value(refined, OWL.equivalentClass) is None
    assert any(isinstance(o, type(nodes_graph.value(NODE.ph_of_soil, OWL.equivalentClass)))
               for o in nodes_graph.objects(refined, RDFS.subClassOf))
    assert "depth 0 to 15" in str(nodes_graph.value(refined, RDFS.label))


def test_refinement_on_a_template_without_it_is_refused(tmp_path, derived):
    data = copy.deepcopy(derived)
    defn = next(d for d in data["node_definitions"] if d["node"] == "node:wet_meadow")
    defn["season"] = "spring"
    src = tmp_path / "t.yaml"
    src.write_text(yaml.safe_dump(data), encoding="utf-8")
    r = subprocess.run([sys.executable, str(SCRIPTS / "expand_nodes.py"), str(ROOT / "templates" / "node_templates.yaml"),
                        str(src)], capture_output=True, text=True)
    assert r.returncode != 0 and "no refinement" in r.stderr


# --- RDF and OWL -----------------------------------------------------------------------

def test_export_puts_ranges_on_the_qualifier_individual(schemaview, derived):
    g, _ = export_rdf.export(schemaview, [derived])
    s = URIRef("https://w3id.org/ecoweaver/warp/statement/usda-bogr-ph")
    q = g.value(s, WARP.predicate_qualifiers)
    r = g.value(q, WARP.range)
    assert g.value(r, WARP.min) == Literal(6.0, datatype=URIRef("http://www.w3.org/2001/XMLSchema#float"))
    assert (NODE.spartina_pectinata, RO["0002303"], NODE.wet_meadow) in g
    assert (NODE.bouteloua_gracilis, WARP.tolerates, NODE.ph_of_soil_0_15cm) in g
    curve = list(g.objects(g.value(URIRef("https://w3id.org/ecoweaver/warp/statement/hsi-y-temperature"),
                                   WARP.predicate_qualifiers), WARP.response_curve))
    assert len(curve) == 4


def universal_assessed(derived, sid):
    data = copy.deepcopy(load_yaml(EXAMPLES / "tolerance_statements.yaml"))
    for s in data["tolerance_statements"]:
        s["scope"], s["modality"] = "universal", "observed"
    dp.derive_all(data, SCHEMA)
    pid = prop_of(data, sid)["id"]
    return data, {"assessments": [{"id": "warp:assessment/t", "type": "SynthesisAssessment",
                                   "proposition": pid, "direction": "supports", "strength": "high"}]}


def test_only_has_habitat_projects(schemaview, derived):
    data, a = universal_assessed(derived, "stmt:flora-spartina-habitat")
    g, report = project_owl.Projector(schemaview).run([data, a])
    r = g.value(NODE.spartina_pectinata, RDFS.subClassOf)
    assert (r, OWL.onProperty, RO["0002303"]) in g and (r, OWL.someValuesFrom, NODE.wet_meadow) in g


def test_ranges_never_project_even_through_the_gate(schemaview, derived):
    data, a = universal_assessed(derived, "stmt:usda-bogr-ph")
    g, report = project_owl.Projector(schemaview).run([data, a])
    assert report["no_projection"]["tolerance"]
    assert not list(g.triples((None, RDFS.subClassOf, None)))


def test_prototypical_habitat_does_not_project(schemaview, derived):
    pid = prop_of(derived, "stmt:flora-spartina-habitat")["id"]
    a = {"assessments": [{"id": "warp:assessment/t", "type": "SynthesisAssessment",
                          "proposition": pid, "direction": "supports", "strength": "high"}]}
    _, report = project_owl.Projector(schemaview).run([derived, a])
    assert not report["passed"]


# --- the report -----------------------------------------------------------------------

def test_report_flags_non_overlap_and_unscaled_values(derived):
    results, _ = report_tolerance.analyse([derived])
    by_id = {r["proposition"]["id"]: r for r in results}
    ph = by_id[prop_of(derived, "stmt:usda-bogr-ph")["id"]]
    assert any("non-overlapping" in f and "trial-bogr-ph" in f for f in ph["flags"])
    assert not any("usda-bogr-ph` (" in f and "flora-bogr-ph` (" in f for f in ph["flags"])  # those overlap
    wet = by_id[prop_of(derived, "stmt:practitioner-spartina-wet")["id"]]
    assert any("on no scale" in f for f in wet["flags"])


def test_report_flags_unit_mismatch_and_never_converts(derived):
    data = copy.deepcopy(derived)
    s = next(x for x in data["tolerance_statements"] if x["id"] == "stmt:flora-bogr-ph")
    s["predicate_qualifiers"]["range"]["unit"] = "TODO:unit_other"
    results, _ = report_tolerance.analyse([data])
    flags = [f for r in results for f in r["flags"]]
    assert any("unit mismatch" in f for f in flags)
