# WARP in RDF and OWL

WARP's output is RDF, and OWL wherever the content allows it. This file is the
contract: which files are produced, what each one may be read as, and the rules
every predicate group follows so that the seventh group is no harder to add
than the third.

It exists because the content does not all belong in the same place. A node
template produces a class definition a reasoner can use. A statement that
*typically* soil pH between 5.5 and 8 suits blue grama, said by one database,
with a range nobody else agrees with, is not a class axiom in any logic — and
asserting it as one would state something stronger than the source did. So
WARP has two layers, and the rules below are mostly about keeping them apart.

> **Status.** This describes the target, built in Phase 2.5 of the 0.4 work
> (`warp-0.4-dev-guide.md`, decisions D11 to D20). Today only the node layer and
> the schema OWL are generated; `examples/kramer1995.ttl` is a hand-written
> rendering of one statement, and it is the worked specification for
> `export_rdf.py`. The "state of play" table in section 9 says what exists.
>
> **Terminology.** The 0.4 proposals write `Claim` and `ClaimSet` where the
> code writes `Statement` and `StatementSet`. This file follows the code.

```
templates/node_templates.yaml ──▶ project/nodes.ttl         classes       OWL 2 EL
vocab/scales.yaml ────────────▶ project/scales.ttl          SKOS schemes
                                project/criteria_concepts.ttl
StatementSet *.yaml ──────────┬▶ project/statements.ttl     reification   RDF
     + *.derived.yaml         ├▶ project/sites.ttl          individuals   OWL 2 EL
                              ├▶ project/projects.ttl       individuals   OWL 2 EL
                              └▶ project/axioms.ttl         class axioms  OWL 2 EL
src/warp/schema/warp.yaml ────▶ project/warp.owl.ttl        schema        OWL 2 DL
src/warp/owl/warp-relations.ttl                             predicates    OWL 2 DL
                                                            (hand-written)
```

---

## 1. Two layers

**The reification layer** is the whole graph: every statement, proposition,
evidence line, qualifier bundle, amount, quantity and strategy component, as
RDF individuals. Scope, hedging, modality, negation, ranges, costs, order,
provenance and CARE all live here. **Nothing in it is asserted as true of the
world.** `warp:statement/x` saying that tidal restoration prevents larval
density is a record that someone said so, and the graph says exactly that.

**The logical layer** is node classes, site and project individuals, and the
few class axioms projected from propositions that pass the gate in section 6.
It is what WARP is prepared to let a reasoner use, and it is deliberately
small. On the examples in the repository today it is empty of projected
axioms, which is the correct answer for a set of assertional and prototypical
statements, not a bug to be worked around.

The layers are kept apart by three rules, one per section below: one IRI is one
kind of thing (§2), predicates are declared once as object properties (§3), and
nothing becomes an axiom without passing the gate (§6).

## 2. One IRI, one kind of thing

### 2.1 The four spaces

| Space | Kind | Holds | Written by |
|---|---|---|---|
| `node:` | OWL **class** | Actions, outcomes, environmental variables, taxa and populations, strategies ([node-templates.md](node-templates.md)) | `expand_nodes.py` (strategy IRIs come from `derive_strategies.py`) |
| `site:` | OWL **individual** | One piece of ground | `expand_nodes.py` → `sites.ttl` |
| `proj:` | OWL **individual** | The work that was done: a process instance | `derive_projects.py` → `projects.ttl` |
| `warp:statement/`, `warp:prop/`, `warp:el/`, `stmt:`, `crit:`, `comp:`, `amount:` … | RDF individual | The reification layer | `export_rdf.py` |

A `node:` IRI is a class everywhere it appears. A `site:` or `proj:` IRI is an
individual everywhere it appears. No IRI is ever both, and `check_owl.py`
fails the build if one is.

The prefixes are doing real work. Sites and projects are particulars, so they
have to be individuals; strategies and actions are kinds, so they have to be
classes; and both ends turn up in the same LinkML slot (`object: {range:
CausalNode}`) because the annotation record is the same shape for all of them.
Without separate IRI spaces there is nothing to check, and one IRI quietly
means a class in `nodes.ttl` and an individual in the statement layer depending
on which file you read.

### 2.2 How a statement points at a node class

A statement's `subject`, `predicate` and `object` are declared as **annotation
properties** in `warp-relations.ttl`, and `export_rdf.py` emits them as
annotation assertions:

