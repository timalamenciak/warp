# Changelog

All notable changes to WARP.

## 0.7.0 (unreleased)

First public release. Schema version 0.7.0; examples' `profile_version`
0.7.0.

### Schema

- A LinkML profile of the SEPIO Core Information Model
  (`src/warp/schema/warp.yaml`), with SEPIO and the Causal Mosaic (CAMO)
  vendored unchanged at pinned commits in `src/warp/schema/upstream/` and
  every change made by `is_a` and `slot_usage`.
- Statements in SEPIO Assertion Mode (`EcoStatement`), propositions
  (`EcoProposition`), evidence lines (`EcoEvidenceLine`, with
  `evidence_type`, `evidence_object` and references to evidence items by ID)
  and synthesis assessments (`SynthesisAssessment`, Proposition Assessment
  Mode).
- Provenance as SEPIO contributions: `EcoAgent` (with `agent_kind`),
  `EcoContribution` (with `role`: author, evidence_assessor, annotator,
  reviewer) and `EcoRecordMetadata`. `CareMetadata` for knowledge holders,
  community, consent, access level and Local Contexts labels.
- Scope (`SemanticUnitScopeEnum`: assertional, contingent, prototypical,
  universal, unclear) on statements and propositions.
- Shared statement slots: `modality`, `context`, `ecosystem_context`,
  `place`, `temporal_extent`, `specified_in`, `justified_by`,
  `explained_by`.
- Shared value types: `Quantity`, `QuantityRange`, `ScaledValue`,
  `CurvePoint`, `Count`, `Period`. Units are CURIEs, source scales are SKOS
  schemes (`vocab/scales.yaml`), dates are ISO 8601 strings.
- Seven predicate groups, each a statement class, a qualifiers class and a
  proposition class, discovered from `warp_*` schema annotations:
  **causal** (CAMO predicates and causal features), **interaction** (RO),
  **recommendation**, **tolerance**, **cost**, **implementation** and
  **criteria**. See `docs/predicate-groups.md`.
- Versioned definitions (`CriteriaSet`) that criteria statements apply, with
  criteria concepts as SKOS (`vocab/local/criteria-concepts.yaml`).

### Nodes

- Node templates in LinkML (`templates/node_templates.yaml`), compiled to
  DOSDP patterns and to OWL classes. Three kinds: class expressions,
  composites (`management_strategy`) and particulars (`site`). Refinements
  (depth, season) make a refined node a subclass of its template's
  expression.
- Management strategies: ordered bundles of action nodes with lag, repeat,
  role and optional parts, canonicalized to `node:strategy-<hash>`.
- Sites: OWL individuals under `site:`, with geometry and its precision
  recorded but never exported.

### Derivation

- `derive_strategies.py` (`warp-strategy-identity/1`): canonical strategy
  nodes; superseded IDs recorded in `replaces` and deprecated in OWL.
- `derive_propositions.py` (`warp-prop-identity/4`): propositions for every
  group, keyed on group, subject, predicate, object, negation and scope plus
  each group's declared extras. Criteria use the same engine under their own
  rule name, `warp-criteria-identity/1`.
- `derive_projects.py` (`warp-impl-identity/1`): projects from
  implementation statements, as grouping records about `proj:` individuals.
- `transfer_costs.py`: explicit, versioned transfer of costs to another
  place, year or currency (`config/cost_transfer/`).

### RDF and OWL

- Two layers, kept apart (`docs/rdf-owl.md`): a logical layer
  (`nodes.ttl`, `axioms.ttl`, `sites.ttl`, `projects.ttl`, OWL 2 EL) and a
  reification layer (`statements.ttl`, every statement, proposition,
  evidence line, agent and document as RDF).
- The schema as OWL 2 DL (`project/warp.owl.ttl`, `gen-owl` then
  `clean_owl.py`) and every predicate WARP mints, declared once
  (`src/warp/owl/warp-relations.ttl`).
- A projection gate: a proposition becomes an OWL axiom only when its scope
  is universal, it is not negated, every statement under it is observed and
  a synthesis assessment supports it. `project/reports/projection.md` says
  why each proposition did or did not pass.
- One IRI, one kind of thing, checked by `check_owl.py`.

### Profiles

- WARP restricted to some predicate groups, for projects that need fewer:
  `config/profiles.yaml` declares them, `scripts/subset_schema.py`
  (`make profiles`) writes each schema and a matching relations file to
  `project/profiles/`, and `scripts/build_profile.py` (`make profile
  PROFILE=<name>`) builds and checks one on its example sets. Two profiles
  ship: `causal`, and `causal-interaction`.
- A profile is a strict subset with WARP's own IRIs: its data validates
  against the full profile, with the same derived IDs and RDF. `make all`
  checks every profile, including that its derived records equal the full
  build's.

### Checks and reports

- Checks: schema validation, `check_statements.py`, `check_refs.py`,
  `check_values.py`, `check_tolerance.py`, `check_cost.py`,
  `check_sites.py`, `check_owl.py`, and ROBOT profile checks
  (`make owl-check`, skipped with a warning where ROBOT is not installed).
- Reports in `project/reports/`: projection, guidance, tolerance, cost
  completeness (after Iacona et al.'s five standards) and Target 2.

### Terminology

- A ranked order for choosing a term (`docs/terminology.md`): an ontology
  term; else a local term with a plan to upstream it; else a local term that
  stays local, with the reason; plain text only in slots that allow it.
  `TODO:` placeholders are a pending lookup, not a tier.
- The local term register, `vocab/local/`, one file per scheme, each term
  with a label, a definition and its upstream status (`not_checked`,
  `to_request`, `requested`, `accepted`, `not_appropriate`).
  `gen_vocab.py` (`warp-local-terms/1`) writes concept schemes (`concept:`,
  `place:`) as SKOS to `project/local_terms.ttl` and class schemes (`term:`,
  a new prefix) as OWL classes to `project/local_classes.ttl`, so a local
  term used as a template filler is a class, never a punned concept. An
  accepted term is written `owl:deprecated`, replaced by (`IAO:0100001`) its
  upstream term.
- The criteria concepts moved into the register
  (`vocab/criteria_concepts.yaml` → `vocab/local/criteria-concepts.yaml`;
  `project/criteria_concepts.ttl` → `project/local_terms.ttl`). Their IRIs
  are unchanged.
- The five locally minted places (`place:europe`,
  `place:mediterranean-coastal-israel`, `place:northern-great-plains`,
  `place:nwpl-great-plains`, `place:nwpl-midwest`) are registered in
  `vocab/local/places.yaml`, upstream status `not_checked`. Their IRIs are
  unchanged, so no derived ID changed.
- `check_values.py` refuses a `concept:`, `place:` or `term:` IRI that is not
  in the register, and a deprecated one, naming its replacement.

### Examples and docs

- Seven worked example sets in `examples/` (bloodroot, Kramer et al. 1995,
  recommendations, strategies, tolerance, cost, implementation), each with
  its derived file. Citations, quotes and figures are placeholders unless a
  comment says otherwise.
- How-to guides in `docs/`: node templates, predicate groups, terminology, values, the
  RDF and OWL contract, and annotator's tests. Introductory pages in
  `docs/html/`.

### Known limitations

- Neither OWL profile has yet been confirmed by ROBOT on the development
  machine.
- Ontology terms not yet verified are `TODO:` placeholders, listed in
  `TODOS.md`.
- SEPIO's own classes still use upstream's placeholder namespace; WARP gives
  the SEPIO slots it uses WARP IRIs until SEPIO grounds its terms.
