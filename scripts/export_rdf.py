#!/usr/bin/env python3
"""Export WARP statement sets as RDF: the reification layer.

    python scripts/export_rdf.py FILE.yaml [FILE.yaml ...] --out project/statements.ttl

Pass annotated sets, their derived files and assessments together. Writes one
Turtle file holding every statement, proposition, evidence line, study result,
agent and document, with every qualifier bundle and value object. Nothing in
it is asserted as true of the world: it records who said what, on what basis.
The contract is docs/rdf-owl.md; in short:

- Schema-driven. Every class and slot IRI comes from the profile (class_uri,
  slot_uri, with WARP IRIs for the SEPIO slots WARP uses, Q13), so the
  exporter and project/warp.owl.ttl always agree. There is no namespace
  constant here to re-point when SEPIO grounds its terms: a mapping file of
  owl:equivalentProperty axioms will do that.
- Named individuals, no blank nodes (D11). A record with an id gets its id's
  IRI. An inlined record without one (qualifier bundles, amounts, quantities,
  ranges, comparators) gets `<owner IRI>/<slot>` (`/<slot>/<n>` when the slot
  is multivalued), so anything can be cited across files.
- Enum values are IRIs (D14): a value's `meaning`, else `<enum IRI>#<value>`,
  the IRIs gen-owl declares as individuals. Sentinel values (SENTINELS in
  clean_owl.py) record an absence and are not exported at all.
- Dates (D19): ISO 8601 strings are written verbatim, and their normalized
  xsd:dateTime bounds go beside them on `<slot>_lower_bound` and
  `<slot>_upper_bound` (half-open; see scripts/warp_time.py). No xsd:date,
  xsd:gYear or xsd:duration literal is written.
- Node records (`nodes`, `node_definitions`) are not exported here: a node is
  a class, and project/nodes.ttl says what it means. Statements point at node
  classes through the annotation properties warp:subject, warp:predicate and
  warp:object (D12).
- Relation triples (D16). For each annotated statement that is not negated,
  one triple `<subject> <predicate> <object>` is written, so the relation
  layer can be read without the qualifiers. Groups whose polarity lives in a
  qualifier register a function in RELATIONS that picks the predicate (a
  sub-property) and the object; the same predicate replaces the enum value in
  the record's warp:predicate. A negated statement exports its record and no
  relation triple. This file is RDF for SPARQL, never merged into the logical
  layer for reasoning: relation triples there may have a node class as
  subject.
"""

import argparse
import sys
from pathlib import Path

import yaml
from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.namespace import OWL, RDF, RDFS, XSD

sys.path.insert(0, str(Path(__file__).resolve().parent))
import warp_schema as ws  # noqa: E402
import warp_time  # noqa: E402
from clean_owl import SENTINELS  # noqa: E402

WARP = Namespace("https://w3id.org/ecoweaver/warp/")
STATEMENTS_ONTOLOGY = URIRef("https://w3id.org/ecoweaver/warp/ontology/statements")
EXPORT_VERSION = "warp-export-rdf/1"
NOT_EXPORTED = {"nodes", "node_definitions"}     # nodes are classes: project/nodes.ttl
SKIP_SLOTS = {"id", "type"}
DATE_PATTERN_MARK = "[0-9]{4}(-(0[1-9]|1[0-2])"
XSD_FOR = {"xsd:boolean": XSD.boolean, "xsd:integer": XSD.integer, "xsd:float": XSD.float,
           "xsd:double": XSD.double, "xsd:decimal": XSD.decimal, "xsd:dateTime": XSD.dateTime}


def is_date_slot(slot):
    return slot.range in ("date",) or bool(slot.pattern and DATE_PATTERN_MARK in slot.pattern)


# --- relation triples, per group (D16) -------------------------------------------
# Each function takes (exporter, group, record, record IRI) and returns
# (predicate IRI, object IRI) for the relation triple, or None for none. The
# default writes the predicate's own IRI between subject and object. Later
# groups register theirs here.