```turtle
warp:statement/kramer1995-c1 a warp:CausalStatement ;
    sepio:subject   node:tidal_restoration_of_marsh ;      # an annotation assertion
    sepio:predicate camo:prevents ;
    sepio:object    node:volumetric_density_of_ochlerotatus_dorsalis_population_at_larval_stage ;
    warp:scope      <https://w3id.org/ecoweaver/warp/SemanticUnitScopeEnum#assertional> ;
    warp:negated    false .
```

An annotation assertion sits outside the logical part of the ontology, so a
class IRI may appear in it without anything being inferred and without the IRI
acquiring a second life as an individual. This is the standard OBO move, and it
is what the layer needs: the statement is *about* the class, it does not relate
instances of it.

OWL 2 DL does permit punning a class IRI as an individual. It is legal and
useless: the punned individual is a different entity from the class as far as
the semantics is concerned, so `sepio:subject` declared as an object property
would buy an assertion that says nothing about any marsh, while making every
merged file carry two unrelated meanings for one IRI. Annotation assertions say
the same thing and say it honestly. They are invisible to a reasoner, which is
the point, and fully visible to SPARQL, which is how the layer is queried.

## 3. Predicates

### 3.1 Declared once, by hand

Every predicate WARP mints is declared in `src/warp/owl/warp-relations.ttl`,
once, as an `owl:ObjectProperty`, with a label, an `IAO:0000115` definition
taken from its proposal, and `rdfs:isDefinedBy`. The file is hand-maintained
and never generated. Each group phase adds its own predicates and touches
nothing else.

Predicates from other ontologies — RO's `RO:0002303 has habitat`, CAMO's
`camo:prevents` — are **reused exactly as published and never re-declared**.

The reason is specific. Generating OWL from the LinkML schema types every
permissible value of a predicate enum as a class, so `project/warp.owl.ttl`
contains:

```turtle
RO:0002470 a owl:Class ;                     # "eats" — an object property in RO
    rdfs:subClassOf warp:InteractionPredicateEnum .
```

OWL 2 DL permits an IRI to be both a class and an individual. It does not
permit one to be both a class and an object property, so merging that file with
RO gives an ontology that DL-typing tools reject. `clean_owl.py` strips those
triples after `gen-owl` runs, and the declarations live in the relations file
instead. Until LinkML can be told that an enum value denotes a property, this
stays a post-processing step; the list of what it removes is in the script, and
in `TODOS.md` as a candidate upstream issue.

### 3.2 Domains and ranges: usually none

A domain or range axiom is written only when the predicate's end is a single
kind of thing. Where it varies — `has_habitat` takes an ENVO habitat while the
other three tolerance predicates take a `quality_of_environmental_material`
node; `incurs_cost` takes a category where `costs_relative_to` takes a node —
the relations file carries a comment and the group's check script enforces it
in Python. A range axiom that is wrong for one predicate in a group is worse
than no range axiom, because a reasoner will act on it.

### 3.3 Polarity belongs in the predicate

If a qualifier can reverse what a statement says, the relation layer has to
carry that in the predicate, or a triple read without its qualifiers says the
opposite of what the source said. So each such group gets an abstract parent
that is never asserted, and sub-properties the exporter chooses between:

| Group | Abstract parent | Sub-properties | Chosen by |
|---|---|---|---|
| recommendation | `warp:suggested_to` | `recommended_to_achieve`, `advised_against_for`, `suggested_for_consideration` | `guidance` |
| criteria | `warp:assessed_against` | `qualifies_as`, `does_not_qualify_as` | `direction` |
| cost | `warp:incurs_cost` | `incurs_total_cost`, `incurs_labour_cost`, `incurs_capital_equipment_cost`, `incurs_consumables_cost`, `incurs_overhead_cost` | the object category |

The qualifier stays: it is what annotators fill in and what enters the identity
key. Only the export changes.

Two cases do not become sub-properties:

- **Negation.** A statement with `negated: true` exports its reified record and
  **no relation triple at all**. There is no `did_not_prevent` predicate,
  because a null result is not a relation that holds.
- **A neutral criteria verdict.** Same treatment: the record, no triple.

Cost is the same move for a different reason. "This action `incurs_cost`
*total*" is not a relation between an action and a category: a cost is three
things at once — an action, a category and an amount — and the only part of it
that is a relation is action-to-amount. Putting the category in the predicate
leaves the amount as the object, where it belongs, and means no `costcat:` IRIs
have to be minted for things nothing can say the kind of.

## 4. Enum values

Every permissible value exports as an IRI, not a literal:

