"""Build and check one WARP profile on its example sets.

    python scripts/build_profile.py config/profiles.yaml causal [--out build/profiles]

Runs the same pipeline as `make all`, restricted to a profile's schema
(project/profiles/warp_<name>.yaml, from scripts/subset_schema.py) and the
example sets the config lists for it: derivation, LinkML validation, the
reference, statement and value checks, node expansion, RDF export, the
projection gate, the schema as OWL (gen-owl, then clean_owl.py with the
profile's relations), and the OWL lint over everything it wrote.

One extra check: each set's derived records must equal the committed
examples/*.derived.yaml from the full build, since a profile changes no IRI
and no identity key. The group-specific checks and reports belong to the
groups a profile leaves out or are not needed to show it works, so they are
not run.

Output goes to <out>/<name>/ (not committed). Exits 1 if any step fails.
"""

import argparse
import os
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable
OWLGEN_FLAGS = ("--no-use-native-uris --xsd-anyuri-as-iri "
                "--default-permissible-value-type owl:NamedIndividual")


def body(path):
    """A derived file without its GENERATED header line."""
    lines = Path(path).read_text(encoding="utf-8").splitlines()
    return "\n".join(l for l in lines if not l.startswith("# GENERATED"))


class Runner:
    def __init__(self):
        self.failed = []

    def run(self, label, cmd, stdout=None):
        print(f"--- {label}", flush=True)
        exe = shutil.which(cmd[0]) or cmd[0]
        with (open(stdout, "w", encoding="utf-8") if stdout else open(os.devnull, "w")) as out:
            proc = subprocess.run([exe, *cmd[1:]], cwd=ROOT, text=True,
                                  stdout=out if stdout else subprocess.PIPE,
                                  stderr=subprocess.PIPE if stdout else subprocess.STDOUT,
                                  env={**os.environ, "PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8"})
        text = proc.stdout if not stdout else ""
        if text:
            print(text.rstrip())
        if proc.returncode != 0:
            if stdout and proc.stderr:
                print(proc.stderr.rstrip()[-3000:])
            print(f"FAILED ({proc.returncode}): {label}")
            self.failed.append(label)
        return proc.returncode == 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("config", type=Path)
    parser.add_argument("profile")
    parser.add_argument("--profiles-dir", type=Path, default=Path("project/profiles"))
    parser.add_argument("--out", type=Path, default=Path("build/profiles"))
    parser.add_argument("--templates", type=Path, default=Path("templates/node_templates.yaml"))
    parser.add_argument("--owlgen-flags", default=OWLGEN_FLAGS)
    args = parser.parse_args(argv)

    config = yaml.safe_load((ROOT / args.config).read_text(encoding="utf-8"))
    prof = (config.get("profiles") or {}).get(args.profile)
    if prof is None:
        sys.exit(f"ERROR: no profile '{args.profile}' in {args.config}")
    schema = args.profiles_dir / f"warp_{args.profile}.yaml"
    relations = args.profiles_dir / f"warp-relations_{args.profile}.ttl"
    if not (ROOT / schema).exists():
        sys.exit(f"ERROR: {schema} not found; run make profiles")
    out = args.out / args.profile
    (ROOT / out).mkdir(parents=True, exist_ok=True)
    sch = ["--schema", str(schema)]
    inputs = [Path(p) for p in prof.get("examples") or []]
    assessments = [str(p) for p in prof.get("assessments") or []]
    r = Runner()

    derived = []
    for inp in inputs:
        d = out / (inp.stem + ".derived.yaml")
        derived.append(str(d))
        r.run(f"derive strategies: {inp}", [PY, "scripts/derive_strategies.py", str(inp), str(d), *sch])
        r.run(f"derive propositions: {inp}", [PY, "scripts/derive_propositions.py", str(d), str(d), *sch])
        r.run(f"derive projects: {inp}", [PY, "scripts/derive_projects.py", str(d), str(d), *sch])
        full = inp.with_name(inp.stem + ".derived.yaml")
        print(f"--- same derived records as the full build: {full}")
        if (ROOT / d).exists() and (ROOT / full).exists() and body(ROOT / d) == body(ROOT / full):
            print("identical")
        else:
            print(f"FAILED: {d} differs from {full}")
            r.failed.append(f"derived records differ: {inp}")

    files = [str(p) for p in inputs] + derived + assessments
    r.run("linkml-validate", ["linkml-validate", "-s", str(schema), "-C", "StatementSet", *files])
    r.run("check_refs", [PY, "scripts/check_refs.py", *files, *sch])
    r.run("check_statements", [PY, "scripts/check_statements.py", *derived, *assessments, *sch])
    r.run("check_values", [PY, "scripts/check_values.py", *files, *sch])
    r.run("expand_nodes", [PY, "scripts/expand_nodes.py", str(args.templates), *derived,
                           "--owl", str(out / "nodes.ttl"), "--sites", str(out / "sites.ttl"),
                           "--tsv-dir", str(out / "tsv")])
    r.run("export_rdf", [PY, "scripts/export_rdf.py", *derived, *assessments,
                         "--out", str(out / "statements.ttl"), *sch])
    r.run("project_owl", [PY, "scripts/project_owl.py", *derived, *assessments,
                          "--out", str(out / "axioms.ttl"), "--report", str(out / "projection.md"),
                          "--projects", str(out / "projects.ttl"), *sch])
    r.run("gen-json-schema", ["gen-json-schema", str(schema)], stdout=ROOT / out / "warp.schema.json")
    if r.run("gen-owl", ["gen-owl", *shlex.split(args.owlgen_flags), str(schema)],
             stdout=ROOT / out / "warp.owl.raw.ttl"):
        r.run("clean_owl", [PY, "scripts/clean_owl.py", str(out / "warp.owl.raw.ttl"),
                            str(out / "warp.owl.ttl"), "--relations", str(relations), *sch])
        (ROOT / out / "warp.owl.raw.ttl").unlink(missing_ok=True)
    ttl = [str(out / f) for f in ("nodes.ttl", "axioms.ttl", "statements.ttl", "warp.owl.ttl",
                                  "sites.ttl", "projects.ttl") if (ROOT / out / f).exists()]
    r.run("check_owl", [PY, "scripts/check_owl.py", *ttl, str(relations)])

    print()
    if r.failed:
        print(f"profile {args.profile}: {len(r.failed)} step(s) failed: {'; '.join(r.failed)}")
        sys.exit(1)
    print(f"profile {args.profile}: every step passed; output in {out}")


if __name__ == "__main__":
    main()
