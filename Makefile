SCHEMA    := src/warp/schema/warp.yaml
TSCHEMA   := src/warp/schema/warp_templates.yaml
TEMPLATES := templates/node_templates.yaml
PY        ?= python
# Optional: path to dosdp-tools (https://github.com/INCATools/dosdp-tools/releases)
DOSDP_TOOLS ?= dosdp-tools

# Generators print to stdout; on Windows that is not UTF-8 unless told.
export PYTHONIOENCODING := utf-8
export PYTHONUTF8 := 1

# Annotated statement sets (inputs). Each gets a derived file next to it.
STATEMENTS  := examples/bloodroot_statements.yaml \
               examples/kramer1995_statements.yaml \
               examples/recommendation_statements.yaml \
               examples/strategy_statements.yaml \
               examples/tolerance_statements.yaml \
               examples/cost_statements.yaml \
               examples/implementation_statements.yaml
DERIVED     := $(STATEMENTS:.yaml=.derived.yaml)
ASSESSMENTS := examples/bloodroot_assessment.yaml examples/kramer1995_assessment.yaml

# Explicit cost transfers (transfer_costs.py): a versioned rule and a
# selection of source statements, giving a generated set of derived costs.
TRANSFER_SELECTION := config/cost_transfer/selection.yaml
TRANSFERRED := examples/cost_statements.transferred.yaml
ALL_DERIVED  = $(DERIVED) $(TRANSFERRED)

# Enum values are OWL individuals unless an enum says otherwise with
# `implements:` (predicate enums say owl:ObjectProperty). The flag covers the
# enums imported from CAMO, which the profile cannot annotate (D14, R14).
# --no-use-native-uris honours slot_uri (WARP IRIs for SEPIO slots, Q13);
# --xsd-anyuri-as-iri makes CURIE-valued slots object properties, so their
# values are IRIs, not strings.
OWLGEN_FLAGS := --no-use-native-uris --xsd-anyuri-as-iri \
                --default-permissible-value-type owl:NamedIndividual

# Hand-maintained predicate declarations (D13) and the ROBOT catalog that
# resolves the logical layer's owl:imports to local files.
RELATIONS := src/warp/owl/warp-relations.ttl
CATALOG   := src/warp/owl/catalog-v001.xml
ROBOT     ?= robot

# Every generated Turtle file, for check_owl.py. Files that later phases add
# are picked up by wildcard once they exist.
OWL_FILES = project/nodes.ttl project/axioms.ttl project/statements.ttl \
            project/warp.owl.ttl project/scales.ttl project/local_terms.ttl \
            $(wildcard project/sites.ttl project/projects.ttl project/local_classes.ttl) \
            $(RELATIONS)
LOGICAL   = project/nodes.ttl project/axioms.ttl \
            $(wildcard project/sites.ttl project/projects.ttl project/local_classes.ttl)

.PHONY: all templates patterns vocab nodes derive validate check lint gen rdf owl \
        owl-check reports profiles profile profile-check test owl-dosdp clean

# templates -> vocab -> nodes -> propositions -> schema OWL -> rdf -> owl ->
# validate (shapes, references, OWL lint) -> checks -> OWL profiles -> reports ->
# predicate-group profiles -> tests
all: patterns vocab derive nodes gen rdf owl validate check owl-check reports \
     profiles profile-check test

# --- Node templates ----------------------------------------------------------

# Validate the template definitions against their LinkML schema.
templates:
	linkml-validate -s $(TSCHEMA) -C NodeTemplateCollection $(TEMPLATES)