```turtle
warp:scope         <https://w3id.org/ecoweaver/warp/SemanticUnitScopeEnum#assertional> .
warp:evidence_type <https://w3id.org/ecoweaver/warp/EvidenceTypeEnum#quasi_experiment> .
```

and each value IRI is declared once as an `owl:NamedIndividual` typed by its
enum class. The form is the one `gen-owl` already mints, so `clean_owl.py`
retypes those IRIs rather than minting new ones. Note that neither these nor
proposition IRIs (`https://w3id.org/ecoweaver/warp/prop/9f0b068ca33b`) are
legal Turtle prefixed names — `#` and `/` need escaping in a local part — so
write them out in full in hand-written Turtle and SPARQL. No covering axiom is emitted: `gen-owl` writes `owl:unionOf`
directly onto the named enum class, which does not reverse-map to OWL 2 DL and
is outside EL in any case, so `clean_owl.py` removes it.

Literals were the old behaviour and they do not work. The schema declares
`warp:scope` an `owl:ObjectProperty` with `rdfs:range warp:SemanticUnitScopeEnum`,
while `examples/kramer1995.ttl` writes `warp:scope "assertional"` — a literal in
an object property's object position, which has no OWL 2 DL reading at all.
Exporting IRIs fixes both ends, and makes the value joinable with its
definition and its mappings.

**Sentinels are not values.** `not_stated`, `unknown`, `unclear`,
`not_reported` and `not_addressed` record the *absence* of something. They get
no `meaning:` in the schema, and `export_rdf.py` emits nothing for them: an IRI
asserting "there is evidence, of type not-stated" would be false, and OWL has
no null. The same goes for the explicit null that `derive_propositions.py` puts
in an identity key for a missing extra — it lives inside the key string and
reaches no slot and no file.

The list of sentinel values is in one place in `clean_owl.py`. Add to it when a
group adds one.

## 5. Values, units, scales and dates

**Units** are verified CURIEs from UO, or QUDT where UO has no term. Never a
bare token: `unit: ha` and `unit: UO:hectare` are not CURIEs that resolve (UO
IDs are numeric), and in Turtle they become relative IRIs against the base —
silent garbage that looks fine until two files disagree. One quantity gets one
IRI: site area and cost scale cannot use two different hectares, or nothing
aggregates. A count of things (46 protected areas) is a count with an entity
CURIE, not a unit.

**Scales** are SKOS. `vocab/scales.yaml` lists each source scale and its values
in order; `gen_vocab.py` writes `project/scales.ttl` with one
`skos:ConceptScheme` per scale and an explicit ordinal per concept, so "medium"
can be compared with "high" without a script hard-coding DFO's ordering. A
`ScaledValue` carries the source's wording verbatim in `value`, the scheme IRI
in `scale` and the concept IRI in `concept`. A practitioner's "wet" carries no
scale and no concept, because it is not on a scale; the tolerance report says
so rather than inventing one.

**Dates and durations.** The OWL 2 datatype map contains `xsd:dateTime` and
`xsd:dateTimeStamp` and **not** `xsd:date`, `xsd:gYear` or `xsd:duration`. So:
temporal values are ISO 8601 strings in the data, at whatever granularity the
source gave (`2024-05`, `2023`, `2026-03-31`), and every exporter writes the
verbatim string plus normalized `xsd:dateTime` lower and upper bounds beside
it. The bounds are also what period-overlap tests use — `derive_projects.py`
compares bounds, never strings, because no string ordering handles `2024-05`
against `2023`.

**Structured values get IRIs, not blank nodes.** Qualifier bundles, monetary
amounts, quantities, ranges and strategy components are named individuals.
Blank nodes are not addressable across files and duplicate on merge, and
several things here must be citable: a transferred cost names the amount it was
computed from, a strategy's components carry its order, and anything in an
identity key has to be reachable.

## 6. The projection gate

A proposition becomes an OWL class axiom only when **all four** conditions
hold. `project_owl.py` prints every rejection with its reason.

| Condition | Why |
|---|---|
| `scope` is `universal` | OWL 2 has no defaults and no non-monotonic reasoning. `prototypical` means "typically, allowing exceptions", which a `subClassOf` axiom cannot express: projecting it would state something stronger than the source. `assertional` is about one plot and is not a class axiom at all. |
| `negated` is false | A null result is not a relation. |
| every grouped statement has `modality: observed` | An anticipated or inferred claim is a forecast or a derivation, not a report of how the world is. |
| a `SynthesisAssessment` supports the proposition | One statement is a source's view. An axiom is WARP's. The assessment is where that judgement is made, by people or by the synthesis pipeline, and it is revisable. |

