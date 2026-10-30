# WARP roadmap: November 2026 to April 2027

Goal for the six months: **WARP 1.0.0-rc1**, a semantically complete schema
that means the same thing in YAML, JSON and RDF/OWL, built on Lars Vogt's
semantic units, with the node and predicate modules validated by
automated tests rather than by reading.

Each `###` heading below is meant to become one GitHub issue. Copy the
heading as the title and the body as the issue text. Milestones are
months; issues within a month are in suggested order.

Sources for the Vogt material:
- Vogt, Kuhn & Hoehndorf 2024, *Semantic units*, J Biomed Semantics 15:7,
  doi:10.1186/s13326-024-00310-5
- Vogt et al. 2025, *A Framework for FAIR and CLEAR Ecological Data and
  Knowledge*, arXiv:2508.08959
- Vogt et al. 2026, *Rosetta Statements*

Existing open work in [TODOS.md](TODOS.md) is referenced as `TODOS §n`
rather than repeated.

## What "semantically complete" means here

Use this as the acceptance test for 1.0. WARP is semantically complete
when:

1. Every class, slot and enum value has a definition, a `class_uri` /
   `slot_uri` / `meaning`, and at least one valid and one invalid
   example in the test corpus.
2. Every statement scope has a stated formal reading in OWL (or an
   explicit, documented "not expressible in OWL", with the pattern used
   instead).
3. Every node template produces OWL that a reasoner accepts and that is
   in OWL 2 EL, and every filler is checked against its variable's range
   in the source ontology.
4. Every predicate group can be checked by machine to be complete
   (enum, qualifiers, statement class, proposition class, registry
   annotations, verbalization, RDF pattern).
5. The same corpus validates in YAML, in JSON (JSON Schema), and in RDF
   (SHACL), with the same pass/fail result per file, and round-trips
   YAML → JSON → RDF → YAML without loss.
6. Rules the schema cannot express are written once, run against both
   the YAML and the RDF, and their results agree.

## Suggested labels

| Label | For |
|---|---|
| `area:validation` | test harness, CI, fixtures |
| `area:semantic-units` | Vogt alignment |
| `area:nodes` | node templates, NodeDefinition, OWL for nodes |
| `area:predicates` | predicate groups, qualifiers, verbalization |
| `area:serialization` | JSON, JSON-LD, RDF, SHACL parity |
| `area:upstream` | SEPIO, CAMO, ECO, ELMO, RO contributions |
| `area:docs` | documentation |
| `type:decision` | a modelling decision to make and record |
| `type:research` | reading or consultation before building |

Make an issue for each decision too: write the decision in the issue
before closing it, and link it from the schema comment it affects.

---

## Month 1 (November 2026): validation foundation

Nothing else in this roadmap can be "validated" until there is a test
harness that fails loudly. Build that first.

### 1.1 Put WARP under version control with CI

Labels: `area:validation`

The working copy is not a git repository yet. CI is what turns "make
validate passed on my laptop" into a gate on every change.

Tasks:
- [ ] Initialise the repo (or connect the existing remote), add a
      `.gitignore` for generated files you do not want committed
      (decide whether `project/` and `patterns/` stay committed; see 1.3).
- [ ] Add a GitHub Actions workflow that installs `requirements.txt`
      and runs `make all` and the test suite (1.2) on every push and PR.
- [ ] Add Java + ROBOT + dosdp-tools to the CI image, so the OWL checks
      in Month 3 can run there.
- [ ] Add issue templates for "schema change", "new node template" and
      "new predicate group" (the how-to guides become their checklists).

Done when: a PR that breaks `make validate` shows a red check.

### 1.2 Test suite with valid and invalid fixtures

Labels: `area:validation`

Today the only tests are that three example files validate. A schema is
only validated when files that *should* fail do fail.

Tasks:
- [ ] Add `tests/` with pytest. Layout:
      `tests/fixtures/valid/<Class>/*.yaml` and
      `tests/fixtures/invalid/<Class>/<rule>.yaml`, each invalid fixture
      with a one-line comment naming the rule it breaks.
- [ ] A test that runs `linkml-validate` on every valid fixture
      (expect pass) and every invalid one (expect fail, and the error
      mentions the expected slot).
- [ ] A test that runs `check_statements.py` the same way for the
      rules it owns (Assertion Mode, negation, roles, CARE, references).
