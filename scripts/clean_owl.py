#!/usr/bin/env python3
"""Post-process gen-owl's output into an OWL 2 DL schema ontology.

    gen-owl ... src/warp/schema/warp.yaml > project/warp.owl.raw.ttl
    python scripts/clean_owl.py project/warp.owl.raw.ttl project/warp.owl.ttl \
        [--schema PATH] [--relations src/warp/owl/warp-relations.ttl]

Most of what this script was first meant to do turned out to be schema
settings (`implements:` on enums and slots, see the dev guide's appendix), so
the profile does it. What is left are things the profile cannot say, either
because they are LinkML generator behaviour or because they concern the
vendored upstreams, which are never edited. Each job is one function, runs in
the order below, and reports every change it makes. Anything else in the
graph is left alone.

1. predicate_enums: the predicate enums of registered groups that come from
   an upstream (CAMO's CausalPredicateEnum) cannot carry
   `implements: [owl:ObjectProperty]`, so gen-owl types their values as
   individuals of the enum. Retype them as object properties, turn
   value-to-value rdfs:subClassOf into rdfs:subPropertyOf, and drop the
   enum's covering axiom (what gen-owl does for the profile's own predicate
   enums). (R13)
2. sentinels: permissible values that denote absence (not_stated, unknown,
   unclear, not_reported, not_addressed) are removed. They record that
   something is missing; an IRI asserting "there is evidence, of type
   not-stated" would be false. (D14) Listed once, in SENTINELS.
3. annotation_restrictions: gen-owl writes class restrictions on every slot,
   including subject, predicate and object, which are annotation properties
   (D12). A restriction on an annotation property is not OWL 2 DL; remove it.
4. datatypes: LinkML maps `date` to xsd:date, which is not in the OWL 2
   datatype map (D19). WARP writes dates as ISO 8601 strings, so the
   reference becomes xsd:string. (Only upstream SEPIO slots still use it.)
5. declarations: gen-owl never declares a slot IRI set by `slot_uri` in
   `slot_usage` (the WARP IRIs for SEPIO slots, Q13), though it uses them in
   restrictions. OWL 2 DL needs every entity declared, so declare each as an
   object or datatype property, decided by the fillers of its restrictions.
6. kind_conflicts: same-named attributes with different ranges in the
   upstreams (CAMO `id`, SEPIO `subtype`) are declared both object and
   datatype property, which OWL 2 DL forbids. Keep the kind most
   restrictions use and drop the restrictions of the other kind.
8. relative_iris (runs last): element metadata such as SEPIO's `status:
   Draft` comes out as a relative IRI (<Draft>). It is a word, not a thing,
   so it becomes a literal.
7. covering_axioms: gen-owl writes owl:unionOf / owl:oneOf directly on the
   named enum class. Those constructors are only legal on an anonymous class
   expression, so move each to `<enum> owl:equivalentClass [ a owl:Class ;
   owl:oneOf (...) ]` (R15). This is the one real LinkML defect; the dev
   guide's appendix has the upstream patch. One-value enums get an explicit
   one-item list, never `Enum owl:equivalentClass <value>`.

Jobs 3 to 8 are candidate upstream LinkML issues (TODOS.md, "Upstream").
"""

import argparse
import sys
from collections import Counter, defaultdict
from pathlib import Path

from rdflib import BNode, Graph, Literal, URIRef
from rdflib.collection import Collection
from rdflib.namespace import DCTERMS, OWL, RDF, RDFS, XSD

sys.path.insert(0, str(Path(__file__).resolve().parent))
import warp_schema as ws  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_RELATIONS = ROOT / "src" / "warp" / "owl" / "warp-relations.ttl"

# Permissible values that record an absence (D14). Add to this list when a
# group adds one; export_rdf.py reads it from here.
SENTINELS = frozenset({"not_stated", "unknown", "unclear", "not_reported", "not_addressed"})