Scope is the condition that bites, and it should. Most ecological
generalizations are prototypical, which is why WARP records scope at all. **On
the examples in this repository the gate passes nothing**, and
`project/axioms.ttl` is an ontology header with no axioms under it. That is the
right answer. If a change makes something pass, check which condition stopped
being true before believing it.

What is projected, per group, is in the register in section 8. The shape for
causal and interaction is existential subsumption, annotated with its source:

```turtle
node:soil_compaction rdfs:subClassOf [
    a owl:Restriction ;
    owl:onProperty camo:prevents ;
    owl:someValuesFrom node:seedling_survival ] .
# axiom annotation: warp:derived_from warp:prop/9f0b068ca33b
```

Never `owl:equivalentClass`, and never a plain triple between two class IRIs.

### What never reaches OWL, at any scope

- **Guidance.** "You should do X" has no OWL rendering. A graph that cannot
  tell advice from description is worse than one that holds only description.
- **Ranges, optima, curves, amounts, efforts.** Measurements across populations
  and episodes, not class axioms.
- **Criteria verdicts.** A criteria set is a stated, versioned test and
  deliberately not an OWL definition — which is exactly what lets a definition
  change without a record being rewritten.
- **Step order, lags, repeats.** They stay addressable in the reification
  layer.
- **Costs.** There is no universal-scope cost, and if there were it still
  would not be a class axiom.

## 7. What each file means

| File | A reader may infer | A reader may **not** infer |
|---|---|---|
| `nodes.ttl` | What a node means: its genus and the relations in its definition. Classification under other node classes. | Anything about particular sites, populations or episodes. |
| `axioms.ttl` | That WARP holds this of every instance, on the evidence as currently assessed. Each axiom names the proposition it came from. | That it is settled. An assessment can change and the axiom goes with it. |
| `sites.ttl`, `projects.ttl` | That this piece of ground exists, is of these ecosystem types, is in this jurisdiction; that this project occurred, instantiating this strategy, at this site, over this period. | Anything about geometry — it is never exported. Anything about whether the project worked; that is a criteria claim. |
| `statements.ttl` | That someone said this, with this scope and hedging, on this evidence, under this CARE metadata. Relation triples read correctly on their own, including polarity. | **That anything in it is true.** Propositions are groupings, not findings; the relation triples are what a claimant asserted. |
| `warp.owl.ttl` | The shape of the records: classes, slots, ranges, enum values and their definitions. | Anything about the world. `owl:minCardinality` here is LinkML's `required`, not a constraint a reasoner should act on. |
| `warp-relations.ttl` | What each WARP predicate means, and how they nest. | Domains and ranges that are not written down; most are deliberately absent. |

The merged logical layer (`nodes.ttl` + `axioms.ttl` + `sites.ttl` +
`projects.ttl`) is OWL 2 EL and is what a reasoner should be given.
`warp.owl.ttl` and `warp-relations.ttl` are OWL 2 DL and describe the schema;
merging them into the logical layer for reasoning is a mistake. `statements.ttl`
is RDF and is for SPARQL.

## 8. Adding a group

Five questions, alongside the schema work in
[predicate-groups.md](predicate-groups.md). Answer them in the group's proposal
section and record the answers in the register below.

1. **Which predicates does it mint?** Declared once in `warp-relations.ttl`, as
   object properties, with the proposal's definitions. Reused predicates are
   named, not re-declared.
2. **What kind of thing is each end?** A class, an individual, or a value. If
   it varies by predicate, say which script checks it.
3. **Which qualifier carries polarity?** If one does, it becomes sub-properties
   (§3.3). If none does, say so explicitly.
4. **What does it export?** Which individuals, with which IRIs, and which values
   need IRIs of their own because something else will cite them.
5. **What does it project?** The default — and the answer for most groups — is
   nothing.

### The register

