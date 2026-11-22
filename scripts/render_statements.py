"""Render whole statements as English sentences (Rosetta Statements).

    python scripts/render_statements.py FILE... [--out REPORT.md] [--check]
                                        [--config config/rosetta.yaml] [--schema S]

A proposition's text (derive_propositions.py) says only subject, predicate,
object, scope and negation. This script says everything a statement records,
in one sentence per statement, so a reviewer can read the structured record
next to the source's own words (`statementText`, `original_text`,
`source_spans`) and see whether they agree. Rule `warp-rosetta/1`
(constant RULE_VERSION).

What each slot contributes is set in config/rosetta.yaml, by class, and
inherited along `is_a`, so the code names no group, slot or enum value. The
predicate's own words come from the `rosetta_template` annotations on the
group's predicate enum (the templates propositions use), put into the
negative or the past tense with the config's verb table.

Every value is accounted for. A value is rendered by a template, shown
verbatim (`quoted`), shown in the report outside the sentence with a stated
reason (`elsewhere`), or it is an error. `--check` fails (exit 1) when:

- a slot reachable from a statement class (or a `roots` class) is covered by
  no template, `quoted`, `elsewhere`, `unused` or `claim` entry of its class
  or an ancestor;
- a template names a slot its class does not have;
- a predicate's template cannot be put in the negative or past tense;
- a statement in FILE... has a value that was not rendered (a value in an
  `unused` slot, or in a segment dropped for want of another value).

Labels for references come from the files given (nodes, agents, documents,
sites, criteria sets, propositions, statements, study results; pass files
that cite each other together), the local term register (vocab/local/) and
the source scales (vocab/scales.yaml). A reference with no label is printed
as its CURIE and listed under the statement in the report.
"""

import argparse
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
import warp_schema as ws  # noqa: E402
from derive_propositions import load_groups  # noqa: E402
from gen_vocab import SCALE, load_register, load_scales  # noqa: E402

RULE_VERSION = "warp-rosetta/1"
ROOT = ws.ROOT
DEFAULT_CONFIG = ROOT / "config" / "rosetta.yaml"
CLAIM = "@claim"
GROUP = "@group"
CLAIM_SLOTS = ("subject", "predicate", "object", "negated", "direction")
PH = re.compile(r"^(@?\w+|\*)(?:\[(\w+)(!?=)([^\]]*)\])?(?::(\w+))?(?:\|([^}]*))?$")


class RosettaError(ValueError):
    pass


# --- templates ----------------------------------------------------------------

@dataclass
class Ph:
    name: str
    field: str = None
    op: str = None
    value: str = None
    variant: str = None
    default: str = None


@dataclass
class Opt:
    nodes: list = field(default_factory=list)


def parse(text):
    """A template as a list of str, Ph and Opt. `{slot}` is a placeholder
    (`{slot[field=value]}` filters a list, `{slot:variant}` picks a named
    template of the value's class, `{slot|text}` gives text to use when the
    slot has no value); `[...]` is a segment rendered only when every
    placeholder directly inside it has a value. `{*}` is the joined parts of
    a list template, in its `frame`."""
    stack = [Opt()]
    i = 0
    while i < len(text):
        c = text[i]
        if c == "{":
            j = text.index("}", i)
            m = PH.match(text[i + 1:j])
            if not m:
                raise RosettaError(f"bad placeholder {text[i:j + 1]!r} in {text!r}")
            stack[-1].nodes.append(Ph(*m.groups()))
            i = j + 1
            continue
        if c == "[":
            stack.append(Opt())
        elif c == "]":
            if len(stack) == 1:
                raise RosettaError(f"unbalanced ']' in {text!r}")
            seg = stack.pop()
            stack[-1].nodes.append(seg)
        else:
            if stack[-1].nodes and isinstance(stack[-1].nodes[-1], str):
                stack[-1].nodes[-1] += c
            else:
                stack[-1].nodes.append(c)
        i += 1
    if len(stack) != 1:
        raise RosettaError(f"unbalanced '[' in {text!r}")
    return stack[0].nodes


