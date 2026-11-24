#!/usr/bin/env python3
"""Report Target 2 area under chosen definitions of degraded and effective.

    python scripts/report_target2.py FILE.yaml [FILE.yaml ...] \
        --jurisdiction CA-SK --year 2026 \
        --degraded crit:degraded-area/fed-draft-1 [--degraded ...] \
        --effective crit:effective-restoration/fed-draft-1 [--effective ...] \
        [--include-planned] [--show-restricted] --out project/reports/target2.md

Pass derived statement sets (sites, projects, criteria). For each pair of a
degraded-area definition D and an effective-restoration definition E:

  1. sites in the jurisdiction with a degraded_area proposition under D;
  2. derived projects on those sites whose status is in_progress, completed
     or maintained (planned too, with --include-planned) and whose period
     overlaps the reporting year;
  3. of those, projects with an effective_restoration proposition under E;
  4. area. Without geometry the overlap of projects on one site is unknown,
     so area is reported as bounds: a lower bound (per site, the largest
     area treated by any counted project) and an upper bound (per site, the
     sum of the counted projects' areas, capped at the site's area).

Support is reported in three buckets rather than as a yes/no (decision D9,
as amended by Q15a): a proposition is SUPPORTED when at least one statement
supports it and none disputes it; CONTESTED when some support and some
dispute it; UNSUPPORTED otherwise (none supports it, or there is none). One
disputing claim from any claimant therefore moves a site from supported to
contested rather than out of the count, which a reporting policy can then
choose to count or not. The headline totals use the supported bucket; the
contested bucket is reported beside it. All of this is behind flags, and
several definition sets in one run give a comparison table, so the effect
of choosing a definition is visible.

Records under restricted care (access restricted or community_restricted)
count toward totals, but are listed individually only with
--show-restricted. Findings, not errors.
"""

import argparse
import sys
from collections import defaultdict
from itertools import product
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
import warp_time  # noqa: E402

ACTIVE = {"in_progress", "completed", "maintained"}
RESTRICTED = {"restricted", "community_restricted"}
BUCKETS = ("supported", "contested", "unsupported")


def index(sets):
    sites, projects, crit_props, statements = {}, [], [], {}
    for data in sets:
        for d in data.get("site_definitions") or []:
            sites[d["node"]] = d
        projects += data.get("implementation_propositions") or []
        crit_props += data.get("criteria_propositions") or []
        for s in data.get("criteria_statements") or []:
            statements[s["id"]] = s
    return sites, projects, crit_props, statements


def bucket(prop, statements):
    dirs = [statements.get(s, {}).get("direction") for s in prop.get("derived_from_statements") or []]
    if "supports" in dirs and "disputes" not in dirs:
        return "supported"
    if "supports" in dirs:
        return "contested"
    return "unsupported"


def verdicts(crit_props, statements, concept, crit_set):
    """{subject: bucket} for one concept under one criteria set. A subject with
    propositions for several assessed periods takes its best bucket."""
    order = {b: i for i, b in enumerate(BUCKETS)}
    out = {}
    for p in crit_props:
        q = p.get("predicate_qualifiers") or {}
        if p.get("object") != concept or q.get("criteria_set") != crit_set:
            continue
        b = bucket(p, statements)
        if p["subject"] not in out or order[b] < order[out[p["subject"]]]:
            out[p["subject"]] = b
    return out


def active_in(project, year, include_planned):
    statuses = {e.get("status") for e in project.get("status_by_claimant") or []}
    wanted = ACTIVE | ({"planned"} if include_planned else set())
    if not statuses & wanted:
        return False
    period = project.get("period") or {}
    if not period.get("start"):
        return False
    return warp_time.overlaps(warp_time.period_bounds(period["start"], period.get("end")),
                              warp_time.bounds(str(year)))


def project_area(project):
    """The largest area any claimant reports for the project, and its unit."""
    areas = [(a["area"]["value"], a["area"].get("unit")) for a in project.get("area_by_claimant") or []]
    return max(areas) if areas else (None, None)


