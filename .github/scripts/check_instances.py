#!/usr/bin/env python3
"""Validate template instances against the working-tree template schema.

Each ``tests/template/valid/*.json`` is a full template that must pass.
Each ``tests/template/invalid/*.json`` names a ``base`` file in ``valid/``, a
``set`` of top-level keys to merge over that base, and the one error the merge
must cause: its JSON Schema ``keyword`` and its error ``path`` (``json_path``).
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

SCHEMA = "domain/template.schema.json"
VALID = Path("tests/template/valid")
INVALID = Path("tests/template/invalid")


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
    validator = Draft202012Validator(docs[SCHEMA], registry=registry)

    def errors(instance) -> list[list[str]]:
        return sorted([e.validator, e.json_path] for e in validator.iter_errors(instance))

    valid = sorted(VALID.glob("*.json"))
    invalid = sorted(INVALID.glob("*.json"))
    if not valid or not invalid:
        print(f"error: {VALID} and {INVALID} must each hold a fixture", file=sys.stderr)
        return 1

    failures = []
    for path in valid:
        if found := errors(load(path)):
            failures.append(f"{path}: expected no error, got {found}")
    for path in invalid:
        case = load(path)
        want = [[case["keyword"], case["path"]]]
        if (found := errors({**load(VALID / case["base"]), **case["set"]})) != want:
            failures.append(f"{path}: expected {want}, got {found}")

    for line in failures:
        print(f"error: {line}", file=sys.stderr)
    if failures:
        return 1
    print(f"ok -- {len(valid)} valid and {len(invalid)} invalid template fixture(s) behave")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
