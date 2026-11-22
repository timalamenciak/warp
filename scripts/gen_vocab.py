#!/usr/bin/env python3
"""Generate SKOS vocabularies and local OWL classes from WARP's vocabulary files.

    python scripts/gen_vocab.py vocab/scales.yaml --out project/scales.ttl \
        [--local vocab/local --local-out project/local_terms.ttl \
         --classes-out project/local_classes.ttl]

Scales. Each scale in vocab/scales.yaml becomes a skos:ConceptScheme, and
each of its values a skos:Concept with skos:inScheme, skos:prefLabel,
skos:notation (the value id) and an explicit warp:ordinal, so values can be
compared without a script knowing the source's order (decision D18). Scales
marked `not_a_scale` are not emitted.

Local terms (docs/terminology.md). Each file in vocab/local/ is one scheme of
terms WARP mints because no ontology has them, each with its upstream status.
A `concept` scheme (prefix concept: or place:) is written as SKOS to
--local-out; a `class` scheme (prefix term:) as OWL classes to --classes-out,
so a local term used as a template filler is a class and never a punned
concept. A term whose upstream status is `accepted` is written as
owl:deprecated, replaced by (IAO:0100001) its upstream term.

Exits non-zero on a malformed file: duplicate ids, a scale with fewer than
two values, an id that cannot be part of an IRI, or a local term without a
label, a definition or the fields its upstream status needs.
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
OBO = Namespace("http://purl.obolibrary.org/obo/")
SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
VOCAB_VERSION = "warp-scales/1"
LOCAL_VERSION = "warp-local-terms/1"
DEFINITION = OBO.IAO_0000115
TERM_REPLACED_BY = OBO.IAO_0100001

# The prefixes a local scheme may use, and the kind of term each holds
# (docs/terminology.md, section 3). Each is declared in warp.yaml.
REGISTER_PREFIXES = {"concept": "concept", "place": "concept", "term": "class"}
# What each upstream status needs (docs/terminology.md, section 4.2).
UPSTREAM_STATUS = {
    "not_checked": (),
    "to_request": ("target",),
    "requested": ("target", "issue"),
    "accepted": ("target", "replaced_by"),
    "not_appropriate": ("reason",),
}
UPSTREAM_FIELDS = {"target", "status", "issue", "reason", "replaced_by"}


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


# -- local term register (vocab/local/, docs/terminology.md) ------------------

def _expand(curie, pm, where):
    if not isinstance(curie, str) or ":" not in curie:
        raise VocabError(f"{where}: {curie!r} is not a CURIE")
    if "://" in curie:
        return curie
    prefix, _, local = curie.partition(":")
    if prefix not in pm:
        raise VocabError(f"{where}: undeclared prefix {prefix!r} in {curie!r}")
    return pm[prefix] + local


def _check_upstream(where, up, pm):
    if not isinstance(up, dict) or "status" not in up:
        raise VocabError(f"{where}: needs upstream.status")
    unknown = set(up) - UPSTREAM_FIELDS
    if unknown:
        raise VocabError(f"{where}: unknown upstream field(s) {', '.join(sorted(unknown))}")
    status = up["status"]
    if status not in UPSTREAM_STATUS:
        raise VocabError(f"{where}: upstream.status {status!r} is not one of {', '.join(UPSTREAM_STATUS)}")
    for field in UPSTREAM_STATUS[status]:
        if not up.get(field):
            raise VocabError(f"{where}: upstream.status {status} needs upstream.{field}")
    if up.get("replaced_by") and status != "accepted":
        raise VocabError(f"{where}: upstream.replaced_by is only for status accepted")
    if up.get("issue") and not str(up["issue"]).startswith(("http://", "https://")):
        raise VocabError(f"{where}: upstream.issue must be a URL")
    if up.get("replaced_by"):
        if str(up["replaced_by"]).startswith("TODO:"):
            raise VocabError(f"{where}: upstream.replaced_by cannot be a TODO: placeholder")
        _expand(up["replaced_by"], pm, where)


def _load_scheme(f, pm, iris):
    data = yaml.safe_load(f.read_text(encoding="utf-8")) or {}
    scheme, terms = data.get("scheme") or {}, data.get("terms") or []
    where = f.name
    sid, prefix, kind = scheme.get("id"), scheme.get("prefix"), scheme.get("kind")
    if not sid or not SAFE_ID.match(str(sid)):
        raise VocabError(f"{where}: scheme id {sid!r} is missing or not IRI-safe")
    if not scheme.get("label"):
        raise VocabError(f"{where}: scheme needs a label")
    if prefix not in REGISTER_PREFIXES:
        raise VocabError(f"{where}: prefix {prefix!r} is not a register prefix "
                         f"({', '.join(sorted(REGISTER_PREFIXES))})")
    if prefix not in pm:
        raise VocabError(f"{where}: prefix {prefix!r} is not declared in the profile")
    if kind != REGISTER_PREFIXES[prefix]:
        raise VocabError(f"{where}: prefix {prefix}: holds {REGISTER_PREFIXES[prefix]} terms, "
                         f"not kind {kind!r}")
    if not terms:
        raise VocabError(f"{where}: needs at least one term")
    s_iri = pm[prefix] + str(sid)
    if kind == "concept":
        if s_iri in iris:
            raise VocabError(f"{where}: scheme {prefix}:{sid} is already {iris[s_iri]}")
        iris[s_iri] = f"the scheme in {where}"
    checked = []
    for t in terms:
        tid = t.get("id")
        if not tid or not SAFE_ID.match(str(tid)):
            raise VocabError(f"{where}: term id {tid!r} is missing or not IRI-safe")
        twhere = f"{where}: {prefix}:{tid}"
        iri = pm[prefix] + str(tid)
        if iri in iris:
            raise VocabError(f"{twhere} is already {iris[iri]}")
        iris[iri] = f"a term in {where}"
        for field in ("label", "definition"):
            if not t.get(field):
                raise VocabError(f"{twhere}: needs a {field}")
        _check_upstream(twhere, t.get("upstream"), pm)
        broader = _expand(t["broader"], pm, twhere) if t.get("broader") else None
        checked.append(dict(t, iri=iri, broader_iri=broader))
    return {**scheme, "iri": s_iri, "file": where, "terms": checked}


def load_register(directory, pm):
    """Every scheme in vocab/local/*.yaml, checked. pm is the profile's prefix map."""
    iris = {}
    schemes = [_load_scheme(f, pm, iris) for f in sorted(Path(directory).glob("*.yaml"))]
    bases = register_bases(pm)
    for sch in schemes:           # a broader term under a register prefix must be registered
        for t in sch["terms"]:
            b = t["broader_iri"]
            if b and b.startswith(bases) and b not in iris:
                raise VocabError(f"{sch['file']}: {t['id']}: broader {t['broader']} is not registered")
    return schemes


def register_index(schemes):
    """{IRI: {kind, scheme, deprecated, replaced_by}} for every local term."""
    index = {}
    for sch in schemes:
        for t in sch["terms"]:
            up = t["upstream"]
            index[t["iri"]] = {"kind": sch["kind"], "scheme": sch["id"],
                               "deprecated": up["status"] == "accepted",
                               "replaced_by": up.get("replaced_by")}
    return index


def register_bases(pm):
    """The namespaces the register governs: every IRI under them must be registered."""
    return tuple(pm[p] for p in REGISTER_PREFIXES if p in pm)


def _upstream_note(up):
    if up["status"] == "not_appropriate":
        return "Local by design, not upstreamed: " + str(up["reason"])
    note = f"Upstream: {up.get('target') or 'no target chosen'}; status {up['status']}."
    if up.get("issue"):
        note += f" Request: {up['issue']}."
    if up.get("reason"):
        note += " " + str(up["reason"])
    return note


def _text(value):
    return Literal(" ".join(str(value).split()), lang="en")


def build_local_graphs(schemes, pm):
    """(SKOS graph of the concept schemes, OWL graph of the class schemes, or None
    when there are no class schemes)."""
    concepts, classes = Graph(), Graph()
    for g, name, label in ((concepts, "local_terms", "WARP local terms"),
                           (classes, "local_classes", "WARP local classes")):
        g.bind("skos", SKOS)
        g.bind("obo", OBO)
        for p in REGISTER_PREFIXES:
            if p in pm:
                g.bind(p, pm[p])
        onto = URIRef(f"https://w3id.org/ecoweaver/warp/ontology/{name}")
        g.add((onto, RDF.type, OWL.Ontology))
        g.add((onto, RDFS.label, Literal(label)))
        g.add((onto, OWL.versionInfo, Literal(LOCAL_VERSION)))
    for sch in schemes:
        (_add_concepts if sch["kind"] == "concept" else _add_classes)(
            concepts if sch["kind"] == "concept" else classes, sch, pm)
    has_classes = any(s["kind"] == "class" for s in schemes)
    return concepts, (classes if has_classes else None)


def _deprecate(g, iri, up, pm, where):
    new = URIRef(_expand(up["replaced_by"], pm, where))
    g.add((iri, OWL.deprecated, Literal(True)))
    g.add((iri, TERM_REPLACED_BY, new))
    g.add((TERM_REPLACED_BY, RDF.type, OWL.AnnotationProperty))
    return new


def _add_concepts(g, sch, pm):
    s_iri = URIRef(sch["iri"])
    g.add((s_iri, RDF.type, SKOS.ConceptScheme))
    g.add((s_iri, SKOS.prefLabel, _text(sch["label"])))
    in_scheme = {t["iri"] for t in sch["terms"]}
    for t in sch["terms"]:
        c, up, b = URIRef(t["iri"]), t["upstream"], t["broader_iri"]
        g.add((c, RDF.type, SKOS.Concept))
        g.add((c, SKOS.inScheme, s_iri))
        g.add((c, SKOS.prefLabel, _text(t["label"])))
        g.add((c, SKOS.definition, _text(t["definition"])))
        g.add((c, SKOS.editorialNote, _text(_upstream_note(up))))
        if b and b in in_scheme:
            g.add((c, SKOS.broader, URIRef(b)))
        else:
            g.add((s_iri, SKOS.hasTopConcept, c))
            if b:
                g.add((c, SKOS.broadMatch, URIRef(b)))
        if up["status"] == "accepted":
            g.add((c, SKOS.exactMatch, _deprecate(g, c, up, pm, t["id"])))


def _add_classes(g, sch, pm):
    g.add((DEFINITION, RDF.type, OWL.AnnotationProperty))
    for t in sch["terms"]:
        c, up = URIRef(t["iri"]), t["upstream"]
        g.add((c, RDF.type, OWL.Class))
        g.add((c, RDFS.label, _text(t["label"])))
        g.add((c, DEFINITION, _text(t["definition"])))
        g.add((c, RDFS.comment, _text(_upstream_note(up))))
        if up["status"] == "accepted":
            _deprecate(g, c, up, pm, t["id"])   # OBO convention: no logical axioms once deprecated
        elif t["broader_iri"]:
            parent = URIRef(t["broader_iri"])
            g.add((c, RDFS.subClassOf, parent))
            g.add((parent, RDF.type, OWL.Class))   # declared, so the file is OWL 2 DL on its own


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("scales", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--local", type=Path, help="vocab/local (the local term register)")
    parser.add_argument("--local-out", type=Path, help="project/local_terms.ttl")
    parser.add_argument("--classes-out", type=Path, help="project/local_classes.ttl")
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
    if args.local:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        import warp_schema as ws
        pm = ws.prefix_map(ws.load())
        try:
            schemes = load_register(args.local, pm)
        except VocabError as err:
            sys.exit(f"ERROR {err}")
        concepts, classes = build_local_graphs(schemes, pm)
        out = args.local_out or args.out.with_name("local_terms.ttl")
        concepts.serialize(out, format="turtle")
        n_terms = sum(len(s["terms"]) for s in schemes)
        print(f"wrote {out}: {len(schemes)} scheme(s), {n_terms} term(s), {len(concepts)} triples")
        cout = args.classes_out or args.out.with_name("local_classes.ttl")
        if classes is not None:
            classes.serialize(cout, format="turtle")
            print(f"wrote {cout}: {len(classes)} triples")
        elif cout.exists():
            cout.unlink()     # generated output from a class scheme since removed
            print(f"removed {cout}: no class schemes")


if __name__ == "__main__":
    main()
