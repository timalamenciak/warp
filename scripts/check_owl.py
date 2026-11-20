#!/usr/bin/env python3
"""OWL lint for WARP's generated RDF (decisions D11 to D20).

    python scripts/check_owl.py project/*.ttl src/warp/owl/warp-relations.ttl

Runs over every file given, merged where a rule is about the whole graph.
Errors (exit status 1):

  - kinds: an IRI is more than one kind of entity (class, object property,
    datatype property, annotation property, individual, datatype) across all
    files (D11). Kinds come from declarations and typing in every file, and
    from usage (subClassOf, someValuesFrom, ...) in the OWL files. The
    reification layer (statements*.ttl) is RDF: its relation triples may have
    a node class as subject, so usage there does not count, but typing does:
    `node:x a warp:Something` would be caught. This is the check that would
    have caught R13 (predicate IRIs typed as classes) and node punning.
  - datatypes: an xsd:date, xsd:gYear, xsd:gYearMonth or xsd:duration literal
    or datatype reference anywhere (D19). They are not in the OWL 2 datatype
    map.
  - iris: a relative or file: IRI (a bare token that never became a CURIE);
    a placeholder under a real ontology's namespace (anything with TODO
    outside the TODO: namespace, D20); or SEPIO's placeholder namespace
    (https://example.org/) in a data file. It may appear in warp.owl.ttl,
    which carries the vendored SEPIO schema as it is (Q13).
  - sentinels: an enum value that records an absence (not_stated, unknown,
    unclear, not_reported, not_addressed) was exported (D14).
  - predicates: a predicate in the reification or logical layer that is
    neither declared (schema or warp-relations.ttl) nor from an upstream
    ontology (OBO, CAMO, Biolink) (D13); an abstract predicate
    (warp:abstract_predicate true) asserted of anything (D16); or a datatype
    property with an IRI value / an object property with a literal value in
    the data (R14).
  - declarations: in the schema files, an owl:onProperty target that is not
    declared (OWL 2 DL needs every entity declared).
"""

import argparse
import sys
from collections import defaultdict
from pathlib import Path

from rdflib import BNode, Graph, Literal, URIRef
from rdflib.namespace import DCTERMS, OWL, RDF, RDFS, SKOS, XSD

sys.path.insert(0, str(Path(__file__).resolve().parent))
from clean_owl import SENTINELS  # noqa: E402

WARP = "https://w3id.org/ecoweaver/warp/"
TODO_BASE = WARP + "TODO/"
SEPIO_PLACEHOLDER = "https://example.org/"
UPSTREAM_PROPERTY_BASES = ("http://purl.obolibrary.org/obo/", "https://w3id.org/camo/",
                           "https://w3id.org/biolink/vocab/")
VOCAB_BASES = tuple(str(ns) for ns in (RDF, RDFS, OWL, XSD, SKOS, DCTERMS)) + ("https://w3id.org/linkml/",)
BAD_DATATYPES = {XSD.date, XSD.gYear, XSD.gYearMonth, XSD.duration}
DECLARED_KINDS = {OWL.Class: "class", OWL.ObjectProperty: "object property",
                  OWL.DatatypeProperty: "datatype property", OWL.AnnotationProperty: "annotation property",
                  OWL.NamedIndividual: "individual", RDFS.Datatype: "datatype"}
STRUCTURAL_TYPES = {OWL.Ontology, OWL.Restriction, OWL.Axiom, OWL.AllDisjointClasses, OWL.AllDifferent,
                    RDF.List, RDF.Property, OWL.TransitiveProperty, OWL.SymmetricProperty,
                    OWL.FunctionalProperty, OWL.InverseFunctionalProperty, OWL.AsymmetricProperty,
                    OWL.ReflexiveProperty, OWL.IrreflexiveProperty, OWL.DeprecatedClass,
                    OWL.DeprecatedProperty, RDFS.Class}
CLASS_POSITIONS = (RDFS.subClassOf, OWL.equivalentClass, OWL.disjointWith)
FILLERS = (OWL.someValuesFrom, OWL.allValuesFrom, OWL.onClass)
SCHEMA_FILES = ("warp.owl.ttl", "warp-relations.ttl")
DATA_FILES = ("statements", "axioms", "nodes", "sites", "projects")


def is_reification(path):
    return Path(path).name.startswith("statements")


def is_schema(path):
    return Path(path).name in SCHEMA_FILES


def is_data(path):
    return Path(path).name.split(".")[0] in DATA_FILES


def vocab(iri):
    return str(iri).startswith(VOCAB_BASES)