def compute(sets, jurisdiction, year, degraded, effective, include_planned=False):
    sites, projects, crit_props, statements = index(sets)
    in_j = {sid: d for sid, d in sites.items() if d.get("jurisdiction") == jurisdiction}
    by_site = defaultdict(list)
    for p in projects:
        by_site[p["object"]].append(p)
    results = []
    for d_set, e_set in product(degraded, effective):
        site_v = verdicts(crit_props, statements, "degraded_area", d_set)
        proj_v = verdicts(crit_props, statements, "effective_restoration", e_set)
        row = {"degraded": d_set, "effective": e_set, "sites": {}, "projects": {}, "area": {}}
        for b in BUCKETS:
            sites_b = sorted(s for s in in_j if site_v.get(s, "unsupported") == b)
            row["sites"][b] = sites_b
        counted_sites = row["sites"]["supported"]
        candidates = [p for s in counted_sites for p in by_site.get(s, []) if active_in(p, year, include_planned)]
        for b in BUCKETS:
            row["projects"][b] = sorted((p["about_project"], p["object"]) for p in candidates
                                        if proj_v.get(p["about_project"], "unsupported") == b)
        effective_projects = [p for p in candidates if proj_v.get(p["about_project"]) == "supported"]
        lower = upper = 0.0
        units = set()
        for s in sorted({p["object"] for p in effective_projects}):
            vals = []
            for p in effective_projects:
                if p["object"] == s:
                    v, u = project_area(p)
                    if v is not None:
                        vals.append(v)
                        units.add(u)
            if not vals:
                continue
            cap = (in_j[s].get("area") or {}).get("value")
            lower += max(vals)
            upper += min(sum(vals), cap) if cap is not None else sum(vals)
        row["area"] = {"lower": lower, "upper": upper, "units": sorted(u for u in units if u)}
        results.append(row)
    return results, in_j


def render(results, sites, jurisdiction, year, show_restricted, include_planned):
    restricted = {s for s, d in sites.items() if (d.get("care") or {}).get("access_level") in RESTRICTED}

    def show(items):
        shown = [i for i in items if (i[1] if isinstance(i, tuple) else i) not in restricted or show_restricted]
        hidden = len(items) - len(shown)
        text = ", ".join(f"`{i[0]}` (`{i[1]}`)" if isinstance(i, tuple) else f"`{i}`" for i in shown) or "none"
        return text + (f" (+{hidden} under restricted care, not listed)" if hidden else "")

    lines = ["# Target 2 report", "",
             f"Jurisdiction `{jurisdiction}`, reporting year {year}. Generated by `scripts/report_target2.py`; "
             "every definition here is a placeholder.", "",
             "**How to read this.** A proposition is *supported* when at least one statement supports it and "
             "none disputes it, *contested* when some support and some dispute it, *unsupported* otherwise. "
             "Headline totals count supported sites and supported projects; contested ones are shown beside "
             "them, so a policy can decide whether to count them. Projects count when their status is in "
             "progress, completed or maintained" + (" (or planned)" if include_planned else "") + " and their "
             "period overlaps the year. Area is a range because there is no geometry to tell whether projects "
             "on one site overlap: the lower bound takes, per site, the largest area treated by one counted "
             "project; the upper bound adds them up, capped at the site's area.", "",
             "## Comparison", "",
             "| Degraded under | Effective under | Degraded sites (supported / contested / unsupported) | "
             "Projects on supported sites, effective (supported / contested / unsupported) | Area (lower to upper) |",
             "|---|---|---|---|---|"]
    for r in results:
        s, p, a = r["sites"], r["projects"], r["area"]
        unit = " ".join(a["units"])
        lines.append(f"| `{r['degraded']}` | `{r['effective']}` | {len(s['supported'])} / {len(s['contested'])} / "
                     f"{len(s['unsupported'])} | {len(p['supported'])} / {len(p['contested'])} / "
                     f"{len(p['unsupported'])} | {a['lower']:g} to {a['upper']:g} {unit} |")
    lines.append("")
    for r in results:
        lines += [f"## `{r['degraded']}` with `{r['effective']}`", ""]
        for b in BUCKETS:
            lines.append(f"- Degraded sites, {b}: {show(r['sites'][b])}")
        for b in BUCKETS:
            lines.append(f"- Projects on supported sites, effectiveness {b}: {show(r['projects'][b])}")
        lines.append("")
    if restricted and not show_restricted:
        lines += [f"{len(restricted)} site(s) are under restricted care: they count toward totals but are not "
                  "listed. Use --show-restricted where you are authorized to list them.", ""]
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("files", type=Path, nargs="+")
    parser.add_argument("--jurisdiction", required=True)
    parser.add_argument("--year", type=int, required=True)
    parser.add_argument("--degraded", action="append", required=True, help="degraded-area criteria set ID (repeatable)")
    parser.add_argument("--effective", action="append", required=True, help="effective-restoration criteria set ID (repeatable)")
    parser.add_argument("--include-planned", action="store_true")
    parser.add_argument("--show-restricted", action="store_true")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    sets = [yaml.safe_load(f.read_text(encoding="utf-8")) or {} for f in args.files]
    results, sites = compute(sets, args.jurisdiction, args.year, args.degraded, args.effective, args.include_planned)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(render(results, sites, args.jurisdiction, args.year, args.show_restricted,
                               args.include_planned) + "\n", encoding="utf-8")
    print(f"wrote {args.out}: {len(results)} definition pair(s)")
    for r in results:
        print(f"  {r['degraded']} x {r['effective']}: {len(r['sites']['supported'])} supported degraded site(s), "
              f"{len(r['projects']['supported'])} effective project(s), area {r['area']['lower']:g} to {r['area']['upper']:g}")


if __name__ == "__main__":
    main()