def placeholders(nodes):
    for n in nodes:
        if isinstance(n, Ph):
            yield n
        elif isinstance(n, Opt):
            yield from placeholders(n.nodes)


# --- config -------------------------------------------------------------------

TEMPLATE_KEYS = ("template", "frame", "sentence", "clauses", "record", "label")


class Config:
    def __init__(self, path, sv):
        data = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
        self.path = Path(path)
        self.sv = sv
        self.classes = data.get("classes") or {}
        self.enum_phrases = data.get("enum_phrases") or {}
        self.verbs = data.get("verbs") or {}
        self.predicates = data.get("predicates") or {}
        self.claim = data.get("claim") or {}
        self.roots = data.get("roots") or []
        self.parsed = {}

    def chain(self, cls):
        """Config entries for a class and its ancestors, nearest first."""
        names = self.sv.class_ancestors(cls) if ws.is_class(self.sv, cls) else [cls]
        return [(n, self.classes[n]) for n in names if n in self.classes]

    def first(self, cls, key, variant=None):
        for _, c in self.chain(cls):
            if variant:
                v = (c.get("variants") or {}).get(variant)
                if v is not None:
                    return v
            elif c.get(key) is not None:
                return c[key]
        return None

    def union(self, cls, key):
        out = {}
        for _, c in reversed(self.chain(cls)):
            v = c.get(key) or {}
            out.update(v if isinstance(v, dict) else {k: None for k in v})
        return out

    def phrase(self, cls, slot, enum, value):
        key = str(value).lower() if isinstance(value, bool) else str(value)
        for _, c in self.chain(cls):
            ph = (c.get("phrases") or {}).get(slot)
            if ph and key in ph:
                return ph[key]
        ph = self.enum_phrases.get(enum) or {}
        return ph.get(key)

    def nodes(self, text):
        if text not in self.parsed:
            self.parsed[text] = parse(text)
        return self.parsed[text]


# --- rendering ------------------------------------------------------------------

@dataclass
class Out:
    text: str = ""
    used: set = field(default_factory=set)
    aside: dict = field(default_factory=dict)       # path -> (reason, value)
    unlabelled: set = field(default_factory=set)

    def merge(self, other):
        self.used |= other.used
        self.aside.update(other.aside)
        self.unlabelled |= other.unlabelled


def fmt_number(v):
    """A number as written: a small float keeps its ".0" (pH 6.0), a large
    whole one drops it (69996.0 hectares reads 69996)."""
    if isinstance(v, float) and v.is_integer() and abs(v) < 1e15:
        return str(int(v)) if v >= 1000 else str(v)
    return str(v)


def clean_text(v):
    text = " ".join(str(v).split())
    return text[:-1] if text.endswith(".") and not text.endswith("..") else text


def join(parts, sep=None):
    parts = [p for p in parts if p]
    if sep:
        return sep.join(parts)
    if len(parts) < 3:
        return " and ".join(parts)
    return ", ".join(parts[:-1]) + " and " + parts[-1]


def capitalise(text):
    return text[:1].upper() + text[1:]


