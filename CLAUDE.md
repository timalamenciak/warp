# CLAUDE.md

Working notes for anyone (person or Claude Code session) changing WARP. Read
this before touching the schema, a script or an example. The design record is
in `docs/proposals/`: the build guide and its decisions
(`warp-0.4-dev-guide.md`), the reference for every slot and enum
(`warp-0.4-reference.html`) and the proposals themselves
(`warp-proposals-0.4.html`); "0.4" names the proposal round, not a release.
The graph contract is `docs/rdf-owl.md`.

## Running the build

- `make all` runs patterns → vocab → derive → nodes → gen → rdf → owl →
  validate → check → owl-check → reports → profiles → profile-check → test.
  It takes six to ten minutes on the development machine.
- `make profile PROFILE=causal` builds and checks one predicate-group
  profile (`config/profiles.yaml`) into `build/profiles/` (not committed).
- `make test` runs the pytest suite in `tests/` (one to two minutes; some
  tests read the generated files in `project/`, so run `make all` first after
  changing the schema).
- Edit the `Makefile` with a file editor, not a shell heredoc: heredocs in
  this environment have folded its backslash line continuations.
- Windows: GNU make is not in Git Bash. Rtools ships one: put
  `/c/rtools45/usr/bin` on `PATH` (`export PATH="$PATH:/c/rtools45/usr/bin"`).
- `robot` is not on `PATH` on the development machine. `make owl-check` warns
  and exits 0 without it (Q9); releases are checked with ROBOT.
- `pip install -r requirements.txt` installs everything, including `dosdp`,
  which `make patterns` needs.

## Conventions

- **Never edit `src/warp/schema/upstream/`.** Make every change in the profile
  (`src/warp/schema/warp.yaml`) by `is_a` and `slot_usage`.
- **Never hand-edit generated files**: `patterns/`, `project/`,
  `examples/*.derived.yaml`, and any other output a script writes. Regenerate
  them with `make`.
- **Every derivation rule has a version constant**, and every derived record
  stores the rule version that made it. Changing a rule means bumping its
  version.
- **Derived records** (propositions, canonical strategies, projects,
  transferred costs) are never written by annotators or in input examples.
- **New predicate groups** follow `docs/predicate-groups.md` and are discovered
  from schema annotations. Derivation code is group-agnostic unless a rule
  cannot be expressed as an identity key.
- **Examples are illustrative.** Mark placeholders with TODO. Never invent DOIs,
  ontology IDs or figures that could pass as real.
- **Choose terms by `docs/terminology.md`**: an ontology term, else a local
  term in `vocab/local/` with its upstream status (a plan to upstream it, or
  why not), and text only where a slot allows it.
- **Use only ontology CURIEs you have verified.** Otherwise use a placeholder
  under the `TODO:` prefix (`TODO:planting`, never `ELMO:TODO_planting`) and add
  it to `TODOS.md`. Nothing under a real ontology's prefix is invented. Offline,
  the ECOCORE imports in `C:\ODK\harvest\ecocore\imports\*.owl` are a local
  source for BFO, RO, IAO, ENVO, PATO, PCO, PO, UBERON, CHEBI and GO IDs.
- **Every prefix an example uses is declared in the profile.** A CURIE that
  cannot be expanded is an error, not a warning.
- **The graph rules in `docs/rdf-owl.md` hold for every group**: one IRI is one
  kind of thing; predicates are declared once as object properties; polarity is
  in the predicate, never only in a qualifier; nothing becomes an OWL axiom
  unless it passes the projection gate.
- **Names.** The code says `Statement`, `StatementSet`, `EcoStatement`; the
  proposals say `Claim`, `ClaimSet`, `RecommendationClaim`. Use the code's
  names everywhere (Q1). Where a proposal sketch says `claimant`, the code's
  equivalent is a contribution with role `author`.
- **Versions.** The schema version is in `warp.yaml` (`version`), mirrored in
  `warp_templates.yaml`, `warp-relations.ttl` and the examples'
  `profile_version`. Change them together.
- **Ask before adding a dependency** to `requirements.txt`.

## Definition of done (every change)

- `make all` passes, including tests, reference checks and `make owl-check`.
- Existing examples still validate. If any derived ID changed, say which and
  why.
- Every IRI the change introduces has exactly one kind (class, individual,
  object property, annotation property, datatype), and `scripts/check_owl.py`
  is clean.
- An entry in `CHANGELOG.md` under the unreleased version.
- Docs updated where the change altered behaviour (`README.md`, `docs/*.md`).
- Open questions not resolved are added to `TODOS.md`, citing the proposal and
  its question number where there is one.
- Tests for every new rule, check and script.
- One commit per change, its message naming the change.

## How the code works

### Predicate group registry

A group is any `EcoStatement` subclass in `warp.yaml` carrying these class
annotations, read by `load_groups()` in `scripts/derive_propositions.py`:

| Annotation | Meaning |
|---|---|
| `warp_group` | short name; first field of the identity key |
| `warp_statements_slot` | `StatementSet` list holding the group's statements |
| `warp_propositions_slot` | `StatementSet` list holding its propositions |
| `warp_proposition_class` | the group's proposition class |
| `warp_identity_extras` | optional: ordered slot paths added to the identity key |
| `warp_identity_rule` | optional: rule name recorded instead of the shared one |
| `warp_derived_by` | optional: the script that derives the group, if not `derive_propositions.py` |

The predicate enum is found as the induced range of `predicate` on the
statement class; `rosetta_template` annotations on its values render
proposition text.

### Proposition identity and IDs

Rule `warp-prop-identity/4` (constant `RULE_VERSION`).
The key is `"|".join([group, subject, predicate, object,
"negated"|"affirmed", scope])`, followed by `path=<canonical JSON>` for each
of the group's `warp_identity_extras` (missing extras are `null`). Causal and
interaction declare no extras, so their keys are the six shared fields.
The proposition ID is `"warp:prop/" + sha1(key)[:12]`. **The rule version is
not part of the hash** (it is recorded on the proposition as
`identity_rule_version`), so a rule change that leaves a group's key string
unchanged leaves its IDs unchanged (D4, Q11). Statements whose scope is
missing or `unclear` are not grouped and are reported. Propositions written by
people with `status: open_question` keep their IDs.

### Slots on CausalStatement

- Inherited from SEPIO `Statement` (attributes, not top-level slots):
  `subject`, `predicate`, `object`, `proposition`, `statementText`,
  `direction`, `strength`, `hasEvidenceLines`, `contributions`,
  `recordMetadata`, `reportedIn`, `dateAuthored`.
- Top-level slot from the profile: `scope`.
- Inline attributes on `EcoStatement`: `original_text`, `source_spans`, `care`.
- Inline attributes on `CausalStatement`: `negated`, `causal_language`,
  `predicate_qualifiers`, `comparator`, `camo_edge_id`.
- Shared slots on `EcoStatement`: `modality`, `context`, `ecosystem_context`,
  `place`, `temporal_extent`, `specified_in`.

### Claimant

There is no `claimant` slot. The claimant is the `contributor` of the
statement's `EcoContribution` with `role: author`. The EcoWeaver synthesis
pipeline, as claimant of `SynthesisAssessment`s, is the agent
`warp:agent/ecoweaver-synthesis` (`agent_kind: synthesis_pipeline`).

### Types of `temporal_extent` and `ecosystem_context`

- `temporal_extent`: CAMO `TemporalExtent` (`duration_months`,
  `duration_text`, `lag_months`, `observation_grain`, `observation_seasons`).
  It has **no start or end**, so periods use the profile's own `Period` class.
- `ecosystem_context`: CAMO `EcosystemFunctionalGroupEnum`, the IUCN Global
  Ecosystem Typology functional groups (110 values). A kind of ecosystem, not
  a place: places go in `place`.

### Shared helpers

- `scripts/warp_schema.py`: cached SchemaView, the prefix map of the profile
  and its imports, CURIE expansion, and `walk()`, which yields every slot
  value of a StatementSet with its class and induced slot. Use it for any
  new schema-driven check rather than hard-coding slot names.
- `scripts/warp_time.py`: ISO 8601 strings to half-open `xsd:dateTime`
  bounds, and period overlap. Never compare date strings.
- `scripts/check_values.py`: CURIEs, units, places, scales and dates. Slots
  restrict their prefixes with a `warp_allowed_prefixes` annotation.
- `scripts/gen_vocab.py`: `vocab/scales.yaml` to SKOS, and the local term
  register `vocab/local/` to SKOS concepts (`concept:`, `place:`) and OWL
  classes (`term:`). `load_register()` and `register_index()` give any check
  the registered local IRIs.

### Templates to OWL and DOSDP

- `scripts/templates_lib.py` loads `templates/node_templates.yaml` and checks
  each template (every var used, every fixed term labelled).
- `scripts/gen_dosdp.py` writes one DOSDP pattern per template to `patterns/`
  (Manchester text built from term labels) plus `patterns/prefixes.yaml`.
- `scripts/expand_nodes.py` reads the `node_definitions` of each StatementSet,
  checks fillers against the template (allowed prefixes, entity type), and
  writes each node as an `owl:Class` with label, `IAO:0000115` definition and
  an `owl:equivalentClass` intersection to `project/nodes.ttl`, plus DOSDP fill
  tables in `patterns/data/`.

### RDF and OWL

- `project/warp.owl.ttl`: `gen-owl $(OWLGEN_FLAGS)` then `scripts/clean_owl.py`
  (eight reported jobs; see `docs/rdf-owl.md` §9.1). Enum values are
  individuals, predicate enum values object properties, SEPIO slots WARP uses
  have `warp:` IRIs via `slot_uri` in `slot_usage` (Q13).
- `src/warp/owl/warp-relations.ttl`: hand-maintained; every predicate WARP
  mints, abstract parents marked `warp:abstract_predicate true`, and the
  annotation properties `warp:subject`/`predicate`/`object`/`focus`.
