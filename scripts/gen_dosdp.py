#!/usr/bin/env python3
"""Generate DOSDP pattern files from EcoWeaver node templates.

    python scripts/gen_dosdp.py templates/node_templates.yaml patterns/

Writes one <template_id>.yaml per template, plus prefixes.yaml for
dosdp-tools. The LinkML templates file is the source of truth: never edit the
generated patterns by hand.

The patterns use only the DOSDP basics (classes, relations, vars, name, def,
equivalentTo), so they work with dosdp-tools and the ODK pattern pipeline.
"""

import argparse
import sys
from pathlib import Path

import yaml

from templates_lib import (
    TemplateError, check_template, load_collection, manchester, text_template,
)

PATTERN_BASE = "https://w3id.org/ecoweaver/patterns/"

# DOSDP only knows 'development' and 'published'.
DOSDP_STATUS = {"draft": "development", "testing": "development", "released": "published"}


def to_dosdp(template, labels, kinds):
    check_template(template, labels, kinds)

    used = set()
    def collect(expr):
        if "genus" in expr:
            used.add(expr["genus"])
        for r in expr.get("restrictions") or []:
            used.add(r["property"])
            collect(r["filler"])
    collect(template["equivalent_to"])
    used.update(v["range"] for v in template["vars"])

    classes = {labels[c]: c for c in sorted(used) if kinds[c] == "class"}
    relations = {labels[c]: c for c in sorted(used) if kinds[c] == "object_property"}

    order = []
    equivalent = manchester(template["equivalent_to"], labels, order)
    name_text, name_vars = text_template(template["name"])
    def_text, def_vars = text_template(template["definition"])

    pattern = {
        "pattern_name": template["id"],
        "pattern_iri": f"{PATTERN_BASE}{template['id']}.yaml",
        "description": " ".join(template["description"].split()),
        "classes": classes,
        "relations": relations,
        "vars": {v["name"]: f"'{labels[v['range']]}'" for v in template["vars"]},
        "name": {"text": name_text, "vars": name_vars},
        "def": {"text": " ".join(def_text.split()), "vars": def_vars},
        "equivalentTo": {"text": equivalent, "vars": order},
    }
    if not relations:
        del pattern["relations"]
    status = DOSDP_STATUS.get(template.get("status", "draft"))
    if status:  # deprecated templates get no DOSDP status
        pattern = {**dict(list(pattern.items())[:3]), "status": status, **dict(list(pattern.items())[3:])}
    return pattern


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("templates", type=Path)
    parser.add_argument("outdir", type=Path)
    args = parser.parse_args(argv)

    coll = load_collection(args.templates)
    args.outdir.mkdir(parents=True, exist_ok=True)
    failed = False
    for tid, template in coll["templates"].items():
        try:
            pattern = to_dosdp(template, coll["labels"], coll["kinds"])
        except TemplateError as err:
            print(f"ERROR {err}", file=sys.stderr)
            failed = True
            continue
        out = args.outdir / f"{tid}.yaml"
        out.write_text(
            f"# GENERATED from {args.templates.as_posix()} by scripts/gen_dosdp.py. Do not edit.\n"
            + yaml.safe_dump(pattern, sort_keys=False, allow_unicode=True, width=1000),
            encoding="utf-8",
        )
        print(f"wrote {out}")
    (args.outdir / "prefixes.yaml").write_text(
        "# GENERATED. Pass to dosdp-tools with --prefixes.\n"
        + yaml.safe_dump(coll["prefixes"], sort_keys=True),
        encoding="utf-8",
    )
    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
