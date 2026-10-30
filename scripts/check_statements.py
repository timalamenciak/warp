#!/usr/bin/env python3
"""Check WARP statement sets for what the schema cannot express.

linkml-validate checks shapes and enums. SEPIO leaves some constraints to
"additional tooling"; this is that tooling. Pass every file that refers to
another together, so cross-file references resolve (e.g. an assessment and
the derived statement set it cites).

Errors (exit status 1):
  - Assertion Mode: annotated statements leave direction, strength, score
    and subjectClassification empty. Only SynthesisAssessment fills them.
  - Negation: on causal statements, negated is true exactly when
    causal_language is no_relationship (CAMO convention).
  - Specialized fields: a generic SEPIO field is empty when WARP's named
    specialization is used (EvidenceLine.subtype vs evidence_type,
    Contribution.activityType vs role).
  - Contribution roles are where they belong: author on a statement,
    evidence_assessor on an evidence line, annotator in recordMetadata.
  - CARE: statements authored by an Indigenous knowledge holder or community
    member carry care metadata.
  - References resolve to an id in the files given: proposition,
    targetProposition, evidence_item_refs, contributor, knowledge_holders,
    reportedIn, and statement / proposition subject and object.
  - An id means one thing: objects repeated under the same id (e.g. a
    dataset inlined under two study results) must be identical.

Warnings:
  - An annotated statement or assessment with no author contribution.
  - An annotated statement with no annotator in recordMetadata.

Usage:
    python scripts/check_statements.py FILE.yaml [FILE.yaml ...] [--schema PATH]
"""

import argparse
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from derive_propositions import DEFAULT_SCHEMA, load_groups  # noqa: E402

ASSESSMENT_ONLY = ("direction", "strength", "score", "subjectClassification")
CARE_REQUIRED_KINDS = {"indigenous_knowledge_holder", "community_member"}
ROLE_PLACES = {
    "author": "statement",
    "evidence_assessor": "evidence_line",
    "annotator": "record",
}


def walk_ids(node, out):
    """Collect (id, object) for every object with an `id` in a nested structure."""
    if isinstance(node, dict):
        if isinstance(node.get("id"), str):
            out.append((node["id"], node))
        for v in node.values():
            walk_ids(v, out)
    elif isinstance(node, list):
        for v in node:
            walk_ids(v, out)


def as_list(value):
    if value is None:
        return []
    return value if isinstance(value, list) else [value]


class Checker:
    def __init__(self, known_ids, agents):
        self.known = known_ids
        self.agents = agents
        self.errors = []
        self.warnings = []

    def error(self, where, msg):
        self.errors.append(f"{where}: {msg}")

    def warn(self, where, msg):
        self.warnings.append(f"{where}: {msg}")

    def refs(self, where, field, values):
        for v in as_list(values):
            if v not in self.known:
                self.error(where, f"{field} '{v}' does not resolve to any id")

    def contributions(self, where, contribs, place):
        roles = []
        for c in as_list(contribs):
            cid = c.get("id", "?")
            role = c.get("role")
            roles.append(role)
            if c.get("activityType"):
                self.error(cid, "activityType is set; use role (its WARP specialization) only")
            expected = ROLE_PLACES.get(role)
            if expected and expected != place:
                self.error(cid, f"role '{role}' belongs on a {expected.replace('_', ' ')}, "
                                f"not a {place.replace('_', ' ')} ({where})")
            self.refs(cid, "contributor", c.get("contributor"))
        return roles

    def evidence_lines(self, where, lines):
        for line in as_list(lines):
            lid = line.get("id", where)
            if line.get("subtype") and line.get("evidence_type"):
                self.error(lid, "subtype is set; use evidence_type (its WARP specialization) only")
            self.refs(lid, "targetProposition", line.get("targetProposition"))
            self.refs(lid, "evidence_item_refs", line.get("evidence_item_refs"))
            self.contributions(lid, line.get("contributions"), "evidence_line")

    def statement(self, s, annotated):
        sid = s.get("id", "?")
        if annotated:
            for f in ASSESSMENT_ONLY:
                if s.get(f) not in (None, ""):
                    self.error(sid, f"{f} is set, but annotated statements are in SEPIO "
                                    "Assertion Mode (use a SynthesisAssessment)")
        if "causal_language" in s:
            negated = bool(s.get("negated", False))
            if (s["causal_language"] == "no_relationship") != negated:
                self.error(sid, f"negated is {str(negated).lower()} but causal_language is "
                                f"'{s['causal_language']}' (negated iff no_relationship)")

        roles = self.contributions(sid, s.get("contributions"), "statement")
        if "author" not in roles:
            self.warn(sid, "no contribution with role author (who made the statement?)")
        record_roles = self.contributions(
            sid, (s.get("recordMetadata") or {}).get("contributions"), "record")
        if annotated and "annotator" not in record_roles:
            self.warn(sid, "no annotator in recordMetadata.contributions")

        authors = [c.get("contributor") for c in as_list(s.get("contributions"))
                   if c.get("role") == "author"]
        kinds = {(self.agents.get(a) or {}).get("agent_kind") for a in authors}
        if kinds & CARE_REQUIRED_KINDS and not s.get("care"):
            self.error(sid, "authored by an Indigenous knowledge holder or community member "
                            "but has no care metadata")
        self.refs(sid, "knowledge_holders", (s.get("care") or {}).get("knowledge_holders"))

        self.refs(sid, "proposition", s.get("proposition"))
        self.refs(sid, "reportedIn", s.get("reportedIn"))
        for f in ("subject", "object"):
            self.refs(sid, f, s.get(f))
        self.evidence_lines(sid, s.get("hasEvidenceLines"))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("files", type=Path, nargs="+")
    parser.add_argument("--schema", type=Path, default=DEFAULT_SCHEMA)
    args = parser.parse_args(argv)

    groups = load_groups(args.schema)
    sets = [(f, yaml.safe_load(f.read_text(encoding="utf-8")) or {}) for f in args.files]

    known, agents, dupes = set(), {}, []
    for f, data in sets:
        found, seen = [], {}
        walk_ids(data, found)
        for i, obj in found:
            if i in seen and seen[i] != obj:
                dupes.append(f"{f}: id '{i}' is used for two different objects")
            seen.setdefault(i, obj)
        known.update(seen)
        for a in data.get("agents") or []:
            agents[a["id"]] = a

    checker = Checker(known, agents)
    checker.errors += dupes
    for _, data in sets:
        for g in groups:
            for s in data.get(g["statements_slot"]) or []:
                checker.statement(s, annotated=True)
            for p in data.get(g["propositions_slot"]) or []:
                for f in ("subject", "object"):
                    checker.refs(p.get("id", "?"), f, p.get(f))
        for a in data.get("assessments") or []:
            checker.statement(a, annotated=False)

    for w in checker.warnings:
        print("warning:", w, file=sys.stderr)
    for e in checker.errors:
        print("error:", e, file=sys.stderr)
    print(f"{len(checker.errors)} error(s), {len(checker.warnings)} warning(s) "
          f"in {len(sets)} file(s)")
    return 1 if checker.errors else 0


if __name__ == "__main__":
    sys.exit(main())
