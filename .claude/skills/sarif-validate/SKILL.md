---
name: sarif-validate
description: 'User-invoked only. Validates SARIF output from SARIFReporter (reporting/sarif.py) against the SARIF 2.1.0 schema and the shape expected by the django-query-optimizer-vscode extension, before a release.'
disable-model-invocation: true
---

# SARIF validate

## When to invoke
Manually, before a release, or when the VS Code extension repo
(`django-query-optimizer-vscode`) reports it can't parse a generated report.
Not auto-triggered — SARIF is a cross-repo contract, validation is a deliberate
pre-release gate, not something to run on every edit.

## What to check

1. **Schema conformance** — the JSON must validate against SARIF 2.1.0
   (`$schema` field in `reporting/sarif.py` points at the canonical schema URL).
   Use a JSON Schema validator (e.g. `pip install jsonschema` in the Docker test
   image, or an online SARIF validator) against a sample report generated via
   `--sarif-output`.
2. **Required top-level shape** — `version: "2.1.0"`, `runs[].tool.driver.name`
   matching `TOOL_NAME`, `runs[].results[]` each with `ruleId`, `level`, `message.text`,
   and `locations[].physicalLocation`.
3. **Severity mapping** — cross-check `recommendations/base.py`'s `Severity` enum
   against the level mapping in `reporting/sarif.py` (`CRITICAL`/`HIGH` → `error`,
   `MEDIUM` → `warning`, others → `note`). A new `Severity` member added without
   updating this mapping will silently default/crash.
4. **VS Code extension expectations** — diff the generated report's rule ids and
   location format against what `django-query-optimizer-vscode` expects to parse
   (check that repo's fixture/test SARIF files if available locally).

## How to run

```bash
# Generate a sample SARIF report inside Docker (never on host, per repo rule)
make docker-test  # or the project's --sarif-output pytest invocation, e.g.:
# docker compose run --rm --no-deps --profile test backend-test \
#   pytest --sarif-output=/tmp/report.sarif tests/

# Validate against schema (inside the same container or a throwaway venv)
python -c "
import json, urllib.request, jsonschema
schema = json.loads(urllib.request.urlopen(
    'https://raw.githubusercontent.com/oasis-tcs/sarif-spec/master/Schemata/sarif-schema-2.1.0.json'
).read())
report = json.load(open('/tmp/report.sarif'))
jsonschema.validate(report, schema)
print('SARIF schema: OK')
"
```

## Report findings as
- Schema violations: exact path + expected vs actual.
- Severity mapping gaps: which `Severity` member has no `level` mapping.
- Cross-repo drift: which field the VS Code extension reads that this report omits/renames.

Do not modify `reporting/sarif.py` as part of this skill — report findings, let the
user or a follow-up task fix the generator.