- [ ] Seed it: at least one invalid fixture per `required`, `range`,
      `pattern` and enum constraint in `warp.yaml` and
      `warp_templates.yaml`.
- [ ] A coverage script that lists classes and slots with no valid or
      no invalid fixture. Run it in CI as a report (not a failure) for
      now; make it a failure before 1.0 (6.6).

Done when: deleting a `required: true` from the schema makes a test fail.

### 1.3 Pin the toolchain and make builds reproducible

Labels: `area:validation`

LinkML generator output changes between releases, which makes
`project/*.ttl` and `project/*.json` diffs noisy and hides real changes.

Tasks:
- [ ] Pin `linkml`, `linkml-runtime`, `dosdp`, `rdflib`, `pyshacl`,
      `oaklib` versions in `requirements.txt` (or move to `pyproject.toml`
      with a lock file).
- [ ] Pin ROBOT and dosdp-tools versions in the Makefile/CI.
- [ ] Decide whether generated files are committed. If yes, add a CI
      check that regenerating them produces no diff.
- [ ] Generalise the Makefile so `derive`, `validate` and `check` take
      file lists rather than hard-coded example paths (TODOS §7.1).
- [ ] Add a Python task runner (or document a make install) for
      Windows (TODOS §7.2).

Done when: a clean checkout on CI and on your machine produce identical
`project/` output.

### 1.4 Clear the lint and generator warnings, or allowlist them

Labels: `area:validation`, `area:upstream`

`linkml-lint` warnings from SEPIO camelCase slots and `gen-owl`
"ambiguous attribute" warnings from CAMO are currently ignored by
eye. Ignored warnings hide new ones.

Tasks:
- [ ] Capture the current warnings from `linkml-lint`, `gen-owl`,
      `gen-json-schema` and `gen-shacl` into a file.
- [ ] Classify each: upstream (SEPIO/CAMO), fixable here, or accepted.
- [ ] Fix the ones that are WARP's.
- [ ] Add a CI step that fails on any warning not in an allowlist file,
      each allowlist entry pointing to the upstream issue that will
      remove it.

Done when: a new warning fails CI.

### 1.5 Research: read the Vogt papers against WARP

Labels: `area:semantic-units`, `type:research`

The scope enum carries the comment "working glosses; confirm against
Vogt" and README §9 lists it as a gap. Month 2 depends on getting this
right, so do the reading first and write down what it says.

Tasks:
- [ ] Extract from Vogt et al. 2024 and 2025: the definitions of each
      statement unit type, the list of compound unit types, how a
      semantic unit is represented in RDF (unit resource vs. its data
      graph), and how they treat metadata, provenance and access.
- [ ] Extract from the Rosetta Statements paper: what a statement type
      is, how its slots (positions) and verbalization templates are
      defined, and how versioning works.
- [ ] Write `docs/semantic-units.md`: a table mapping each Vogt concept
      to its WARP counterpart (existing, planned, or out of scope), with
      page references.
- [ ] List the questions for Lars (feeds 2.1 and 6.4).

Done when: `docs/semantic-units.md` exists and every row says where in
WARP the concept lives or why it does not.

---

## Month 2 (December 2026): semantic units in the core

### 2.1 Confirm the statement unit types and fix `SemanticUnitScopeEnum`

Labels: `area:semantic-units`, `type:decision`
Depends on: 1.5

Tasks:
- [ ] Replace the glosses on `assertional`, `contingent`,
      `prototypical`, `universal` with Vogt's definitions (quoted
      briefly and cited).
- [ ] Decide whether any further statement unit type in the papers
      applies to WARP (for example terminological or identification
      statements), and add or explicitly exclude it.
- [ ] Decide what `unclear` is: a fifth scope value, or the absence of a
      value with a review flag. Vogt has no "unclear" type, so if it
      stays, document it as a WARP workflow value, not a semantic unit
      type.
- [ ] Settle the "can" vs "may" guidance in `camo.html` (TODOS §0.2b).
- [ ] Add one valid fixture per scope value that a reader can check
      against the definition.
- [ ] Add `meaning` IRIs for each value (Vogt's own if published,
      otherwise `warp:` IRIs with a mapping comment).

Done when: Lars (or someone who has read him closely) agrees with the
definitions in the enum.

