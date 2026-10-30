# TODOs

Open work on WARP, roughly in priority order.
ECO facts below were checked against ECO release 2026-07-10 in OLS on
2026-10-10.

---

## 0. Review the HTML documentation (drafted 2026-10-11)

`docs/html/` holds draft documentation at three levels, written from
`warp.yaml`, the scripts, the how-to guides, this file and the examples:

| Page | Reader | Size |
|---|---|---|
| `index.html` | everyone: picks a level | 1 screen |
| `basic.html` | contributors filing GitHub issues; no schema knowledge | ~13 sections |
| `camo.html` | annotators who already know CAMO (added 2026-10-11) | ~15 sections |
| `advanced.html` | users who want the model explained but won't build | ~16 sections |
| `mechanic.html` | maintainers: schema internals and the build | ~18 sections |

Most of the content restates the README and how-to guides. What needs
your judgement is (a) whether each page fits its reader and (b) the
handful of places where the docs **say something the repo doesn't**:
an invented process, an unverified command, a design suggestion. Those
are listed below so you don't have to hunt for them.

Review in this order: the contributor page is the one that will be
public, and decisions there (0.1) block linking the docs from the README.

### 0.1 Decisions the contributor page depends on (do first, ~15 min)

These describe processes that don't exist yet. Decide them, then edit
the page to match (or remove the passage).

- [ ] **Issue tracker URL.** `basic.html` says "open an issue" but never
      links one. Add the repository's issues URL (and an issue template
      in `.github/ISSUE_TEMPLATE/` if you want the template pre-filled;
      the text is in the "The issue template" section).
- [ ] **Private route for community knowledge.** The "Your own and
      community knowledge" section tells people with Indigenous or
      community knowledge to open an issue saying only that they'd like
      to contribute, after which "a maintainer will arrange a private
      route". No such route is defined. Decide what it is (email, form,
      Loom intake; ties to 5, consent capture) and who answers.
- [ ] **Pseudonymous credit.** The page says contributors "can stay
      pseudonymous". The schema allows it (`warp:agent/...` ids), but
      who decides is still open (4, agent identity). Confirm or soften.
- [ ] **"What happens next".** Describes a maintainer recording the
      issue, checks, grouping and synthesis. The intake workflow isn't
      decided (5). Confirm it's close enough, or reword as intent.

### 0.2 Contributor page: read as a newcomer (~20 min)

Open `docs/html/basic.html` in a browser. Read it as someone who knows
the ecology but has never seen a schema.

- [ ] Any jargon left? (Words to watch: node, predicate, proposition,
      scope. Each should be explained before or where it's used.)
- [ ] Plain-language glosses match the schema's meaning:
      - scope labels "one case / sometimes / typically / always / not
        sure" for assertional / contingent / prototypical / universal /
        unclear (the "sometimes" gloss for contingent is mine);
      - the relationship table's one-line meanings (from CAMO's
        `CausalPredicateEnum` descriptions, simplified);
      - the confidence options for `ClaimStrengthEnum`.
- [ ] The filled-in example (the notebook entry) still matches
      `warp:statement/notebook-c1` in `examples/bloodroot_statements.yaml`.
- [ ] Phone width: browser dev tools, ~375 px. No sideways scrolling
      except inside tables and code blocks.
- [ ] Light and dark mode both readable (pages follow the OS setting).

### 0.2b CAMO annotators page: check, then test on a student (~30 min + a session)

`docs/html/camo.html`. The field mapping comes from the README's CAMO
table and CAMO 0.8.0's `CausalEdge`; the rest is guidance I wrote.
Check these first:

- [ ] **Node convention.** The page tells annotators to drop
      `state_or_change_qualifier` and let the predicate carry the sign
      ("Nodes: drop the state qualifier"). That follows the example and
      `docs/node-templates.md`, but it's a habit change for CAMO users
      and affects FCM rendering, which CAMO keeps at the state level.
      Confirm it's the instruction you want to give.
- [ ] **"can" vs "may" callout** under scope: "may" is hedging (stays
      prototypical), "can" is contingent. This is my reading of Vogt's
      types, not something in the repo. Confirm or rewrite.
