#!/usr/bin/env python3
"""Derive projects from implementation statements (WARP).

    python scripts/derive_projects.py IN.yaml OUT.yaml [--previous OLD.yaml] [--names SET.yaml ...]

Runs after derive_strategies.py, so statement subjects are canonical
strategy nodes, and before derive_propositions.py (which leaves the
implementation group to this script: warp_derived_by), so the project nodes
it adds name the projects that criteria propositions are about. With
--names, strategies and sites defined in other files are named too. Rule
warp-impl-identity/1:

  Two implementation statements describe the same project when they share
  an external ID (same scheme and value), or when they have the same
  subject (canonical strategy or action), the same site and overlapping
  periods. An open end means ongoing. Overlap is computed on normalized
  ISO 8601 bounds (scripts/warp_time.py), never by comparing strings: the
  proposal's periods are 2024-05 and 2023, which no string ordering
  handles. Linked statements are clustered with union-find. Sites match only
  by ID in this version; there is no spatial matching (no geometry library
  is a dependency).

Each cluster gives two records (decision D17):

  - an ImplementationProposition, the grouping record: member statements,
    each claimant's latest status (latest reported_on within that claimant
    only) and area treated, kept and attributed rather than resolved; the
    union of implementers, funders and external IDs; the envelope of
    periods; and `about_project`, the project it is about (IAO:0000136);
  - the project itself, proj:<id>: the work, an occurrent. project_owl.py
    writes it to project/projects.ttl, typed by its strategy class and
    located at its site. It also gets a node record here, so criteria
    statements about it resolve.

Project IDs. The record and the individual share their local ID. When the
cluster has external IDs, the ID is the smallest of them,
proj:<scheme>-<value>: stable when a statement joins, unless the newcomer
brings an external ID that sorts first. Without external IDs it is a hash of
the site, subject and earliest period start: stable unless the newcomer
starts earlier. No scheme is fully stable, so when an ID moves the old one
is recorded in `replaces` (comparing with the previous derived file), and
OWL marks it deprecated, as for strategies.

A cluster holding two different external IDs from the same scheme is
reported as a candidate bad merge for review.
"""

import argparse
import hashlib
import re
import sys
from collections import defaultdict
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
import derive_propositions as dp  # noqa: E402
import warp_time  # noqa: E402

RULE_VERSION = "warp-impl-identity/1"


def slug(text):
    return re.sub(r"[^A-Za-z0-9]+", "-", str(text)).strip("-").lower()


class UnionFind:
    def __init__(self, items):
        self.parent = {i: i for i in items}

    def find(self, i):
        while self.parent[i] != i:
            self.parent[i] = self.parent[self.parent[i]]
            i = self.parent[i]
        return i

    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.parent[max(ra, rb)] = min(ra, rb)


def claimant(s):
    return next((c.get("contributor") for c in s.get("contributions") or [] if c.get("role") == "author"), None)


def ext_ids(s):
    return [(e["scheme"], str(e["value"])) for e in (s.get("predicate_qualifiers") or {}).get("external_ids") or []]


def period(s):
    return (s.get("predicate_qualifiers") or {}).get("period") or {}


def cluster(statements):
    """Union-find over statement indexes; returns lists of statements."""
    uf = UnionFind(range(len(statements)))
    by_ext = defaultdict(list)
    for i, s in enumerate(statements):
        for e in ext_ids(s):
            by_ext[e].append(i)
    for members in by_ext.values():
        for j in members[1:]:
            uf.union(members[0], j)
    for i, a in enumerate(statements):
        for j in range(i + 1, len(statements)):
            b = statements[j]
            if a["subject"] == b["subject"] and a["object"] == b["object"]:
                try:
                    if warp_time.period_overlaps(period(a), period(b)):
                        uf.union(i, j)
                except (warp_time.TimeError, KeyError):
                    pass   # an unreadable period links nothing; check_values reports it
    groups = defaultdict(list)
    for i, s in enumerate(statements):
        groups[uf.find(i)].append(s)
    return [groups[k] for k in sorted(groups)]


def project_local_id(members):
    ids = sorted({e for s in members for e in ext_ids(s)})
    if ids:
        scheme, value = ids[0]
        return f"{slug(scheme)}-{slug(value)}"
    first = members[0]
    starts = sorted(warp_time.bounds(period(s)["start"])[0] for s in members if period(s).get("start"))
    anchor = f"{first['object']}|{first['subject']}|{starts[0].isoformat() if starts else ''}"
    return hashlib.sha1(anchor.encode("utf-8")).hexdigest()[:12]


def envelope(members):
    lows, highs, open_end = [], [], False
    starts, ends = {}, {}
    for s in members:
        p = period(s)
        if not p.get("start"):
            continue
        lo, hi = warp_time.period_bounds(p["start"], p.get("end"))
        lows.append(lo)
        starts[lo] = p["start"]
        if hi is None:
            open_end = True
        else:
            highs.append(hi)
            ends[hi] = p["end"]
    out = {}
    if lows:
        out["start"] = starts[min(lows)]
    if highs and not open_end:
        out["end"] = ends[max(highs)]
    return out