# Generate DOSDP pattern files from the templates and check them.
patterns: templates
	$(PY) scripts/gen_dosdp.py $(TEMPLATES) patterns
	for f in patterns/*.yaml; do \
	  [ $$f = patterns/prefixes.yaml ] || $(PY) -m dosdp validate -i $$f || exit 1; \
	done

# Source scales as SKOS, and the local term register (vocab/local/,
# docs/terminology.md): concepts as SKOS, local classes as OWL.
vocab:
	$(PY) scripts/gen_vocab.py vocab/scales.yaml --out project/scales.ttl \
	  --local vocab/local --local-out project/local_terms.ttl \
	  --classes-out project/local_classes.ttl

# Expand node definitions: OWL (Turtle) + DOSDP fill tables. Reads the
# derived sets, where canonical strategy nodes live.
nodes: templates derive
	$(PY) scripts/expand_nodes.py $(TEMPLATES) $(DERIVED) \
	  --owl project/nodes.ttl --sites project/sites.ttl --tsv-dir patterns/data

# Same OWL via the ODK route (needs dosdp-tools installed).
owl-dosdp: patterns nodes
	mkdir -p project/dosdp
	for t in patterns/data/*.tsv; do \
	  p=$$(basename $$t .tsv); \
	  $(DOSDP_TOOLS) generate --obo-prefixes=true --prefixes=patterns/prefixes.yaml \
	    --template=patterns/$$p.yaml --infile=$$t --outfile=project/dosdp/$$p.ofn || exit 1; \
	done

# --- Statements ------------------------------------------------------------------

# Derive, one set at a time: canonical strategies first (references to local
# strategy IDs are rewritten), then propositions for every registered
# predicate group, so statements about one strategy meet in one proposition.
derive:
	for f in $(STATEMENTS); do \
	  d=$${f%.yaml}.derived.yaml; \
	  $(PY) scripts/derive_strategies.py $$f $$d && \
	  $(PY) scripts/derive_propositions.py $$d $$d && \
	  $(PY) scripts/derive_projects.py $$d $$d || exit 1; \
	done
	$(PY) scripts/transfer_costs.py $(DERIVED) --select $(TRANSFER_SELECTION) --out $(TRANSFERRED)

# Shapes and enums (LinkML), every reference resolving (check_refs.py), the
# OWL lint over every generated Turtle file (check_owl.py), and the groups'
# own rules (check_tolerance.py, check_cost.py).
validate: derive gen rdf owl
	linkml-validate -s $(SCHEMA) -C StatementSet $(STATEMENTS) $(ALL_DERIVED) $(ASSESSMENTS)
	$(PY) scripts/check_refs.py $(STATEMENTS) $(ALL_DERIVED) $(ASSESSMENTS)
	$(PY) scripts/check_owl.py $(OWL_FILES)
	$(PY) scripts/check_tolerance.py $(ALL_DERIVED)
	$(PY) scripts/check_cost.py $(ALL_DERIVED)
	$(PY) scripts/check_sites.py $(ALL_DERIVED)

# What the schema cannot express: Assertion Mode, negation, contribution
# roles, CARE, references resolving across files (check_statements.py); and
# identifiers, units, places, scales and dates (check_values.py); and that
# every slot has a place in the plain-language rendering and every value is
# rendered (render_statements.py --check, config/rosetta.yaml). Pass files
# that cite each other together.
check: derive
	$(PY) scripts/check_statements.py $(ALL_DERIVED) $(ASSESSMENTS)
	$(PY) scripts/check_values.py $(STATEMENTS) $(ALL_DERIVED) $(ASSESSMENTS)
	$(PY) scripts/render_statements.py $(ALL_DERIVED) $(ASSESSMENTS) --check

# Warnings about camelCase slot names come from upstream SEPIO and are expected.
lint:
	-linkml-lint $(SCHEMA)
	linkml-lint $(TSCHEMA)

# The schema as JSON Schema and as OWL. gen-owl's output goes through
# clean_owl.py, which reports each change it makes.
gen:
	mkdir -p project
	gen-json-schema $(SCHEMA) > project/warp.schema.json
	gen-owl $(OWLGEN_FLAGS) $(SCHEMA) > project/warp.owl.raw.ttl
	$(PY) scripts/clean_owl.py project/warp.owl.raw.ttl project/warp.owl.ttl \
	  --relations $(RELATIONS)
	rm -f project/warp.owl.raw.ttl

# --- RDF and OWL (docs/rdf-owl.md) -------------------------------------------------

# The reification layer: every statement, proposition, evidence line, ...
rdf: derive
	$(PY) scripts/export_rdf.py $(ALL_DERIVED) $(ASSESSMENTS) --out project/statements.ttl

# The logical layer: class axioms for propositions that pass the gate (D15).
owl: derive
	$(PY) scripts/project_owl.py $(ALL_DERIVED) $(ASSESSMENTS) --out project/axioms.ttl \
	  --report project/reports/projection.md --projects project/projects.ttl

# OWL 2 profiles with ROBOT: EL for the logical layer, DL for the schema and
# relations. Without robot on PATH this warns and succeeds (Q9); releases are
# checked with it.
owl-check:
	@if command -v $(ROBOT) >/dev/null 2>&1; then \
	  mkdir -p project/reports && \
	  $(ROBOT) merge --catalog $(CATALOG) $(foreach f,$(LOGICAL),--input $(f)) \
	    validate-profile --profile EL --output project/reports/profile-el.txt && \
	  $(ROBOT) merge --catalog $(CATALOG) --input project/warp.owl.ttl --input $(RELATIONS) \
	    validate-profile --profile DL --output project/reports/profile-dl.txt && \
	  echo "owl-check: EL (logical layer) and DL (schema, relations) both pass"; \
	else \
	  echo "WARNING: '$(ROBOT)' is not on PATH: OWL 2 profile checks skipped."; \
	  echo "         Releases are checked with ROBOT (make owl-check ROBOT=/path/to/robot)."; \
	fi

# --- Reports ------------------------------------------------------------------------

# Findings, not validation: project/reports/.
reports: derive
	$(PY) scripts/render_statements.py $(ALL_DERIVED) $(ASSESSMENTS) \
	  --out project/reports/statements.md
	$(PY) scripts/report_guidance.py $(ALL_DERIVED) $(ASSESSMENTS) \
	  --out project/reports/guidance.md --csv project/reports/guidance.csv
	$(PY) scripts/report_tolerance.py $(ALL_DERIVED) --out project/reports/tolerance.md
	$(PY) scripts/report_cost_completeness.py $(ALL_DERIVED) \
	  --out project/reports/cost_completeness.md --csv project/reports/cost_completeness.csv
	$(PY) scripts/report_target2.py $(ALL_DERIVED) --jurisdiction CA-SK --year 2026 \
	  --degraded crit:degraded-area/fed-draft-1 --degraded crit:degraded-area/ref-ecosystem-1 \
	  --effective crit:effective-restoration/fed-draft-1 --out project/reports/target2.md

# --- Predicate-group profiles (config/profiles.yaml) -----------------------------

# WARP restricted to some predicate groups: one schema and one relations file
# per profile in project/profiles/ (committed, like the rest of project/).
PROFILES_CONFIG := config/profiles.yaml
PROFILE_NAMES = $(shell $(PY) scripts/subset_schema.py $(PROFILES_CONFIG) --list)

profiles:
	$(PY) scripts/subset_schema.py $(PROFILES_CONFIG) --out-dir project/profiles

# Build and check one profile on its example sets: make profile PROFILE=causal.
# Output in build/profiles/<name>/ (not committed).
profile: profiles
	@test -n "$(PROFILE)" || { echo "usage: make profile PROFILE=<name> (one of: $(PROFILE_NAMES))"; exit 1; }
	$(PY) scripts/build_profile.py $(PROFILES_CONFIG) $(PROFILE) --owlgen-flags "$(OWLGEN_FLAGS)"

# Every profile, as make all runs it.
profile-check: profiles
	for p in $(PROFILE_NAMES); do \
	  $(PY) scripts/build_profile.py $(PROFILES_CONFIG) $$p --owlgen-flags "$(OWLGEN_FLAGS)" || exit 1; \
	done

# pytest suite under tests/.
test:
	$(PY) -m pytest -q tests

clean:
	rm -rf project build examples/*.derived.yaml patterns/data patterns/*.yaml