def default_relation(ex, group, record, iri):
    p = ex.predicate_iri(group, record)
    o = ex.iri(record["object"]) if record.get("object") else None
    return (p, o) if p is not None and o is not None else None


RELATIONS = {}


class Exporter:
    def __init__(self, sv):
        self.sv = sv
        self.pm = ws.prefix_map(sv)
        self.g = Graph()
        self.g.bind("warp", WARP)
        for p in ("node", "camo", "causal_mosaic", "RO", "BFO", "IAO", "orcid", "prop", "stmt", "doc", "site", "proj",
                  "comp", "crit", "scale", "place", "TODO", "wd", "ENVO", "NCBITaxon", "UO"):
            if p in self.pm:
                self.g.bind(p, self.pm[p])
        self.bound_props = set()
        import derive_propositions as dp
        self.groups = dp.load_groups(Path(sv.schema.source_file), all_groups=True)
        self.group_of_class = {g["statement_class"]: g for g in self.groups}
        self.group_of_class.update({g["proposition_class"]: g for g in self.groups})
        self.counts = {"records": 0, "relations": 0, "negated": 0, "sentinels": 0}

    # -- IRIs --------------------------------------------------------------

    def iri(self, curie):
        return URIRef(ws.expand(curie, self.pm))

    def class_iri(self, cls):
        return URIRef(self.sv.get_uri(self.sv.get_class(cls), expand=True, native=False))

    def slot_iri(self, slot):
        return URIRef(self.sv.get_uri(slot, expand=True, native=False))

    def enum_iri(self, enum_name):
        return URIRef(self.sv.expand_curie(f"{self.sv.schema.default_prefix}:{enum_name}"))

    def enum_value_iri(self, enum_name, value):
        if value in SENTINELS:
            self.counts["sentinels"] += 1
            return None
        pv = self.sv.get_enum(enum_name).permissible_values.get(value)
        if pv is not None and pv.meaning:
            return self.iri(pv.meaning)
        return URIRef(f"{self.enum_iri(enum_name)}#{value}")

    def predicate_iri(self, group, record):
        """The plain predicate IRI of a statement or proposition (its enum meaning)."""
        ename = self.sv.induced_slot("predicate", group["statement_class"]).range
        return self.enum_value_iri(ename, record["predicate"])

    # -- records -------------------------------------------------------------

    def literal(self, slot, value):
        t = self.sv.get_type(slot.range) if slot.range in self.sv.all_types() else None
        uri = t.uri if t is not None else None
        if uri in XSD_FOR:
            if uri == "xsd:dateTime":
                return Literal(str(value), datatype=XSD.dateTime, normalize=False)
            return Literal(value, datatype=XSD_FOR[uri])
        return Literal(str(value))

    def bounds(self, owner, slot, value):
        try:
            lo, hi = warp_time.bounds(str(value))
        except warp_time.TimeError:
            return
        base = str(self.slot_iri(slot))
        for suffix, dt in (("_lower_bound", lo), ("_upper_bound", hi)):
            p = URIRef(base + suffix)
            self.bound_props.add(p)
            self.g.add((owner, p, Literal(warp_time.xsd_datetime(dt), datatype=XSD.dateTime,
                                          normalize=False)))

    def value(self, owner, slot, value, child_iri):
        rng = slot.range
        if ws.is_class(self.sv, rng):
            if isinstance(value, dict):
                rid = value.get("id")
                iri = self.iri(rid) if isinstance(rid, str) else child_iri
                self.record(value, rng, iri)
                return iri
            return self.iri(value)
        if rng in self.sv.all_enums():
            return self.enum_value_iri(rng, value)
        if rng in ws.CURIE_RANGES:
            return self.iri(value)
        if is_date_slot(slot) and isinstance(value, str):
            self.bounds(owner, slot, value)
            return Literal(value)
        return self.literal(slot, value)

    def record(self, obj, cls, iri):
        cls = ws.concrete_class(self.sv, obj, cls)
        self.g.add((iri, RDF.type, self.class_iri(cls)))
        self.counts["records"] += 1
        slots = ws.induced_slots(self.sv, cls)
        for key, val in obj.items():
            slot = slots.get(key)
            if slot is None or key in SKIP_SLOTS or slot.identifier:
                continue
            p = self.slot_iri(slot)
            many = isinstance(val, list)
            for i, v in enumerate(val if many else [val]):
                if v is None:
                    continue
                child = URIRef(f"{iri}/{key}/{i}" if many else f"{iri}/{key}")
                o = self.value(iri, slot, v, child)
                if o is not None:
                    self.g.add((iri, p, o))
        group = self.group_of_class.get(cls)
        if group is not None and obj.get("predicate"):
            self.relation(group, obj, iri, is_statement=(cls == group["statement_class"]))

    def relation(self, group, record, iri, is_statement):
        fn = RELATIONS.get(group["group"], default_relation)
        rel = fn(self, group, record, iri)
        pred_slot = self.slot_iri(self.sv.induced_slot("predicate", group["statement_class"]))
        if rel is not None:
            p, o = rel
            # The record names the polarity-bearing predicate too (D16).
            self.g.remove((iri, pred_slot, None))
            self.g.add((iri, pred_slot, p))
        if not is_statement:
            return
        if record.get("negated"):
            self.counts["negated"] += 1
            return
        if rel is not None and record.get("subject"):
            p, o = rel
            self.g.add((self.iri(record["subject"]), p, o))
            self.counts["relations"] += 1

    def statement_set(self, data):
        root = ws.induced_slots(self.sv, "StatementSet")
        if isinstance(data.get("id"), str):
            set_iri = self.iri(data["id"])
            self.g.add((set_iri, RDF.type, self.class_iri("StatementSet")))
        for key, val in data.items():
            slot = root.get(key)
            if slot is None or key in NOT_EXPORTED or not isinstance(val, list):
                continue
            for obj in val:
                if isinstance(obj, dict) and isinstance(obj.get("id"), str):
                    self.record(obj, slot.range, self.iri(obj["id"]))

    def finish(self):
        self.g.add((STATEMENTS_ONTOLOGY, RDF.type, OWL.Ontology))
        self.g.add((STATEMENTS_ONTOLOGY, RDFS.label, Literal("WARP statements (reification layer)")))
        self.g.add((STATEMENTS_ONTOLOGY, RDFS.comment, Literal(
            "Who said what, on what basis. Nothing here is asserted as true of the world, and "
            "relation triples may have a node class as subject: query with SPARQL, never merge "
            "into the logical layer for reasoning. See docs/rdf-owl.md.")))
        self.g.add((STATEMENTS_ONTOLOGY, OWL.versionInfo, Literal(EXPORT_VERSION)))
        for p in sorted(self.bound_props):
            self.g.add((p, RDF.type, OWL.AnnotationProperty))
            self.g.add((p, RDFS.comment, Literal(
                "Normalized xsd:dateTime bound of an ISO 8601 date (half-open: lower inclusive, "
                "upper exclusive). Written by export_rdf.py beside the verbatim string (D19).")))
        return self.g


def export(sv, sets):
    ex = Exporter(sv)
    for data in sets:
        ex.statement_set(data)
    return ex.finish(), ex.counts


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("files", type=Path, nargs="+")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--schema", type=Path, default=ws.DEFAULT_SCHEMA)
    args = parser.parse_args(argv)
    sets = [yaml.safe_load(f.read_text(encoding="utf-8")) or {} for f in args.files]
    g, counts = export(ws.load(args.schema), sets)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    g.serialize(args.out, format="turtle")
    print(f"wrote {args.out}: {len(g)} triples, {counts['records']} record(s), "
          f"{counts['relations']} relation triple(s), {counts['negated']} negated statement(s) "
          f"with no relation triple, {counts['sentinels']} sentinel value(s) not exported")


if __name__ == "__main__":
    main()
