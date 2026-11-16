#!/usr/bin/env python3
"""Validate instances against the working-tree schemas.

Each suite pairs a schema with a fixture folder. Each ``<folder>/valid/*.json``
is a full instance that must pass.
Each ``<folder>/invalid/*.json`` names a ``base`` file in ``valid/``, a
``set`` of top-level keys to merge over that base, and the one error the merge
must cause: its JSON Schema ``keyword`` and its error ``path`` (``json_path``),
reported ``count`` times (default 1) where two subschemas refuse the same value.
The base passes as a valid fixture, so the error comes from the merged defect.

Schemas resolve offline through the registry that check_refs.py builds: frozen
copies register first, and no retriever fetches a published schema.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from jsonschema import Draft202012Validator
from referencing import Registry, Resource
from referencing.jsonschema import DRAFT202012

from check_refs import discover, is_frozen_copy

# (schema, fixture folder): every suite must hold a valid and an invalid fixture.
SUITES = [
    ("domain/template.schema.json", Path("tests/template")),
    ("domain/v2.0.0/template.schema.json", Path("tests/v2.0.0/template")),
    ("domain/v2.0.0/event.schema.json", Path("tests/v2.0.0/event")),
]
# Root ``examples`` of these schemas must validate against the schema that holds them.
EXAMPLE_SCHEMAS = [
    "domain/v2.0.0/event.schema.json",
    "domain/v2.0.0/template.schema.json",
    "domain/v2.0.0/expected-transfer.schema.json",
]


def load(path):
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def main() -> int:
    docs = {path: load(path) for path in discover()}
    registry = Registry()
    for path in sorted(docs, key=lambda p: (0 if is_frozen_copy(p) else 1, p)):
        registry = registry.with_resource(
            uri=docs[path]["$id"],
            resource=Resource.from_contents(docs[path], default_specification=DRAFT202012),
        )
    failures = []
    counts = []
    for schema, folder in SUITES:
        validator = Draft202012Validator(docs[schema], registry=registry)
        valid = sorted((folder / "valid").glob("*.json"))
        invalid = sorted((folder / "invalid").glob("*.json"))
        if not valid or not invalid:
            print(f"error: {folder}/valid and {folder}/invalid must each hold a fixture", file=sys.stderr)
            return 1
        failures += check_suite(validator, folder, valid, invalid)
        counts.append(f"{schema}: {len(valid)} valid and {len(invalid)} invalid")
    for schema in EXAMPLE_SCHEMAS:
        validator = Draft202012Validator(docs[schema], registry=registry)
        examples = docs[schema].get("examples", [])
        if not examples:
            failures.append(f"{schema}: holds no root examples")
        for index, example in enumerate(examples):
            for error in validator.iter_errors(example):
                failures.append(f"{schema} examples[{index}]: {error.validator} at {error.json_path}")
        counts.append(f"{schema}: {len(examples)} root example(s)")

    for line in failures:
        print(f"error: {line}", file=sys.stderr)
    if failures:
        return 1
    print("ok -- fixture(s) behave: " + "; ".join(counts))
    return 0


def check_suite(validator, folder, valid, invalid) -> list[str]:
    def errors(instance) -> list[list[str]]:
        return sorted([e.validator, e.json_path] for e in validator.iter_errors(instance))

    failures = []
    for path in valid:
        if found := errors(load(path)):
            failures.append(f"{path}: expected no error, got {found}")
    for path in invalid:
        case = load(path)
        want = [[case["keyword"], case["path"]]] * case.get("count", 1)
        if (found := errors({**load(folder / "valid" / case["base"]), **case["set"]})) != want:
            failures.append(f"{path}: expected {want}, got {found}")
    return failures


if __name__ == "__main__":
    raise SystemExit(main())