- [ ] **Scope decision table** (`type` → prototypical / contingent /
      universal): check the questions match how you'd teach it.
- [ ] **"Keep filling `causal_language` and `philosophical_accounts`".**
      CAMO requires both; WARP doesn't (see 4, new item). The page
      tells annotators to fill them anyway. Confirm.
- [ ] **"Not mapped yet"** tells annotators to keep recording study
      metadata (`SourceDocument`), `annotation_confidence` and
      `annotation_notes` in CAMO for now. Confirm that's the interim
      instruction.
- [ ] **The side-by-side CAMO edge** is reconstructed by hand from the
      example statement. Validate it against CAMO if you want to be sure.
- [ ] **Test it.** Have the student read it and translate two or three
      of her own CAMO edges into WARP statements. Run `make derive check`
      on the result (or the commands in `mechanic.html`). Where she got
      stuck or guessed is what to fix on the page.

### 0.3 Advanced page: check claims against the schema (~30 min)

`docs/html/advanced.html`. Mostly field tables copied from `warp.yaml`
and CAMO; spot-check rather than read every row. Specific things to
confirm:

- [ ] **Nodes section**: "a reasoner can tell … a node about a species
      sits under a node about its genus". True only once NCBITaxon is
      imported alongside `nodes.ttl`. Keep, qualify, or cut.
- [ ] **"Same or different?" table** in Propositions: five worked cases
      of the identity rule. Check each verdict, especially the context
      row (says context is not identity "yet").
- [ ] **Roles table**: `reviewer` is shown as allowed "anywhere". That's
      what `check_statements.py` does (it has no rule for reviewer), but
      is it what you intend?