# Datatypes outside the OWL 2 datatype map, and what replaces them (D19).
NOT_IN_DATATYPE_MAP = {XSD.date: XSD.string, XSD.gYear: XSD.string, XSD.duration: XSD.string,
                       XSD.gYearMonth: XSD.string, XSD.time: XSD.string}

FILLER_PREDICATES = (OWL.someValuesFrom, OWL.allValuesFrom, OWL.onClass, OWL.onDataRange, OWL.hasValue)


# --- RDF list helpers ----------------------------------------------------------

def list_items(g, head):
    return list(Collection(g, head))


def drop_list(g, head):
    node = head
    while node and node != RDF.nil:
        nxt = g.value(node, RDF.rest)
        g.remove((node, RDF.first, None))
        g.remove((node, RDF.rest, None))
        node = nxt


def new_list(g, items):
    if not items:
        return RDF.nil
    head = BNode()
    Collection(g, head, items)
    return head


def replace_list(g, head, items):
    """Rebuild the list at `head` with `items`, repointing whoever used it."""
    users = list(g.subject_predicates(head))
    drop_list(g, head)
    new = new_list(g, items)
    for s, p in users:
        g.remove((s, p, head))
        g.add((s, p, new))
    return new


def remove_node(g, node):
    """Remove a blank node, its outgoing triples, and every reference to it,
    taking it out of any RDF list it is a member of."""
    for cell in list(g.subjects(RDF.first, node)):
        heads = [cell]
        # find the list head: walk back along rdf:rest
        while True:
            prev = g.value(predicate=RDF.rest, object=heads[0])
            if prev is None:
                break
            heads.insert(0, prev)
        head = heads[0]
        items = [i for i in list_items(g, head) if i != node]
        replace_list(g, head, items)
    for s, p in list(g.subject_predicates(node)):
        g.remove((s, p, node))
    stack = [node]
    while stack:
        n = stack.pop()
        for p, o in list(g.predicate_objects(n)):
            g.remove((n, p, o))
            if isinstance(o, BNode) and not any(True for _ in g.subject_predicates(o)):
                stack.append(o)


# --- kind of a restriction filler -----------------------------------------------------

def is_datatype(g, node):
    if isinstance(node, URIRef):
        return str(node).startswith(str(XSD)) or node == RDFS.Literal or \
            (node, RDF.type, RDFS.Datatype) in g
    if isinstance(node, BNode):
        if (node, RDF.type, RDFS.Datatype) in g or (node, OWL.onDatatype, None) in g:
            return True
        for pred in (OWL.unionOf, OWL.intersectionOf, OWL.oneOf):
            lst = g.value(node, pred)
            if lst is not None:
                items = list_items(g, lst)
                if pred == OWL.oneOf:
                    return all(isinstance(i, Literal) for i in items)
                return bool(items) and all(is_datatype(g, i) for i in items)
    return False


def restriction_kind(g, r):
    """'data', 'object' or None (cardinality without a qualifier)."""
    if (r, OWL.onDataRange, None) in g:
        return "data"
    for pred in FILLER_PREDICATES:
        for o in g.objects(r, pred):
            if pred == OWL.hasValue:
                return "data" if isinstance(o, Literal) else "object"
            return "data" if is_datatype(g, o) else "object"
    return None


def restrictions_on(g, prop):
    return [r for r in g.subjects(OWL.onProperty, prop) if (r, RDF.type, OWL.Restriction) in g]


# --- the jobs -------------------------------------------------------------------

