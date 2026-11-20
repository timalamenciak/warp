#!/usr/bin/env python3
"""Project propositions that pass the gate into OWL: the logical layer.

    python scripts/project_owl.py FILE.yaml [FILE.yaml ...] --out project/axioms.ttl \
        [--report project/reports/projection.md]

Pass derived statement sets and the assessments that cite them. Writes an
OWL 2 EL ontology that imports the node classes, holding one class axiom per
proposition that passes the projection gate (decision D15), and nothing else.

The gate. A proposition projects only when ALL of these hold:

  1. scope is `universal`. OWL 2 has no defaults and no non-monotonic
     reasoning, so `prototypical` ("typically, allowing exceptions") has no
     rendering: a subclass axiom would be exceptionless, stronger than the
     source. `assertional` is about particular things and is no class axiom.
  2. negated is false. A null result is not a relation.
  3. every statement grouped under it has `modality: observed`. An inferred
     or anticipated statement is a derivation or a forecast, not a report.
  4. at least one SynthesisAssessment supports it (direction `supports`). One
     statement is a source's view; an axiom is WARP's, and the assessment is
     where that judgement is made.

Then the group's projection function, if it has one, decides the axiom. A
group with none projects nothing, which is the default (PROJECTIONS below).
Causal and interaction project existential subsumption:

    <subject node> rdfs:subClassOf [ owl:onProperty <predicate> ;
                                     owl:someValuesFrom <object node> ]

never owl:equivalentClass, and never a plain triple between two class IRIs.
Every axiom carries an axiom annotation, warp:derived_from, naming the
proposition it came from.

The report says how many propositions were considered, how many passed, and
why each rejected one failed. On the worked examples nothing passes: they are
assertional or prototypical. That is the correct answer, not a reason to
loosen the gate.
"""

import argparse
import sys
from collections import defaultdict
from pathlib import Path

import yaml
from rdflib import BNode, Graph, Literal, URIRef
from rdflib.namespace import OWL, RDF, RDFS

sys.path.insert(0, str(Path(__file__).resolve().parent))
import warp_schema as ws  # noqa: E402

AXIOMS_ONTOLOGY = URIRef("https://w3id.org/ecoweaver/warp/ontology/axioms")
NODES_ONTOLOGY = URIRef("https://w3id.org/ecoweaver/warp/ontology/nodes")
DERIVED_FROM = URIRef("https://w3id.org/ecoweaver/warp/derived_from")
GATE_VERSION = "warp-projection-gate/1"


# --- projection functions, per group --------------------------------------------
# Each takes (projector, group, proposition) and returns a list of
# (subject class IRI, property IRI, filler class IRI) existential axioms, or
# an empty list when this proposition has nothing to project.

def existential(pj, group, prop):
    p = pj.predicate_iri(group, prop)
    if p is None:
        return []
    return [(pj.iri(prop["subject"]), p, pj.iri(prop["object"]))]


PROJECTIONS = {
    "causal": existential,
    "interaction": existential,
}


