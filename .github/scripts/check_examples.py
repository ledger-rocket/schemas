#!/usr/bin/env python3
"""Offline check of every embedded example and of the event workflow rule.

1. Every ``examples`` value on a schema node validates against that node.
   Each file is checked in a registry where it holds its own ``$id``, so a
   frozen copy is checked as itself and not as its latest sibling.
2. Each event root example fails with exactly one ``required`` error when
   ``workflow_id`` or ``step_code`` is removed (event schema 2.0.0).
3. Each template example still validates when both fields are removed from
   every ``event_request``: stored templates keep both fields optional.

Frozen copies that predate this check and stay unchanged are exempt by name.
"""

from __future__ import annotations

import copy
import sys

sys.dont_write_bytecode = True  # the import below must not write __pycache__ into the repo

import check_refs  # noqa: E402
from jsonschema import Draft202012Validator  # noqa: E402
from referencing import Registry, Resource  # noqa: E402
from referencing.jsonschema import DRAFT202012  # noqa: E402

EXEMPT = {
    "common/v1.0.0/defs.schema.json": "frozen v1.0.0 copy, unchanged; its uuidV7 example is a v4 id",
    "domain/v1.0.0/event.schema.json": "frozen v1.0.0 copy, unchanged by the 2.0.0 release",
}
WORKFLOW_FIELDS = ("workflow_id", "step_code")
OPTIONAL_DEF = "eventWithOptionalWorkflow"
EVENT = ("domain", "event.schema.json")
TEMPLATE = ("domain", "template.schema.json")
DATA_KEYWORDS = {"examples", "enum", "const", "default"}  # instance data, never a subschema
NAME_MAPS = {"properties", "$defs", "patternProperties", "dependentSchemas"}  # keys are names


def escape(token: str) -> str:
    return token.replace("~", "~0").replace("/", "~1")


def example_nodes(node: dict, ptr: str = ""):
    """Yield ``(pointer, examples)`` for every schema node that carries examples."""
    for key, value in node.items():
        here = f"{ptr}/{escape(key)}"
        if key == "examples":
            if not isinstance(value, list):
                raise ValueError(f"{here}: examples must be a list, got {type(value).__name__}")
            yield ptr, value
        elif key in DATA_KEYWORDS:
            continue
        elif key in NAME_MAPS and isinstance(value, dict):
            for name, sub in value.items():
                if isinstance(sub, dict):
                    yield from example_nodes(sub, f"{here}/{escape(name)}")
        elif isinstance(value, dict):
            yield from example_nodes(value, here)
        elif isinstance(value, list):
            for index, item in enumerate(value):
                if isinstance(item, dict):
                    yield from example_nodes(item, f"{here}/{index}")


def validator(doc: dict, base: Registry, ptr: str = "") -> Draft202012Validator:
    registry = base.with_resource(
        uri=doc["$id"], resource=Resource.from_contents(doc, default_specification=DRAFT202012)
    )
    return Draft202012Validator(
        {"$ref": f"{doc['$id']}#{ptr}"},
        registry=registry,
        format_checker=Draft202012Validator.FORMAT_CHECKER,
    )


def check_event(path: str, doc: dict, base: Registry) -> list[str]:
    errors = []
    optional = doc.get("$defs", {}).get(OPTIONAL_DEF)
    # The def must be the root with only the two workflow fields optional.
    mirror = {
        "type": doc.get("type"),
        "required": [name for name in doc.get("required", []) if name not in WORKFLOW_FIELDS],
        "properties": {name: {"$ref": f"#/properties/{name}"} for name in doc.get("properties", {})},
        "additionalProperties": doc.get("additionalProperties"),
        "allOf": [{"$ref": f"#/allOf/{index}"} for index in range(len(doc.get("allOf", [])))],
    }
    if not set(WORKFLOW_FIELDS) <= set(doc.get("required", [])):
        errors.append(f"{path}: root required must hold {list(WORKFLOW_FIELDS)}")
    if optional is None:
        errors.append(f"{path}: has no $defs/{OPTIONAL_DEF} for template examples")
    elif {key: value for key, value in optional.items() if key != "$comment"} != mirror:
        errors.append(f"{path}: $defs/{OPTIONAL_DEF} must be {mirror}")
    examples = doc.get("examples", [])
    if not examples:
        errors.append(f"{path}: no root example to test the workflow rule with")
    root = validator(doc, base)
    for index, example in enumerate(examples):
        for field in WORKFLOW_FIELDS:
            instance = {key: value for key, value in example.items() if key != field}
            got = [(e.validator, list(e.path), e.message) for e in root.iter_errors(instance)]
            want = [("required", [], f"{field!r} is a required property")]
            if got != want:
                errors.append(f"{path}#/examples/{index} without {field}: want {want}, got {got}")
    print(f"{path}: {len(examples)} root example(s) tested without each workflow field")
    return errors


def check_template(path: str, doc: dict, base: Registry) -> list[str]:
    stripped = copy.deepcopy(doc["examples"])
    tested = 0
    errors = []
    for index, template in enumerate(stripped):
        for number, example in enumerate(template["examples"]):
            request = example["event_request"]
            tested += 1
            if not all(field in request for field in WORKFLOW_FIELDS):
                errors.append(
                    f"{path}#/examples/{index}/examples/{number}/event_request: "
                    f"an authored example carries {list(WORKFLOW_FIELDS)}"
                )
            for field in WORKFLOW_FIELDS:
                request.pop(field, None)
    if not tested:
        errors.append(f"{path}: no event_request example to test the stored-template rule with")
    root = validator(doc, base)
    for index, template in enumerate(stripped):
        for e in root.iter_errors(template):
            errors.append(
                f"{path}#/examples/{index} without the workflow fields: {e.message} at {e.json_path}"
            )
    print(f"{path}: {tested} event_request example(s) tested without the workflow fields")
    return errors


def main() -> int:
    docs = check_refs.load_docs()
    if not docs:
        print("error: no *.schema.json files found", file=sys.stderr)
        return 1
    base = check_refs.build_registry(docs)
    errors: list[str] = []
    for path, doc in docs.items():
        if path in EXEMPT:
            print(f"{path}: skipped, {EXEMPT[path]}")
            continue
        count = 0
        for ptr, examples in example_nodes(doc):
            node = validator(doc, base, ptr)
            for index, example in enumerate(examples):
                count += 1
                for e in node.iter_errors(example):
                    errors.append(f"{path}#{ptr}/examples/{index}: {e.message} at {e.json_path}")
        print(f"{path}: {count} example(s) validated")
        logical = check_refs.logical_path(path)
        if logical == EVENT:
            errors += check_event(path, doc, base)
        elif logical == TEMPLATE:
            errors += check_template(path, doc, base)

    for line in errors:
        print(f"error: {line}", file=sys.stderr)
    if errors:
        print(f"\n{len(errors)} example check(s) failed", file=sys.stderr)
        return 1
    print("ok -- every embedded example validates and the event workflow rule holds")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