class Cleaner:
    def __init__(self, g, sv, relations=None):
        self.g = g
        self.sv = sv
        self.relations = relations if relations is not None else Graph()
        self.report = defaultdict(list)

    def enum_iri(self, name):
        return URIRef(self.sv.expand_curie(f"{self.sv.schema.default_prefix}:{name}"))

    def pv_iri(self, enum_name, pv):
        if pv.meaning:
            return URIRef(self.sv.expand_curie(pv.meaning))
        return URIRef(str(self.enum_iri(enum_name)) + "#" + pv.text)

    def drop_covering(self, enum):
        for pred in (OWL.unionOf, OWL.oneOf):
            for lst in list(self.g.objects(enum, pred)):
                self.g.remove((enum, pred, lst))
                drop_list(self.g, lst)

    # 1
    def predicate_enums(self):
        import derive_propositions as dp
        groups = dp.load_groups(Path(self.sv.schema.source_file), all_groups=True)
        for grp in groups:
            ename = self.sv.induced_slot("predicate", grp["statement_class"]).range
            enum = self.sv.get_enum(ename)
            if "owl:ObjectProperty" in (enum.implements or []):
                continue   # the profile said so; gen-owl already did the right thing
            eiri = self.enum_iri(ename)
            values = {pv.text: self.pv_iri(ename, pv) for pv in enum.permissible_values.values()}
            for name, v in values.items():
                for t in (OWL.NamedIndividual, OWL.Class, eiri):
                    self.g.remove((v, RDF.type, t))
                self.g.remove((v, RDFS.subClassOf, eiri))
                self.g.add((v, RDF.type, OWL.ObjectProperty))
                self.g.add((v, DCTERMS.isPartOf, eiri))
                for parent in list(self.g.objects(v, RDFS.subClassOf)):
                    if parent in values.values():
                        self.g.remove((v, RDFS.subClassOf, parent))
                        self.g.add((v, RDFS.subPropertyOf, parent))
                self.report["predicate_enums"].append(f"{v} -> owl:ObjectProperty ({ename})")
            self.drop_covering(eiri)

    # 2
    def sentinels(self):
        for ename, enum in self.sv.all_enums().items():
            eiri = self.enum_iri(ename)
            for pv in enum.permissible_values.values():
                if pv.text not in SENTINELS:
                    continue
                v = self.pv_iri(ename, pv)
                if (v, None, None) not in self.g and (None, None, v) not in self.g:
                    continue
                for lst in list(self.g.objects(eiri, OWL.oneOf)) + list(self.g.objects(eiri, OWL.unionOf)):
                    items = list_items(self.g, lst)
                    if v in items:
                        replace_list(self.g, lst, [i for i in items if i != v])
                self.g.remove((v, None, None))
                self.g.remove((None, None, v))
                self.report["sentinels"].append(f"{ename}#{pv.text}")

    # 3
    def annotation_properties(self):
        props = set(self.relations.subjects(RDF.type, OWL.AnnotationProperty))
        for cname in self.sv.all_classes():
            for slot in self.sv.class_induced_slots(cname):
                if "owl:AnnotationProperty" in (slot.implements or []):
                    props.add(URIRef(self.sv.get_uri(slot, expand=True, native=False)))
        return props

    def annotation_restrictions(self):
        for prop in sorted(self.annotation_properties()):
            rs = restrictions_on(self.g, prop)
            for r in rs:
                remove_node(self.g, r)
            if rs:
                self.report["annotation_restrictions"].append(f"{prop}: {len(rs)} restriction(s)")

    # 4
    def datatypes(self):
        for bad, good in NOT_IN_DATATYPE_MAP.items():
            for s, p in list(self.g.subject_predicates(bad)):
                self.g.remove((s, p, bad))
                self.g.add((s, p, good))
                self.report["datatypes"].append(f"{bad} -> {good} ({p.split('#')[-1]})")

    # 5
    def declared(self, prop):
        return any((prop, RDF.type, t) in self.g for t in
                   (OWL.ObjectProperty, OWL.DatatypeProperty, OWL.AnnotationProperty))

    def declarations(self):
        for prop in sorted(set(self.g.objects(None, OWL.onProperty))):
            if not isinstance(prop, URIRef) or self.declared(prop):
                continue
            kinds = Counter(k for k in (restriction_kind(self.g, r) for r in restrictions_on(self.g, prop)) if k)
            kind = OWL.ObjectProperty if kinds["object"] > kinds["data"] else OWL.DatatypeProperty
            self.g.add((prop, RDF.type, kind))
            self.report["declarations"].append(f"{prop} a {kind.split('#')[-1]}")

    # 6
    def kind_conflicts(self):
        both = set(self.g.subjects(RDF.type, OWL.ObjectProperty)) & set(self.g.subjects(RDF.type, OWL.DatatypeProperty))
        for prop in sorted(both):
            rs = restrictions_on(self.g, prop)
            kinds = Counter(restriction_kind(self.g, r) for r in rs)
            keep = "object" if kinds["object"] > kinds["data"] else "data"
            drop_type = OWL.DatatypeProperty if keep == "object" else OWL.ObjectProperty
            self.g.remove((prop, RDF.type, drop_type))
            dropped = 0
            for r in rs:
                k = restriction_kind(self.g, r)
                if k and k != keep:
                    remove_node(self.g, r)
                    dropped += 1
            self.report["kind_conflicts"].append(
                f"{prop}: kept {keep} property, dropped {dropped} restriction(s) of the other kind")

    # 7
    def covering_axioms(self):
        for pred in (OWL.unionOf, OWL.oneOf):
            for enum, lst in list(self.g.subject_objects(pred)):
                if not isinstance(enum, URIRef):
                    continue
                items = list_items(self.g, lst)
                self.g.remove((enum, pred, lst))
                drop_list(self.g, lst)
                if not items:
                    continue
                anon = BNode()
                literal = all(isinstance(i, Literal) for i in items)
                self.g.add((anon, RDF.type, RDFS.Datatype if literal else OWL.Class))
                self.g.add((anon, pred, new_list(self.g, items)))
                self.g.add((enum, OWL.equivalentClass, anon))
                self.report["covering_axioms"].append(
                    f"{enum}: owl:{pred.split('#')[-1]} moved to an anonymous class ({len(items)} member(s))")

    # 8
    def relative_iris(self, base):
        """Element metadata such as SEPIO's `status: Draft` comes out of
        gen-owl as a relative IRI (<Draft>), which a parser resolves against
        the file's own location. It is a word, not a thing: make it a literal."""
        for s, p, o in list(self.g):
            if isinstance(o, URIRef) and str(o).startswith(base):
                word = str(o)[len(base):]
                self.g.remove((s, p, o))
                self.g.add((s, p, Literal(word)))
                self.report["relative_iris"].append(f"<{word}> -> \"{word}\" ({p})")

    JOBS = ("predicate_enums", "sentinels", "annotation_restrictions", "datatypes",
            "declarations", "kind_conflicts", "covering_axioms")

    def run(self, base=None):
        for job in self.JOBS:
            getattr(self, job)()
        if base:
            self.relative_iris(base)
        return self.report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("input", type=Path, help="gen-owl output (Turtle)")
    parser.add_argument("output", type=Path)
    parser.add_argument("--schema", type=Path, default=ws.DEFAULT_SCHEMA)
    parser.add_argument("--relations", type=Path, default=DEFAULT_RELATIONS)
    parser.add_argument("--verbose", action="store_true", help="list every change, not only counts")
    args = parser.parse_args(argv)

    # Parse against a known base, so relative IRIs can be found again (job 8).
    base = "https://relative.invalid/"
    g = Graph().parse(args.input, format="turtle", publicID=base)
    before = len(g)
    relations = Graph().parse(args.relations, format="turtle") if args.relations.exists() else Graph()
    report = Cleaner(g, ws.load(args.schema), relations).run(base=base)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    g.serialize(args.output, format="turtle")
    print(f"clean_owl: {before} -> {len(g)} triples, wrote {args.output}")
    for job in Cleaner.JOBS + ("relative_iris",):
        items = report.get(job, [])
        print(f"  {job}: {len(items)} change(s)")
        if args.verbose:
            for i in items:
                print(f"    {i}")


if __name__ == "__main__":
    main()
