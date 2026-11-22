# Statements in plain language

Every WARP statement can be said as one English sentence that carries
everything it records. `scripts/render_statements.py` writes those sentences
to `project/reports/statements.md` (`make reports`), each next to the
source's own words (`statementText`, `original_text`, `source_spans`), so a
reviewer can check that the structured record says what the source said.
The idea follows Vogt et al.'s Rosetta Statements: a statement type has
positions and a template that says them in a natural language. Rule
`warp-rosetta/1` (`RULE_VERSION` in the script).

A proposition's text (`propositionText`, written by
`derive_propositions.py`) is a different thing: subject, predicate, object,
scope and negation only, because that is all a proposition is. The statement
sentence adds who said it, where it was reported, the qualifiers, place and
time, comparators, evidence and care conditions.

## An example

Kramer et al. 1995 (`examples/kramer1995_statements.yaml`), abridged:

> According to Kramer, Collins, Malamud-Roam and Beesley (…) (1995), as
> reported in Reduction of Aedes dorsalis by enhancing tidal action in a
> northern California marsh, in a particular case Tidal restoration of marsh
> prevented Larval density of Aedes (Ochlerotatus) dorsalis, by approximately
> 98.7% reduction in seasonal mean 4th-instar larvae per dip (3.6 to 0.05), a
> strong effect (stated), the direction of causation asserted (shown by
> experimental evidence), …, compared with a pre-treatment baseline: Same site
> and monitoring stations in 1991, before tidal enhancement (stated) …, on the
> basis of quasi experiment evidence about a correlation that supports the
> statement (moderate), from Project site before tidal enhancement (1991), ….

Under it the report lists the record (annotator, date, the proposition), the
source's words verbatim, each study result the evidence cites as a sentence
of its own ("mean 3.6 larvae per dip, range 0.0-52.8, number of monitoring
stations 64 …"), values kept out of the sentence with the reason, and every
reference that has no label.

## Every value is accounted for

`render_statements.py --check` runs in `make check` and in every profile
build. It fails when:

- a slot that a statement can reach (a statement class's slots, the slots of
  the classes they inline, recursively; and the classes listed in `roots`)
  has no place in `config/rosetta.yaml`;
- a template names a slot its class does not have;
- a predicate's `rosetta_template` cannot be put in the negative or the past
  tense (its verb is missing from `verbs`, and `predicates` gives no forms);
- a statement in the files given has a value the sentence did not render: a
  value in a slot marked `unused`, or one inside a segment dropped because
  another value it needs is missing.

So a new slot, qualifier or group cannot reach the examples without someone
deciding how it reads.

## The config

`config/rosetta.yaml` has entries by class, inherited along `is_a` (nearest
class first). SEPIO's generic slots are settled once, on `Entity`,
`InformationEntity` and `Statement`. Each slot of a class is in exactly one
of:

| Key | Meaning |
|---|---|
| `template` | How a value of the class reads: a string, or a list of clauses joined by `sep` (default ", ") and placed in `frame` at `{*}` |
| `variants` | Other templates, picked with `{slot:variant}` |
| `sentence` | `EcoStatement`: the clauses of the statement's sentence. `@group` is replaced by the group class's `clauses` |
| `clauses` | A statement class: its own clauses (qualifiers, comparators, group slots) |
| `record` | The record line under the sentence (annotation, proposition) |
| `quoted` | Shown verbatim next to the sentence: the source's own words |
| `elsewhere` | Shown in the report, outside the sentence, with the reason given |
| `unused` | WARP does not use the slot. A value in it fails the check |
| `claim` | Rendered within the predicate's own words (an identity extra such as `guidance`) |

`label` (a list of alternatives, the first that renders wins) says how a
reference to an object of the class reads; `label_lower_first` lowers the
first letter of a label that would otherwise start a sentence (proposition
text, embedded after "justified by the claim that").

### Templates

```yaml
template: "{currency} {value|(amount not transcribed)}[ at {price_year} prices]"
```

- `{slot}` is the slot's value. A list reads "a, b and c". An inlined object
  reads by its class's template; an enum value by a phrase, its title or
  `preferred_label`, or its name with underscores as spaces; a reference by
  its label.
- `{slot[field=value]}` keeps the list items whose field has that value
  (`!=` keeps the others): `{contributions[role=author]:agent}`.
- `{slot:variant}` uses a named variant of the value's class template.
- `{slot|text}` gives text to use when the slot has no value.
- `[...]` is dropped unless every placeholder directly inside it has a
  value. A clause is dropped the same way.
- `{@claim}` is subject, predicate and object in the words of the
  predicate's `rosetta_template` annotation (the schema).

Words for values come from `phrases` (per class, by slot name), then
`enum_phrases` (by enum), then the schema.

### The claim

`claim.when` decides the form: `negated: true` or `direction: disputes`
gives the negative; `direction: neutral` frames the claim as "it is left open
whether …". `claim.past_tense` puts a statement about a particular case
(`scope: assertional`) in the past tense, unless it is a prediction
(`modality: anticipated`). The negative and past forms come from `verbs`
(base form and past of the first word after `{subject}`; "is" and "was" are
built in) or from whole forms in `predicates`. A template with no leading
verb (`suggested_to`) is negated as "it is not the case that …".

## Adding a group or a slot

1. Run `make check`. The coverage check names each slot that has no place.
2. Give each one a clause in the group class's `clauses`, a template on its
   value class, or (with a reason) `elsewhere` or `unused`.
3. Add the first word of each new `rosetta_template` to `verbs`, or give
   whole forms in `predicates`.
4. Read the group's sentences in `project/reports/statements.md` next to the
   statement texts.

## What a sentence does not do

- It cannot be read back into the record: `place`, `context` and
  `ecosystem_context` all read "in …". The structured record stays the
  authority; the sentence is for people.
- Node names are inserted as written, capitals included (TODOS §7.2). A
  sentence such as "prevented Larval density of …" also shows a modelling
  question: on an attribute node, CAMO's `prevents` reads as "reduces".
- Long free-text fields (comparator descriptions, `duration_text`) are copied
  in whole, which is most of the length of the longest sentences.
- Values that are machine copies of others (`quantitative_numeric`) and links
  set by derivation (`targetProposition`) are listed outside the sentence.
