"""Scale vocabularies (vocab/scales.yaml -> project/scales.ttl, decision D18)."""

import pytest
from rdflib import Graph, Namespace
from rdflib.namespace import RDF, SKOS

import gen_vocab
from conftest import ROOT

WARP = Namespace("https://w3id.org/ecoweaver/warp/")
SCALES = ROOT / "vocab" / "scales.yaml"
NAMED_BY_PROPOSALS = {
    "dfo-recovery-priority", "dfo-timing-of-influence", "eive-1.0-reaction",
    "usda-texture-class", "usda-tolerance-rating", "wetland-indicator-status",
}


@pytest.fixture(scope="module")
def graph():
    return gen_vocab.build_graph(gen_vocab.load_scales(SCALES))


def test_proposal_scales_are_registered():
    ids = {s["id"] for s in gen_vocab.load_scales(SCALES)}
    assert NAMED_BY_PROPOSALS <= ids


def test_practitioner_free_is_not_a_scale(graph):
    scales = {s["id"]: s for s in gen_vocab.load_scales(SCALES)}
    assert scales["practitioner-free"].get("not_a_scale")
    assert (gen_vocab.scheme_iri("practitioner-free"), RDF.type, SKOS.ConceptScheme) not in graph


def test_every_scheme_has_two_or_more_ordered_concepts(graph):
    schemes = set(graph.subjects(RDF.type, SKOS.ConceptScheme))
    assert schemes
    for sch in schemes:
        concepts = list(graph.subjects(SKOS.inScheme, sch))
        assert len(concepts) >= 2, sch
        ordinals = sorted(int(graph.value(c, WARP.ordinal)) for c in concepts)
        assert ordinals == list(range(1, len(concepts) + 1)), sch


def test_medium_is_comparable_with_high(graph):
    ordinal = lambda v: int(graph.value(gen_vocab.concept_iri("dfo-recovery-priority", v), WARP.ordinal))  # noqa: E731
    assert ordinal("medium") < ordinal("high")


def test_generated_turtle_round_trips(graph, tmp_path):
    out = tmp_path / "scales.ttl"
    graph.serialize(out, format="turtle")
    assert len(Graph().parse(out)) == len(graph)


@pytest.mark.parametrize("bad, message", [
    ({"scales": [{"id": "x", "values": [{"id": "a"}]}]}, "at least two"),
    ({"scales": [{"id": "x", "values": [{"id": "a"}, {"id": "a"}]}]}, "duplicate value"),
    ({"scales": [{"id": "x", "values": [{"id": "a"}, {"id": "b"}]}, {"id": "x", "not_a_scale": True}]}, "duplicate scale"),
    ({"scales": [{"id": "has space", "values": [{"id": "a"}, {"id": "b"}]}]}, "IRI-safe"),
])
def test_malformed_vocab_is_refused(tmp_path, bad, message):
    import yaml
    p = tmp_path / "scales.yaml"
    p.write_text(yaml.safe_dump(bad), encoding="utf-8")
    with pytest.raises(gen_vocab.VocabError, match=message):
        gen_vocab.load_scales(p)