- [ ] **Two kinds of direction and strength**: the worked sentence ("a
      large effect measured in a weak study is …") reads correctly.
- [ ] **Open decisions** list matches sections 1 and 4–6 of this file;
      drop anything you no longer consider open.
- [ ] **Writing a precise suggestion**: the YAML snippet omits ids on
      contributions and evidence lines (contributors don't know them).
      Fine for an issue, but it won't validate as-is. Say so on the
      page, or add placeholder ids.

### 0.4 Mechanic page: verify commands and the design suggestions (~30 min)

`docs/html/mechanic.html`. Everything about the scripts was read from
the code; the derivation and check behaviour was confirmed by running
them. Not verified:

- [ ] **Windows `make` install commands** (`choco install make`,
      `winget install GnuWin32.Make`): untested. Test one or replace
      with "install GNU make".
- [ ] **ROBOT EL check** in "Compiling a full database":
      `robot validate-profile --profile EL --input project/nodes.ttl --output …`.
      The README says nodes.ttl was checked with ROBOT but not how; run
      it once and confirm the command.
- [ ] **"Compiling a full database"** describes a merge step that doesn't
      exist (see 7.1). That section is a design proposal. Agree with it
      or rewrite it before anyone follows it.
- [ ] **"Gotchas"**: confirm each one is a known limitation and not a
      bug you'd rather fix (several are now items in section 7).

### 0.5 Publish

- [ ] Link `docs/html/index.html` from the README's "How-to guides" list.
- [ ] Decide where the docs are served (GitHub Pages from `docs/`, or
      only browsed in the repo).
- [ ] Add a docs check to the release checklist (README "Changes" and
      the mechanic page's "Versioning and release"): the pages quote
      enum values, field names, the identity rule and the version. When
      any of these change, update the matching page:

      | If you change | Update |
      |---|---|
      | `version`, `RULE_VERSION` | all five pages (footer and intro) |
      | scope, predicate, evidence type or role enums | `basic.html`, `camo.html`, `advanced.html` |
      | statement, evidence line or CARE fields | `camo.html`, `advanced.html`, `mechanic.html` "Profile classes" |
      | anything mapped from CAMO, or a CAMO re-vendor | `camo.html`, `advanced.html` "Coming from CAMO" |
      | a script or the Makefile | `mechanic.html` |
      | node templates | `advanced.html` "Nodes", `mechanic.html` "Node template subsystem" |

---

## 1. Evidence recording

### 1.1 Record how each assertion was made (manual or automatic)

ECO already distinguishes assertions made by a person from those made by a
pipeline. EcoWeaver needs the same distinction between Loom-curated statements
and LLM-extracted ones.

- [ ] Add an `assertion_method` slot to `EcoEvidenceLine` (and probably
      `EcoStatement`), constrained to:
  - `ECO:0000218` manual assertion
  - `ECO:0000203` automatic assertion
- [ ] Have Loom fill it automatically (human-confirmed → manual;
      extraction pipeline output not yet reviewed → automatic).
- [ ] Decide what a human-reviewed LLM extraction counts as, and write it
      down. Suggestion: manual, with the pipeline recorded as a contributor.
- [ ] Surface it in outputs, so a synthesis can be filtered to manually
      asserted evidence only.

### 1.2 Record study quality separately from evidence strength

SEPIO's `informationQuality` slot exists on every information entity but
the profile does not constrain it.

- [ ] Choose the appraisal scheme (align with the grassland systematic map's
      critical appraisal, so quality is recorded once).
- [ ] Constrain `informationQuality` on `EcoStudyResult` / `EcoDocument` to
      that scheme's values.
- [ ] Document the rule: quality describes the study; `strengthOfEvidenceProvided`
      describes how strongly an evidence line bears on a proposition. Do not
      fold one into the other.

### 1.3 Decide where CAMO's `certainty_grade` lives

- [ ] Rosetta rendering currently reads `certainty_grade` from the CAMO edge.
      Choose between: (a) article level → `EcoEvidenceLine.strengthOfEvidenceProvided`;
      (b) synthesis only → `SynthesisAssessment.strength`. Update the renderer.

---

## 2. ECO term requests

ECO has no terms for ecological study designs. Searches for field experiment,
observational study, survey, expert opinion, traditional knowledge,
randomized trial, meta-analysis, systematic review, case report and
ecological returned nothing relevant (2026-10-10). CAMO's `EvidenceTypeEnum`
therefore uses `broad_mappings` to ECO parents where they exist and leaves
the rest unmapped.

Plan: one joint request on the ECO tracker
(<https://github.com/evidenceontology/evidenceontology/issues>), framed as a
new ecology and environmental evidence domain, with CAMO's annotations as
the worked use case. Once terms exist, switch CAMO's `broad_mappings` to
`meaning` (exact) for the matching values.

- [ ] Check the ECO tracker for related open requests first.
- [ ] Agree the list and definitions below with EcoWeaver colleagues
      (semantics working group), and the Indigenous knowledge entry with
      knowledge holders before anything is submitted.
- [ ] Submit, link the issue here, and follow up.

### Draft requests

Definitions follow ECO's "A type of … evidence that …" style. Parents are
existing ECO terms.

| # | Proposed label | Proposed parent | Draft definition | CAMO value it would ground |
|---|---|---|---|---|
| 1 | field experiment evidence | ECO:0000006 experimental evidence | A type of experimental evidence resulting from a manipulation carried out in a natural or semi-natural setting, in which treatments are applied to field plots, sites or populations and compared with untreated or alternative-treatment controls. | randomized_experiment (field case) |
| 2 | randomized field experiment evidence | #1 | A type of field experiment evidence in which treatments are assigned to experimental units at random. | randomized_experiment |
| 3 | before-after-control-impact evidence | #1 (or ECO:0000006 if not judged a field experiment) | A type of evidence comparing a variable before and after an intervention or impact at affected and unaffected sites, so that change due to the intervention can be separated from background change. | quasi_experiment (BACI) |
| 4 | natural experiment evidence | ECO:0000006 experimental evidence | A type of evidence in which the comparison groups are created by an event or circumstance not controlled by the investigator (e.g. a wildfire, a flood, a policy boundary), analysed as if it were a treatment. | natural_experiment |
| 5 | observational study evidence | new branch under ECO:0000000 evidence, or under ECO:0000006 (to discuss with ECO) | A type of evidence obtained by measuring or recording variables in their natural setting without the investigator assigning treatments. | parent for #6–#8 |
| 6 | longitudinal observational study evidence | #5 | A type of observational study evidence in which the same units are measured repeatedly over time (e.g. monitoring plots, panel surveys). | observational_longitudinal |
| 7 | cross-sectional observational study evidence | #5 | A type of observational study evidence in which units are measured at a single point in time and compared across conditions. | observational_cross_sectional |
| 8 | case study evidence | #5 | A type of observational study evidence describing a single site, project or event in detail, without a comparison group designed in advance. | case_study |
| 9 | structural equation model evidence | ECO:0007672 computational evidence, or ECO:0000361 inferential evidence | A type of evidence in which hypothesised causal relationships among several variables are fitted to observational or experimental data as a system of equations. | structural_equation_model |
| 10 | practitioner statement evidence | ECO:0006151 documented statement evidence | A type of documented statement evidence in which a practitioner (e.g. a restoration practitioner, land manager or farmer) reports observations or outcomes from their own practice. Precedent: ECO:0006152 medical practitioner statement evidence. | practitioner_experience |
| 11 | expert elicitation evidence | ECO:0006151 documented statement evidence | A type of documented statement evidence obtained through a structured process of eliciting judgements from people with relevant expertise (e.g. Delphi, structured expert judgement). | expert_judgment |
| 12 | Indigenous knowledge evidence | **To be framed with knowledge holders. Do not submit without that.** | Placeholder. Should NOT be placed under "self-reported individual's statement evidence" (ECO:0006153): Indigenous knowledge is held and governed collectively, is often place- and practice-based, and is subject to community protocols (CARE). Consider whether ECO is the right home at all, and what governance any term would need. | indigenous_knowledge |

Not requested: meta_analysis and systematic_review map acceptably to
ECO:0000212 combinatorial evidence for now; modeling_simulation to
ECO:0007672 computational evidence; theoretical to ECO:0000361 inferential
evidence. Revisit if finer terms would change any output.

---

## 3. Upstream contributions

### SEPIO (pull requests to sepio-framework/sepio-linkml)

- [ ] **Mappings**: `class_uri` / mappings from the LinkML classes to the
      SEPIO OWL terms, and a real default prefix in place of
      `https://example.org/sepio-model/`. Highest value; until then the
      profile's `EcoStatement` and `EcoProposition` carry TODO comments.
- [ ] `direction` as an enum (supports / disputes / neutral).
- [ ] Reference-by-ID for evidence items (`evidence_item_refs` here).
- [ ] Offer `evidence_object` (correlation / mechanism / both).
- [ ] Contact Matthew Brush before opening PRs.

### CAMO

- [ ] Promote `CausalEdge` inline `attributes` to top-level `slots`, so the
      profile can reuse them (and to clear `gen-owl` ambiguity warnings).
- [ ] Rename edge `direction` → `causal_direction`, `strength` → `effect_strength`.
- [ ] Replace `token_or_type` with `scope` (semantic unit types).
- [ ] Rename `CausalNode` → `Node` (or similar): WARP uses it for every
      predicate group's nodes, including non-causal interaction statements.
- [ ] Rename `ClaimStrengthEnum` (e.g. `CausalLanguageEnum`), so WARP uses
      SEPIO's "statement" vocabulary without a leftover "claim".
- [ ] Add a planting / seeding action term to ELMO; replace
      `ELMO:TODO_planting` in the example and templates.

---

## 4. Modelling decisions

- [ ] Map `ContributionRoleEnum` values to Contribution Role Ontology (CRO)
      terms, and confirm the four roles cover Loom's workflow.
- [ ] Agent identity for practitioners and knowledge holders: when to use
      ORCID, when a pseudonymous `warp:agent/...` id, and who decides (ties
      to consent capture in section 5).
- [ ] Confirm semantic unit definitions (assertional, contingent,
      prototypical, universal) against Vogt's own; update `SemanticUnitScopeEnum`.
- [ ] Identity rule: should any context (ecosystem type, comparator) be part
      of proposition identity? Bump `RULE_VERSION` if so.
- [ ] BFO review of the `quality_of_process_of_population` template
      (PATO quality of a process vs BFO 2020 process profiles).
- [ ] SSSOM crosswalk between Wikidata QIDs (CAMO `entity_term`) and
      NCBITaxon IDs (template fillers).
- [ ] Fill the example's `TODO` QIDs, DOI and verbatim sentence, or replace
      the example with a real annotated paper.
- [ ] Required fields: CAMO requires `causal_language` and
      `philosophical_accounts` on every edge; WARP's `CausalStatement`
      makes neither required. Decide whether to require them (slot_usage)
      or keep them optional for non-literature statements.
- [ ] Where CAMO's `SourceDocument` study metadata goes (coordinates,
      country/province, study period and duration, study design, sample
      size, sampling effort). `EcoDocument` has none of it; options are
      attributes on `EcoDocument`, or a study class that documents report.
- [ ] Map `annotation_confidence` and `annotation_notes` (README §5 lists
      them as not yet mapped), probably on `EcoRecordMetadata`.
- [ ] Map the remaining `EvidenceBaseAssessmentEdge` aggregate fields
      (counts, Russo-Williamson, Bradford Hill, effect-size summaries,
      refresh tracking) onto `SynthesisAssessment`, or decide they're
      computed outputs and not stored.
- [ ] Node convention for CAMO users: `state_or_change_qualifier` is
      still on `CausalNode`, but WARP nodes are variables with the sign on
      the predicate. Decide whether WARP forbids, ignores or maps the
      qualifier, and how FCM weights (stored at state level in CAMO) are
      derived without it.

---

## 5. Annotation workflow (Loom)

See README section 10 for the questions. Decisions needed:

- [ ] What annotators see (CAMO edge form with statements written behind it?).
- [ ] How scope is asked (four-way choice, or "one place and time, or in general?").
- [ ] Who creates evidence lines (annotators, or derived from study design fields).
- [ ] Intake forms and consent capture for non-literature sources.
- [ ] When derivation runs, and who reviews ungrouped statements.
- [ ] Migration of CAMO 0.8 edges via `camo_edge_id`.

---

## 6. Outputs

- [ ] Prototype exporters (evidence gap map, fuzzy cognitive map, Bayesian
      network, TREK) on the example statement set, to test roll-up and
      aggregation choices before the annotation protocol is fixed.
- [ ] Decide the unit of counting (studies, statements or study arms).
- [ ] Write the evidence-type weighting rules as explicit, versioned config.

---

## 7. Build and tooling

Found while writing `docs/html/mechanic.html` (2026-10-11). Each was
confirmed by reading the code or running the scripts; the mechanic page
documents them as "gotchas" until fixed.

### 7.1 Derivation across files

`derive_propositions.py` takes one StatementSet. Statements in different
files never share a proposition object: matching statements get the same
hash id, but separate `derived_from_statements` lists. Fine for the
example; a real database needs statements from many sources grouped together.

- [ ] Decide: merge StatementSets before deriving, or derive per file and
      union propositions by id afterwards.
- [ ] Write the merge script (concatenate every StatementSet list, dedupe
      by id, fail when one id names two different objects, pass open
      questions through untouched).
- [ ] Generalize the Makefile: `derive`, `validate` and `check` hard-code
      the example paths; only `STATEMENTS` is a variable.

### 7.2 Smaller fixes

- [ ] **Hand-written propositions vanish.** Derivation silently drops any
      existing proposition that isn't `open_question` / `raised_as_question`.
      Warn on stderr, or refuse.
- [x] **Patterns skipped by validation.** `make patterns` validates
      `patterns/*_*.yaml`, so a template id without an underscore is never
      DOSDP-validated. Loop over template ids instead, or exclude
      `prefixes.yaml` by name.
- [ ] **Comments lost.** Derivation rewrites the input through
      `yaml.safe_dump`, dropping YAML comments. Either accept it and say
      so in the annotation guidance, or switch to `ruamel.yaml`.
- [ ] **Capitals mid-sentence.** Proposition text inserts node `name`s
      verbatim ("…prevents Population growth rate…"). Lowercase the first
      letter of non-proper names, or use the template-generated label.
- [ ] **Duplicate ids across files.** `check_statements.py` compares
      duplicate ids within a file only. Compare across all files given.
- [ ] **Windows.** `make` is not in Git Bash. Document an install, or add
      a small Python task runner alongside the Makefile.
