"""Shared helpers for EcoWeaver node templates (used by gen_dosdp.py and expand_nodes.py).

A template's logical definition is a nested class expression:

    ClassExpression := (genus CURIE | var NAME)  AND  restriction*
    Restriction     := property CURIE  some  ClassExpression
"""

import re
from pathlib import Path

import yaml

PLACEHOLDER = re.compile(r"\{([a-z][a-z0-9_]*)\}")


class TemplateError(ValueError):
    """A template or filling is malformed."""


def load_collection(path):
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    prefixes = {p["prefix"]: p["expansion"] for p in data["prefixes"]}
    labels = {t["id"]: t["label"] for t in data["terms"]}
    kinds = {t["id"]: t["kind"] for t in data["terms"]}
    templates = {t["id"]: t for t in data["templates"]}
    return {"prefixes": prefixes, "labels": labels, "kinds": kinds, "templates": templates}


def expand_curie(curie, prefixes):
    if "://" in curie:
        return curie
    prefix, _, local = curie.partition(":")
    if prefix not in prefixes:
        raise TemplateError(f"Unknown prefix in {curie!r}; declare it under 'prefixes'")
    return prefixes[prefix] + local


def walk(expr):
    """Yield every class expression and restriction in a nested expression."""
    yield ("expr", expr)
    for r in expr.get("restrictions") or []:
        yield ("restriction", r)
        yield from walk(r["filler"])


def check_template(template, labels, kinds):
    """Raise TemplateError for anything a generator would trip over."""
    tid = template["id"]
    declared = [v["name"] for v in template["vars"]]
    if len(set(declared)) != len(declared):
        raise TemplateError(f"{tid}: duplicate variable names")
    used = []
    for kind, item in walk(template["equivalent_to"]):
        if kind == "expr":
            has_genus, has_var = "genus" in item, "var" in item
            if has_genus == has_var:
                raise TemplateError(f"{tid}: each class expression needs exactly one of genus or var: {item}")
            if has_genus:
                need(item["genus"], "class", labels, kinds, tid)
            else:
                used.append(item["var"])
        else:
            need(item["property"], "object_property", labels, kinds, tid)
    for v in template["vars"]:
        need(v["range"], "class", labels, kinds, tid)
    missing = set(declared) - set(used)
    unknown = set(used) - set(declared)
    if unknown:
        raise TemplateError(f"{tid}: logical definition uses undeclared vars {sorted(unknown)}")
    if missing:
        raise TemplateError(f"{tid}: vars never used in the logical definition: {sorted(missing)}")
    for field in ("name", "definition"):
        bad = set(PLACEHOLDER.findall(template[field])) - set(declared)
        if bad:
            raise TemplateError(f"{tid}: {field} uses undeclared vars {sorted(bad)}")


def need(curie, kind, labels, kinds, tid):
    if curie not in labels:
        raise TemplateError(f"{tid}: {curie} has no label; add it under 'terms'")
    if kinds[curie] != kind:
        raise TemplateError(f"{tid}: {curie} is declared as {kinds[curie]}, used as {kind}")


def manchester(expr, labels, order):
    """Render a class expression as DOSDP Manchester text. Vars become %s and
    are appended to `order` in the order they appear."""
    if "var" in expr:
        head = "%s"
        order.append(expr["var"])
    else:
        head = quote(labels[expr["genus"]])
    parts = [head]
    for r in expr.get("restrictions") or []:
        filler = manchester(r["filler"], labels, order)
        if r["filler"].get("restrictions"):
            filler = f"({filler})"
        parts.append(f"({quote(labels[r['property']])} some {filler})")
    return " and ".join(parts)


def quote(label):
    return "'" + label.replace("'", "\\'") + "'"


def text_template(text):
    """'{a} of {b}' -> ('%s of %s', ['a', 'b'])"""
    order = PLACEHOLDER.findall(text)
    return PLACEHOLDER.sub("%s", text), order


def fill_text(text, values):
    return PLACEHOLDER.sub(lambda m: values[m.group(1)], text)
