# Changelog

All notable changes to WARP. The 0.4 proposal round
(`docs/proposals/warp-proposals-0.4.html`, built from
`docs/proposals/warp-0.4-dev-guide.md`) ships as two releases, **0.6.0** and
**0.7.0**: the repository was already at 0.5.0 when the work started, so
"0.4.0" would have been a downgrade (dev guide, Q15b). The documents keep their
"0.4" names as the name of the proposal round only.

Each entry names the dev-guide phase it came from.

## 0.7.0 (unreleased)

The five new predicate groups and three node templates of the 0.4 proposal
round, built on the 0.6.0 foundations. Schema version 0.7.0; examples'
`profile_version` 0.7.0. Seven predicate groups in all.

### Phase 8: consolidation

- **README** rewritten for seven predicate groups, management strategies and
  sites, criteria sets, all four derivation rules (a table of rule, script,
  key and what is not keyed), the seven example sets, the five reports, the
  full output table with the IRI spaces, and the layout. Removed claims the
  work made untrue (two predicate groups; node classes checked with ROBOT).
- **`docs/annotation-tests.md`**: the annotator's test for every group and for
  strategies, in one place, with one example each.
- **`TODOS.md`**: the complete list of `TODO:` placeholders and locally minted
  places (8.1), Phase 9 recorded as not in this release (Q15c), items this
  work settled closed or reworded, and an item to bring `docs/html/` up to
  0.7.0. Open questions stay grouped by proposal with their question numbers
  (8.5 to 8.9), the Lars conversation in order (8.10), and the candidate
  LinkML issues behind `clean_owl.py` (8.4).
- **`CLAUDE.md`**: the derivation chain, the group-specific scripts and the
  build order as they now are.
- **Release note.** This round changes what WARP emits as RDF (see 0.6.0):
  four IRI spaces (`node:` classes; `site:` and `proj:` individuals; the
  reification layer's `stmt:`, `prop:`, `doc:`, `crit:`, `comp:`, `warp:el/`
  individuals), WARP IRIs for SEPIO's slots, enum values as IRIs, and
  `warp:prop/<hash>` with a slash in its local part (write it in full, or as
  `prop:<hash>`, in hand-written Turtle and SPARQL). The guide's "bump the
  schema version to 0.4.0" was not done: the work shipped as 0.6.0 and 0.7.0
  (Q15b).
- Verified with `make clean` and `make all` on a fresh clone of the branch.
  ROBOT profile checks were skipped there too (not installed).

### Release tidy

- **Proposal documents moved** to `docs/proposals/`: the proposals
  (`warp-proposals-0.4.html`), the build guide (`warp-0.4-dev-guide.md`)
  and the slot reference (`warp-0.4-reference.html`), unchanged. Every
  reference to them (README, CLAUDE.md, TODOS.md, `docs/rdf-owl.md`, schema
  and relations comments, example headers, test docstrings) now gives the
  new path.
- **Versions.** The node template schema (`warp_templates.yaml`) goes from
  0.1.0 to 0.7.0, matching the profile, since 0.7.0 changed it (`kind`,
  `parent_class`, `part_property`, `refinements`). The profile, examples'
  `profile_version`, its default and `warp-relations.ttl` were already
  0.7.0. `docs/rdf-owl.md`'s state-of-play row for `warp-relations.ttl` no
  longer says it declares only annotation properties.
- **`docs/html/`** pages still describe 0.5.0; each now says so at the top
  and points to the current Markdown docs (TODOS 0.4b).

### Phase 7.1: sites

- **`site` template** (`kind: particular`) and **`SiteDefinition`** (is_a
  `NodeDefinition`): `label`, `geometry`, `geometry_precision` (required),
  `area`, `area_source`, `ecosystem_type`, `jurisdiction`, `tenure`, `care`.
  Enums `GeometryPrecisionEnum`, `AreaSourceEnum`, `TenureEnum` (`unknown` a
  sentinel). New `StatementSet.site_definitions`.
- Sites are particulars (D7, D11): IDs under `site:`, never `node:`;
  `expand_nodes.py --sites` writes `project/sites.ttl` with each site as an
  `owl:NamedIndividual`, `rdf:type` its ecosystem types, its label, and its
  jurisdiction (`warp:in_jurisdiction` an ISO 3166-2 IRI where there is a
  code, `warp:jurisdiction_name` a literal where there is none). Geometry is
  never exported, not even to `statements.ttl`.
- **`scripts/check_sites.py`** in `make validate`: site IDs under `site:`
  only; withheld precision means no geometry; GeoJSON parses; a warning for
  exact geometry under restricted care. No geometry library is used.
- `docs/node-templates.md`: sites as the first particular, and why they are
  nodes anyway.

### Phase 7.2: implementation group and derived projects

