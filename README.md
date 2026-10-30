# WARP: Weaving Assertions, Reasons and Provenance

**WARP** is EcoWeaver's schema for recording **sourced, scoped statements** about ecological
relationships, the **evidence** behind them, and **syntheses** across them.
It builds on the [SEPIO](https://github.com/sepio-framework/sepio-linkml)
Core Information Model and reuses the
[Causal Mosaic (CAMO)](https://github.com/timalamenciak/causalmosaic) for
causal statements.

Status: draft 0.5.0. The worked example is illustrative; its citation, quotes
and numbers are placeholders.

**How-to guides**
- [Adding a node template](docs/node-templates.md): define a fillable node
  shape in LinkML and get DOSDP patterns and OWL classes from it.
- [Adding a predicate group](docs/predicate-groups.md): add a new kind of
  statement (its predicates, qualifiers, statement and proposition classes).

Open work, including draft ECO term requests: [TODOS.md](TODOS.md).

**Why "WARP"?** On a loom, the warp is the set of threads held fixed under
tension; everything else is woven across it. WARP is that fixed structure for
EcoWeaver: statements, propositions, evidence and scope stay the same, while node
templates and predicate groups are the weft that changes with each kind of
statement.

---

## 1. The idea in one paragraph

A statement is **who said it** (a contribution by an agent), plus
**subject → predicate → object**, plus **what backs it**. Annotators record statements. Statements that say the same thing
are grouped into a shared **proposition** by a script, under a versioned
rule. Evidence for and against a proposition is organized into **evidence
lines**, and a **synthesis assessment** is itself a statement, made by EcoWeaver,
whose evidence is other people's statements.

## 2. Architecture

| Part | What it is | Where it lives |
|---|---|---|
| **Node shapes** | Fillable templates for what statements are about, e.g. *rate of a process of a population of a taxon* | Templates in `templates/node_templates.yaml` (LinkML-validated), compiled to DOSDP patterns and OWL; CAMO `CausalNode` stays the annotation record |
| **Predicate groups** | Controlled predicates plus the qualifiers that say what *kind* of relation is asserted | One group per kind of statement: **causal** (CAMO `CausalPredicateEnum`, features bundled as `CausalPredicateQualifiers`) and **interaction** (RO predicates, worked example) |
| **Overall shape** | Statement, proposition, evidence line | SEPIO `Statement`, `Proposition`, `EvidenceLine`, upstream |
| **Scope** | What a statement is about: one case, some cases, typical cases, all cases | `SemanticUnitScopeEnum` (Vogt's semantic unit types), here |
| **Evidential basis** | Study design, evidence object, practitioner and Indigenous knowledge as evidence | `EcoEvidenceLine`, here |

Other statement types (occurrence, composition, TEK statements via IUS) get their own
node templates and predicate groups and slot into the same SEPIO frame, the
same way `CausalStatement` and `InteractionStatement` do. The scripts discover groups
from annotations in the schema, so adding one needs no code changes.

```
StatementSet
├── agents                    EcoAgent               (← SEPIO Agent) people, communities, software
├── nodes                     CausalNode             (CAMO) what statements are about
├── node_definitions          NodeDefinition         node → template + fillers (→ OWL, DOSDP)
├── causal_statements         CausalStatement        (EcoStatement ← SEPIO Statement, Assertion Mode)
│     ├── subject / predicate / object      → nodes, CAMO predicate
│     ├── predicate_qualifiers              → accounts + causal features
│     ├── scope, causal_language, comparator, context   (statement level)
│     ├── contributions     EcoContribution → who made it (role author)
│     ├── recordMetadata                    → who annotated it, and when
│     ├── care                              → consent, access, knowledge holders
│     ├── proposition                       → DERIVED, never annotated
│     └── hasEvidenceLines  EcoEvidenceLine → evidence_type, evidence_object,
│                                             direction, strength, item refs,
│                                             targetProposition (DERIVED)
├── causal_propositions       CausalProposition      (EcoProposition ← SEPIO Proposition)
├── interaction_statements    InteractionStatement   (second predicate group)
├── interaction_propositions  InteractionProposition
├── assessments               SynthesisAssessment    (EcoStatement, SEPIO Proposition Assessment Mode)
├── study_results             EcoStudyResult         (← SEPIO StudyResult) summarized data
└── documents                 EcoDocument            (← SEPIO Document) sources
```

## 3. Import, don't fork

The upstream schemas are **vendored unchanged** at pinned commits in
`src/warp/schema/upstream/` (see `UPSTREAM.md`) and imported by
`warp.yaml`. Every EcoWeaver change is made in the profile by
subclassing (`is_a`) and narrowing (`slot_usage`), never by editing upstream
files. This means:

- **Updating is mechanical.** `scripts/update_upstream.sh [SEPIO_REF] [CAMO_REF]`
  re-vendors and records commit hashes; `make validate` tells you if anything
  broke.
- **A real fork is only for contributing back.** Fork `sepio-linkml` on
  GitHub when preparing a pull request (section 9), not to carry EcoWeaver
  changes.
- **CAMO is treated the same way**, even though you maintain it. That keeps
  the statements layer honest about what it needs from CAMO, and makes the
  CAMO refactors in section 9 visible as explicit changes.

Vendoring rather than importing by URL is deliberate: LinkML URL imports are
not pinned, and an upstream change should never silently change what your
data means.

## 4. What the profile adds or changes

| Profile class | Builds on | Changes |
|---|---|---|
| `EcoStatement` (abstract) | SEPIO `Statement` | Annotated statements are in SEPIO Assertion Mode (no `direction` / `strength`). IDs become identifiers; `direction` constrained to supports / disputes / neutral; adds `scope`, `original_text`, `source_spans`, `care`. Who made it: `contributions` (role author); who recorded it: `recordMetadata`. `proposition` is marked as derived. |
| `CausalStatement` | `EcoStatement` | Subject and object must be CAMO nodes; predicate must be a CAMO predicate. Adds `negated`, `causal_language`, `predicate_qualifiers`, `comparator`, `context`, `ecosystem_context`, `temporal_extent`, `camo_edge_id`. |
| `CausalPredicateQualifiers` | (new) | CAMO's philosophical accounts and causal features, grouped. CAMO's `direction` → `causal_direction` and `strength` → `effect_strength`, so they cannot be confused with SEPIO's evidential direction and strength. |
| `EcoProposition` (abstract) | SEPIO `Proposition` | Adds `scope`, `status` (asserted / open question), `raised_as_question`, `identity_key`, `identity_rule_version`, `derived_from_statements`. |
| `CausalProposition` | `EcoProposition` | Subject, predicate and object constrained as for `CausalStatement`. |
| `InteractionStatement`, `InteractionQualifiers`, `InteractionProposition` | `EcoStatement`, (new), `EcoProposition` | The biotic interaction group: RO predicates (eats, pollinates, parasite of, biotically interacts with) and the sign of the effect on each partner. |
| `NodeDefinition`, `TemplateFiller` | (new) | Which node template a CAMO node fills, and with which terms. |
| `EcoEvidenceLine` | SEPIO `EvidenceLine` | Direction and strength constrained to enums; who judged them is a contribution (role evidence_assessor). Adds `evidence_type` (CAMO; specializes `subtype`), `evidence_object` (Russo-Williamson: correlation, mechanism, both), and `evidence_item_refs` (by ID instead of SEPIO's inlined objects). |
| `SynthesisAssessment` | `EcoStatement` | SEPIO Proposition Assessment Mode: `proposition`, `direction` and `strength` (CAMO certainty grade) required. Adds `evidence_balance`. Replaces CAMO `EvidenceBaseAssessmentEdge`. |
| `EcoAgent`, `EcoContribution`, `EcoRecordMetadata` | SEPIO `Agent`, `Contribution`, `RecordMetadata` | Agents get identifiers and an `agent_kind` (researcher, practitioner, Indigenous knowledge holder, …). Contributions reference agents by id and carry a `role` (author, evidence_assessor, annotator, reviewer; specializes `activityType`). |
| `CareMetadata` | (new) | Knowledge holders (agent ids), community, consent, access level, Local Contexts labels, protocols. |
| `EcoStudyResult`, `EcoDocument` | SEPIO `StudyResult`, `Document` | IDs become identifiers so evidence lines can point at them. |

## 5. Where CAMO's edge fields go

Most of CAMO is the **predicate layer** of a statement. Two kinds of field are not:
hedging and scope belong to whoever is speaking, and evidence type belongs to
the evidence.

| CAMO `CausalEdge` field | In this profile |
|---|---|
| `subject`, `predicate`, `object`, `negated` | `CausalStatement`, same names |
| `philosophical_accounts`, `necessity`, `sufficiency`, `temporal_ordering`, `mediation`, `moderation`, `specificity`, `stability`, `determinism`, `proximate_distal`, `contributing_sole`, `reversibility`, `proportionality` | `CausalStatement.predicate_qualifiers`, same names |
| `direction`, `strength` | `predicate_qualifiers.causal_direction`, `predicate_qualifiers.effect_strength` (renamed) |
| `causal_language` | `CausalStatement.causal_language` (statement-level hedging) |
| `token_or_type` | `scope` (token → assertional, type → prototypical by default; check by hand) |
| `context_dependence` | `CausalStatement.context` |
| `comparator`, `ecosystem_context`, `temporal_extent` | `CausalStatement`, same names |
| `original_sentence`, `source_spans`, `source_document` | `original_text`, `source_spans`, `reportedIn` |
| `evidential_basis.evidence_types` / `evidence_objects` | `EcoEvidenceLine.evidence_type` / `evidence_object` (one evidence line per type) |
| `certainty_grade` | `SynthesisAssessment.strength`; at article level use `EcoEvidenceLine.strengthOfEvidenceProvided` (**decision needed**: Rosetta rendering currently reads `certainty_grade` from the edge) |
| `annotator`, `annotation_timestamp` | `recordMetadata`: a contribution with role annotator, and `dateRecordCreated` |
| `annotation_confidence`, `annotation_notes` | not yet mapped (Loom workflow metadata) |
| `fcm_weight`, `fcm_weight_source` | not in the statements layer: rendering metadata, derived downstream |
| `EvidenceBaseAssessmentEdge` | `SynthesisAssessment`; `included_edge_ids` → evidence lines' `evidence_item_refs`. Aggregate criteria fields not yet mapped. |

## 6. Propositions are derived

Annotators never write propositions. `scripts/derive_propositions.py` groups
statements and writes them for every predicate group, under **identity rule
`warp-prop-identity/3`**:

> Two statements share a proposition when **group, subject node, predicate,
> object node, negated and scope** all match.

(Version 1, in 0.1.0, had no group field; version 2 wrote "asserted" into
the key for non-negated statements, the same word as the proposition status,
and version 3, in 0.5.0, writes "affirmed". Derived proposition ids changed
with each version; open-question ids are kept.)

Everything else (hedging, causal features, comparator, context, evidence)
stays on the statement and is aggregated, not used for identity. Proposition IDs
are hashes of the identity key, so they are stable across runs.

Consequences worth knowing:

- **Scope splits propositions.** "Bloodroot reduced garlic mustard on this
  plot" (assertional) and "bloodroot typically reduces garlic mustard"
  (prototypical) are different propositions. The particular statement enters as
  **evidence for** the general one, in a synthesis assessment. That is how a
  case report supports a generalization. (This supersedes the earlier Turtle
  sketch, where both statements shared one proposition.)
- **Statements with scope missing or `unclear` are not grouped**, and the script
  reports them. Scope is part of what a proposition says.
- **Open questions are propositions with no statements yet**: an empty evidence
  gap map cell, or a practitioner's question in TREK. People write them with
  `status: open_question`; they keep their ID, become `asserted` when a statement
  matches, and revert if those statements go away.
- **Changing the rule regroups statements.** Bump `RULE_VERSION` in the script
  whenever the rule changes; every proposition records the version that made it.

The identity rule is a modelling decision, not a technicality. The main open
question: should any context qualifiers (ecosystem type, comparator) be part
of identity? Adding them makes propositions narrower and evidence gap maps
sparser.

## 7. Practitioners and Indigenous knowledge holders as agents making statements

Practitioner reports and Indigenous knowledge appear in two roles:

1. **As statements in their own right.** The knowledge holder is an
   `EcoAgent` (`agent_kind: practitioner` or `indigenous_knowledge_holder`)
   and the statement's author contribution names them. `care` metadata
   records consent, community authority, access level and the knowledge
   holders, who may differ from the author (knowledge relayed by a community
   member may be held by an elder or by the community). `check_statements.py`
   refuses a statement authored by an Indigenous knowledge holder or community
   member without `care`.
2. **As evidence for other statements.** Their statements can be evidence items in
   evidence lines, typed as `practitioner_experience` or
   `indigenous_knowledge`.

Recording them only as evidence would make knowledge holders sources for
other people's statements, never agents making their own. The worked example records the
notebook entry as a practitioner's statement. TEK statements should come through IUS
once that is aligned with this profile.

## 8. Worked example

```
make all        # templates → DOSDP patterns, nodes → OWL, derive propositions,
                # validate, generate JSON Schema and OWL for the profile
```

1. `examples/bloodroot_statements.yaml`: what annotators produce. Four nodes with
   their template fillings, a type-level published causal statement, a
   token-level practitioner causal statement, a practitioner interaction statement,
   and one open question raised before any annotation.
2. `examples/bloodroot_statements.derived.yaml`: after derivation. Two causal
   propositions (the open question, now asserted by the published statement, and
   an assertional proposition for the notebook statement) and one interaction
   proposition.
3. `examples/bloodroot_assessment.yaml`: a synthesis assessment of the
   general proposition, with one evidence line from the experiment and one
   from practitioner experience.

All three validate against the profile, and `make check` runs
`scripts/check_statements.py` over the derived set and the assessment
together: Assertion Mode, negation, contribution roles, CARE, and every
reference resolving. `make nodes` also writes
`project/nodes.ttl`, the four nodes as OWL classes (checked to be in OWL 2
EL with ROBOT), and `patterns/data/*.tsv`, the same fillings as DOSDP input.

## 9. Known gaps and upstream contributions

**In SEPIO (candidate pull requests):**
- No `class_uri` or mappings to the SEPIO OWL ontology, and the default
  prefix is a placeholder (`https://example.org/sepio-model/`), so generated
  OWL is not yet grounded. Contributing mappings is the single most valuable
  PR. Until then, `EcoStatement` and `EcoProposition` carry TODOs for
  `exact_mappings`.
- `direction` is a free string; an enum (supports / disputes / neutral) would help everyone.
- `hasEvidenceItems` inlines whole objects; referencing by ID is needed for
  statement networks (here: `evidence_item_refs`).
- `evidence_object` (correlation / mechanism / both) is a genuine addition to
  offer upstream.

**In CAMO (refactors this profile is waiting for):**
- `CausalEdge` defines its fields as inline `attributes`. Promoting them to
  top-level `slots` would let this profile reuse them instead of re-listing
  them, and clears many of the "ambiguous attribute" warnings from `gen-owl`.
- Rename edge `direction` and `strength` to match the names used here.
- Replace `token_or_type` with `scope`.

**Elsewhere:**
- Semantic unit definitions are working glosses; confirm against Vogt.
- ECO lacks ecological study designs (natural experiment, BACI, case study,
  practitioner experience, Indigenous knowledge): a joint ECO term request.
- CAMO node `entity_term`s in the example are free text (`TODO` Wikidata
  QIDs); their template fillings use verified NCBITaxon IDs. The planting
  action is a placeholder (`ELMO:TODO_planting`).

## 10. Next: the annotation workflow

Questions this design raises for Loom:

- **What annotators see.** Can Loom keep presenting a CAMO edge form and
  write `CausalStatement`s behind it, with predicate qualifiers as a collapsible
  section?
- **Scope.** Annotators currently choose token or type. Is the four-way
  scope choice teachable to undergraduate annotators, or should Loom ask a
  simpler question ("about one place and time, or in general?") and map it?
- **Evidence lines.** Who creates them: annotators (one per evidence type
  per statement) or a post-processing step from study design fields?
- **Statements from non-literature sources.** Field notebooks, interviews,
  monitoring databases: what does the intake form look like, and where is
  consent captured?
- **When derivation runs.** On every export, nightly, or before each
  synthesis? Who reviews statements left ungrouped because scope is unclear?
- **Migration.** Existing CAMO 0.8 edges → `CausalStatement` via `camo_edge_id`,
  with `token_or_type` mapped to scope and flagged for review.

## Layout

```
src/warp/schema/
  warp.yaml              the profile (edit this)
  warp_templates.yaml           schema for node templates
  upstream/                   vendored SEPIO and CAMO (never edit)
templates/
  node_templates.yaml         node templates (edit this)
patterns/                     GENERATED DOSDP patterns, prefixes, fill tables
scripts/
  derive_propositions.py      proposition derivation, all groups (identity rule v3)
  check_statements.py         checks the schema cannot express
  gen_dosdp.py                templates → DOSDP patterns
  expand_nodes.py             node definitions → OWL + DOSDP fill tables
  templates_lib.py            shared template code
  update_upstream.sh          re-vendor upstream at pinned commits
docs/                         how-to guides
examples/                     worked example
project/                      GENERATED JSON Schema, OWL, node classes
```

Requires Python 3.10+ with `pip install -r requirements.txt`. The optional
`make owl-dosdp` route needs [dosdp-tools](https://github.com/INCATools/dosdp-tools)
(and Java).

## Changes

- **0.5.0**: provenance the SEPIO way, and checks for what the schema cannot
  say. New `EcoAgent`, `EcoContribution` (with `role`) and
  `EcoRecordMetadata`; `StatementSet.agents`. Who made a statement is now a
  contribution with role author (replaces `agent_kind` on the statement,
  which moves to the agent); `annotator` and `annotation_timestamp` move to
  `recordMetadata`; evidence lines can record who judged them
  (`evidence_assessor`). `CareMetadata.knowledge_holder` (text) →
  `knowledge_holders` (agent ids). `evidence_type` and `role` documented as
  specializations of SEPIO's `subtype` and `activityType`. New
  `scripts/check_statements.py` and `make check`. Identity rule
  `warp-prop-identity/3`: the key says "affirmed" rather than "asserted";
  derived proposition ids change.
- **0.4.0**: back to SEPIO's own terms. "Claim" is now "statement"
  throughout: `Claim` → `EcoStatement`, `CausalClaim` → `CausalStatement`,
  `InteractionClaim` → `InteractionStatement`, `ClaimSet` → `StatementSet`;
  slots `causal_claims` / `interaction_claims` / `derived_from_claims` →
  `*_statements`, `claimant_kind` → `agent_kind` (`AgentKindEnum`); registry
  annotation `warp_claims_slot` → `warp_statements_slot`; example ids
  `warp:claim/…` → `warp:statement/…`. Profile classes get their own
  `class_uri`s (`warp:EcoProposition`, `warp:EcoEvidenceLine`, …) instead of
  names that look like SEPIO's; example `type` values name the concrete
  class. Derivation now also fills `targetProposition` on each statement's
  evidence lines. Identity rule and proposition ids unchanged.
- **0.3.0**: renamed WARP (Weaving Assertions, Reasons and Provenance), from
  "EcoWeaver Claims". Namespace `https://w3id.org/ecoweaver/warp/` and CURIE
  prefix `warp:` (were `.../claims/` and `ew:`); schema files `warp.yaml` and
  `warp_templates.yaml`; group registry annotations `warp_*`; identity rule
  renamed `warp-prop-identity/2` (same rule as before). No structural changes.
- **0.2.0**: node templates (LinkML → DOSDP and OWL); predicate group
  registry and the biotic interaction group; `EcoProposition` base class;
  `propositions` list renamed `causal_propositions`; identity rule v2 adds
  the group to the key.
- **0.1.0**: first draft of the SEPIO profile.
