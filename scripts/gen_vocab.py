#!/usr/bin/env python3
"""Generate SKOS vocabularies from WARP's vocabulary files.

    python scripts/gen_vocab.py vocab/scales.yaml --out project/scales.ttl \
        [--criteria vocab/criteria_concepts.yaml --criteria-out project/criteria_concepts.ttl]

Each scale in vocab/scales.yaml becomes a skos:ConceptScheme, and each of its
values a skos:Concept with skos:inScheme, skos:prefLabel, skos:notation (the
value id) and an explicit warp:ordinal, so values can be compared without a
script knowing the source's order (decision D18). Scales marked
`not_a_scale` are not emitted.

Exits non-zero on a malformed file: duplicate ids, a scale with fewer than
two values, or a value id that cannot be part of an IRI.
"""

import argparse
import re
import sys
from pathlib import Path

import yaml
from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.namespace import DCTERMS, OWL, RDF, RDFS, SKOS, XSD

WARP = Namespace("https://w3id.org/ecoweaver/warp/")
SCALE = Namespace("https://w3id.org/ecoweaver/warp/scale/")
CONCEPT = Namespace("https://w3id.org/ecoweaver/warp/concept/")
SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
VOCAB_VERSION = "warp-scales/1"


class VocabError(ValueError):
    pass


def load_scales(path):
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    scales = data.get("scales") or []
    seen = set()
    for s in scales:
        sid = s.get("id")
        if not sid or not SAFE_ID.match(sid):
            raise VocabError(f"scale id {sid!r} is missing or not IRI-safe")
        if sid in seen:
            raise VocabError(f"duplicate scale id {sid!r}")
        seen.add(sid)
        if s.get("not_a_scale"):
            continue
        values = s.get("values") or []
        if len(values) < 2:
            raise VocabError(f"scale {sid!r} needs at least two ordered values")
        vids = [v.get("id") for v in values]
        for v in vids:
            if not v or not SAFE_ID.match(str(v)):
                raise VocabError(f"scale {sid!r}: value id {v!r} is missing or not IRI-safe")
        if len(set(vids)) != len(vids):
            raise VocabError(f"scale {sid!r} has duplicate value ids")
    return scales


def scheme_iri(scale_id):
    return SCALE[scale_id]


def concept_iri(scale_id, value_id):
    return URIRef(f"{SCALE}{scale_id}/{value_id}")


def scale_index(scales):
    """{scheme IRI: {concept IRI: ordinal}} plus the set of not-a-scale IRIs."""
    index, refused = {}, set()
    for s in scales:
        if s.get("not_a_scale"):
            refused.add(str(scheme_iri(s["id"])))
            continue
        index[str(scheme_iri(s["id"]))] = {
            str(concept_iri(s["id"], v["id"])): i
            for i, v in enumerate(s["values"], start=1)
        }
    return index, refused


def build_graph(scales):
    g = Graph()
    g.bind("skos", SKOS)
    g.bind("warp", WARP)
    g.bind("scale", SCALE)
    g.bind("dcterms", DCTERMS)
    onto = URIRef("https://w3id.org/ecoweaver/warp/ontology/scales")
    g.add((onto, RDF.type, OWL.Ontology))
    g.add((onto, RDFS.label, Literal("WARP source scales")))
    g.add((onto, OWL.versionInfo, Literal(VOCAB_VERSION)))
    g.add((WARP.ordinal, RDF.type, OWL.AnnotationProperty))
    g.add((WARP.ordinal, RDFS.label, Literal("ordinal")))
    g.add((WARP.ordinal, SKOS.definition, Literal(
        "1-based position of a concept in its scheme, ascending in what the scheme's "
        "skos:scopeNote says the order measures.")))
    for s in scales:
        if s.get("not_a_scale"):
            continue
        sch = scheme_iri(s["id"])
        g.add((sch, RDF.type, SKOS.ConceptScheme))
        g.add((sch, SKOS.prefLabel, Literal(s.get("label", s["id"]), lang="en")))
        g.add((sch, SKOS.notation, Literal(s["id"])))
        if s.get("body"):
            g.add((sch, DCTERMS.source, Literal(s["body"])))
        if s.get("ordinal"):
            g.add((sch, SKOS.scopeNote, Literal("Ordinal order: " + s["ordinal"], lang="en")))
        if s.get("comment"):
            g.add((sch, RDFS.comment, Literal(" ".join(s["comment"].split()), lang="en")))
        for i, v in enumerate(s["values"], start=1):
            c = concept_iri(s["id"], v["id"])
            g.add((c, RDF.type, SKOS.Concept))
            g.add((c, SKOS.inScheme, sch))
            g.add((c, SKOS.prefLabel, Literal(v.get("label", v["id"]), lang="en")))
            g.add((c, SKOS.notation, Literal(str(v["id"]))))
            g.add((c, WARP.ordinal, Literal(i, datatype=XSD.integer)))
            g.add((sch, SKOS.hasTopConcept, c))   # flat schemes: every value is a top concept
    return g


def build_criteria_graph(path):
    """vocab/criteria_concepts.yaml -> SKOS (project/criteria_concepts.ttl).

    Each concept is a skos:Concept under concept:, the same IRI
    CriteriaConceptEnum's values give as their meaning, so a concept exists
    once; never an owl:Class (decision D14)."""
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    scheme, concepts = data.get("scheme") or {}, data.get("concepts") or []
    if not scheme.get("id") or not concepts:
        raise VocabError(f"{path}: needs a scheme id and at least one concept")
    g = Graph()
    g.bind("skos", SKOS)
    g.bind("concept", CONCEPT)
    onto = URIRef("https://w3id.org/ecoweaver/warp/ontology/criteria_concepts")
    g.add((onto, RDF.type, OWL.Ontology))
    g.add((onto, RDFS.label, Literal("WARP criteria concepts")))
    sch = CONCEPT[scheme["id"]]
    g.add((sch, RDF.type, SKOS.ConceptScheme))
    g.add((sch, SKOS.prefLabel, Literal(scheme.get("label", scheme["id"]), lang="en")))
    for c in concepts:
        if not c.get("id") or not SAFE_ID.match(c["id"]):
            raise VocabError(f"{path}: concept id {c.get('id')!r} is missing or not IRI-safe")
        iri = CONCEPT[c["id"]]
        g.add((iri, RDF.type, SKOS.Concept))
        g.add((iri, SKOS.inScheme, sch))
        g.add((sch, SKOS.hasTopConcept, iri))
        g.add((iri, SKOS.prefLabel, Literal(c.get("label", c["id"]), lang="en")))
        if c.get("definition"):
            g.add((iri, SKOS.definition, Literal(" ".join(c["definition"].split()), lang="en")))
    return g


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("scales", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--criteria", type=Path, help="vocab/criteria_concepts.yaml")
    parser.add_argument("--criteria-out", type=Path, help="project/criteria_concepts.ttl")
    args = parser.parse_args(argv)
    try:
        scales = load_scales(args.scales)
    except VocabError as err:
        sys.exit(f"ERROR {err}")
    g = build_graph(scales)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    g.serialize(args.out, format="turtle")
    n = sum(1 for s in scales if not s.get("not_a_scale"))
    print(f"wrote {args.out}: {n} scheme(s), {len(g)} triples")
    if args.criteria:
        try:
            cg = build_criteria_graph(args.criteria)
        except VocabError as err:
            sys.exit(f"ERROR {err}")
        out = args.criteria_out or args.out.with_name("criteria_concepts.ttl")
        cg.serialize(out, format="turtle")
        print(f"wrote {out}: {len(cg)} triples")


if __name__ == "__main__":
    main()
