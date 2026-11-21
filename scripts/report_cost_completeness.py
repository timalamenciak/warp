#!/usr/bin/env python3
"""Report how completely each cost statement meets Iacona et al.'s standards.

    python scripts/report_cost_completeness.py FILE.yaml [FILE.yaml ...] \
        --out project/reports/cost_completeness.md --csv project/reports/cost_completeness.csv

Pass derived statement sets (and the sets holding the study results their
sources report). For each cost statement it checks the five cost reporting
standards of Iacona et al. (2018), plus reporting level and basis, against
the slots the cost proposal maps them to: which required and recommended
fields are filled, which are missing, and a simple score (filled over
applicable). It also flags:

  - includes_categories [unknown]: the breakdown of a total is unknown;
  - cost_basis payment_rate: a payment is not necessarily a cost; check
    cost_bearer (flagged harder when there is none);
  - an amount with no value: a figure not yet transcribed.

stated_goal (standard 1) is looked up through the statement's reportedIn and
the EcoStudyResults reported in the same document. Findings, not errors:
the script always exits 0. A statement missing fields can still be recorded
and used; the report is what lets a sensitivity analysis exclude or
down-weight it.
"""

import argparse
import csv
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
import derive_propositions as dp  # noqa: E402

REQUIRED, RECOMMENDED = "required", "recommended"


def as_list(v):
    return v if isinstance(v, list) else ([] if v is None else [v])


def fields(s, goals):
    """[(standard, field, level, filled)] for one cost statement."""
    q = s.get("predicate_qualifiers") or {}
    amount = q.get("amount") or {}
    incurs = s.get("predicate") == "incurs_cost"
    total = incurs and s.get("object") == "total"
    has_goal = any(goals.get(d) for d in as_list(s.get("reportedIn")))
    rows = [
        ("1 Objective and outcome", "stated_goal (study result)", RECOMMENDED, has_goal),
        ("1 Objective and outcome", "outcome_reported", RECOMMENDED, bool(s.get("outcome_reported"))),
        ("2 Context and method", "phase", REQUIRED, bool(q.get("phase"))),
        ("2 Context and method", "intensity", RECOMMENDED, bool(q.get("intensity"))),
        ("2 Context and method", "starting_conditions", RECOMMENDED, bool(s.get("starting_conditions"))),
        ("2 Context and method", "context", RECOMMENDED, bool(s.get("context"))),
        ("3 When, where, scale", "place", REQUIRED, bool(s.get("place"))),
        ("3 When, where, scale", "period", RECOMMENDED, bool(s.get("period"))),
    ]
    if incurs:
        rows += [
            ("3 When, where, scale", "scale", REQUIRED, bool(q.get("scale") or q.get("count"))),
            ("4 Cost categories", "amount or effort", REQUIRED, bool(amount.get("value") is not None or q.get("effort"))),
            ("4 Cost categories", "cost_behaviour", RECOMMENDED, bool(q.get("cost_behaviour"))),
            ("4 Cost categories", "volunteer_effort", RECOMMENDED, bool(q.get("volunteer_effort"))),
        ]
        if total:
            rows.append(("4 Cost categories", "includes_categories", REQUIRED, bool(q.get("includes_categories"))))
        if amount:
            rows += [
                ("5 Currency and date", "amount.currency", REQUIRED, bool(amount.get("currency"))),
                ("5 Currency and date", "amount.price_year", REQUIRED, amount.get("price_year") is not None),
                ("5 Currency and date", "amount.adjustment", RECOMMENDED, bool(amount.get("adjustment"))),
            ]
    else:
        rows.append(("4 Cost categories", "ratio", REQUIRED, bool(q.get("ratio"))))
    rows += [
        ("Reporting level and basis", "reporting_level", REQUIRED, bool(q.get("reporting_level"))),
        ("Reporting level and basis", "cost_basis", RECOMMENDED, bool(q.get("cost_basis"))),
        ("Reporting level and basis", "cost_bearer", RECOMMENDED, bool(s.get("cost_bearer"))),
    ]
    return rows


def flags(s):
    q = s.get("predicate_qualifiers") or {}
    out = []
    if "unknown" in (q.get("includes_categories") or []):
        out.append("includes_categories [unknown]: breakdown not known")
    if q.get("cost_basis") == "payment_rate":
        out.append("payment_rate: a payment is not necessarily a cost"
                   + ("; check cost_bearer" if s.get("cost_bearer") else "; no cost_bearer given"))
    amount = q.get("amount")
    if amount is not None and amount.get("value") is None:
        out.append("amount has no value yet (TODO)")
    if s.get("transferred_from"):
        out.append(f"transferred from {s['transferred_from']} under {s.get('transfer_rule')}")
    return out


def analyse(sets, schema=dp.DEFAULT_SCHEMA):
    g = {x["group"]: x for x in dp.load_groups(schema, all_groups=True)}["cost"]
    goals = {}
    for data in sets:
        for r in data.get("study_results") or []:
            for d in as_list(r.get("reportedIn")):
                if r.get("stated_goal"):
                    goals.setdefault(d, r["stated_goal"])
    out = []
    for data in sets:
        for s in data.get(g["statements_slot"]) or []:
            rows = fields(s, goals)
            filled = sum(1 for *_, f in rows if f)
            missing_req = [f for _, f, lvl, ok in rows if lvl == REQUIRED and not ok]
            missing_rec = [f for _, f, lvl, ok in rows if lvl == RECOMMENDED and not ok]
            out.append({"statement": s["id"], "predicate": s.get("predicate"), "object": s.get("object"),
                        "score": round(filled / len(rows), 2), "missing_required": missing_req,
                        "missing_recommended": missing_rec, "flags": flags(s), "rows": rows})
    return out


def render(results):
    lines = ["# Cost completeness report", "",
             "Generated by `scripts/report_cost_completeness.py`. Each cost statement checked against "
             "Iacona et al. (2018)'s five cost reporting standards, plus reporting level and basis. "
             "Score is filled fields over applicable fields. Findings, not errors.", "",
             "| Statement | Predicate | Object | Score | Missing (required) | Flags |",
             "|---|---|---|---|---|---|"]
    for r in sorted(results, key=lambda r: r["score"]):
        lines.append(f"| `{r['statement']}` | {r['predicate']} | {r['object']} | {r['score']:.2f} | "
                     f"{', '.join(r['missing_required']) or 'none'} | {'; '.join(r['flags'])} |")
    lines.append("")
    for r in results:
        lines += [f"## `{r['statement']}`", "", "| Standard | Field | Level | Filled |", "|---|---|---|---|"]
        lines += [f"| {std} | {f} | {lvl} | {'yes' if ok else '**no**'} |" for std, f, lvl, ok in r["rows"]]
        lines.append("")
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("files", type=Path, nargs="+")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--csv", type=Path)
    args = parser.parse_args(argv)
    sets = [yaml.safe_load(f.read_text(encoding="utf-8")) or {} for f in args.files]
    results = analyse(sets)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(render(results) + "\n", encoding="utf-8")
    if args.csv:
        with args.csv.open("w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh)
            w.writerow(["statement", "predicate", "object", "score", "missing_required",
                        "missing_recommended", "flags"])
            for r in results:
                w.writerow([r["statement"], r["predicate"], r["object"], r["score"],
                            "; ".join(r["missing_required"]), "; ".join(r["missing_recommended"]),
                            "; ".join(r["flags"])])
    print(f"wrote {args.out}: {len(results)} cost statement(s)")


if __name__ == "__main__":
    main()