### 2.2 Specify the formal (OWL) reading of each scope

Labels: `area:semantic-units`, `type:decision`
Depends on: 2.1

Scope is part of proposition identity, but it currently changes nothing
in the OWL output. Semantic completeness needs each scope to have a
formal reading, or an explicit statement that it has none.

Tasks:
- [ ] Write `docs/scope-semantics.md` with, for each scope, the RDF/OWL
      pattern a proposition's content is rendered as. Starting points
      to check against Vogt:
      - assertional → triples between individuals (ABox);
      - universal → class axiom (`Subject SubClassOf predicate some Object`);
      - contingent → an existential claim about some instances
        (decide: anonymous individuals, or a class-level pattern that
        does not entail universality);
      - prototypical → not expressible in OWL DL; choose a non-entailing
        pattern (annotation-level, or a dedicated `warp:typically`
        construct) so reasoners never treat it as universal.
- [ ] Say how negation renders for each scope (negated universal vs.
      "no instance" vs. a negated assertional statement).
- [ ] Say which scopes a reasoner may combine, and which must be kept
      apart (a prototypical statement must never entail a universal one).
- [ ] Record the decisions in the issue and link from the enum.

Done when: every (scope × negated) combination has a written pattern
and a worked Turtle example.

### 2.3 Add a semantic unit layer to the schema

Labels: `area:semantic-units`
Depends on: 1.5, 2.1

In Vogt's model a semantic unit is its own resource, with its own
identifier and metadata, that stands for a subgraph. WARP statements
already have ids and provenance; make the alignment explicit.

Tasks:
- [ ] Decide: is `EcoStatement` *itself* a statement unit (unit resource
      = the statement record), or does a separate `StatementUnit` wrap
      the subject–predicate–object data graph? Write down why.
      (Likely answer: the `EcoProposition` content is the data graph;
      the statement is the unit resource that carries discursive
      metadata. Check against the papers.)
- [ ] Add an abstract `SemanticUnit` mixin (or class) with the shared
      metadata slots: id, unit type, provenance, license, access. Have
      `EcoStatement`, `EcoProposition` and the compound units (2.4)
      use it.
- [ ] Add `class_uri`s / `exact_mappings` to Vogt's semantic unit
      classes if they have published IRIs; otherwise mint `warp:` IRIs
      and record the intended mapping.
- [ ] Update `derive_propositions.py` and `check_statements.py` if any
      slot names change, and add fixtures.

Done when: every statement and proposition in the examples is
identifiable as a semantic unit of a stated type.

### 2.4 Model the compound units WARP needs

Labels: `area:semantic-units`
Depends on: 2.3

Vogt's compound units group statement units into larger objects (item,
item group, granularity tree, context, dataset and list units in the
2024 paper; causal networks and maps in the 2025 one). WARP has some
of these implicitly.

Tasks:
- [ ] For each compound unit type, decide: needed now, later, or not
      at all. Write the reasoning into `docs/semantic-units.md`.
- [ ] Likely mappings to confirm:
      - `StatementSet` → dataset unit;
      - all statements about one node → item unit (generated view, not
        stored);
      - `EcoEvidenceLine` and `SynthesisAssessment` → compound units
        over statement units;
      - a causal network (propositions sharing nodes) → the causal
        network/map unit from the 2025 paper;
      - `context` on causal statements → context unit.
- [ ] Add schema classes for the ones marked "now", with fixtures.
- [ ] Add a script or query that builds the generated ones (item unit,
      causal network) from a statement set.

Done when: the bloodroot example can be listed as a tree of semantic
units, each with a type.

### 2.5 Separate ontological from discursive content in the RDF

Labels: `area:semantic-units`, `area:serialization`
Depends on: 2.2, 2.3

Vogt distinguishes what is said about the world (ontological) from
what is said about statements (discursive: who said it, how hedged,
what evidence). WARP's statement/proposition split is the same idea,
but the RDF output does not yet keep them apart.

Tasks:
- [ ] Choose the RDF packaging: one named graph per statement unit
      (TriG / nanopublication-style), RDF-star, or SEPIO-style
      reification. Write down the trade-offs; named graphs are the
      option the semantic units papers describe.
- [ ] Write a generator (`scripts/to_rdf.py` or a LinkML generator
      plugin) that emits: the proposition content per 2.2 in the unit's
      data graph, and the statement's discursive metadata on the unit
      resource.
