SCHEMA    := src/warp/schema/warp.yaml
TSCHEMA   := src/warp/schema/warp_templates.yaml
TEMPLATES := templates/node_templates.yaml
STATEMENTS    := examples/bloodroot_statements.yaml
PY        ?= python
# Optional: path to dosdp-tools (https://github.com/INCATools/dosdp-tools/releases)
DOSDP_TOOLS ?= dosdp-tools

.PHONY: all templates patterns nodes derive validate check lint gen owl-dosdp clean

all: patterns nodes derive validate check gen

# --- Node templates ----------------------------------------------------------

# Validate the template definitions against their LinkML schema.
templates:
	linkml-validate -s $(TSCHEMA) -C NodeTemplateCollection $(TEMPLATES)

# Generate DOSDP pattern files from the templates and check them.
patterns: templates
	$(PY) scripts/gen_dosdp.py $(TEMPLATES) patterns
	for f in patterns/*.yaml; do \n	  [ $$f = patterns/prefixes.yaml ] || $(PY) -m dosdp validate -i $$f || exit 1; \n	done

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

# Derive propositions for every registered predicate group.
derive:
	$(PY) scripts/derive_propositions.py $(STATEMENTS) examples/bloodroot_statements.derived.yaml

validate: derive
	linkml-validate -s $(SCHEMA) -C StatementSet \
	  $(STATEMENTS) \
	  examples/bloodroot_statements.derived.yaml \
	  examples/bloodroot_assessment.yaml

# What the schema cannot express: Assertion Mode, negation, contribution roles,
# CARE, and references resolving across files. Pass files that cite each other together.
check: derive
	$(PY) scripts/check_statements.py \
	  examples/bloodroot_statements.derived.yaml \
	  examples/bloodroot_assessment.yaml

# Warnings about camelCase slot names come from upstream SEPIO and are expected.
lint:
	-linkml-lint $(SCHEMA)
	linkml-lint $(TSCHEMA)

gen:
	mkdir -p project
	gen-json-schema $(SCHEMA) > project/warp.schema.json
	gen-owl $(SCHEMA) > project/warp.owl.ttl

clean:
	rm -rf project examples/*.derived.yaml patterns/data patterns/*.yaml
