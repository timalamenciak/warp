"""The recommendation group (proposals section 5)."""

import copy

import pytest
from rdflib import Graph, Namespace, URIRef
from rdflib.namespace import OWL, RDF, RDFS

import derive_propositions as dp
import export_rdf
import project_owl
import report_guidance
from conftest import EXAMPLES, ROOT, SCHEMA, load_yaml

WARP = Namespace("https://w3id.org/ecoweaver/warp/")
NODE = Namespace("https://w3id.org/causal-mosaic/node/")
RELATIONS = ROOT / "src" / "warp" / "owl" / "warp-relations.ttl"
SUBPROPERTY = {"do": WARP.recommended_to_achieve, "avoid": WARP.advised_against_for,
               "consider": WARP.suggested_for_consideration}


@pytest.fixture(scope="module")
def derived():
    return load_yaml(EXAMPLES / "recommendation_statements.derived.yaml")


def props_by_statements(data):
    return {tuple(sorted(p["derived_from_statements"])): p for p in data["recommendation_propositions"]}


def test_group_is_registered_with_guidance_in_the_key():
    g = {x["group"]: x for x in dp.load_groups(SCHEMA)}["recommendation"]
    assert g["extras"] == ["predicate_qualifiers.guidance"]
    assert g["statements_slot"] == "recommendation_statements"


def test_do_and_avoid_are_two_propositions(derived):
    by = props_by_statements(derived)
    do = by[("stmt:burn-do-plan", "stmt:burn-do-practitioner")]
    avoid = by[("stmt:burn-avoid-agency",)]
    assert do["id"] != avoid["id"]
    assert do["predicate_qualifiers"] == {"guidance": "do"}
    assert avoid["predicate_qualifiers"] == {"guidance": "avoid"}
    assert do["subject"] == avoid["subject"] and do["object"] == avoid["object"]


def test_same_guidance_from_two_claimants_is_one_proposition(derived):
    by = props_by_statements(derived)
    assert ("stmt:burn-do-plan", "stmt:burn-do-practitioner") in by


def test_both_sides_cite_the_same_causal_proposition(derived):
    recs = {s["id"]: s for s in derived["recommendation_statements"]}
    assert recs["stmt:burn-do-plan"]["justified_by"] == recs["stmt:burn-avoid-agency"]["justified_by"]
    cited = recs["stmt:burn-do-plan"]["justified_by"][0]
    assert cited in {p["id"] for p in derived["causal_propositions"]}


def test_predictions_are_causal_statements_not_derived_from_guidance(derived):
    causal = {s["id"]: s for s in derived["causal_statements"]}
    assert causal["stmt:ms-11-causal"]["modality"] == "anticipated"
    assert causal["stmt:ms-11-causal"]["hasEvidenceLines"][0]["evidence_type"] == "expert_judgment"
    assert causal["stmt:ms-09-causal"]["hasEvidenceLines"][0]["evidence_type"] == "not_stated"
    # derivation never adds causal statements
    source = load_yaml(EXAMPLES / "recommendation_statements.yaml")
    assert len(source["causal_statements"]) == len(derived["causal_statements"])


def test_road_salt_is_an_open_question(derived):
    q = {p["id"]: p for p in derived["causal_propositions"]}["prop:question-road-salt-spring-salamander"]
    assert q["status"] == "open_question" and q["derived_from_statements"] == []


def test_missing_guidance_fails_validation(validator):
    data = copy.deepcopy(load_yaml(EXAMPLES / "recommendation_statements.yaml"))
    data["recommendation_statements"][0]["predicate_qualifiers"].pop("guidance")
    assert validator.validate(data, "StatementSet").results


# --- RDF ------------------------------------------------------------------------------

@pytest.fixture(scope="module")
def graph(schemaview, derived):
    g, _ = export_rdf.export(schemaview, [derived])
    return g


def test_relation_triples_use_the_sub_property(graph):
    burn, shrub = NODE.prescribed_burning_of_grassland, NODE.decrease_in_shrub_cover_in_grassland
    assert (burn, WARP.recommended_to_achieve, shrub) in graph
    assert (burn, WARP.advised_against_for, shrub) in graph
    assert not list(graph.triples((None, WARP.suggested_to, None)))


def test_records_name_the_sub_property_too(graph):
    stmt = URIRef("https://w3id.org/ecoweaver/warp/statement/ms-11-rec")
    assert graph.value(stmt, WARP.predicate) == WARP.advised_against_for
    for p in graph.subjects(RDF.type, WARP.RecommendationProposition):
        assert graph.value(p, WARP.predicate) in SUBPROPERTY.values()


def test_relations_file_declares_the_group():
    r = Graph().parse(RELATIONS)
    assert (WARP.suggested_to, RDF.type, OWL.ObjectProperty) in r
    assert (WARP.suggested_to, WARP.abstract_predicate, None) in r
    for value, sub in SUBPROPERTY.items():
        assert (sub, RDFS.subPropertyOf, WARP.suggested_to) in r
        assert (sub, WARP.selected_by, URIRef(f"{WARP}GuidanceEnum#{value}")) in r


def test_schema_and_relations_agree_on_sub_properties(schemaview):
    import warp_schema as ws
    for value, pv in schemaview.get_enum("GuidanceEnum").permissible_values.items():
        assert schemaview.expand_curie(ws.annotation(pv, "warp_subproperty")) == str(SUBPROPERTY[value])


# --- OWL: nothing, at any scope ------------------------------------------------------

def test_recommendations_never_project(schemaview):
    data = copy.deepcopy(load_yaml(EXAMPLES / "recommendation_statements.yaml"))
    for s in data["recommendation_statements"]:
        s["scope"], s["modality"] = "universal", "observed"
    dp.derive_all(data, SCHEMA)
    assessments = {"assessments": [{"id": f"warp:assessment/x{i}", "type": "SynthesisAssessment",
                                    "proposition": p["id"], "direction": "supports", "strength": "high"}
                                   for i, p in enumerate(data["recommendation_propositions"])]}
    g, report = project_owl.Projector(schemaview).run([data, assessments])
    assert report["no_projection"]["recommendation"]
    assert not [p for grp, p, n in report["passed"] if grp == "recommendation"]
    assert not list(g.triples((None, RDFS.subClassOf, None)))


# --- the guidance report ------------------------------------------------------------

def test_guidance_report_findings(derived):
    rows = {r["statement"]: r for r in report_guidance.findings(report_guidance.Index([derived]))}
    assert rows["stmt:burn-do-practitioner"]["findings"] == "unsupported"
    assert rows["stmt:ms-11-rec"]["findings"] == "self-supporting"
    assert rows["stmt:ms-09-rec"]["findings"] == "self-supporting"
    assert rows["stmt:burn-do-plan"]["findings"] == ""
    assert rows["stmt:burn-do-plan"]["weakest_certainty"] == "moderate"


def test_guidance_is_not_self_supporting_when_another_claimant_backs_it(derived):
    data = copy.deepcopy(derived)
    causal = next(s for s in data["causal_statements"] if s["id"] == "stmt:ms-11-causal")
    causal["contributions"][0]["contributor"] = "org:eccc"
    rows = {r["statement"]: r for r in report_guidance.findings(report_guidance.Index([data]))}
    assert rows["stmt:ms-11-rec"]["findings"] == ""
