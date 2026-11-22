"""Shared foundations in the profile: value classes, shared slots,
modality, stated_goal, and the OWL entity types gen-owl is told to emit."""

import copy
from pathlib import Path

import pytest
from rdflib import Graph
from rdflib.namespace import OWL, RDF, RDFS

from conftest import EXAMPLES, ROOT, load_yaml

GROUP_CLASSES = ("CausalStatement", "InteractionStatement")
SHARED = ("modality", "context", "ecosystem_context", "place", "temporal_extent", "specified_in")


@pytest.mark.parametrize("cls", ["EcoStatement", *GROUP_CLASSES, "SynthesisAssessment"])
@pytest.mark.parametrize("slot", SHARED)
def test_shared_slots_on_every_statement_class(schemaview, cls, slot):
    assert slot in schemaview.class_induced_slots(cls) or slot in {s.name for s in schemaview.class_induced_slots(cls)}


def test_shared_slots_are_top_level(schemaview):
    for slot in SHARED:
        assert slot in schemaview.schema.slots, slot


def test_place_and_ecosystem_context_are_different_axes(schemaview):
    place = schemaview.induced_slot("place", "CausalStatement")
    eco = schemaview.induced_slot("ecosystem_context", "CausalStatement")
    assert place.range == "uriorcurie" and place.multivalued
    assert eco.range == "EcosystemFunctionalGroupEnum"


def test_modality_values(schemaview):
    assert set(schemaview.get_enum("ModalityEnum").permissible_values) == {"observed", "inferred", "anticipated"}


def test_stated_goal_only_on_study_results(schemaview):
    assert "stated_goal" in {s.name for s in schemaview.class_induced_slots("EcoStudyResult")}
    for cls in ("CausalStatement", "CausalNode", "NodeDefinition"):
        assert "stated_goal" not in {s.name for s in schemaview.class_induced_slots(cls)}


@pytest.mark.parametrize("cls", ["Quantity", "QuantityRange", "ScaledValue", "CurvePoint", "Count", "Period"])
def test_value_classes_exist(schemaview, cls):
    assert schemaview.get_class(cls) is not None


def test_causal_statement_still_validates_with_promoted_slots(validator):
    data = load_yaml(EXAMPLES / "kramer1995_statements.yaml")
    s = data["causal_statements"][0]
    assert s["context"] and s["ecosystem_context"] and s["temporal_extent"]
    assert not validator.validate(data, "StatementSet").results


def test_new_shared_slots_validate(validator):
    data = copy.deepcopy(load_yaml(EXAMPLES / "bloodroot_statements.yaml"))
    s = data["causal_statements"][0]
    s["modality"] = "observed"
    s["place"] = ["ISO3166-2:CA-ON"]
    s["specified_in"] = ["warp:doc/murphy2005"]
    assert not validator.validate(data, "StatementSet").results
    s["modality"] = "predicted"
    assert validator.validate(data, "StatementSet").results


def test_quantity_range_needs_an_end(validator):
    data = copy.deepcopy(load_yaml(EXAMPLES / "bloodroot_statements.yaml"))
    # QuantityRange is not yet used by a group; validate it as its own target.
    assert not validator.validate({"min": 5.5, "unit": "TODO:unit_pH"}, "QuantityRange").results
    assert validator.validate({"unit": "TODO:unit_pH"}, "QuantityRange").results
    assert data   # the example itself is untouched


def test_curve_point_suitability_bounded(validator):
    assert not validator.validate({"x": 1.0, "suitability": 0.5}, "CurvePoint").results
    assert validator.validate({"x": 1.0, "suitability": 1.5}, "CurvePoint").results


def test_period_pattern(validator):
    assert not validator.validate({"start": "2024-05", "end": "2026-03-31"}, "Period").results
    assert validator.validate({"start": "May 2024"}, "Period").results


# --- OWL entity types (R13, R14; checked on the generated schema OWL) ---------

OWL_FILE = ROOT / "project" / "warp.owl.ttl"


@pytest.fixture(scope="module")
def owl_graph():
    if not OWL_FILE.exists():
        pytest.fail("project/warp.owl.ttl is missing: run make gen")
    return Graph().parse(OWL_FILE)


def predicate_iris(schemaview):
    """IRIs of every value of every registered group's predicate enum."""
    import derive_propositions as dp
    iris = set()
    for g in dp.load_groups(Path(schemaview.schema.source_file)):
        enum = schemaview.get_enum(schemaview.induced_slot("predicate", g["statement_class"]).range)
        for pv in enum.permissible_values.values():
            if pv.meaning:
                iris.add(schemaview.expand_curie(pv.meaning))
    return iris


def test_no_predicate_iri_is_an_owl_class(owl_graph, schemaview):
    from rdflib import URIRef
    iris = predicate_iris(schemaview)
    assert iris
    classes = [i for i in iris if (URIRef(i), RDF.type, OWL.Class) in owl_graph]
    assert not classes, f"predicate IRIs emitted as owl:Class: {sorted(classes)}"
    enum_classes = {URIRef(schemaview.get_uri(e, expand=True)) for e in schemaview.all_enums().values()}
    enum_classes |= {o for o in owl_graph.objects(None, RDFS.subClassOf) if str(o).endswith("PredicateEnum")}
    subclassed = [i for i in iris
                  if any(o in enum_classes for o in owl_graph.objects(URIRef(i), RDFS.subClassOf))]
    assert not subclassed, f"predicate IRIs subclassing their enum: {sorted(subclassed)}"


def test_profile_predicate_enums_are_object_properties(owl_graph):
    from rdflib import URIRef
    for curie in ("RO_0002437", "RO_0002470", "RO_0002455", "RO_0002444"):
        iri = URIRef("http://purl.obolibrary.org/obo/" + curie)
        assert (iri, RDF.type, OWL.ObjectProperty) in owl_graph


def test_enum_values_are_individuals(owl_graph):
    from rdflib import URIRef
    v = URIRef("https://w3id.org/ecoweaver/warp/SemanticUnitScopeEnum#assertional")
    assert (v, RDF.type, OWL.NamedIndividual) in owl_graph
    assert (v, RDF.type, OWL.Class) not in owl_graph
