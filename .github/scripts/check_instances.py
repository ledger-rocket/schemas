#!/usr/bin/env python3
"""Validate fixture instances against the working-tree schemas.

For each schema in SUITES, every ``tests/<name>/valid/*.json`` is a full
instance that must pass, and every ``tests/<name>/invalid/*.json`` names a
``base`` file in ``valid/``, a ``set`` of top-level keys to merge over that
base, and the one error the merge must cause: its JSON Schema ``keyword`` and
its error ``path`` (``json_path``). The base passes as a valid fixture, so the
error comes from the merged defect.

Schemas resolve offline through the registry that check_refs.py builds: frozen
copies register first, and no retriever fetches a published schema.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from jsonschema import Draft202012Validator
from referencing import Registry, Resource
from referencing.jsonschema import DRAFT202012

from check_refs import discover, is_frozen_copy

# Each schema with its fixture directory. The access-grant schemas describe
# write-once objects kept for at least 400 days, so their frozen copies are
# checked too: an edit there ships as a new version, never in place.
SUITES = (
    ("domain/template.schema.json", Path("tests/template")),
    ("domain/access-grant-log-row.schema.json", Path("tests/access-grant-log-row")),
    ("domain/v1.0.0/access-grant-log-row.schema.json", Path("tests/access-grant-log-row")),
    ("domain/access-grant-alert.schema.json", Path("tests/access-grant-alert")),
    ("domain/v1.0.0/access-grant-alert.schema.json", Path("tests/access-grant-alert")),
)

# The version 2 approver subject must hold a character outside Python's
# str.isspace set, the test ledger-service's verifier applies through
# str.strip(). The schema writes that set as an explicit class, so every
# regex engine reads it alike; this keeps the class equal to str.isspace.
APPROVER_CLASS_SCHEMAS = (
    "domain/access-grant-log-row.schema.json",
    "domain/v1.0.0/access-grant-log-row.schema.json",
)


def approver_class_problems(path: str, doc) -> list[str]:
    pattern = doc["allOf"][0]["else"]["allOf"][0]["oneOf"][1]["properties"]["approver_subject"]["pattern"]
    if "\\" in pattern:
        # A backslash escape (\\S, \\s, \\uXXXX) is read differently by ECMAScript,
        # Python re, RE2 and PCRE2; the class must hold literal code points.
        return [f"{path}: the approver subject pattern holds a backslash escape"]
    rx = re.compile(pattern)
    wrong = [
        f"U+{code:04X}"
        for code in range(0x110000)
        if not 0xD800 <= code <= 0xDFFF and bool(rx.search(chr(code))) == chr(code).isspace()
    ]
    return [f"{path}: approver subject class disagrees with str.isspace at {wrong[:5]}"] if wrong else []


def load(path):
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def check(schema, root: Path, registry) -> tuple[int, int, list[str]]:
    validator = Draft202012Validator(schema, registry=registry)

    def errors(instance) -> list[list[str]]:
        return sorted([e.validator, e.json_path] for e in validator.iter_errors(instance))

    valid_dir, invalid_dir = root / "valid", root / "invalid"
    valid = sorted(valid_dir.glob("*.json"))
    invalid = sorted(invalid_dir.glob("*.json"))
    if not valid or not invalid:
        return 0, 0, [f"{valid_dir} and {invalid_dir} must each hold a fixture"]

    failures = []
    for path in valid:
        if found := errors(load(path)):
            failures.append(f"{path}: expected no error, got {found}")
    for path in invalid:
        case = load(path)
        want = [[case["keyword"], case["path"]]]
        if (found := errors({**load(valid_dir / case["base"]), **case["set"]})) != want:
            failures.append(f"{path}: expected {want}, got {found}")
    return len(valid), len(invalid), failures


def main() -> int:
    docs = {path: load(path) for path in discover()}
    registry = Registry()
    for path in sorted(docs, key=lambda p: (0 if is_frozen_copy(p) else 1, p)):
        registry = registry.with_resource(
            uri=docs[path]["$id"],
            resource=Resource.from_contents(docs[path], default_specification=DRAFT202012),
        )

    failures = []
    for schema_path, root in SUITES:
        valid, invalid, found = check(docs[schema_path], root, registry)
        failures.extend(f"{schema_path}: {line}" for line in found)
        if not found:
            print(f"ok -- {schema_path}: {valid} valid and {invalid} invalid fixture(s) behave")

    for path in APPROVER_CLASS_SCHEMAS:
        found = approver_class_problems(path, docs[path])
        failures.extend(found)
        if not found:
            print(f"ok -- {path}: the approver subject class is the complement of str.isspace")

    for line in failures:
        print(f"error: {line}", file=sys.stderr)
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