class Projector:
    def __init__(self, sv):
        self.sv = sv
        self.pm = ws.prefix_map(sv)
        import derive_propositions as dp
        self.groups = dp.load_groups(Path(sv.schema.source_file), all_groups=True)

    def iri(self, curie):
        return URIRef(ws.expand(curie, self.pm))

    def predicate_iri(self, group, prop):
        enum = self.sv.get_enum(self.sv.induced_slot("predicate", group["statement_class"]).range)
        pv = enum.permissible_values.get(prop["predicate"])
        return self.iri(pv.meaning) if pv is not None and pv.meaning else None

    def gate(self, prop, statements, assessments):
        """List of reasons the proposition fails the gate (empty if it passes)."""
        reasons = []
        if prop.get("scope") != "universal":
            reasons.append(f"scope is {prop.get('scope')}, not universal")
        if prop.get("negated"):
            reasons.append("negated")
        members = prop.get("derived_from_statements") or []
        if not members:
            reasons.append("no statements grouped under it")
        not_observed = [s for s in members if (statements.get(s) or {}).get("modality") != "observed"]
        if not_observed:
            reasons.append(f"{len(not_observed)} of {len(members)} statement(s) not modality observed")
        if not any(a.get("direction") == "supports" for a in assessments.get(prop["id"], [])):
            reasons.append("no supporting SynthesisAssessment")
        return reasons

    def run(self, sets):
        statements, assessments, props = {}, defaultdict(list), []
        for data in sets:
            for g in self.groups:
                for s in data.get(g["statements_slot"]) or []:
                    statements[s["id"]] = s
                for p in data.get(g["propositions_slot"]) or []:
                    props.append((g, p))
            for a in data.get("assessments") or []:
                if a.get("proposition"):
                    assessments[a["proposition"]].append(a)

        out = Graph()
        out.bind("warp", "https://w3id.org/ecoweaver/warp/")
        for p in ("node", "camo", "RO", "prop", "biolink"):
            if p in self.pm:
                out.bind(p, self.pm[p])
        out.add((AXIOMS_ONTOLOGY, RDF.type, OWL.Ontology))
        out.add((AXIOMS_ONTOLOGY, RDFS.label, Literal("WARP projected axioms")))
        out.add((AXIOMS_ONTOLOGY, OWL.imports, NODES_ONTOLOGY))
        out.add((AXIOMS_ONTOLOGY, OWL.versionInfo, Literal(GATE_VERSION)))
        out.add((AXIOMS_ONTOLOGY, RDFS.comment, Literal(
            "Class axioms projected from WARP propositions that passed the projection gate "
            "(scope universal, not negated, every statement observed, supported by a synthesis "
            "assessment). Each axiom is annotated with warp:derived_from <proposition>.")))
        out.add((DERIVED_FROM, RDF.type, OWL.AnnotationProperty))

        report = {"considered": 0, "passed": [], "rejected": defaultdict(list), "no_projection": defaultdict(list)}
        seen = set()
        for g, prop in props:
            if prop["id"] in seen:
                continue
            seen.add(prop["id"])
            report["considered"] += 1
            reasons = self.gate(prop, statements, assessments)
            if reasons:
                report["rejected"][g["group"]].append((prop["id"], reasons))
                continue
            fn = PROJECTIONS.get(g["group"])
            axioms = fn(self, g, prop) if fn else []
            if not axioms:
                report["no_projection"][g["group"]].append(prop["id"])
                continue
            for sub, p, filler in axioms:
                out.add((p, RDF.type, OWL.ObjectProperty))
                out.add((sub, RDF.type, OWL.Class))
                out.add((filler, RDF.type, OWL.Class))
                r = BNode()
                out.add((r, RDF.type, OWL.Restriction))
                out.add((r, OWL.onProperty, p))
                out.add((r, OWL.someValuesFrom, filler))
                out.add((sub, RDFS.subClassOf, r))
                ax = BNode()
                out.add((ax, RDF.type, OWL.Axiom))
                out.add((ax, OWL.annotatedSource, sub))
                out.add((ax, OWL.annotatedProperty, RDFS.subClassOf))
                out.add((ax, OWL.annotatedTarget, r))
                out.add((ax, DERIVED_FROM, self.iri(prop["id"])))
            report["passed"].append((g["group"], prop["id"], len(axioms)))
        return out, report


def render_report(report):
    lines = ["# Projection report", "",
             f"Gate `{GATE_VERSION}`: scope universal, not negated, every grouped statement "
             "`modality: observed`, and a supporting SynthesisAssessment. Generated by "
             "`scripts/project_owl.py`; see docs/rdf-owl.md section 6.", "",
             f"- Propositions considered: {report['considered']}",
             f"- Passed the gate and projected: {len(report['passed'])}",
             f"- Rejected by the gate: {sum(len(v) for v in report['rejected'].values())}",
             f"- Passed, but the group projects nothing: "
             f"{sum(len(v) for v in report['no_projection'].values())}", ""]
    if not report["passed"]:
        lines += ["Nothing passed. On the worked examples this is the correct answer: their "
                  "propositions are assertional or prototypical, and OWL 2 cannot say "
                  "\"typically\". Do not loosen the gate to change it.", ""]
    else:
        lines += ["## Projected", ""]
        for group, pid, n in report["passed"]:
            lines.append(f"- `{pid}` ({group}): {n} axiom(s)")
        lines.append("")
    if report["rejected"]:
        lines += ["## Rejected, by group", ""]
        for group in sorted(report["rejected"]):
            lines.append(f"### {group}")
            lines.append("")
            for pid, reasons in report["rejected"][group]:
                lines.append(f"- `{pid}`: {'; '.join(reasons)}")
            lines.append("")
    if report["no_projection"]:
        lines += ["## Passed the gate, nothing to project", ""]
        for group in sorted(report["no_projection"]):
            for pid in report["no_projection"][group]:
                lines.append(f"- `{pid}` ({group}): this group projects nothing")
        lines.append("")
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("files", type=Path, nargs="+")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--report", type=Path)
    parser.add_argument("--schema", type=Path, default=ws.DEFAULT_SCHEMA)
    args = parser.parse_args(argv)
    sets = [yaml.safe_load(f.read_text(encoding="utf-8")) or {} for f in args.files]
    g, report = Projector(ws.load(args.schema)).run(sets)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    g.serialize(args.out, format="turtle")
    text = render_report(report)
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(text + "\n", encoding="utf-8")
    print(f"wrote {args.out}: {len(report['passed'])} of {report['considered']} proposition(s) projected")
    for group in sorted(report["rejected"]):
        print(f"  {group}: {len(report['rejected'][group])} rejected")
        for pid, reasons in report["rejected"][group]:
            print(f"    {pid}: {'; '.join(reasons)}")
    if not report["passed"]:
        print("  none passed: the examples are assertional or prototypical, which is the correct answer")


if __name__ == "__main__":
    main()
