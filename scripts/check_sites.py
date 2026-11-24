#!/usr/bin/env python3
"""Check sites, implementation statements and criteria statements.

    python scripts/check_sites.py FILE.yaml [FILE.yaml ...]

Pass statement sets together with the sets that define the sites, criteria
sets and projects they cite. Errors (exit status 1):

  Sites (particulars, decisions D7, D11)
  - a site definition's ID is under site:, and nothing defined from a
    class-expression or composite template is;
  - geometry_precision withheld means no geometry at all;
  - GeoJSON geometry (text starting with "{") parses as JSON.
  Implementation
  - the object of carried_out_at is a site defined in the files given.
  Criteria
  - the subject is a particular: a site (site:) or project (proj:);
  - the criteria set exists, and its `operationalizes` equals the
    statement's object (the concept).

Warnings:
  - exact geometry on a site whose care access is restricted or
    community_restricted (consider generalizing it);
  - a subject whose kind does not match the criteria set's assessment_unit
    (site individuals against `site`; project individuals against the rest).

No geometry library is used (none is a dependency), so geometry is only
checked to parse, never for validity or overlap.
"""

import argparse
import json
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
import derive_propositions as dp  # noqa: E402

RESTRICTED = {"restricted", "community_restricted"}


def check(sets, schema=dp.DEFAULT_SCHEMA):
    groups = {g["group"]: g for g in dp.load_groups(schema, all_groups=True)}
    errors, warnings = [], []
    sites, crit_sets = {}, {}
    for data in sets:
        for d in data.get("site_definitions") or []:
            sites[d["node"]] = d
        for c in data.get("criteria_sets") or []:
            crit_sets[c["id"]] = c
        for d in (data.get("node_definitions") or []) + (data.get("strategy_definitions") or []):
            if str(d.get("node", "")).startswith("site:"):
                errors.append(f"{d['node']}: only sites are under site:; this is a {d.get('template')} node")

    for sid, d in sites.items():
        if not sid.startswith("site:"):
            errors.append(f"{sid}: a site's ID must be under site:, not node: (decision D11)")
        geom, precision = d.get("geometry"), d.get("geometry_precision")
        if precision == "withheld" and geom:
            errors.append(f"{sid}: geometry_precision is withheld, so no geometry may be recorded")
        if isinstance(geom, str) and geom.lstrip().startswith("{"):
            try:
                json.loads(geom)
            except json.JSONDecodeError as err:
                errors.append(f"{sid}: GeoJSON geometry does not parse: {err}")
        access = (d.get("care") or {}).get("access_level")
        if precision == "exact" and geom and access in RESTRICTED:
            warnings.append(f"{sid}: exact geometry under {access} care access; consider generalizing it")

    impl = groups.get("implementation")
    crit = groups.get("criteria")
    for data in sets:
        for s in data.get(impl["statements_slot"]) or [] if impl else []:
            if s.get("object") not in sites:
                errors.append(f"{s['id']}: carried_out_at needs a site as object; {s.get('object')} is not "
                              "a site defined in the files given")
        for s in data.get(crit["statements_slot"]) or [] if crit else []:
            sid, subject, concept = s["id"], s.get("subject", ""), s.get("object")
            kind = "site" if subject.startswith("site:") else "project" if subject.startswith("proj:") else None
            if kind is None:
                errors.append(f"{sid}: a criteria statement's subject is a site (site:) or project (proj:) "
                              f"individual, not {subject}")
            cset_id = (s.get("predicate_qualifiers") or {}).get("criteria_set")
            cset = crit_sets.get(cset_id)
            if cset is None:
                errors.append(f"{sid}: criteria set {cset_id} is not defined in the files given")
                continue
            if cset.get("operationalizes") != concept:
                errors.append(f"{sid}: object is {concept} but {cset_id} operationalizes "
                              f"{cset.get('operationalizes')}")
            unit = cset.get("assessment_unit")
            if unit and kind == "site" and unit != "site":
                warnings.append(f"{sid}: a site judged against {cset_id}, whose assessment unit is {unit}")
            if unit and kind == "project" and unit == "site":
                warnings.append(f"{sid}: a project judged against {cset_id}, whose assessment unit is a site")
    return errors, warnings


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("files", type=Path, nargs="+")
    parser.add_argument("--schema", type=Path, default=dp.DEFAULT_SCHEMA)
    args = parser.parse_args(argv)
    sets = [yaml.safe_load(f.read_text(encoding="utf-8")) or {} for f in args.files]
    errors, warnings = check(sets, args.schema)
    for w in warnings:
        print("warning:", w, file=sys.stderr)
    for e in errors:
        print("error:", e, file=sys.stderr)
    print(f"check_sites: {len(errors)} error(s), {len(warnings)} warning(s) in {len(sets)} file(s)")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
