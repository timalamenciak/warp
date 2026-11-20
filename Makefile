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
STATEMENTS  := examples/bloodroot_statements.yaml examples/kramer1995_statements.yaml
DERIVED     := $(STATEMENTS:.yaml=.derived.yaml)
ASSESSMENTS := examples/bloodroot_assessment.yaml examples/kramer1995_assessment.yaml

# Enum values are OWL individuals unless an enum says otherwise with
# `implements:` (predicate enums say owl:ObjectProperty). The flag covers the
# enums imported from CAMO, which the profile cannot annotate (D14, R14).
# --no-use-native-uris honours slot_uri (WARP IRIs for SEPIO slots, Q13);
# --xsd-anyuri-as-iri makes CURIE-valued slots object properties, so their
# values are IRIs, not strings.
OWLGEN_FLAGS := --no-use-native-uris --xsd-anyuri-as-iri --default-permissible-value-type owl:NamedIndividual

# Hand-maintained predicate declarations (D13) and the ROBOT catalog that
# resolves the logical layer's owl:imports to local files.
RELATIONS := src/warp/owl/warp-relations.ttl
CATALOG   := src/warp/owl/catalog-v001.xml
ROBOT     ?= robot

# Every generated Turtle file, for check_owl.py. Sites and projects arrive in
# Phase 7; wildcard keeps the list honest until then.
OWL_FILES = project/nodes.ttl project/axioms.ttl project/statements.ttl project/warp.owl.ttl             project/scales.ttl $(wildcard project/sites.ttl project/projects.ttl             project/criteria_concepts.ttl) $(RELATIONS)
LOGICAL   = project/nodes.ttl project/axioms.ttl $(wildcard project/sites.ttl project/projects.ttl)

.PHONY: all templates patterns vocab nodes derive validate check lint gen rdf owl owl-check test owl-dosdp clean

# templates -> vocab -> nodes -> propositions -> schema OWL -> rdf -> owl ->
# validate (shapes, references, OWL lint) -> checks -> profiles -> tests
all: patterns vocab nodes derive gen rdf owl validate check owl-check test

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

# Source scales (and, later, criteria concepts) as SKOS.
vocab:
	$(PY) scripts/gen_vocab.py vocab/scales.yaml --out project/scales.ttl

# Expand node definitions: OWL (Turtle) + DOSDP fill tables.
nodes: templates
	$(PY) scripts/expand_nodes.py $(TEMPLATES) $(STATEMENTS) \
	  --owl project/nodes.ttl --tsv-dir patterns/data

# Same OWL via the ODK route (needs dosdp-tools installed).
owl-dosdp: patterns nodes
	mkdir -p project/dosdp
	for t in patterns/data/*.tsv; do \
	  p=$$(basename $$t .tsv); \
	  $(DOSDP_TOOLS) generate --obo-prefixes=true --prefixes=patterns/prefixes.yaml \
	    --template=patterns/$$p.yaml --infile=$$t --outfile=project/dosdp/$$p.ofn || exit 1; \
	done

# --- Statements ------------------------------------------------------------------

# Derive propositions for every registered predicate group, one set at a time.
derive:
	for f in $(STATEMENTS); do \
	  $(PY) scripts/derive_propositions.py $$f $${f%.yaml}.derived.yaml || exit 1; \
	done

# Shapes and enums (LinkML), every reference resolving (check_refs.py), and
# the OWL lint over every generated Turtle file (check_owl.py).
validate: derive gen rdf owl
	linkml-validate -s $(SCHEMA) -C StatementSet $(STATEMENTS) $(DERIVED) $(ASSESSMENTS)
	$(PY) scripts/check_refs.py $(STATEMENTS) $(DERIVED) $(ASSESSMENTS)
	$(PY) scripts/check_owl.py $(OWL_FILES)

# What the schema cannot express: Assertion Mode, negation, contribution roles,
# CARE, and references resolving across files. Pass files that cite each other together.
# Identifiers, units, places, scales and dates: scripts/check_values.py.
check: derive
	$(PY) scripts/check_statements.py $(DERIVED) $(ASSESSMENTS)
	$(PY) scripts/check_values.py $(STATEMENTS) $(DERIVED) $(ASSESSMENTS)

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
	$(PY) scripts/clean_owl.py project/warp.owl.raw.ttl project/warp.owl.ttl --relations $(RELATIONS)
	rm -f project/warp.owl.raw.ttl

# --- RDF and OWL (docs/rdf-owl.md) -------------------------------------------------

# The reification layer: every statement, proposition, evidence line, ...
rdf: derive
	$(PY) scripts/export_rdf.py $(DERIVED) $(ASSESSMENTS) --out project/statements.ttl

# The logical layer: class axioms for propositions that pass the gate (D15).
owl: derive
	$(PY) scripts/project_owl.py $(DERIVED) $(ASSESSMENTS) --out project/axioms.ttl 	  --report project/reports/projection.md

# OWL 2 profiles with ROBOT: EL for the logical layer, DL for the schema and
# relations. Without robot on PATH this warns and succeeds (Q9); releases are
# checked with it.
owl-check:
	@if command -v $(ROBOT) >/dev/null 2>&1; then 	  mkdir -p project/reports && 	  $(ROBOT) merge --catalog $(CATALOG) $(foreach f,$(LOGICAL),--input $(f)) 	    validate-profile --profile EL --output project/reports/profile-el.txt && 	  $(ROBOT) merge --catalog $(CATALOG) --input project/warp.owl.ttl --input $(RELATIONS) 	    validate-profile --profile DL --output project/reports/profile-dl.txt && 	  echo "owl-check: EL (logical layer) and DL (schema, relations) both pass"; 	else 	  echo "WARNING: '$(ROBOT)' is not on PATH: OWL 2 profile checks skipped."; 	  echo "         Releases are checked with ROBOT (make owl-check ROBOT=/path/to/robot)."; 	fi

# pytest suite under tests/.
test:
	$(PY) -m pytest -q tests

clean:
	rm -rf project examples/*.derived.yaml patterns/data patterns/*.yaml