- [ ] Check that running a reasoner over the union of data graphs
      (ontological content only) gives no unwanted entailments from
      hedged, negated or prototypical statements.

Done when: the example renders to TriG, and loading it into a triple
store lets you query "what is claimed" and "who claims it" separately.

### 2.6 Per-unit access and CARE

Labels: `area:semantic-units`
Depends on: 2.3

Vogt notes that semantic units make access restrictions manageable per
subgraph. WARP's `care` sits on statements only.

Tasks:
- [ ] Decide whether `care` moves to the `SemanticUnit` level, so
      compound units (an evidence line built on restricted knowledge) can
      inherit or declare access.
- [ ] Define the inheritance rule: is a compound unit at least as
      restricted as its most restricted member?
- [ ] Add the rule to `check_statements.py` and an invalid fixture.
- [ ] Ties to the private-route decision in TODOS §0.1.

Done when: an assessment citing a `community_restricted` statement is
flagged unless its own access level is compatible.

---

## Month 3 (January 2027): validating the node module

### 3.1 Enforce template-schema rules the prose only describes

Labels: `area:nodes`, `area:validation`

`warp_templates.yaml` says "give exactly one of genus or var" and that
every CURIE needs a label, but only in descriptions.

Tasks:
- [ ] Add LinkML `exactly_one_of` (or `rules`) to `ClassExpression`
      for genus/var.
- [ ] Add a check (in `templates_lib.py`, run by `make templates`)
      that: every `{var}` in `name` and `definition` is declared in
      `vars`; every declared var is used in `equivalent_to`; every
      CURIE in a template has a `terms` entry of the right `kind`
      (classes as genus/range, object properties as `property`); every
      prefix used is declared.
- [ ] One invalid fixture per rule under
      `tests/fixtures/invalid/NodeTemplate/`.

Done when: a template with a typo in a placeholder fails `make templates`.

### 3.2 Check fillers against the ontologies, not just their prefixes

Labels: `area:nodes`, `area:validation`

`allowed_prefixes` stops `PATO` where `NCBITaxon` belongs, but not a
NCBITaxon id that is not under the variable's range, an obsolete term,
or a wrong label.

Tasks:
- [ ] Use OAK (`oaklib`) with local, cached ontology files (or
      SemSQL databases) for each prefix in `node_templates.yaml`.
- [ ] For every `TemplateFiller`: check the term exists, is not
      obsolete, is a subclass of the variable's `range`, and its
      `label` matches the ontology label (warn on mismatch).
- [ ] Do the same for every `terms` entry in `node_templates.yaml`
      (labels drift; RO:0000052 already did).
- [ ] Cache ontology versions in CI and record the versions used in
      the output.
- [ ] Replace `ELMO:TODO_planting` (TODOS §3) or allowlist it until ELMO
      has the term.

Done when: filling `taxon` with a PATO term or an obsolete NCBITaxon id
fails `make nodes`.

### 3.3 Reason over generated node classes

Labels: `area:nodes`, `area:validation`

`nodes.ttl` is said to be OWL 2 EL but that is not checked in the
build, and nothing reasons over it together with the ontologies it
uses.

Tasks:
- [ ] Extract a module (ROBOT `extract --method BOT` or SLME) of each
      source ontology for the terms used.
- [ ] Merge with `nodes.ttl`, run `robot reason --reasoner ELK` and
      `robot validate-profile --profile EL`; fail on unsatisfiable
      classes or profile violations. Add to the Makefile and CI.
- [ ] Report inferred equivalences between node classes: two nodes that
      reason to the same class are duplicate nodes. Make this a CI
      warning now and a check in 3.5.
- [ ] Report the inferred node hierarchy (e.g. a species node under a
      genus node) so the claim in `advanced.html` (TODOS §0.3) is
      either shown to hold or removed.

Done when: CI reasons over the example nodes and fails on an
unsatisfiable template filling.

### 3.4 Prove the two OWL routes agree

Labels: `area:nodes`, `area:validation`

Nodes reach OWL two ways: `expand_nodes.py` (rdflib) and DOSDP via
dosdp-tools. If they ever diverge, which one is right?