- **New predicate group `implementation`**: `ImplementationStatement` (scope
  always assertional), `ImplementationQualifiers` (`period`, `status`,
  `reported_on`, `area_treated`, `implemented_by`, `funded_by`,
  `external_ids`), `ImplementationProposition`, plus `ExternalId`
  (`{scheme, value}`, D20), `ClaimantStatus`, `ClaimantArea`, and
  `ImplementationPredicateEnum` / `ImplementationStatusEnum`. Registered with
  `warp_identity_rule: warp-impl-identity/1` and `warp_derived_by:
  derive_projects.py`. The plan document is the statement's `specified_in`.
- **`scripts/derive_projects.py`** (run by `make derive` after propositions):
  union-find over shared external IDs, or same subject, same site and
  overlapping periods on normalized bounds. Each cluster gives an
  `ImplementationProposition` (members; each claimant's latest status and
  area, attributed; union of implementers, funders, external IDs; envelope of
  periods; `about_project`, slot IRI `IAO:0000136`) and a project node
  record. Candidate bad merges (two external IDs from one scheme) are
  reported.
- **Projects are individuals (D17, replacing D8).** `project_owl.py
  --projects` writes `project/projects.ttl`: `proj:<id>` typed by its
  strategy class, `RO:0001025` (located in, verified locally) its site, with
  its period's bounds. **Decision made on your behalf:** project IDs are the
  smallest external ID (`proj:agreement-0412`) or a hash of site, subject and
  earliest start; when an ID moves, the old one is kept in `replaces` and
  deprecated in OWL.
- **RDF:** `warp:carried_out_at` declared (class to individual: reification
  layer only); nothing projects through the gate.

### Phase 7.3: criteria sets, criteria group and the Target 2 report