class OwlChecker:
    def __init__(self, graphs):
        self.graphs = graphs          # [(path, Graph)]
        self.errors = []
        self.kinds = defaultdict(lambda: defaultdict(set))   # iri -> kind -> {file}
        self.declared_props = {}      # iri -> kind
        self.abstract = set()

    def error(self, rule, msg):
        self.errors.append(f"[{rule}] {msg}")

    # -- collect --------------------------------------------------------------

    def note(self, iri, kind, path):
        if isinstance(iri, URIRef) and not vocab(iri):
            self.kinds[iri][kind].add(Path(path).name)

    def collect(self):
        for path, g in self.graphs:
            for s, t in g.subject_objects(RDF.type):
                if t in DECLARED_KINDS:
                    self.note(s, DECLARED_KINDS[t], path)
                    if "property" in DECLARED_KINDS[t]:
                        self.declared_props.setdefault(s, DECLARED_KINDS[t])
                elif t not in STRUCTURAL_TYPES and isinstance(t, URIRef):
                    self.note(s, "individual", path)
                    self.note(t, "class", path)
            for s in g.subjects(URIRef(WARP + "abstract_predicate"), None):
                if any(str(o).lower() == "true" for o in g.objects(s, URIRef(WARP + "abstract_predicate"))):
                    self.abstract.add(s)
            if is_reification(path):
                continue
            for pred in CLASS_POSITIONS:
                for s, o in g.subject_objects(pred):
                    self.note(s, "class", path)
                    if isinstance(o, URIRef):
                        self.note(o, "class", path)
            for pred in FILLERS:
                for o in g.objects(None, pred):
                    if isinstance(o, URIRef) and not str(o).startswith(str(XSD)) and o != RDFS.Literal \
                            and (o, RDF.type, RDFS.Datatype) not in g:
                        self.note(o, "class", path)

    # -- rules ----------------------------------------------------------------

    def check_kinds(self):
        for iri, kinds in sorted(self.kinds.items()):
            if len(kinds) > 1:
                where = "; ".join(f"{k} in {', '.join(sorted(f))}" for k, f in sorted(kinds.items()))
                self.error("kinds", f"{iri} is more than one kind of thing: {where}")

    def check_datatypes(self):
        for path, g in self.graphs:
            for s, p, o in g:
                if isinstance(o, Literal) and o.datatype in BAD_DATATYPES:
                    self.error("datatypes", f"{Path(path).name}: {o.datatype} literal {o!r} on {s} {p}")
                elif o in BAD_DATATYPES:
                    self.error("datatypes", f"{Path(path).name}: reference to {o} ({p})")

    def check_iris(self):
        for path, g in self.graphs:
            name = Path(path).name
            seen = set()
            for triple in g:
                for term in triple:
                    if not isinstance(term, URIRef) or term in seen:
                        continue
                    seen.add(term)
                    t = str(term)
                    if t.startswith("file:") or "://" not in t and not t.startswith(("urn:", "mailto:")):
                        self.error("iris", f"{name}: relative IRI {t} (a bare token, not a CURIE?)")
                    elif "TODO" in t and not t.startswith(TODO_BASE):
                        self.error("iris", f"{name}: placeholder under a real namespace: {t} (use TODO:)")
                    elif t.startswith(SEPIO_PLACEHOLDER) and is_data(path):
                        self.error("iris", f"{name}: SEPIO placeholder namespace in data: {t}")
                    frag = t.rsplit("#", 1)[-1] if "#" in t else None
                    if frag in SENTINELS:
                        self.error("sentinels", f"{name}: sentinel value exported: {t}")

    def check_predicates(self):
        for path, g in self.graphs:
            if is_schema(path):
                continue
            name = Path(path).name
            used = set(g.predicates()) | set(g.objects(None, OWL.onProperty))
            for p in sorted(used):
                if vocab(p):
                    continue
                if p in self.abstract:
                    self.error("predicates", f"{name}: abstract predicate {p} is asserted (use a sub-property)")
                if p in self.declared_props or str(p).startswith(UPSTREAM_PROPERTY_BASES):
                    continue
                self.error("predicates", f"{name}: predicate {p} is not declared in the schema or "
                                         "warp-relations.ttl and is not from an upstream ontology")
            if not is_reification(path):
                continue
            for s, p, o in g:
                kind = self.declared_props.get(p)
                if kind == "datatype property" and not isinstance(o, Literal):
                    self.error("predicates", f"{name}: datatype property {p} has an IRI value {o} on {s}")
                elif kind == "object property" and isinstance(o, Literal):
                    self.error("predicates", f"{name}: object property {p} has a literal value {o!r} on {s}")

    def check_declarations(self):
        for path, g in self.graphs:
            if not is_schema(path):
                continue
            for p in set(g.objects(None, OWL.onProperty)):
                if isinstance(p, URIRef) and p not in self.declared_props:
                    self.error("declarations", f"{Path(path).name}: {p} is used in a restriction but never declared")

    def run(self):
        self.collect()
        self.check_kinds()
        self.check_datatypes()
        self.check_iris()
        self.check_predicates()
        self.check_declarations()
        return self.errors


def check_files(paths):
    graphs = [(p, Graph().parse(p, format="turtle")) for p in paths]
    return OwlChecker(graphs).run()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("files", type=Path, nargs="+")
    args = parser.parse_args(argv)
    errors = check_files(args.files)
    for e in errors:
        print("error:", e, file=sys.stderr)
    print(f"check_owl: {len(errors)} error(s) in {len(args.files)} file(s)")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