Tasks:
- [ ] Run `make owl-dosdp` in CI.
- [ ] Convert both outputs to the same syntax and compare logical
      axioms (ROBOT `diff`, ignoring annotations that are expected to
      differ). Fail on any logical difference.
- [ ] Decide which route is canonical for releases and say so in
      `docs/node-templates.md`.

Done when: CI fails if a template change makes the two routes disagree.

### 3.5 Node identity: deterministic ids and duplicate detection

Labels: `area:nodes`, `type:decision`

Node ids are currently hand-written slugs, so two annotators can mint
two ids for one node.

Tasks:
- [ ] Decide the id rule for defined nodes: a hash or slug of template
      id + sorted fillers, versioned like the proposition identity rule.
- [ ] Add a check that a node's id matches its definition (or record
      the derived id as an alias, if ids must stay human-readable).
- [ ] Fail when two `NodeDefinition`s have the same template and
      fillers, or when 3.3 finds two nodes equivalent.
- [ ] Decide what happens to propositions when two nodes are merged
      (they regroup; bump the identity rule version?).

Done when: the same node defined twice in two files is caught by `make
check`.

### 3.6 Decide the node record and CAMO's state qualifier

Labels: `area:nodes`, `type:decision`, `area:upstream`

WARP uses CAMO `CausalNode` for every group's nodes and treats nodes as
variables with the sign on the predicate, while CAMO keeps
`state_or_change_qualifier` (TODOS §3, §4).

Tasks:
- [ ] Decide: forbid, ignore or map `state_or_change_qualifier` in WARP;
      add the matching check and fixture.
- [ ] Decide how FCM weights are derived without it.
- [ ] Decide on the rename (`CausalNode` → `Node`) and open the CAMO
      issue/PR; until it lands, add a WARP alias class if it helps
      readability.
- [ ] Decide whether a `NodeDefinition` is required for every node in a
      release-quality statement set, and add the check (warn first).
- [ ] Add `camo_entity_type` consistency: the node's `entity_type`
      must equal its template's `camo_entity_type`.

Done when: these four questions have recorded answers and checks.

### 3.7 Template coverage and lifecycle

Labels: `area:nodes`

There are 21 templates, all `draft`.

Tasks:
- [ ] For each template, add a valid filling to the test corpus and run
      it through 3.2–3.4.
- [ ] BFO review of `quality_of_process_of_population` (TODOS §4); apply
      the outcome to other quality-of-process templates
      (`rate_of_ecosystem_process`).
- [ ] Define what moves a template from `draft` → `testing` →
      `released` (e.g. reviewed, used on real data, passes 3.2–3.4) and
      `deprecated` (with `replaced_by`). Add `replaced_by` to the
      template schema.
- [ ] Map every CAMO `EntityTypeEnum` value to the templates that serve
      it; list gaps.
- [ ] SSSOM crosswalk Wikidata QID ↔ NCBITaxon for the example taxa
      (TODOS §4), validated with `sssom-py`.

Done when: every template has a fixture and a status justified by the
lifecycle rules.

---

## Month 4 (February 2027): validating the predicate module

### 4.1 Predicate group conformance check

Labels: `area:predicates`, `area:validation`

Groups are discovered from `warp_*` annotations, so a half-registered
group fails silently or confusingly.