- `project/statements.ttl`: `scripts/export_rdf.py`, schema-driven. Group
  polarity hooks go in its `RELATIONS` dict.
- `project/axioms.ttl` + `project/reports/projection.md`:
  `scripts/project_owl.py`. Group projections go in its `PROJECTIONS` dict;
  no entry means the group projects nothing.
- `scripts/check_owl.py` (in `make validate`) must stay clean. Sentinel
  values are listed once, in `SENTINELS` in `clean_owl.py`.
- New slot names: if a slot name already exists elsewhere with a different
  kind of value (literal vs IRI), give the new one its own `slot_uri`, or
  `check_owl.py` will report the IRI as two kinds.

### Derivation

`make derive`, per statement set: `derive_strategies.py IN OUT` (canonical
strategies, references rewritten; superseded IDs in `replaces`) →
`derive_propositions.py OUT OUT` (every group not `warp_derived_by` another
script) → `derive_projects.py OUT OUT` (implementation group: projects, with
`proj:` node records). Then `transfer_costs.py` writes
`examples/cost_statements.transferred.yaml`. Derived IDs that annotators must
cite (a causal proposition in `justified_by`, a project in a criteria
statement) are computed by running derivation once and pasting the ID, as the
examples do. `tests/test_derived_ids.py` fails if any committed derived file
is stale.

### Profiles

- `scripts/subset_schema.py` reads `config/profiles.yaml` and writes
  `project/profiles/warp_<name>.yaml` and `warp-relations_<name>.ttl`: the
  shared core, the named groups, the named optional lists, and anything they
  reach (ranges, is_a, mixins, class slots, slot_usage keys, recursively).
  Group lists come from the registry annotations; no group is named in code.
  An all-groups profile must reproduce `warp.yaml` exactly (tested).
- `scripts/build_profile.py` runs the core pipeline with `--schema` on a
  profile and fails if its derived records differ from the full build's.
- Every script that reads the schema takes `--schema`, and must work when a
  group it knows about is absent (as `derive_projects.py` does without the
  implementation group). Profiles change no IRI, so never give a profile's
  elements their own URIs.

### Group-specific scripts

- Checks, in `make validate`: `check_tolerance.py` (object kind per
  predicate, curves), `check_cost.py` (per-predicate cost rules),
  `check_sites.py` (sites, implementation objects, criteria statements).
- Reports, in `make reports`: `report_guidance.py`, `report_tolerance.py`,
  `report_cost_completeness.py`, `report_target2.py`.
- `expand_nodes.py` also writes strategies (subclass axioms) and, with
  `--sites`, site individuals; `project_owl.py --projects` writes project
  individuals.
- Templates have a `kind` (class_expression, composite, particular) and may
  list `refinements` (depth, season); `templates_lib.check_template` enforces
  what each kind needs.
- `check_statements.py` allows `direction` on a statement class whose schema
  requires it (criteria verdicts) and enum-valued subjects or objects.

## Where the proposals' sketches differ from the code

The proposals were written before the code settled. Read their sketches with
these translations:

- `Claim`, `ClaimSet`, `causal_claims`, `RecommendationClaim` → `Statement`,
  `StatementSet`, `causal_statements`, `RecommendationStatement` (Q1).
- `claimant: org:dfo` → a contribution with `role: author` and a `contributor`
  agent ID.
- Sketch IDs use prefixes the profile did not declare (`stmt:`, `prop:`,
  `org:`, `site:`, `proj:`, `comp:`, `crit:`, `scale:`, `dfoprio:`) (D20).
- `predicate: warp:suggested_to` and `predicate: camo:decreases`: predicates
  are enum value names (`suggested_to`, `prevents`), not CURIEs, and CAMO has
  no `decreases`.
- `causal_language: hedged` is not a CAMO `ClaimStrengthEnum` value
  (`no_relationship`, `associational`, `uncertain_causal`, `direct_causal`).
- `evidence_type: expert_opinion` → CAMO's `expert_judgment` (D2).
- `QuantityValue` → `Quantity` (R1); `Period` vs `temporal_extent`: CAMO's
  `TemporalExtent` has no start or end, so `Period` is new (R2).
- Registry keys such as `warp_group` placeholders → the four real `warp_*`
  annotations (R11).
- `ImplementationProposition # = project` and `subject_proposition` → a
  project individual under `proj:` (D17, R18).
- `predicate_qualifiers` declared under `attributes` in the implementation
  sketch, as an inline attribute per group in the code (R6).
- `ecosystem_context: florida-usa` and similar: regions are not
  `EcosystemFunctionalGroupEnum` values → `place` (D18, R19).
- Units such as `UO:hectare`, `ha`, `protected_area` → verified CURIEs or
  `TODO:` placeholders, and counts as `Count` (R20).
- The guide calls the per-group extras rule v3; in the code it is
  `warp-prop-identity/4`.
