#!/usr/bin/env python3
"""Transfer costs to another place, price year and currency, explicitly.

    python scripts/transfer_costs.py FILE.yaml [FILE.yaml ...] \
        --select config/cost_transfer/selection.yaml \
        --out examples/cost_statements.transferred.yaml

Reusing a cost in another year, currency or region is never silent: it
creates a NEW derived cost statement, with EcoWeaver as claimant
(warp:agent/ecoweaver-synthesis, as for synthesis assessments), naming its
source (transferred_from), the versioned rule that adjusted it
(transfer_rule) and the steps applied (transfer_steps). Source statements
are never modified.

The rule (config/cost_transfer/<rule>.yaml) declares the target place, price
year and currency, a price index table per currency, exchange rates, a
regional labour rate per person-day, and per cost category whether it is
re-priced, indexed or left unchanged:

  - reprice (labour): when the source gives effort in the labour rate's unit
    (person-days), the amount is effort x the regional rate, rather than a
    scaled dollar total; without such effort, it falls back to index.
  - index: amount x index[target year] / index[price year], in the source
    currency, then converted at the exchange rate.
  - unchanged: converted to the target currency, not indexed.

A source without an amount value, currency or price year (and not
re-priceable from effort) is refused and reported, as is one whose currency
or years are missing from the rule's tables.

The derived amount cites the source amount it was computed from
(derived_from_amount: `<source>/predicate_qualifiers/amount`), which is why
amounts are named individuals in RDF (decision D11). IDs include the rule
ID, so changing the rule version regenerates the derived statements under
new IDs. Propositions are derived for the output in the same run.
"""

import argparse
import copy
import re
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
import derive_propositions as dp  # noqa: E402

ECOWEAVER = "warp:agent/ecoweaver-synthesis"
TREATMENTS = {"reprice", "index", "unchanged"}
RULE_KEYS = ("id", "target_place", "target_price_year", "target_currency", "price_indices",
             "exchange_rates", "labour_rates", "categories")


class TransferRefused(ValueError):
    """A cost that cannot be transferred under the rule."""


def slug(text):
    return re.sub(r"[^A-Za-z0-9]+", "-", text).strip("-").lower()


def load_rule(path):
    rule = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    missing = [k for k in RULE_KEYS if k not in rule]
    if missing:
        raise SystemExit(f"ERROR rule {path} is missing {missing}")
    bad = {c: t for c, t in rule["categories"].items() if t not in TREATMENTS}
    if bad:
        raise SystemExit(f"ERROR rule {path}: unknown treatments {bad}; use {sorted(TREATMENTS)}")
    return rule


def index_amount(value, currency, year, rule, steps):
    target = rule["target_price_year"]
    table = rule["price_indices"].get(currency) or {}
    if year not in table or target not in table:
        raise TransferRefused(f"no {currency} price index for {year} and {target} in {rule['id']}")
    factor = table[target] / table[year]
    steps.append(f"indexed {currency} {year} to {target} (x{factor:.4f})")
    return value * factor


def convert(value, currency, rule, steps):
    target = rule["target_currency"]
    if currency == target:
        return value, None
    rate = (rule["exchange_rates"] or {}).get(currency)
    if rate is None:
        raise TransferRefused(f"no exchange rate {currency} to {target} in {rule['id']}")
    steps.append(f"converted {currency} to {target} at {rate}")
    return value * rate, rate