Tasks:
- [ ] Write `scripts/check_groups.py` (run in `make lint` and CI) that
      checks for every class with `warp_group`:
      - all four registry annotations are present and point at real
        slots/classes;
      - `warp_group` values are unique;
      - the proposition class `is_a` `EcoProposition` and constrains
        subject/predicate/object to the *same* ranges as the statement
        class;
      - the statement class has `negated` and `predicate_qualifiers`,
        and the qualifier class uses no reserved SEPIO slot names
        (`direction`, `strength`, `score`, `subject`, `predicate`,
        `object`, `qualifier`);
      - every predicate value has a `meaning` and a `rosetta_template`
        whose placeholders are only `{subject}` and `{object}` (or the
        group's declared positions; see 4.4).
- [ ] Invalid fixtures: copies of the schema with one registry mistake
      each.

Done when: deleting `warp_propositions_slot` from `InteractionStatement`
fails CI with a clear message.

### 4.2 Check predicate IRIs and labels against their ontologies

Labels: `area:predicates`, `area:validation`

Tasks:
- [ ] Using OAK (as in 3.2), check every `meaning` in
      `InteractionPredicateEnum` and CAMO's `CausalPredicateEnum`
      exists, is an object property, is not obsolete, and matches the
      label in the enum's text.
- [ ] Record which CAMO predicates have no external IRI and need a
      `camo:` one minted or an RO request.
- [ ] Add RO hierarchy checks where it matters (e.g. `eats`,
      `pollinates`, `parasite_of` are under `biotically interacts
      with`), so queries can roll up.

Done when: CI fails on an RO id typo.

### 4.3 Constrain subjects and objects by node template

Labels: `area:predicates`, `area:nodes`

`InteractionStatement` says "subject and object are population nodes"
in its description, but any `CausalNode` validates.

Tasks:
- [ ] Add a group annotation (e.g. `warp_subject_templates`,
      `warp_object_templates`) listing the node templates allowed in
      each position, optionally per predicate.
- [ ] Check in `check_statements.py` that each statement's subject and
      object have a `NodeDefinition` with an allowed template.
- [ ] Optionally check RO domain/range of the predicate against the
      template genus with the reasoner from 3.3.
- [ ] Fixtures: an interaction statement whose subject is a
      quality-of-process node must fail.

Done when: the description's constraint is enforced.

### 4.4 Align predicate groups with Rosetta statement types

Labels: `area:predicates`, `area:semantic-units`
Depends on: 1.5

In the Rosetta Statements approach each statement type has defined
positions (subject, object, and further slots such as quantity, unit,
time) and verbalization templates for display. WARP's groups are close
to this but only have `{subject}`/`{object}` templates.

Tasks:
- [ ] Map the parts of a Rosetta statement type onto a WARP group
      (positions → subject/object/qualifier slots; verbalization →
      `rosetta_template`; versioning → group version).
- [ ] Add a group version annotation, and record it on propositions
      next to `identity_rule_version`.
- [ ] Extend verbalization to use qualifiers and scope (e.g. "typically
      prevents", "did not reduce on this plot"), with negated and
      per-scope variants; test the rendered text for every fixture.
- [ ] Fix capitalisation in rendered text (TODOS §7.2).
- [ ] Decide whether WARP publishes its groups as Rosetta statement
      type definitions (for ORKG reuse), and if so, generate them.

Done when: every fixture statement renders to a correct English
sentence that reflects scope and negation.

### 4.5 Move qualifier consistency rules into the schema

Labels: `area:predicates`, `area:validation`

Several rules live only in Python (negated ⇔ `no_relationship`) or not
at all.

Tasks:
- [ ] Express what LinkML `rules` can express directly in `warp.yaml`
      (preconditions/postconditions on slot values), so JSON Schema and
      SHACL generation carry them; keep the rest in
      `check_statements.py`.
- [ ] Add interaction rules as warnings: `eats` and `parasite_of`
      normally have effect_on_subject positive, effect_on_object
      negative; `pollinates` mutualistic. Decide whether these are
      defaults, warnings or errors.
- [ ] Review the causal qualifiers for combinations that are
      contradictory (e.g. `sufficiency` asserted with `contributing_sole`
      contributing) and decide which to check.
- [ ] Decide on required fields (`causal_language`,
      `philosophical_accounts`; TODOS §4).

Done when: each qualifier rule is either in the schema, in the checker
with a fixture, or listed as intentionally unchecked.

### 4.6 Specify the RDF pattern for qualified predicates

Labels: `area:predicates`, `area:serialization`
Depends on: 2.5

An RDF predicate is one IRI; WARP adds qualifiers. With statement units
as named graphs (2.5), decide where qualifiers go.

Tasks:
- [ ] Decide: the data graph holds `subject predicate object` per the
      scope pattern (2.2), and qualifiers attach to the unit resource;
      or qualifiers become part of the data graph (n-ary pattern).
      Check what Vogt does for n-ary statements (the Rosetta paper).
- [ ] Document the pattern per group with a Turtle/TriG example in
      `docs/predicate-groups.md`.
- [ ] Implement it in the RDF generator (2.5) and add round-trip tests
      (5.1).

Done when: both groups render to RDF following one documented pattern.

### 4.7 Add a third predicate group: measurement / observation statements

Labels: `area:predicates`, `area:semantic-units`

Two groups is not enough to show the group mechanism generalises.
Measurement and observation statement units are central to Vogt et al.
2025 and connect WARP statements to `EcoStudyResult` data.

Tasks:
- [ ] Write 4–5 example sentences (e.g. "Mean cover of *Alliaria* in
      treated plots was 12%") and decide the shape: node (variable),
      value, unit, uncertainty, time, place.
- [ ] Follow `docs/predicate-groups.md` exactly; record every place the
      guide was wrong or incomplete and fix the guide.
- [ ] Decide how a measurement statement relates to `EcoStudyResult`
      (same thing? statement points at it?) and how measurements enter
      evidence lines for causal propositions.
- [ ] Units from QUDT or UO; check them as in 4.2.
- [ ] Run 4.1–4.6 on the new group.

Done when: the new group passes the conformance check with no script
changes, and the guide needed only fixes, not new steps.

---

## Month 5 (March 2027): serialization parity and grounding

### 5.1 One corpus, three formats: round-trip tests

Labels: `area:serialization`, `area:validation`

Tasks:
- [ ] For every valid fixture: YAML → JSON (`linkml-convert`) → RDF
      (Turtle and the TriG from 2.5) → back to YAML. Compare the
      result with the original as data (not text). Fail on any
      difference.
- [ ] Generate a JSON-LD context (`gen-jsonld-context`); check that
      expanding the JSON with it gives the same triples as the RDF.
- [ ] Validate every JSON fixture against `project/warp.schema.json`
      with a standard JSON Schema validator (not LinkML) and check the
      pass/fail matches `linkml-validate` for every fixture, valid and
      invalid. List and explain any mismatches (JSON Schema cannot
      express some things).

Done when: CI shows a per-fixture table with identical results across
formats.

### 5.2 SHACL shapes and RDF-side validation

Labels: `area:serialization`, `area:validation`
Depends on: 5.1

Tasks:
- [ ] Generate SHACL (`gen-shacl`) and validate every RDF fixture with
      `pyshacl`.
- [ ] Port `check_statements.py` rules that can be written as
      SHACL-SPARQL constraints (Assertion Mode, negation, role
      placement, CARE presence, references resolving) to a hand-written
      `shapes/warp-rules.ttl`.
- [ ] Parity test: for each invalid fixture, the Python checker and
      SHACL report the same rule. Rules only one side can express are
      listed in the test as known exceptions.

Done when: someone with only the RDF and the SHACL files gets the same
verdicts as `make check`.

### 5.3 Ground the OWL: SEPIO mappings and namespaces

Labels: `area:upstream`, `area:serialization`

Generated OWL is not grounded while SEPIO's LinkML has a placeholder
prefix and no mappings (README §9, TODOS §3).

Tasks:
- [ ] Contact Matthew Brush; propose the mappings PR to
      `sepio-linkml`.
- [ ] Until it merges, add `exact_mappings` on WARP's subclasses to
      SEPIO OWL IRIs.
- [ ] Register `https://w3id.org/ecoweaver/warp/` with w3id and make
      class and slot IRIs resolve to generated docs.
- [ ] Check every prefix in `warp.yaml` resolves and matches the
      Bioregistry/OBO canonical expansion.

Done when: `warp.owl.ttl` loaded with the SEPIO OWL file shows WARP
classes under SEPIO classes.

### 5.4 Land the CAMO refactors

Labels: `area:upstream`

Tasks:
- [ ] Promote `CausalEdge` attributes to top-level slots.
- [ ] Rename `direction`/`strength` on edges; replace `token_or_type`
      with `scope`; rename `ClaimStrengthEnum`; the node rename from 3.6.
- [ ] Release CAMO, re-vendor with `scripts/update_upstream.sh`, remove
      the WARP workarounds and allowlist entries (1.4).

Done when: WARP's `CausalPredicateQualifiers` reuses CAMO slots instead
of re-listing them, and the `gen-owl` ambiguity warnings are gone.

### 5.5 Schema completeness report

Labels: `area:validation`, `area:docs`

Tasks:
- [ ] Script that lists, for WARP's own classes, slots and enum values:
      missing description, missing `class_uri`/`slot_uri`/`meaning`,
      missing mapping, missing valid/invalid fixture (from 1.2), TODO
      comments.
- [ ] Publish the report in CI output and track the count down.
- [ ] Generate reference docs from the schema (`gen-doc`) so field
      tables in `docs/html/` stop drifting (TODOS §0.5).

Done when: the report is at zero for WARP-owned elements, or each
remaining item is a linked issue.

### 5.6 ECO term request

Labels: `area:upstream`

Tasks: as TODOS §2 (check the tracker, agree definitions with the
semantics group and, for the Indigenous knowledge entry, with knowledge
holders; submit; follow up). Add a CI check that flags evidence types
still mapped only by `broad_mappings`.

Done when: the request is filed and linked.

---

## Month 6 (April 2027): real data and 1.0.0-rc1

### 6.1 CAMO 0.8 → WARP migration script

Labels: `area:validation`

Tasks:
- [ ] Write `scripts/migrate_camo.py` following README §5: one
      `CausalStatement` per edge, `token_or_type` → scope (flagged for
      review), evidence lines per evidence type, annotator to
      `recordMetadata`, `camo_edge_id` kept.
- [ ] Test on existing CAMO annotations; list fields that do not map.
- [ ] Map `annotation_confidence`/`annotation_notes` and `SourceDocument`
      study metadata (TODOS §4), since migration will need them.

Done when: a real CAMO export migrates, validates and checks.

### 6.2 Multi-file derivation

Labels: `area:validation`

Tasks: TODOS §7.1 (merge vs. union decision, merge script, cross-file
duplicate ids) plus: warn on hand-written propositions that derivation
drops; decide about YAML comment loss (TODOS §7.2).

Done when: deriving over many files gives one proposition per identity
key.

### 6.3 Stress test on a real annotated corpus

Labels: `area:validation`, `area:nodes`, `area:predicates`

Tasks:
- [ ] Annotate (or migrate) 10–20 real papers, e.g. from the grassland
      systematic map, plus at least one practitioner source and, only
      with consent in place, one community knowledge source.
- [ ] Run the full pipeline. Record every validation failure and sort
      it: data error, schema gap, template gap, or rule too strict.
- [ ] Replace the placeholder bloodroot example with real data, or keep
      it and add the real set as `examples/`.
- [ ] Record node and proposition counts with and without context in the
      identity key (input to 6.5).

Done when: a report lists what broke and each item has an issue.

### 6.4 External review of the semantic units alignment

Labels: `area:semantic-units`, `type:research`

Tasks:
- [ ] Send `docs/semantic-units.md`, `docs/scope-semantics.md` and the
      TriG rendering of the real corpus to Lars Vogt (and SEPIO, for
      the provenance side).
- [ ] Turn the feedback into issues; fix blocking ones before rc1.

Done when: the reviewers' comments are answered.

### 6.5 Close the open modelling decisions

Labels: `type:decision`

Tasks: decide and record, using the corpus from 6.3:
- [ ] context in the identity rule (TODOS §4);
- [ ] `certainty_grade` placement (TODOS §1.3);
- [ ] `assertion_method` (TODOS §1.1) and study quality (TODOS §1.2);
- [ ] contribution roles → CRO, agent identity (TODOS §4).

Done when: no `type:decision` issue blocks 1.0.

### 6.6 Release 1.0.0-rc1

Labels: `area:docs`

Tasks:
- [ ] Turn the fixture-coverage (1.2) and completeness (5.5) reports
      into CI failures.
- [ ] Write the versioning and deprecation policy (what is a breaking
      change: identity rule, enum removals, slot renames).
- [ ] Changelog, regenerated docs, tagged release, Zenodo DOI.
- [ ] Check the release against the six criteria at the top of this
      file and record the result in the release notes.

Done when: rc1 is tagged and every criterion is met or has a named
exception.

---

## Dependency summary

```
1.1 → 1.2 → 1.3/1.4 ─────────────────────────────┐
1.5 → 2.1 → 2.2 → 2.5 → 4.6 → 5.1 → 5.2          │
        └→ 2.3 → 2.4, 2.6                         ├→ 6.3 → 6.4/6.5 → 6.6
3.1 → 3.2 → 3.3 → 3.4, 3.5 → 4.3                  │
4.1 → 4.2, 4.4, 4.5 → 4.7                         │
5.3, 5.4, 5.6 (upstream, start early, slow) ──────┘
```

The upstream items (5.3, 5.4, 5.6) depend on other people. Open them in
Month 1 and work on them in the background, so they are not on the
critical path in Month 5.
