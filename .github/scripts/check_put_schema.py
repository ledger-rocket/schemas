#!/usr/bin/env python3
"""Offline check that the template PUT request schema stays the domain
template schema minus the identity the request path names.

``domain/template.put.schema.json`` describes the body of
``PUT /api/v1/sites/{site_id}/templates/{template_id}``: every property of
``domain/template.schema.json`` except ``site_id`` and ``template_id``, each
one a ``$ref`` to the domain property, and the same ``required`` list without
the two ids. The script asserts that shape for the latest file and its frozen
copies, then validates the domain schema's own examples against both schemas:
an example passes the domain schema, the same example without the ids passes
the PUT schema, and the example with either id is refused by it.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from jsonschema import Draft202012Validator
from referencing import Registry, Resource
from referencing.jsonschema import DRAFT202012

DOMAIN = Path("domain/template.schema.json")
PUT_FILES = sorted(Path(".").glob("domain/**/template.put.schema.json"))
PATH_IDS = ("site_id", "template_id")
FROZEN_SEGMENT = re.compile(r"^v\d+\.\d+\.\d+$")  # release-copy directory, e.g. v1.0.0


def load(path: Path) -> dict:
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def registry() -> Registry:
    """Every schema in the tree, by $id; a latest file wins over its frozen copy."""
    paths = sorted(
        (p for p in Path(".").rglob("*.schema.json") if ".git" not in p.parts),
        key=lambda p: (0 if any(FROZEN_SEGMENT.fullmatch(part) for part in p.parts) else 1, p.as_posix()),
    )
    reg = Registry()
    for path in paths:
        doc = load(path)
        reg = reg.with_resource(doc["$id"], Resource.from_contents(doc, default_specification=DRAFT202012))
    return reg


def shape_errors(path: Path, put: dict, domain: dict) -> list[str]:
    errors = []
    want_props = [k for k in domain["properties"] if k not in PATH_IDS]
    if list(put.get("properties", {})) != want_props:
        errors.append(f"{path}: properties {list(put.get('properties', {}))} != domain minus ids {want_props}")
    want_required = [k for k in domain["required"] if k not in PATH_IDS]
    if put.get("required") != want_required:
        errors.append(f"{path}: required {put.get('required')} != domain minus ids {want_required}")
    for name, sub in put.get("properties", {}).items():
        if sub.get("$ref") != f"template.schema.json#/properties/{name}":
            errors.append(f"{path}: properties.{name} must be a $ref to the domain property")
    if put.get("additionalProperties") is not False:
        errors.append(f"{path}: additionalProperties must be false")
    if put.get("version") != domain.get("version"):
        errors.append(f"{path}: version {put.get('version')} != domain {domain.get('version')}")
    return errors


def main() -> int:
    domain = load(DOMAIN)
    if not PUT_FILES:
        print("error: no domain/**/template.put.schema.json found", file=sys.stderr)
        return 1

    errors: list[str] = []
    for path in PUT_FILES:
        errors.extend(shape_errors(path, load(path), domain))

    reg = registry()
    domain_validator = Draft202012Validator(domain, registry=reg)
    put_validator = Draft202012Validator(load(PUT_FILES[0]), registry=reg)
    examples = domain.get("examples", [])
    if not examples:
        errors.append(f"{DOMAIN}: no examples to validate against")
    for i, example in enumerate(examples):
        for err in domain_validator.iter_errors(example):
            errors.append(f"{DOMAIN} examples[{i}]: refused by the domain schema: {err.message}")
        body = {k: v for k, v in example.items() if k not in PATH_IDS}
        for err in put_validator.iter_errors(body):
            errors.append(f"examples[{i}] without ids: refused by the PUT schema: {err.message}")
        for name in PATH_IDS:
            if put_validator.is_valid({**body, name: example[name]}):
                errors.append(f"examples[{i}] with {name}: accepted by the PUT schema")

    if errors:
        for line in errors:
            print(f"error: {line}", file=sys.stderr)
        return 1
    print(f"ok -- {len(PUT_FILES)} PUT schema(s) match the domain template minus {', '.join(PATH_IDS)}; {len(examples)} example(s) checked")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