class Renderer:
    def __init__(self, schema=ws.DEFAULT_SCHEMA, config=DEFAULT_CONFIG,
                 local=ROOT / "vocab" / "local", scales=ROOT / "vocab" / "scales.yaml"):
        self.sv = ws.load(schema)
        self.pm = ws.prefix_map(self.sv)
        self.cfg = Config(config, self.sv)
        self.groups = {g["statement_class"]: g for g in load_groups(schema, all_groups=True)}
        self.index = {}             # id -> (class, object)
        self.parts = None           # the joined parts of the list template being framed
        self.vocab = self._vocab_labels(local, scales)

    # labels ------------------------------------------------------------------

    def _vocab_labels(self, local, scales):
        labels = {}
        if local and Path(local).exists():
            for sch in load_register(local, self.pm):
                labels[sch["iri"]] = sch["label"]
                for t in sch["terms"]:
                    labels[t["iri"]] = t["label"]
        if scales and Path(scales).exists():
            for s in load_scales(scales):
                labels[str(SCALE[s["id"]])] = s["label"]
                for v in s.get("values") or []:
                    labels[f"{SCALE}{s['id']}/{v['id']}"] = v.get("label", v["id"])
        return labels

    def add_files(self, datas):
        """Index every identified object in the statement sets, by the range
        of the StatementSet slot that lists it."""
        slots = ws.induced_slots(self.sv, "StatementSet")
        for data in datas:
            for key, items in (data or {}).items():
                slot = slots.get(key)
                if slot is None or not ws.is_class(self.sv, slot.range) or not isinstance(items, list):
                    continue
                ident = self.sv.get_identifier_slot(slot.range)
                for obj in items:
                    if isinstance(obj, dict) and ident is not None and obj.get(ident.name):
                        cls = ws.concrete_class(self.sv, obj, slot.range)
                        self.index.setdefault(obj[ident.name], (cls, obj))

    def label(self, ref, out):
        if ref in self.index:
            cls, obj = self.index[ref]
            options = self.cfg.first(cls, "label")
            for text in ([options] if isinstance(options, str) else options or []):
                r = self.render_nodes(self.cfg.nodes(text), obj, cls, "", Out())
                if r is not None and r.text.strip():
                    out.unlabelled |= r.unlabelled
                    text = r.text.strip()
                    if self.cfg.first(cls, "label_lower_first"):
                        text = text[:1].lower() + text[1:]
                    return clean_text(text)
        try:
            iri = ws.expand(ref, self.pm)
        except ws.CurieError:
            iri = None
        if iri in self.vocab:
            return self.vocab[iri]
        out.unlabelled.add(ref)
        return ref

    # values ------------------------------------------------------------------

    def one(self, v, slot, cls, path, variant, out):
        enum = slot.range if slot.range in self.sv.all_enums() else None
        if isinstance(v, dict):
            if not ws.is_class(self.sv, slot.range):
                raise RosettaError(f"{path}: an object in {cls}.{slot.name}, whose range is {slot.range}")
            r = self.render_object(v, ws.concrete_class(self.sv, v, slot.range), path, variant)
            out.merge(r)
            return r.text
        out.used.add(path)
        phrase = self.cfg.phrase(cls, slot.name, enum, v)
        if phrase is not None:
            return phrase
        if enum:
            pv = self.sv.get_enum(enum).permissible_values.get(str(v))
            title = pv is not None and (pv.title or ws.annotation(pv, "preferred_label"))
            return title or str(v).replace("_", " ")
        if isinstance(v, str) and not slot.identifier and (
                ws.is_curie_slot(self.sv, slot) or v in self.index):
            return self.label(v, out)
        if isinstance(v, bool):
            return "yes" if v else "no"
        if isinstance(v, (int, float)):
            return fmt_number(v)
        return clean_text(v)

    def value(self, obj, cls, path, ph, out):
        """The rendered value of a placeholder, or None when it has none."""
        if ph.name == CLAIM:
            return self.claim(obj, cls, path, out)
        if ph.name == "*":
            return self.parts or ph.default
        slot = ws.induced_slots(self.sv, cls).get(ph.name)
        if slot is None:
            raise RosettaError(f"config: {cls} has no slot {ph.name!r}")
        raw = obj.get(ph.name)
        if raw is None or raw == [] or raw == "" or raw == {}:
            return ph.default
        here = f"{path}.{ph.name}" if path else ph.name
        items = list(enumerate(raw)) if isinstance(raw, list) else [(None, raw)]
        parts = []
        for i, v in items:
            p = here if i is None else f"{here}[{i}]"
            if ph.field:
                fv = v.get(ph.field) if isinstance(v, dict) else None
                if (str(fv) == ph.value) != (ph.op == "="):
                    continue
                out.used.add(f"{p}.{ph.field}")
            text = self.one(v, slot, cls, p, ph.variant, out)
            if text:
                parts.append(text)
        return join(parts) or ph.default

    def render_nodes(self, nodes, obj, cls, path, out):
        """Render a segment into a new Out; None if a placeholder directly
        inside it has no value."""
        seg = Out()
        text = []
        for n in nodes:
            if isinstance(n, str):
                text.append(n)
            elif isinstance(n, Ph):
                v = self.value(obj, cls, path, n, seg)
                if v is None:
                    return None
                text.append(v)
            else:
                r = self.render_nodes(n.nodes, obj, cls, path, out)
                if r is not None:
                    text.append(r.text)
                    seg.merge(r)
        seg.text = "".join(text)
        return seg

    def render_clauses(self, clauses, obj, cls, path, sep=", "):
        out = Out()
        parts = []
        for clause in clauses:
            r = self.render_nodes(self.cfg.nodes(clause), obj, cls, path, out)
            if r is not None and r.text.strip():
                parts.append(r.text.strip())
                out.merge(r)
        out.text = sep.join(parts)
        return out

    def aside(self, obj, cls, path, out):
        """Values of a class's `quoted` and `elsewhere` slots: shown outside
        the sentence."""
        reasons = {**self.cfg.union(cls, "elsewhere"),
                   **{k: "quoted" for k in self.cfg.union(cls, "quoted")}}
        for name, reason in reasons.items():
            if name in obj and obj[name] not in (None, [], ""):
                p = f"{path}.{name}" if path else name
                for leaf in leaves(obj[name], p):
                    out.aside[leaf] = (reason, None)
                    out.used.add(leaf)
                out.aside[p] = (reason, self.shown(obj[name], cls, name))

    def shown(self, value, cls, name):
        """A value kept out of the sentence, as text: objects by their template."""
        slot = ws.induced_slots(self.sv, cls)[name]
        items = value if isinstance(value, list) else [value]
        texts = []
        for v in items:
            if isinstance(v, dict) and ws.is_class(self.sv, slot.range):
                texts.append(self.render_object(v, ws.concrete_class(self.sv, v, slot.range), "").text)
            else:
                texts.append(clean_text(v) if isinstance(v, str) else str(v))
        return "; ".join(texts)

    def render_object(self, obj, cls, path, variant=None):
        tmpl = self.cfg.first(cls, "template", variant) if variant else self.cfg.first(cls, "template")
        if tmpl is None:
            raise RosettaError(f"config: no {'variant ' + repr(variant) if variant else 'template'} for {cls}")
        if isinstance(tmpl, str):
            out = self.render_clauses([tmpl], obj, cls, path)
        else:
            out = self.render_clauses(tmpl, obj, cls, path, sep=self.cfg.first(cls, "sep") or ", ")
            frame = None if variant else self.cfg.first(cls, "frame")
            if frame:
                saved, self.parts = self.parts, out.text
                r = self.render_nodes(self.cfg.nodes(frame), obj, cls, path, out)
                self.parts = saved
                if r is None:
                    out = Out()
                else:
                    out.merge(r)
                    out.text = r.text
        self.aside(obj, cls, path, out)
        return out

    # the claim -----------------------------------------------------------------

    def framing(self, st):
        """(negative?, frame or None) from the config's `claim.when` rules."""
        neg, frame = False, None
        for rule in self.cfg.claim.get("when") or []:
            if st.get(rule["slot"]) == rule["equals"]:
                neg = neg or rule.get("form") == "negative"
                frame = frame or rule.get("frame")
        return neg, frame

    def past(self, st):
        rule = self.cfg.claim.get("past_tense") or {}
        when = rule.get("when") or {}
        unless = rule.get("unless") or {}
        return (all(st.get(k) in v for k, v in when.items()) and bool(when)
                and not any(st.get(k) in v for k, v in unless.items()))

    def forms(self, predicate, template):
        """{present, negative, past, past_negative} for a predicate template;
        missing forms fall back (see claim())."""
        override = self.cfg.predicates.get(predicate) or {}
        forms = {"present": override.get("present", template)}
        m = re.match(r"^\{subject\} (\S+)(.*)$", forms["present"])
        if m:
            verb, rest = m.groups()
            if verb in ("is", "was"):
                forms.update(negative=f"{{subject}} {verb} not{rest}",
                             past=f"{{subject}} was{rest}", past_negative=f"{{subject}} was not{rest}")
            elif verb in self.cfg.verbs:
                v = self.cfg.verbs[verb]
                forms.update(negative=f"{{subject}} does not {v['base']}{rest}",
                             past=f"{{subject}} {v['past']}{rest}",
                             past_negative=f"{{subject}} did not {v['base']}{rest}")
        forms.update({k: v for k, v in override.items() if k != "present"})
        return forms

    def claim(self, st, cls, path, out):
        g = self.groups.get(cls)
        if g is None:
            raise RosettaError(f"{cls} is not a registered predicate group")
        predicate = st.get("predicate")
        template = g["templates"].get(predicate, "{subject} " + str(predicate).replace("_", " ") + " {object}")
        forms = self.forms(predicate, template)
        (neg, frame), past = self.framing(st), self.past(st)
        key = ("past_" if past else "") + ("negative" if neg else "")
        key = key.rstrip("_") or "present"
        if key in forms:
            text = forms[key]
        else:
            base = forms["past"] if past and "past" in forms else forms["present"]
            text = (self.cfg.claim.get("negation_fallback", "it is not the case that {claim}")
                    .replace("{claim}", base)) if neg else base
        for name in CLAIM_SLOTS:
            if name in st:
                out.used.add(f"{path}.{name}" if path else name)
        fields = {}
        slots = ws.induced_slots(self.sv, cls)
        for name in re.findall(r"\{(\w+)\}", text):
            if name in ("subject", "object"):
                here = f"{path}.{name}" if path else name
                fields[name] = (self.one(st[name], slots[name], cls, here, None, out)
                                if name in st else f"[no {name}]")
                continue
            hit = [p for p in g["extras"] if p.split(".")[-1] == name]
            if not hit:
                raise RosettaError(f"predicate {predicate}: template field {{{name}}} is not "
                                   f"subject, object or an identity extra of {cls}")
            owner, node, here = cls, st, path
            segs = hit[0].split(".")
            for seg in segs[:-1]:
                node = (node or {}).get(seg)
                owner = ws.induced_slots(self.sv, owner)[seg].range
                here = f"{here}.{seg}" if here else seg
            v = (node or {}).get(segs[-1])
            if v is None:
                fields[name] = f"[no {name}]"
                continue
            fields[name] = self.one(v, ws.induced_slots(self.sv, owner)[segs[-1]], owner,
                                    f"{here}.{segs[-1]}" if here else segs[-1], None, out)
        text = re.sub(r"\{(\w+)\}", lambda m: fields[m.group(1)], text)
        return frame.replace("{claim}", text) if frame else text

    # statements -----------------------------------------------------------------

    def statement_clauses(self, cls):
        sentence = self.cfg.first(cls, "sentence")
        if sentence is None:
            raise RosettaError(f"config: no sentence for {cls}")
        group = self.cfg.first(cls, "clauses") or []
        out = []
        for c in sentence:
            out.extend(group if c == GROUP else [c])
        return out

    def render_statement(self, st, cls):
        out = self.render_clauses(self.statement_clauses(cls), st, cls, "")
        text = capitalise(out.text) + "." if out.text else ""
        record = self.render_clauses(self.cfg.first(cls, "record") or [], st, cls, "", sep="; ")
        out.merge(record)
        self.aside(st, cls, "", out)
        missing = sorted(p for p in leaves(st, "") if p not in out.used)
        return {"sentence": text, "record": capitalise(record.text), "aside": out.aside,
                "missing": missing, "unlabelled": sorted(out.unlabelled)}