def aggregate(members):
    statuses, areas = {}, []
    for s in members:
        q = s.get("predicate_qualifiers") or {}
        who = claimant(s)
        rep = q.get("reported_on")
        key = warp_time.bounds(rep)[0] if rep else None
        prev = statuses.get(who)
        if prev is None or (key is not None and (prev[0] is None or key > prev[0])):
            entry = {"claimant": who, "status": q.get("status"), "statement": s["id"]}
            if rep:
                entry["reported_on"] = rep
            statuses[who] = (key, entry)
        if q.get("area_treated"):
            areas.append({"claimant": who, "area": q["area_treated"], "statement": s["id"]})
    union = lambda field: sorted({a for s in members for a in (s.get("predicate_qualifiers") or {}).get(field) or []})  # noqa: E731
    ext = sorted({e for s in members for e in ext_ids(s)})
    return {
        "status_by_claimant": [v[1] for _, v in sorted(statuses.items(), key=lambda kv: str(kv[0]))],
        "area_by_claimant": areas,
        "implemented_by": union("implemented_by"),
        "funded_by": union("funded_by"),
        "external_ids": [{"scheme": a, "value": b} for a, b in ext],
        "period": envelope(members),
    }


def bad_merges(members):
    by_scheme = defaultdict(set)
    for s in members:
        for scheme, value in ext_ids(s):
            by_scheme[scheme].add(value)
    return {k: sorted(v) for k, v in by_scheme.items() if len(v) > 1}


def derive(data, previous=None, schema=dp.DEFAULT_SCHEMA, names=None):
    """Derive projects in place. Returns a report dict. `names` ({node id:
    name}) names strategies and sites defined in other sets; the set's own
    nodes win."""
    g = {x["group"]: x for x in dp.load_groups(schema, all_groups=True)}.get("implementation")
    if g is None:
        # A profile without the implementation group (config/profiles.yaml):
        # nothing to derive, and the input passes through unchanged.
        return {"projects": [], "bad_merges": [], "no_group": True}
    statements = data.get(g["statements_slot"]) or []
    if not statements:
        data.pop(g["propositions_slot"], None)
        return {"projects": [], "bad_merges": []}
    prev_by_member = {}
    for p in (previous or {}).get(g["propositions_slot"]) or []:
        for sid in p.get("derived_from_statements") or []:
            prev_by_member[sid] = p
    names = {**(names or {}), **dp.names_from(data)}
    props, report = [], {"projects": [], "bad_merges": []}
    nodes = data.setdefault("nodes", [])
    have = {n["id"] for n in nodes}
    for members in cluster(statements):
        local = project_local_id(members)
        pid, proj = f"prop:{local}", f"proj:{local}"
        first = members[0]
        rendered = dp.render(g["templates"], names, first["subject"], first["predicate"], first["object"],
                             False, "assertional")
        prop = {
            "id": pid,
            "type": g["proposition_class"],
            "subject": first["subject"],
            "predicate": first["predicate"],
            "object": first["object"],
            "negated": False,
            "scope": "assertional",
            "propositionText": rendered,
            "status": "asserted",
            "identity_key": " + ".join(sorted(s["id"] for s in members)),
            "identity_rule_version": g.get("rule", RULE_VERSION),
            "derived_from_statements": [s["id"] for s in members],
            "about_project": proj,
        }
        prop.update({k: v for k, v in aggregate(members).items() if v})
        old = []
        for s in members:
            p = prev_by_member.get(s["id"])
            if p is not None:
                for o in [p["about_project"], *(p.get("replaces") or [])]:
                    if o != proj and o not in old:
                        old.append(o)
        if old:
            prop["replaces"] = old
        merges = bad_merges(members)
        if merges:
            report["bad_merges"].append((pid, merges))
        for s in members:
            s["proposition"] = pid
            dp.set_evidence_targets(s, pid)
        props.append(prop)
        if proj not in have:
            nodes.append({
                "id": proj,
                "name": f"Project {local}: {dp.word(first['subject'], names)} at "
                        f"{dp.word(first['object'], names)}",
                "entity_type": "management_intervention",
                "entity_term": f"project (derived by {RULE_VERSION})",
            })
            have.add(proj)
        report["projects"].append(prop)
    data[g["propositions_slot"]] = sorted(props, key=lambda p: p["id"])
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--previous", type=Path,
                        help="an earlier derived file, to record superseded project IDs "
                             "(default: the output file, if it exists)")
    parser.add_argument("--schema", type=Path, default=dp.DEFAULT_SCHEMA)
    parser.add_argument("--names", type=Path, nargs="*", default=[],
                        help="other statement sets whose nodes name the strategies and sites "
                             "a project is named after (pass every derived file)")
    args = parser.parse_args(argv)
    data = yaml.safe_load(args.input.read_text(encoding="utf-8")) or {}
    others = [yaml.safe_load(p.read_text(encoding="utf-8")) or {} for p in args.names if p.exists()]
    prev_path = args.previous or (args.output if args.output.exists() else None)
    previous = yaml.safe_load(prev_path.read_text(encoding="utf-8")) if prev_path else None
    report = derive(data, previous, args.schema, dp.names_from(*others))
    text = args.input.read_text(encoding="utf-8")
    header = text.splitlines()[0] if text.startswith("# GENERATED") else \
        "# GENERATED by scripts/derive_*.py. Do not edit derived records by hand."
    args.output.write_text(header + "\n" + yaml.safe_dump(data, sort_keys=False, allow_unicode=True, width=100),
                           encoding="utf-8")
    if report.get("no_group"):
        print("implementation: not in this schema; nothing derived")
        return
    print(f"implementation: {len(report['projects'])} project(s) under {RULE_VERSION}")
    for p in report["projects"]:
        print(f"  {p['id']} -> {p['about_project']}  <- {', '.join(p['derived_from_statements'])}")
    for pid, merges in report["bad_merges"]:
        print(f"  CANDIDATE BAD MERGE {pid}: two external IDs from one scheme: {merges}", file=sys.stderr)


if __name__ == "__main__":
    main()