def transfer(source, rule):
    """A new derived CostStatement for `source` under `rule`; raises TransferRefused."""
    sid = source["id"]
    if source.get("predicate") != "incurs_cost":
        raise TransferRefused("only incurs_cost statements are transferred")
    q = source.get("predicate_qualifiers") or {}
    category = source.get("object")
    treatment = rule["categories"].get(category)
    if treatment is None:
        raise TransferRefused(f"rule {rule['id']} says nothing about category {category!r}")
    steps, conversion, indexed = [], None, False
    labour = (rule["labour_rates"] or {}).get(rule["target_place"])
    effort = [e for e in q.get("effort") or [] if labour and e.get("unit") == labour.get("unit")]

    if treatment == "reprice" and effort:
        days = sum(e["value"] for e in effort)
        value = days * labour["rate"]
        steps.append(f"labour re-priced from effort: {days:g} person-days x {labour['rate']:g} "
                     f"{rule['target_currency']} ({rule['target_place']}, {rule['target_price_year']})")
        derived_from = None
    else:
        amount = q.get("amount") or {}
        if amount.get("value") is None:
            raise TransferRefused("no amount value (and no effort to re-price)")
        if not amount.get("currency"):
            raise TransferRefused("amount has no currency")
        if amount.get("price_year") is None:
            raise TransferRefused("amount has no price_year")
        value, currency, year = float(amount["value"]), amount["currency"], amount["price_year"]
        if treatment == "reprice":
            steps.append("no effort in person-days to re-price: indexed instead")
        if treatment in ("index", "reprice"):
            value = index_amount(value, currency, year, rule, steps)
            indexed = True
        value, conversion = convert(value, currency, rule, steps)
        derived_from = f"{sid}/predicate_qualifiers/amount"

    new_q = copy.deepcopy(q)
    new_amount = {"value": round(value, 2), "currency": rule["target_currency"],
                  "price_year": rule["target_price_year"],
                  "adjustment": "inflation" if indexed else "none"}
    if conversion is not None:
        new_amount["conversion_rate"] = conversion
    if derived_from:
        new_amount["derived_from_amount"] = derived_from
    new_q["amount"] = new_amount

    local = sid.split(":", 1)[-1]
    rid = slug(rule["id"])
    new_id = f"stmt:transfer/{rid}/{local}"
    return {
        "id": new_id,
        "type": "CostStatement",
        "subject": source["subject"],
        "predicate": source["predicate"],
        "object": source["object"],
        "scope": source.get("scope"),
        "modality": "inferred",
        "place": [rule["target_place"]],
        "statementText": (f"{source.get('statementText', sid)} Re-stated for {rule['target_place']} in "
                          f"{rule['target_price_year']} {rule['target_currency']} under {rule['id']}."),
        "predicate_qualifiers": new_q,
        "transferred_from": sid,
        "transfer_rule": rule["id"],
        "transfer_steps": steps,
        "contributions": [{"id": f"warp:contrib/transfer/{rid}/{local}-author", "type": "EcoContribution",
                           "role": "author", "contributor": ECOWEAVER}],
        # The pipeline that wrote the record is also its recorder.
        "recordMetadata": {"contributions": [{"id": f"warp:contrib/transfer/{rid}/{local}-record",
                                              "type": "EcoContribution", "role": "annotator",
                                              "contributor": ECOWEAVER}]},
        "hasEvidenceLines": [{"id": f"warp:el/transfer/{rid}/{local}", "type": "EcoEvidenceLine",
                              "evidence_type": "modeling_simulation", "directionOfEvidenceProvided": "supports",
                              "evidence_item_refs": [sid]}],
    }


def run(sets, selection, rule):
    sources = {}
    for data in sets:
        for s in data.get("cost_statements") or []:
            sources.setdefault(s["id"], s)
    out, refused = [], []
    for sid in selection.get("statements") or []:
        source = sources.get(sid)
        if source is None:
            refused.append((sid, "not found in the files given"))
            continue
        if source.get("transferred_from"):
            refused.append((sid, "already a transferred statement; transfer its source instead"))
            continue
        try:
            out.append(transfer(source, rule))
        except TransferRefused as err:
            refused.append((sid, str(err)))
    return out, refused


def build_set(sets, selection, rule, schema=dp.DEFAULT_SCHEMA):
    """The generated StatementSet of transferred costs, with its propositions
    derived, and the list of refusals."""
    derived, refused = run(sets, selection, rule)
    out = {
        "id": f"warp:statementset/cost-transfers-{slug(rule['id'])}",
        "profile_version": sets[0].get("profile_version", "0.7.0") if sets else "0.7.0",
        "agents": [{"id": ECOWEAVER, "type": "EcoAgent", "name": "EcoWeaver synthesis pipeline",
                    "subtype": "software", "agent_kind": "synthesis_pipeline"}],
        "cost_statements": derived,
    }
    dp.derive_all(out, schema, dp.names_from(*sets))
    return out, refused


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("files", type=Path, nargs="+", help="derived statement sets holding the source costs")
    parser.add_argument("--select", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--schema", type=Path, default=dp.DEFAULT_SCHEMA)
    args = parser.parse_args(argv)
    selection = yaml.safe_load(args.select.read_text(encoding="utf-8")) or {}
    rule = load_rule(Path(selection["rule"]))
    sets = [yaml.safe_load(f.read_text(encoding="utf-8")) or {} for f in args.files]
    out, refused = build_set(sets, selection, rule, args.schema)
    derived = out["cost_statements"]
    args.out.write_text(
        f"# GENERATED by scripts/transfer_costs.py ({rule['id']}) from {args.select.as_posix()}.\n"
        "# Derived cost statements: never edit by hand. Rule values are placeholders.\n"
        + yaml.safe_dump(out, sort_keys=False, allow_unicode=True, width=100),
        encoding="utf-8",
    )
    print(f"wrote {args.out}: {len(derived)} transferred cost statement(s) under {rule['id']}")
    for s in derived:
        print(f"  {s['id']}: {s['predicate_qualifiers']['amount']['value']} "
              f"{s['predicate_qualifiers']['amount']['currency']}  ({'; '.join(s['transfer_steps'])})")
    for sid, why in refused:
        print(f"  refused {sid}: {why}", file=sys.stderr)


if __name__ == "__main__":
    main()
