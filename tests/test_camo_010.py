"""The CAMO 0.10.0 dependency works through WARP's annotation pipeline.

All quantities below are synthetic test data, not claims about the papers.
"""

import copy
import hashlib

import pytest
from rdflib import Literal, Namespace, URIRef
from rdflib.namespace import RDF, XSD

import derive_propositions as dp
import export_rdf
import render_statements as rs
from conftest import EXAMPLES, ROOT, SCHEMA, load_yaml


@pytest.fixture
def annotated():
    data = load_yaml(EXAMPLES / "kramer1995_statements.yaml")
    st = data["causal_statements"][0]
    st["dose"] = {"numeric_value": 9, "unit_text": "ramets/m2",
                  "verbatim": "9 ramets/m2",
                  "counted_entity": {"entity_term": "test plants", "entity_type": "taxon",
                                     "life_stage": "ramet_or_clonal_unit",
                                     "life_stage_term": "test ramets"}}
    st["dose_level"] = "high"
    st["comparator"] = [{"comparator_type": "alternative_dose_level",
                         "comparator_dose": {"minimum_value": 1, "maximum_value": 3,
                                             "unit_text": "ramets/m2"},
                         "comparator_dose_level": "low"}]
    st["temporal_extent"] = {"observation_seasons": ["late_spring"],
                             "time_since_intervention_months": 12,
                             "time_since_intervention_text": "the following spring"}
    st["predicate_qualifiers"]["effect_strength"].update(
        effect_metric="percent_change", interval_lower=5, interval_upper=15,
        interval_level=0.95, interval_type="confidence", dose_response_shape="monotonic",
        significance="significant", p_value=0.02, alpha=0.05, analysis_method="mixed_model")
    return data


def test_vendored_camo_is_exact_release_blob():
    path = ROOT / "src/warp/schema/upstream/causalmosaic.yaml"
    # Git may check files out with CRLF; compare the upstream LF blob.
    blob = path.read_bytes().replace(b"\r\n", b"\n")
    assert hashlib.sha256(blob).hexdigest() == "6a2261c6a6c16f1582a6049ba3f6e67c5a231dcb2284a7e18deec3f50595864f"
    assert load_yaml(path)["version"] == "0.10.0"


def test_new_causal_fields_validate_and_render(annotated, validator):
    assert not validator.validate(annotated, "StatementSet").results
    r = rs.Renderer()
    r.add_files([annotated])
    result = r.render_statement(annotated["causal_statements"][0], "CausalStatement")
    assert not result["missing"]
    for text in ("9 ramets/m2", "high driver level", "minimum 1 maximum 3",
                 "low driver level", "late spring", "12 months after intervention",
                 "the following spring", "interval lower bound 5", "interval upper bound 15",
                 "interval level 0.95", "interval type confidence", "p-value 0.02",
                 "significance threshold 0.05", "mixed effect model", "test ramets"):
        assert text in result["sentence"]
    assert result["aside"]["dose.verbatim"] == ("quoted", "9 ramets/m2")


def test_new_conditions_preserve_proposition_identity(annotated):
    before = load_yaml(EXAMPLES / "kramer1995_statements.yaml")
    dp.derive_all(before, SCHEMA)
    dp.derive_all(annotated, SCHEMA)
    assert annotated["causal_statements"][0]["proposition"] == before["causal_statements"][0]["proposition"]
    first = copy.deepcopy(annotated)
    dp.derive_all(annotated, SCHEMA)
    assert annotated == first


def test_new_values_survive_rdf_export(annotated, schemaview):
    graph, _ = export_rdf.export(schemaview, [annotated])
    camo = Namespace("https://w3id.org/camo/")
    mosaic = Namespace("https://w3id.org/causal-mosaic/")
    sid = URIRef("https://w3id.org/ecoweaver/warp/statement/kramer1995-c1")
    dose = URIRef(f"{sid}/dose")
    assert (sid, camo.dose, dose) in graph
    assert (dose, RDF.type, mosaic.QuantityValue) in graph
    assert (URIRef(f"{sid}/predicate_qualifiers/effect_strength"), camo.p_value,
            Literal(0.02, datatype=XSD.float)) in graph


@pytest.mark.parametrize("field,value", [
    ("dose", {"verbatim": "heavy"}),
    ("dose_level", "heavy"),
    ("temporal_extent", {"observation_seasons": ["May-October"]}),
    ("predicate_qualifiers", {"effect_strength": {"interval_level": 95}}),
])
def test_invalid_new_values_are_rejected(annotated, validator, field, value):
    annotated["causal_statements"][0][field] = value
    assert validator.validate(annotated, "StatementSet").results


def test_composition_and_life_stage_are_available_on_nodes(validator):
    node = {"id": "node:test-assemblage", "name": "Test assemblage",
            "entity_type": "composite_variable", "entity_term": "test assemblage",
            "life_stage": "mixed_or_whole_population",
            "spatial_grain": {"numeric_value": 1, "unit_text": "test sampling unit"},
            "composition": {"basis": "relative_abundance", "members": [
                {"entity_type": "taxon", "entity_term": "test taxon", "rank": 1}]}}
    assert not validator.validate(node, "CausalNode").results
    node["entity_type"] = "taxon"
    assert validator.validate(node, "CausalNode").results
    node["entity_type"] = "composite_variable"
    del node["composition"]["members"][0]["rank"]
    assert validator.validate(node, "CausalNode").results


def test_scope_is_compatible_without_replacing_warp_identity(schemaview):
    assert set(schemaview.get_enum("ScopeEnum").permissible_values) == set(
        schemaview.get_enum("SemanticUnitScopeEnum").permissible_values)
    assert schemaview.induced_slot("scope", "CausalStatement").range == "SemanticUnitScopeEnum"


def test_kramer_keeps_calendar_window_without_guessing_seasons():
    temporal = load_yaml(EXAMPLES / "kramer1995_statements.yaml")["causal_statements"][0]["temporal_extent"]
    assert "May-October 1992" in temporal["duration_text"]
    assert "observation_seasons" not in temporal
