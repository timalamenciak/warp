"""Schema-driven helpers shared by WARP's scripts.

Everything here reads the profile through linkml_runtime's SchemaView, so a
new predicate group, value class or prefix is picked up without code changes:

- ``load(path)``: a cached SchemaView.
- ``prefix_map(sv)``: every prefix declared in the profile and its imports.
- ``expand(curie, pm)``: CURIE to IRI; raises CurieError if the prefix is not
  declared (an undeclared prefix is an error, never a warning: D20).
- ``walk(sv, obj, cls)``: every slot value in a StatementSet (or any object),
  with the class and induced slot it belongs to, recursing into inlined
  objects. Concrete classes are taken from the ``type`` field when present.
- ``is_reference(sv, slot)``: the slot holds ids of objects defined elsewhere.
"""

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

from linkml_runtime.utils.schemaview import SchemaView

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SCHEMA = ROOT / "src" / "warp" / "schema" / "warp.yaml"
CURIE_RANGES = {"uriorcurie", "uri", "curie"}
OBO_BASE = "http://purl.obolibrary.org/obo/"


class CurieError(ValueError):
    """A CURIE whose prefix is not declared, or that is not a CURIE at all."""


@lru_cache(maxsize=4)
def load(path=DEFAULT_SCHEMA):
    return SchemaView(str(path))


def prefix_map(sv):
    """Prefix -> expansion, from the profile and every schema it imports.
    The profile's own declarations win over an import's."""
    pm = {}
    schemas = list(sv.schema_map.values())
    main = sv.schema
    for s in schemas:
        if s is main:
            continue
        for p, decl in (s.prefixes or {}).items():
            pm.setdefault(p, decl.prefix_reference)
    for p, decl in (main.prefixes or {}).items():
        pm[p] = decl.prefix_reference
    return pm


def split(curie):
    """('prefix', 'local') for a CURIE; raise CurieError if there is no colon."""
    if not isinstance(curie, str) or ":" not in curie:
        raise CurieError(f"not a CURIE: {curie!r}")
    prefix, _, local = curie.partition(":")
    return prefix, local


def is_absolute(value):
    return isinstance(value, str) and "://" in value


def expand(curie, pm):
    if is_absolute(curie):
        return curie
    prefix, local = split(curie)
    if prefix not in pm:
        raise CurieError(f"undeclared prefix {prefix!r} in {curie!r}")
    return pm[prefix] + local


def contract(iri, pm):
    """Shortest CURIE for an IRI under the declared prefixes, or the IRI."""
    best = None
    for p, base in pm.items():
        if iri.startswith(base) and (best is None or len(base) > len(pm[best])):
            best = p
    return f"{best}:{iri[len(pm[best]):]}" if best else iri


def is_obo(prefix, pm):
    return pm.get(prefix, "").startswith(OBO_BASE)


def annotation(element, key):
    """The value of an annotation on a schema element, or None.

    Induced slots sometimes carry annotations as a JsonObj rather than a dict,
    so look the key up both ways."""
    anns = element.annotations
    if not anns:
        return None
    try:
        ann = anns[key]
    except (KeyError, TypeError, AttributeError):
        ann = getattr(anns, key, None)
    if ann is None:
        return None
    if isinstance(ann, dict):
        return ann.get("value")
    return getattr(ann, "value", ann)


@lru_cache(maxsize=None)
def _induced(sv_id, cls):
    sv = _SV[sv_id]
    return {s.name: s for s in sv.class_induced_slots(cls)}


_SV = {}


def induced_slots(sv, cls):
    """{slot name: induced SlotDefinition} for a class (cached)."""
    _SV[id(sv)] = sv
    return _induced(id(sv), cls)


def is_class(sv, name):
    return name is not None and name in sv.all_classes()


def is_reference(sv, slot):
    """True when the slot's values are ids of objects defined elsewhere."""
    return is_class(sv, slot.range) and not sv.is_inlined(slot)


def is_curie_slot(sv, slot):
    """True when every value of the slot must be a CURIE or IRI."""
    return slot.range in CURIE_RANGES or bool(slot.identifier) or is_reference(sv, slot)


@dataclass
class Item:
    path: str          # e.g. causal_statements[0].predicate_qualifiers.causal_direction
    cls: str           # class owning the slot
    slot: Any          # induced SlotDefinition
    value: Any         # one value (multivalued slots yield one Item per value)
    owner: dict        # the object holding the slot


def concrete_class(sv, obj, declared):
    t = obj.get("type") if isinstance(obj, dict) else None
    if isinstance(t, str) and is_class(sv, t):
        return t
    return declared


def walk(sv, obj, cls, path=""):
    """Yield an Item for every slot value in obj, recursing into inlined objects."""
    if not isinstance(obj, dict):
        return
    cls = concrete_class(sv, obj, cls)
    slots = induced_slots(sv, cls)
    for key, val in obj.items():
        slot = slots.get(key)
        if slot is None:
            continue
        here = f"{path}.{key}" if path else key
        values = val if isinstance(val, list) else [val]
        for i, v in enumerate(values):
            p = f"{here}[{i}]" if isinstance(val, list) else here
            yield Item(p, cls, slot, v, obj)
            if isinstance(v, dict) and is_class(sv, slot.range):
                yield from walk(sv, v, slot.range, p)


def objects_with_ids(data):
    """{id: object} for every dict with a string id, anywhere in data."""
    found = {}

    def visit(node):
        if isinstance(node, dict):
            if isinstance(node.get("id"), str):
                found.setdefault(node["id"], node)
            for v in node.values():
                visit(v)
        elif isinstance(node, list):
            for v in node:
                visit(v)

    visit(data)
    return found