def leaves(obj, prefix):
    """Every leaf path of a value, lists indexed."""
    if isinstance(obj, dict):
        if not obj:
            yield prefix
        for k, v in obj.items():
            yield from leaves(v, f"{prefix}.{k}" if prefix else k)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from leaves(v, f"{prefix}[{i}]")
    else:
        yield prefix


# --- coverage ----------------------------------------------------------------------

def reachable(sv, cfg, roots):
    """Classes whose objects a rendering can meet: the roots, and the ranges
    of their inlined slots, except through slots the config marks unused."""
    seen = []
    todo = list(roots)
    while todo:
        cls = todo.pop()
        if cls in seen or not ws.is_class(sv, cls):
            continue
        seen.append(cls)
        unused = cfg.union(cls, "unused")
        for s in ws.induced_slots(sv, cls).values():
            if s.name not in unused and ws.is_class(sv, s.range) and sv.is_inlined(s):
                todo.append(s.range)
    return sorted(seen)


def check_config(r):
    """Static checks: coverage of every reachable slot, template slot names,
    predicate forms. Returns a list of problems."""
    sv, cfg = r.sv, r.cfg
    problems = []
    roots = list(r.groups) + [c for c in cfg.roots if ws.is_class(sv, c)]
    for cname, c in cfg.classes.items():
        if not ws.is_class(sv, cname):
            continue        # a class this profile leaves out
        slots = ws.induced_slots(sv, cname)
        texts = []
        for key in TEMPLATE_KEYS:
            v = c.get(key)
            texts += [v] if isinstance(v, str) else [t for t in (v or []) if t != GROUP]
        texts += list((c.get("variants") or {}).values())
        for t in texts:
            try:
                nodes = parse(t)
            except RosettaError as err:
                problems.append(f"{cname}: {err}")
                continue
            for ph in placeholders(nodes):
                if ph.name not in (CLAIM, "*") and ph.name not in slots:
                    problems.append(f"{cname}: template names {ph.name!r}, not a slot of {cname}")
        for key in ("quoted", "elsewhere", "unused", "claim", "phrases"):
            for name in (c.get(key) or []):
                if name not in slots:
                    problems.append(f"{cname}: {key} names {name!r}, not a slot of {cname}")
    for cls in reachable(sv, cfg, roots):
        covered = set()
        for _, c in cfg.chain(cls):
            for key in ("quoted", "elsewhere", "unused", "claim"):
                covered |= set(c.get(key) or [])
        texts = []
        for key in ("template", "frame", "record"):
            v = cfg.first(cls, key)
            texts += [v] if isinstance(v, str) else list(v or [])
        for _, c in cfg.chain(cls):
            texts += list((c.get("variants") or {}).values())
        if cls in r.groups:
            texts += r.statement_clauses(cls)
        for t in texts:
            for ph in placeholders(cfg.nodes(t)):
                covered.add(ph.name)
        if CLAIM in covered:
            covered |= set(CLAIM_SLOTS)
        for name in ws.induced_slots(sv, cls):
            if name not in covered:
                problems.append(f"{cls}.{name}: no template, quoted, elsewhere, unused or claim entry "
                                f"in {cfg.path.name} for {cls} or its ancestors")
        if cls not in r.groups and cfg.first(cls, "template") is None:
            problems.append(f"{cls}: no template in {cfg.path.name}")
    for cls, g in r.groups.items():
        enum = sv.get_enum(sv.induced_slot("predicate", cls).range)
        for value in enum.permissible_values:
            template = g["templates"].get(value, "{subject} " + value.replace("_", " ") + " {object}")
            forms = r.forms(value, template)
            if template.startswith("{subject} ") and not {"negative", "past"} <= set(forms):
                verb = template.split()[1]
                problems.append(f"{cls}: predicate {value}: cannot put {template!r} in the negative "
                                f"or past tense; add {verb!r} to verbs or forms to predicates")
    return problems