| Group | Predicates | Subject → object kinds | Polarity | Projects |
|---|---|---|---|---|
| causal | CAMO (`camo:causes`, `camo:prevents`, …) | class → class | `negated`: no triple | Existential subsumption, through the gate |
| interaction | RO (`RO:0002470`, …), reused | class → class | `negated`: no triple | Existential subsumption, through the gate |
| recommendation | `suggested_to` + 3 sub-properties | class → class | `guidance` | **Nothing**, at any scope: deontic |
| tolerance | `tolerates`, `prefers`, `intolerant_of`; `RO:0002303` reused | class → class; object kind varies by predicate (`check_tolerance.py`) | none | `has_habitat` only, through the gate |
| cost | `incurs_cost` + 5 sub-properties; `costs_relative_to` | class → amount individual, or class → class | the object category | **Nothing** |
| implementation | `carried_out_at` | class → individual | none | Nothing through the gate; the project individuals are its logical-layer output, and they come from the derivation rule |
| criteria | `assessed_against` + `qualifies_as`, `does_not_qualify_as` | individual → criteria set | `direction`; neutral exports no triple | **Nothing** |

Two entries in that table need their reason stated where someone will hit it:

**The criteria object is the criteria set, not the concept.** The exported
triple is `site:0412 warp:qualifies_as crit:degraded-area/fed-draft-1`, and the
concept is recoverable through the set's `operationalizes`. Keeping the set in
the object position is what stops the graph holding `site:0412 qualifies_as
degraded_area` and `site:0412 does_not_qualify_as degraded_area` as a flat
contradiction, when the two verdicts are about two different definitions. This
is the only place where the exported object is not the annotated object.

**Strategy part axioms are `rdfs:subClassOf`, not `owl:equivalentClass`.** The
strategy identity key is the sorted list of `(step, action)` pairs, so order is
part of identity and earthworks-then-seeding is a different node from
seeding-then-earthworks. Their part axioms are identical, because order does
not render in EL. Asserted as equivalence, those axioms tell a reasoner the two
nodes are the same class — contradicting the rule that just held them apart.
Asserted as subsumption they say only what is true. Nothing is lost:
containment was the only thing equivalence was wanted for, and the query class
`has_part some hand_seeding` has every strategy containing hand seeding among
its subclasses. The part relation is declared transitive and used only inside
`some`, never in a cardinality restriction, which keeps the output in EL and
makes the derivation's one-level flattening agree with the OWL.

## 9. Checks, and the state of play

`make validate` runs `check_owl.py` over every generated file, merged:

- no IRI is used as more than one kind of entity
- no `xsd:date`, `xsd:gYear` or `xsd:duration` literal
- every CURIE expands under a declared prefix, and nothing invented sits under
  a real ontology's prefix (placeholders use `TODO:`)
- no sentinel value was exported
- every predicate in a relation triple is declared in `warp-relations.ttl` or
  comes from an upstream ontology

`make owl-check` runs ROBOT, and is skipped with a warning if `robot` is not on
PATH:

```
robot merge nodes.ttl axioms.ttl sites.ttl projects.ttl | validate-profile --profile EL
robot merge warp.owl.ttl warp-relations.ttl             | validate-profile --profile DL
```

| Piece | State |
|---|---|
| `nodes.ttl`, node classes in EL | Built (`expand_nodes.py`) |
| `warp.owl.ttl` | Built, but not yet OWL 2 DL: see §3.1 and §4 |
| `warp-relations.ttl`, `clean_owl.py`, `export_rdf.py`, `project_owl.py`, `check_owl.py`, `make owl-check` | Phase 2.5 |
| `scales.ttl`, `place`, unit checking, date normalization | Phase 1 |
| `sites.ttl` | Phase 7.1 |
| `projects.ttl` | Phase 7.2 |
| `criteria_concepts.ttl` | Phase 7.3 |
| Grounded IRIs for SEPIO's `subject`, `predicate`, `object`, `hasEvidenceLines`, `targetProposition` | **Not solved.** They resolve under `https://example.org/sepio-model/`. `export_rdf.py` reads the namespace from one constant, so re-grounding is a one-line change, but until it happens the reification layer cannot be published. See `TODOS.md`. |

## Checklist for a group's RDF and OWL

- [ ] Predicates declared in `warp-relations.ttl`, once, as object properties, with definitions
- [ ] Upstream predicates reused, not re-declared
- [ ] Polarity answered: sub-properties, or an explicit "none"
- [ ] Object kind per predicate stated, and checked in a script where it varies
- [ ] Projection answered, with its reason, in the register above
- [ ] Any value another record will cite has an IRI, not a blank node
- [ ] Scales registered in `vocab/scales.yaml`; units verified or `TODO:`
- [ ] Sentinel values listed in `clean_owl.py` and not exported
- [ ] `check_owl.py` clean; `make owl-check` passes both profiles
- [ ] The projection report says what passed and why the rest did not