- **`CriteriaSet`** (an information record, not a node) with every element
  of the proposal, and enums `CriteriaConceptEnum`, `CriteriaStatusEnum`,
  `ReferenceBasisEnum`, `EcosystemAttributeEnum` (SER's six, provisional),
  `ThresholdKindEnum`, `AssessmentUnitEnum`, `AssessmentBasisEnum`,
  `AssessmentMethodEnum`.
- **Criteria concepts as SKOS**: `vocab/criteria_concepts.yaml` →
  `gen_vocab.py --criteria` → `project/criteria_concepts.ttl`; the enum's
  `meaning:` is the same `concept:` IRI, so each concept exists once and is
  never an `owl:Class`.
- **New predicate group `criteria`**: `CriteriaStatement` (subject a site or
  project individual, required; object a concept; `direction`, the verdict,
  required), `CriteriaQualifiers` (`criteria_set`, `assessed_period`,
  `assessment_method`), `CriteriaProposition`. Rule
  `warp-criteria-identity/1`, key subject, concept, criteria set and
  assessed period. No `subject_proposition`, no `exactly_one_of` (R7, R18).
- `check_statements.py` allows `direction` where the schema requires it (the
  verdict) and accepts enum-valued objects; `check_sites.py` checks that the
  criteria set operationalizes the statement's concept, that the subject is a
  particular, and warns on assessment-unit mismatches.
- **RDF (D16):** abstract `warp:assessed_against` with `warp:qualifies_as`
  and `warp:does_not_qualify_as`; the exporter picks by direction, writes the
  **criteria set** as the object, and writes no triple for a neutral
  verdict. Nothing projects to OWL.
- **`scripts/report_target2.py`** (`make reports`,
  `project/reports/target2.md`): degraded sites, active projects on them,
  effective projects, area as lower and upper bounds, and a comparison table
  across definitions. **Three buckets (Q15a):** supported, contested,
  unsupported. `--include-planned`, `--show-restricted`.
- **Example** `examples/implementation_statements.yaml`: site 0412
  (generalized geometry, 64 ha, private, restricted care) and site 0517;
  the land trust's and funder's claims (42 vs 40 ha, shared agreement ID)
  deriving one project; the same strategy on site 0517 as a second project;
  three fictional criteria sets; site 0412 contested under one definition and
  supported under the other; site 0517 qualifying under one and not the
  other; an effective project; and a neutral rule-applied verdict by
  EcoWeaver.
- Docs: implementation and criteria groups in `docs/predicate-groups.md`
  (annotator's tests, the project ID scheme); register and state of play in
  `docs/rdf-owl.md`; open questions (Q1, Q2, Q4 to Q8) and the Lars
  conversation (Q14) in `TODOS.md`.
- Tests: sites as individuals, no geometry anywhere, jurisdiction IRI or
  literal, every site check; one project from two reports, attributed areas,
  overlap linking (including a case string order gets wrong), ID stability and
  recorded moves, bad merges, latest status per claimant, `projects.ttl`;
  criteria concepts, shared propositions for disagreeing assessors, verdict
  sub-properties with the set as object, neutral verdicts, criteria checks,
  no projection; Target 2 buckets, the effect of a definition, planned work,
  area caps, restricted listing.
- No existing proposition ID changed.

### Phase 3: recommendation group

- **New predicate group `recommendation`** (proposal section 5):
  `RecommendationStatement`, `RecommendationQualifiers`,
  `RecommendationProposition`, and `StatementSet` lists
  `recommendation_statements` / `recommendation_propositions`. Registered with
  the real `warp_*` annotations and `warp_identity_extras:
  predicate_qualifiers.guidance`.
- Enums `RecommendationPredicateEnum` (`suggested_to`, meaning
  `warp:suggested_to`), `GuidanceEnum` (do, avoid, consider), `DeonticForceEnum`
  (required, recommended, suggested, optional), `ContributionEnum` (direct,
  precursor). Qualifiers: `guidance` (required, in the key), `deontic_force`,
  `priority` and `timing_of_influence` (`ScaledValue`), `contribution`.
- New shared slot **`justified_by`** (propositions, by reference).
- **RDF (D16):** `warp-relations.ttl` declares `warp:suggested_to` as an
  abstract parent (`warp:abstract_predicate true`) and three sub-properties,
  `warp:recommended_to_achieve`, `warp:advised_against_for` and
  `warp:suggested_for_consideration`, each with `warp:selected_by` its
  `GuidanceEnum` value; the enum values name their sub-property in a
  `warp_subproperty` annotation. `export_rdf.py` writes the sub-property in
  relation triples and in the record's `warp:predicate`; the abstract parent
  is never asserted. New annotation property `warp:selected_by`.
- **OWL:** nothing projects from this group, at any scope (guidance is
  deontic).
- **Example** `examples/recommendation_statements.yaml` (+ derived file):
  Mountain Sucker approaches 11 (avoid stocking; prediction with
  `expert_judgment`) and 9 (do water conservation; prediction with
  `not_stated`), the Spring Salamander road-salt open question, and the
  prescribed burning do/avoid pair citing one causal proposition, which
  derives two propositions, plus a practitioner whose "do" joins the plan's
  (one proposition, two claimants). Placeholders marked TODO.
- **`scripts/report_guidance.py`** (`make reports`, new target): unsupported
  guidance, self-supporting guidance, and the assessed strength of cited
  propositions, in `project/reports/guidance.md` and `guidance.csv`.
- `docs/predicate-groups.md`: the recommendation group, the annotator's test,
  and the rule that predictions are causal statements, never derived from
  guidance. Open questions Q1 to Q6 in `TODOS.md`.
- The `Makefile` was rewritten for readability (earlier scripted edits had
  folded its line continuations); no target changed behaviour.
- Tests: identity (do/avoid split, shared guidance merges), predictions not
  derived, open question kept, validation of required guidance,
  sub-properties in the relation layer and records, relations file and schema
  agreeing, no projection at any scope, and the report's three findings.
- No existing proposition ID changed.

### Phase 4: management strategy node

- **Template kinds.** `warp_templates.yaml` gains `kind` (`class_expression`,
  the default; `composite`; `particular`), and `parent_class` /
  `part_property` for composites. `vars`, `name`, `definition` and
  `equivalent_to` are now required only for class-expression templates
  (checked in `templates_lib.py`). `gen_dosdp.py` skips other kinds.
- **`management_strategy` template** (`kind: composite`, parent
  `OBI:0000011` planned process, part relation `BFO:0000051` has part; both
  verified in the local ECOCORE imports).
- **Schema:** `StrategyDefinition` (is_a `NodeDefinition`: `components`, at
  least two; `specified_in`; derived `identity_key`, `identity_rule_version`,
  `canonical_node`, `replaces`), `StrategyComponent` (`action`, `step`, `lag`
  as an ISO 8601 duration string, `repeat`, `role`, `optional`),
  `Recurrence` (`every`, `times`, `until`), `StrategyRoleEnum` (each value
  annotated with its cost phase, R10). New `StatementSet.strategy_definitions`
  (its own list: node definitions have no type designator).
  `NodeDefinition.fillers` is no longer schema-required; `expand_nodes.py`
  requires it for class-expression templates. No objective field, with the
  reason in a schema comment.
- **`scripts/derive_strategies.py`**, rule `warp-strategy-identity/1`:
  flattens one level of nesting (renumbering later steps), keys on the sorted
  (step, action) pairs of required parts, mints `node:strategy-<hash>`,
  records the canonical node on each definition, adds a node record for it,
  rewrites references to local strategy IDs, refuses cycles and deeper
  nesting, and records superseded canonical IDs in `replaces` by comparing
  with the previous derived file. `make derive` runs it before
  `derive_propositions.py`.
- **OWL:** `expand_nodes.py` (now run on the derived files) writes each
  canonical strategy as `rdfs:subClassOf` planned process and
  `has part some <action>` per required part, never `owl:equivalentClass`;
  `BFO:0000051` is declared transitive there; superseded IRIs are
  `owl:deprecated` with `IAO:0100001`. No DOSDP pattern.
- **RDF:** `export_rdf.py` exports strategy components as
  `comp:<local ID>/<n>` individuals with step, lag, repeat, role and
  optional, linked by the new annotation properties `warp:action` and
  `warp:component_of`; the definitions themselves are not exported (their
  nodes are classes).
- **Example** `examples/strategy_statements.yaml`: the proposal's
  earthworks-seed-mow strategy, a second source describing it flat under
  another name (merges), parallel and optional parts, a nested "standard
  site preparation", and two causal statements about the two descriptions,
  which derive one proposition.
- Derived files' header now names both derivation scripts.
- `docs/node-templates.md` section 8: template kinds, strategies, why no
  DOSDP pattern, and that strategy IRIs are stable only while their parts are.
- Tests: flattening, renumbering, parallel and optional parts, nested
  optional, nested and flat meeting, order in the key, cycles, deep nesting,
  merging, one proposition for merged strategies, superseded IDs and their
  deprecation in OWL, subclass-not-equivalence, optional parts absent from
  OWL, component export, and validation (two components, ISO lag).
- No existing proposition ID changed.

### Phase 5: tolerance group

- **New predicate group `tolerance`** (proposal section 7):
  `ToleranceStatement`, `ToleranceQualifiers`, `ToleranceProposition` (which
  carries `place`), and `StatementSet` lists `tolerance_statements` /
  `tolerance_propositions`, with `warp_identity_extras: place` (decision D18:
  `place`, not `ecosystem_context`). Ranges, optima and class values are not
  in the key.
- `TolerancePredicateEnum`: `tolerates`, `prefers`, `intolerant_of` (minted,
  declared in `warp-relations.ttl` with the proposal's definitions) and
  `has_habitat` (`RO:0002303`, verified in the local ENVO import, reused and
  never re-declared). `ToleranceResponseEnum`. Qualifiers: `range`,
  `optimum`, `class_value`, `response`, `response_curve` (ordered).
  New shared slot **`explained_by`**.
- **New node template `quality_of_environmental_material`** (quality of a
  material or medium: soil, water, air), with **refinements**: optional
  `depth` and `season` on the node definition. New template field
  `refinements` and `NodeDefinition.depth` / `season`. A refined node is
  written as a subclass of the expression, never an equivalent class, and is
  left out of the DOSDP fill tables. Subjects use the existing `taxon`,
  `population_of_taxon` and `taxon_at_life_stage` templates.
- **`scripts/check_tolerance.py`** in `make validate`: the object's kind per
  predicate (habitat node for `has_habitat`, quality node for the rest; R17),
  objects without node definitions, and response curves (x strictly
  increasing, suitability in [0, 1]).
- **OWL:** `project_owl.py` projects `has_habitat` only, through the gate,
  as `<taxon> rdfs:subClassOf [ owl:onProperty RO:0002303 ;
  owl:someValuesFrom <habitat> ]`. Prototypical statements, and ranges,
  optima, class values and curves at any scope, never project.
- **Example** `examples/tolerance_statements.yaml`: a database pH range
  (not_stated) plus two more sources on the same range (one proposition, one
  of them non-overlapping), an EIVE-style niche position with class value and
  a range on the EIVE scale, the practitioner's prairie cordgrass pair
  (contingent; "wet" on no scale, "sand" a USDA texture class), two regional
  wetland indicator ratings (two propositions), an HSI curve with the
  combination rule on an `EcoStudyResult`, a tolerance `explained_by` a
  causal proposition, and a `has_habitat` statement. All figures placeholders.
- **`scripts/report_tolerance.py`** (`make reports`):
  `project/reports/tolerance.md`, ranges per proposition by claimant and
  response; flags non-overlapping ranges and unit mismatches; never
  aggregates or converts.
- Docs: the tolerance group and its annotator's test in
  `docs/predicate-groups.md`; refinements in `docs/node-templates.md`. Open
  questions Q1 to Q6 in `TODOS.md`, with Q2 (BFO disposition) recorded as
  narrowed.
- New test: every committed `*.derived.yaml` equals a fresh derivation.
- No existing proposition ID changed.

### Phase 6.1: cost group

- **New predicate group `cost`** (proposal section 8): `CostStatement`,
  `CostQualifiers`, `CostProposition` (with `CostIdentityQualifiers` for its
  keyed fields), `MonetaryAmount`, `CostRatio`, and `StatementSet` lists
  `cost_statements` / `cost_propositions`. Identity extras: `place`,
  `predicate_qualifiers.phase`, `predicate_qualifiers.reporting_level`.
- Enums `CostPredicateEnum` (`incurs_cost`, `costs_relative_to`),
  `CostCategoryEnum` (total, labour, capital_equipment, consumables, overhead,
  and the sentinel unknown), `CostBehaviourEnum`, `CostPhaseEnum`,
  `ReportingLevelEnum`, `CostBasisEnum`, `CostAdjustmentEnum`.
- **Object** is `any_of` a cost category or a node (R16), with no `costcat:`
  IRIs. `MonetaryAmount` adds `adjustment_base_year` (R5) and
  `derived_from_amount`; currency is ISO 4217 (`^[A-Z]{3}$`); price year an
  integer. `CostQualifiers` requires one of amount, effort or ratio (R3);
  `scale` is required only for `incurs_cost` (R4), in `check_cost.py`.
  Statement-level `period`, `outcome_reported`, `starting_conditions`,
  `cost_bearer`, `transferred_from`, `transfer_rule`, `transfer_steps`.
  `stated_goal` stays on `EcoStudyResult`.
- **Decision made on your behalf:** an amount with a value needs its price
  year (error), but an amount with no value is allowed as a record of a
  figure not yet transcribed, so the Florida budget can say "TODO" without
  inventing a number. The completeness report flags it and transfer refuses
  it.
- **`scripts/check_cost.py`** in `make validate`: the per-predicate rules
  (incurs_cost needs amount or effort, scale and phase; totals need
  `includes_categories`; costs_relative_to needs a ratio and a node; amount
  rules; transfer rule; `covers_roles` against the subject strategy's
  component roles).
- **RDF (D16):** `warp:incurs_cost` is abstract, with five category
  sub-properties carrying `warp:selected_by` their category; the exporter
  writes `<action> warp:incurs_<category>_cost <amount>`, the amount a named
  individual (`<statement>/predicate_qualifiers/amount`), and the category IRI
  as the record's `warp:object`. `export_rdf.py` now handles `any_of` slot
  values and relation hooks that return a predicate without a triple
  (propositions). Nothing projects to OWL.
- `check_statements.py` accepts an enum value as a subject or object where
  the group's slot allows one (a cost category).
- **Example** `examples/cost_statements.yaml`: the INPA golden wreath wattle
  costing with `outcome_reported` (two same-source causal statements, one
  negated) and `stated_goal` on its study result; the Florida program budget
  (amount and price year TODO; 46 protected areas as a `Count`); the
  practitioner's drill-seeding-to-plugs ratio; a whole-project cost on the
  Phase 4 strategy and a phase-level labour cost with `covers_roles`; and two
  initial costings that derive one proposition, with a maintenance costing
  that does not join it.

### Phase 6.2: completeness report and explicit transfer

- **`scripts/report_cost_completeness.py`** (`make reports`):
  `project/reports/cost_completeness.md` and `.csv`, each cost statement
  checked against Iacona's five standards plus reporting level and basis,
  required and recommended fields, a score, and flags for
  `includes_categories [unknown]`, `payment_rate` (with or without a
  `cost_bearer`), missing values and transferred statements. `stated_goal`
  is found through `reportedIn` and the study results.
- **`scripts/transfer_costs.py`** with the rule
  `config/cost_transfer/warp-cost-transfer-1.yaml` (obviously fake
  placeholder price indices, exchange rates and labour rate) and a selection
  file: new derived cost statements in
  `examples/cost_statements.transferred.yaml` (claimant EcoWeaver,
  `modality: inferred`, `transferred_from`, `transfer_rule`,
  `transfer_steps`, the target `place`, and an amount citing its source
  amount). Labour is re-priced from effort; other categories indexed or left
  unchanged per the rule; sources are never modified; costs without a value,
  currency or price year are refused and reported. IDs carry the rule ID, so
  a new rule version regenerates them. `make derive` runs it.
- Docs: the cost group in `docs/predicate-groups.md`; open questions Q1 to
  Q6 and the valuation group in `TODOS.md`.
- Tests: identity, every `check_cost` rule, schema validation (one of
  amount, effort or ratio; ISO currency), the RDF shape (category in the
  predicate, named amount, no `costcat:`, no `unknown`, transferred amount
  citing its source), no projection, CPI-only transfer, currency conversion,
  labour re-pricing, refusals, sources untouched, rule versioning, the
  generated file current, and the completeness report.
- No existing proposition ID changed.

## 0.6.0 (unreleased)

Shared foundations, the identity engine and the RDF/OWL contract, with the two
existing predicate groups.

**This release changes what WARP emits as RDF.** Until 0.5.0 nothing generated
RDF for statements, and the schema OWL typed predicate IRIs as classes and
enum values as classes while data wrote literals for them. From 0.6.0:

- Four IRI spaces, and nothing crosses between them (D11): `node:` IRIs are
  OWL classes; `site:` and `proj:` IRIs are OWL individuals (from 0.7.0);
  `stmt:`/`warp:statement/`, `prop:`/`warp:prop/`, `warp:el/`, `doc:` and the
  rest are RDF individuals of the reification layer; enum values are
  individuals of their enum class. `check_owl.py` fails the build if one IRI
  is two kinds of thing.
- Statements point at node classes through annotation properties
  (`warp:subject`, `warp:predicate`, `warp:object`, D12).
- Every SEPIO slot WARP uses has a WARP IRI (`warp:statementText`,
  `warp:hasEvidenceLines`, …) instead of `https://example.org/sepio-model/…`
  (Q13). A mapping to SEPIO's IRIs will follow when SEPIO grounds them.
- `warp:prop/<hash>` keeps a slash in its local part, so it is not a legal
  Turtle prefixed name: write it in full, or as `prop:<hash>` now that `prop:`
  is declared, in hand-written Turtle and SPARQL. The same holds for enum
  value IRIs (`…/SemanticUnitScopeEnum#assertional`), whose `#` needs
  escaping.

### Phase 0: orientation and test harness

- **Build fix.** The `patterns` recipe in the `Makefile` had literal `\n`
  sequences where line continuations belonged, so `make all` failed on a clean
  checkout with a shell syntax error. Fixed.
- **Both worked examples are built.** `make derive`, `validate`, `check` and
  `nodes` now run over `bloodroot` and `kramer1995` (the second was never in
  the build). The file lists are `STATEMENTS` and `ASSESSMENTS` at the top of
  the `Makefile`.
- **Tests.** New pytest suite under `tests/`, run by `make test` and by
  `make all`. First test: every file in `examples/` validates against the
  profile.
- **`CLAUDE.md`** at the repo root: conventions, the definition of done, and
  how the code works, for anyone (or any session) picking the work up.
- **`CHANGELOG.md`** (this file) replaces the README's "Changes" section.
- `.gitignore` for Python caches.
- No derived proposition ID changed.

### Phase 1: shared foundations

- **Value classes** in the profile: `Quantity {value, unit}`,
  `QuantityRange {min, max, unit}` (either end optional, not both; `min <= max`
  checked), `ScaledValue {value, scale, concept}`, `CurvePoint {x, suitability}`
  (suitability in [0, 1]), `Count {value, entity}` and `Period {start, end}`.
  `Period` is new rather than a reuse of `temporal_extent`, because CAMO's
  `TemporalExtent` has no start or end (R2).
- **Shared statement slots.** `context`, `ecosystem_context` and
  `temporal_extent` were inline attributes on `CausalStatement`; they are now
  top-level slots on `EcoStatement`, so every group has them. Validation of
  causal statements is unchanged. New shared slots: `modality`, `place` and
  `specified_in` (plan documents, by reference).
- **`modality`** (`ModalityEnum`: observed, inferred, anticipated): whether a
  statement reports, infers or forecasts. Distinct from hedging
  (`causal_language`).
- **`place`** (decision D18): the region a statement is about, as an IRI from
  ISO 3166-2, Wikidata, GeoNames, Getty TGN, an ENVO ecoregion or a local
  `place:` concept. `ecosystem_context` keeps CAMO's functional-group range;
  both slots now say which is which. How to find a place IRI:
  `docs/values.md`.
- **`WarpEvidenceTypeEnum`** (decisions D2, D3): every CAMO evidence type, with
  the same descriptions and mappings, plus `not_stated` (the source gives no
  basis). It is the range of `EcoEvidenceLine.evidence_type`. A test fails if
  CAMO gains a value the profile enum lacks.
- **`stated_goal`** on `EcoStudyResult`: the aim as the source states it.
- **Scales as SKOS** (decision D18). `vocab/scales.yaml` registers DFO recovery
  priority and timing of influence, ECCC recovery priority, EIVE 1.0 reaction
  (binned; the binning is WARP's and marked TODO), USDA texture class, USDA
  tolerance rating and wetland indicator status; `practitioner-free` is listed
  as *not* a scale. New `scripts/gen_vocab.py` and `make vocab` write
  `project/scales.ttl`: one `skos:ConceptScheme` per scale, one `skos:Concept`
  per value, each with `warp:ordinal`.
- **Prefixes** (decision D20): `stmt`, `prop`, `doc`, `org`, `person`, `site`,
  `proj`, `comp`, `crit`, `concept`, `scale`, `place`, `TODO`, plus `UO`, QUDT
  `unit`, `ISO3166-2`, `geonames`, `tgn` and the ontologies node fillers use.
  `prop:`, `stmt:` and `doc:` expand to the paths already used under `warp:`,
  so no existing IRI changes.
- **Placeholders moved to `TODO:`.** `ELMO:TODO_planting` →
  `TODO:planting` and `ELMO:TODO_tidal_restoration` →
  `TODO:tidal_restoration`, in templates, examples and
  `examples/kramer1995.ttl` (R21). `expand_nodes.py` accepts a `TODO:` filler
  for any template variable.
- **`scripts/check_values.py`**, run by `make check`: undeclared prefixes,
  bare tokens in CURIE slots, placeholders under real prefixes, non-numeric
  OBO IDs, per-slot allowed prefixes (`warp_allowed_prefixes` annotation:
  units, places, scales), `QuantityRange` order, `ScaledValue` scale and
  concept registration, and ISO 8601 periods. Schema-driven through the new
  `scripts/warp_schema.py`.
- **Dates** (decision D19): new `scripts/warp_time.py` turns ISO 8601 years,
  year-months and dates into half-open `xsd:dateTime` bounds and tests period
  overlap on them. No slot uses LinkML `date` or `datetime` except SEPIO's
  `dateRecordCreated`.
- **OWL entity types** (R13, R14). Every profile enum now says what its values
  are with `implements:` — `owl:ObjectProperty` for predicate enums,
  `owl:NamedIndividual` for the rest — and `gen-owl` runs with
  `--default-permissible-value-type owl:NamedIndividual` for the CAMO enums
  the profile cannot annotate. `RO:0002470` and the other interaction
  predicates are now object properties, not classes. CAMO's causal predicate
  values are individuals until Phase 2.5 retypes them.
  `subject`, `predicate` and `object` are marked `owl:AnnotationProperty` on
  statements and propositions (decision D12).
- `project/nodes.ttl` now has an `owl:Ontology` header
  (`https://w3id.org/ecoweaver/warp/nodes`).
- Generators run with UTF-8 output (`PYTHONIOENCODING`), so
  `project/warp.owl.ttl` is UTF-8 on Windows too.
- New guide **`docs/values.md`**: units, counts, scales, places (including how
  to find a Wikidata or gazetteer IRI for a place) and dates.
- Tests: evidence-type mirroring, date bounds and overlap, scale vocabulary,
  value checks, shared slots and value classes, no predicate IRI emitted as an
  `owl:Class`, and the examples' proposition IDs (unchanged).

### Phase 2: identity engine and reference checker

- **Identity rule `warp-prop-identity/4`.** Groups can extend the
  proposition identity key without group-specific code, through two new
  registry annotations: `warp_identity_extras` (ordered slot paths, dotted
  paths reach into inlined objects) and `warp_identity_rule` (a rule name
  that overrides the shared one). A third, `warp_derived_by`, hands a group to
  its own derivation script. Documented in `docs/predicate-groups.md`.
- Extras are canonical JSON in the key (sorted object keys; lists sorted
  unless `list_elements_ordered`); a missing extra is an explicit `null`, so
  the statement still groups, and the derivation report counts it as
  "grouped with missing key fields". The null is never written to a slot.
  Derivation copies each extra onto the proposition. Proposition text
  templates may use an extra by name (`{guidance}`).
- **Why rule 4 and not rule 3.** The dev guide calls this rule v3 because it
  was written against 0.3.0; the code was already at v3 in 0.5.0. The rule
  version is recorded on each proposition and is **not** hashed into its ID
  (decision D4, Q11), and causal and interaction declare no extras (decision
  D1), so **no proposition ID changed**. The derived files changed only in
  `identity_rule_version` (`warp-prop-identity/3` → `/4`).
- **`scripts/check_refs.py`**, run by `make validate`: every value of a slot
  whose range is a class and that is not inlined must resolve to a record in
  the files given. Schema-driven through `warp_schema.walk()`, so later
  groups are checked as soon as their slots exist.
- `check_statements.py` now covers every registered group, including any
  derived by another script.
- Tests: key building with and without extras, missing extras, structured
  extras in a different key order, list ordering, extras read from
  annotations, idempotent re-derivation, unchanged example IDs, and
  dangling references caught (subject, nested contributor, node definition,
  `specified_in`).

### Phase 2.5: the RDF and OWL contract

- **`docs/rdf-owl.md`** corrected against the code and marked as built: the
  IRI spaces, how a statement points at a node class, relation triples, enum
  values, dates, the projection gate and its report, the state of play, and
  what `clean_owl.py` actually does. One correction of substance: the draft
  said OWL 2 DL forbids an IRI being both a class and an object property; it
  allows that as punning. WARP's one-IRI-one-kind rule is a house rule,
  stricter than OWL, and the docs now say so.
- **`src/warp/owl/warp-relations.ttl`** (hand-maintained, D13): an ontology
  with its own IRI and version IRI declaring the reification layer's
  annotation properties (`warp:subject`, `warp:predicate`, `warp:object`,
  `warp:focus`), the axiom annotation `warp:derived_from`, and
  `warp:abstract_predicate` for abstract parents. Causal and interaction reuse
  CAMO and RO predicates, which are never re-declared.
- **WARP IRIs for SEPIO's slots** (Q13, supersedes R22): `slot_uri` set in
  `slot_usage` on the profile classes for every SEPIO slot WARP uses, and new
  thin subclasses `EcoDataItem`, `EcoDataSet` and `EcoCoding` for the SEPIO
  classes the examples used directly (their `type` values in the examples
  changed accordingly). `gen-owl` now runs with `--no-use-native-uris` and
  `--xsd-anyuri-as-iri`.
- **Schema fixes found by the new checks:** `reportedIn` is narrowed from a
  string to a reference to `EcoDocument` (so `check_refs.py` covers it);
  `EcoContribution.date` is an ISO 8601 string, not LinkML `date` (D19);
  `focus` is an annotation property (D12); `TemplateFiller.value` is
  `warp:filler_term` and `EcoAgent.subtype` is `warp:agent_subtype`, because
  `warp:value` and `warp:subtype` hold other kinds of value elsewhere;
  `SynthesisAssessment.direction` and `EcoStatement.strength` restate their
  enum ranges, which `gen-owl` did not inherit.
- **`scripts/clean_owl.py`** runs on `gen-owl`'s output in `make gen`. The
  guide expected one job; there are eight, each reported: retype CAMO's
  predicate enum values as object properties, drop sentinel values, remove
  restrictions on annotation properties, replace `xsd:date`, declare
  `slot_uri` IRIs `gen-owl` uses but never declares, resolve upstream
  object/datatype property conflicts, move covering axioms off named enum
  classes (R15), and turn relative IRIs from element metadata into literals.
- **`scripts/export_rdf.py`** (`make rdf`) writes `project/statements.ttl`:
  every statement, proposition, evidence line, study result, agent and
  document as named individuals, inlined records at `<owner>/<slot>` IRIs
  (no blank nodes), enum values as IRIs, sentinels not exported, ISO dates
  verbatim plus `xsd:dateTime` bounds, and one relation triple per
  non-negated statement. Groups register polarity handling in `RELATIONS`.
- **`scripts/project_owl.py`** (`make owl`) writes `project/axioms.ttl` and
  `project/reports/projection.md`. The gate: scope universal, not negated,
  every grouped statement observed, a supporting SynthesisAssessment.
  Causal and interaction project existential subsumption with a
  `warp:derived_from` axiom annotation. **On the examples nothing passes**
  (5 propositions: assertional or prototypical), which is the correct answer.
- **`scripts/check_owl.py`** in `make validate`: one kind per IRI across every
  generated file, no `xsd:date`/`gYear`/`duration`, no relative IRIs,
  placeholders or SEPIO placeholder IRIs in data, no exported sentinels,
  every predicate declared or upstream, no abstract predicate asserted,
  literal/IRI values matching the declared property kind, and every
  restricted property declared. Clean on all generated files.
- **`make owl-check`**: ROBOT merges and `validate-profile` (EL for nodes,
  axioms, sites and projects; DL for the schema and relations), with a
  catalog for local imports. **ROBOT is not installed on the machine this was
  built on, so neither profile has been checked by ROBOT yet**; the target
  warns and succeeds without it (Q9).
- Generated ontology IRIs live under `https://w3id.org/ecoweaver/warp/ontology/`
  (`…/nodes`, `…/axioms`, `…/statements`, `…/scales`, `…/relations`), so they
  cannot collide with slot IRIs such as `warp:nodes`.
- `examples/kramer1995.ttl` is marked historical: `project/statements.ttl` is
  the generated rendering.
- Schema version **0.6.0**; examples' `profile_version` 0.6.0.
- Tests: exporter (no blank nodes, annotation properties, enum IRIs,
  sentinels, relation triples and negation, date bounds, no SEPIO
  placeholder), the gate (accepts one fixture; rejects assertional,
  prototypical, negated, anticipated, missing modality, unassessed and
  disputed, and a proposition with one anticipated statement among two),
  every `check_owl` rule, `clean_owl` (covering axioms, sentinels and nothing
  else; predicate retyping; annotation restrictions; one-value enums), and
  the generated files lint clean.
- No proposition ID changed.

## 0.5.0

Provenance the SEPIO way, and checks for what the schema cannot say. New
`EcoAgent`, `EcoContribution` (with `role`) and `EcoRecordMetadata`;
`StatementSet.agents`. Who made a statement is now a contribution with role
author (replaces `agent_kind` on the statement, which moves to the agent);
`annotator` and `annotation_timestamp` move to `recordMetadata`; evidence lines
can record who judged them (`evidence_assessor`).
`CareMetadata.knowledge_holder` (text) → `knowledge_holders` (agent ids).
`evidence_type` and `role` documented as specializations of SEPIO's `subtype`
and `activityType`. New `scripts/check_statements.py` and `make check`.
Identity rule `warp-prop-identity/3`: the key says "affirmed" rather than
"asserted"; derived proposition ids change.

## 0.4.0

Back to SEPIO's own terms. "Claim" is now "statement" throughout: `Claim` →
`EcoStatement`, `CausalClaim` → `CausalStatement`, `InteractionClaim` →
`InteractionStatement`, `ClaimSet` → `StatementSet`; slots `causal_claims` /
`interaction_claims` / `derived_from_claims` → `*_statements`, `claimant_kind`
→ `agent_kind` (`AgentKindEnum`); registry annotation `warp_claims_slot` →
`warp_statements_slot`; example ids `warp:claim/…` → `warp:statement/…`.
Profile classes get their own `class_uri`s (`warp:EcoProposition`,
`warp:EcoEvidenceLine`, …) instead of names that look like SEPIO's; example
`type` values name the concrete class. Derivation now also fills
`targetProposition` on each statement's evidence lines. Identity rule and
proposition ids unchanged.

## 0.3.0

Renamed WARP (Weaving Assertions, Reasons and Provenance), from "EcoWeaver
Claims". Namespace `https://w3id.org/ecoweaver/warp/` and CURIE prefix `warp:`
(were `.../claims/` and `ew:`); schema files `warp.yaml` and
`warp_templates.yaml`; group registry annotations `warp_*`; identity rule
renamed `warp-prop-identity/2` (same rule as before). No structural changes.

## 0.2.0

Node templates (LinkML → DOSDP and OWL); predicate group registry and the
biotic interaction group; `EcoProposition` base class; `propositions` list
renamed `causal_propositions`; identity rule v2 adds the group to the key.

## 0.1.0

First draft of the SEPIO profile.