# --- report ---------------------------------------------------------------------------

def statement_sets(r, path, data):
    for g in sorted(r.groups.values(), key=lambda g: g["group"]):
        for st in (data or {}).get(g["statements_slot"]) or []:
            yield g, ws.concrete_class(r.sv, st, g["statement_class"]), st


def evidence_items(r, st):
    for line in st.get("hasEvidenceLines") or []:
        for ref in line.get("evidence_item_refs") or []:
            if ref in r.index and r.cfg.first(r.index[ref][0], "template") is not None:
                yield ref


def report(r, files):
    lines = [
        "# Statements in plain language",
        "",
        f"Generated by `scripts/render_statements.py` (rule `{RULE_VERSION}`, config "
        f"`{r.cfg.path.relative_to(ROOT) if r.cfg.path.is_relative_to(ROOT) else r.cfg.path}`). "
        "One sentence per statement, with everything it records; the source's own words follow "
        "for comparison. Values kept out of the sentence are listed with the reason.",
        "",
    ]
    problems = []
    for path, data in files:
        sts = list(statement_sets(r, path, data))
        if not sts:
            continue
        lines += [f"## {Path(path).as_posix()}", ""]
        for g, cls, st in sts:
            res = r.render_statement(st, cls)
            sid = st.get("id", "?")
            lines += [f"### `{sid}` ({cls})", "", f"> {res['sentence']}", ""]
            if res["record"]:
                lines.append(f"- Record: {res['record']}.")
            for p, (reason, value) in res["aside"].items():
                if value is None or p.split(".")[-1] in ("id", "type"):
                    continue
                if reason == "quoted":
                    lines.append(f"- {p} (verbatim): {value}")
                else:
                    lines.append(f"- {p}: {value} ({reason})")
            for ref in evidence_items(r, st):
                cls_i, obj = r.index[ref]
                item = r.render_object(obj, cls_i, "")
                item_missing = [p for p in leaves(obj, "") if p not in item.used]
                lines.append(f"- Evidence item `{ref}`: {capitalise(item.text)}.")
                res["unlabelled"] = sorted(set(res["unlabelled"]) | item.unlabelled)
                problems += [f"{ref}: {p} not rendered" for p in item_missing]
            if res["unlabelled"]:
                lines.append("- No label for: " + ", ".join(f"`{u}`" for u in res["unlabelled"]) + ".")
            if res["missing"]:
                lines.append("- **Not rendered**: " + ", ".join(f"`{m}`" for m in res["missing"]) + ".")
                problems += [f"{sid}: {m} not rendered" for m in res["missing"]]
            lines.append("")
    return "\n".join(lines).rstrip() + "\n", problems


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("files", nargs="+", type=Path)
    parser.add_argument("--out", type=Path, help="write the Markdown report here")
    parser.add_argument("--check", action="store_true",
                        help="fail on an uncovered slot, a bad template or an unrendered value")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--schema", type=Path, default=ws.DEFAULT_SCHEMA)
    args = parser.parse_args(argv)

    r = Renderer(args.schema, args.config)
    files = [(str(p), yaml.safe_load(p.read_text(encoding="utf-8")) or {}) for p in args.files]
    r.add_files(d for _, d in files)
    problems = check_config(r)
    if problems and args.check:
        for p in problems:
            print(f"ERROR: {p}")
        sys.exit(1)
    text, unrendered = report(r, files)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text, encoding="utf-8")
        print(f"wrote {args.out}")
    problems += unrendered
    for p in problems:
        print(f"{'ERROR' if args.check else 'WARNING'}: {p}")
    if problems and args.check:
        sys.exit(1)
    if args.check:
        print(f"render_statements: every slot covered and every value rendered ({RULE_VERSION})")


if __name__ == "__main__":
    main()
