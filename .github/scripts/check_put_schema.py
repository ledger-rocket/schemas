#!/usr/bin/env python3
"""Offline check that each template PUT request schema stays the domain
template schema minus the identity the request path names.

``template.put.schema.json`` describes the body of
``PUT /api/v1/sites/{site_id}/templates/{template_id}``: every property of the
``template.schema.json`` beside it except ``site_id`` and ``template_id``, each
one a bare ``$ref`` to that property (``$schema`` excepted: it names the PUT
schema itself), the same ``required`` set without the two ids, and
``additionalProperties: false``. Each PUT file is compared with the template in
its own directory. Its published ``$ref``s resolve by ``$id``, which a latest
template shares with its frozen copy, so the template files that share an
``$id`` must be identical. A template keyword outside the ones a PUT mirrors
(``allOf``, ``if``, ``dependentRequired`` ...) fails the check, because the PUT
would not carry it.

Every PUT file then validates the domain schema's own examples: an example
with its ``$schema`` set to a PUT URL and without the ids passes, and the same
body with either id is refused. A self-test first proves that each shape
check refuses a mutated copy, so a check that can never fail fails here.
"""

from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

from jsonschema import Draft202012Validator
from referencing import Registry, Resource
from referencing.jsonschema import DRAFT202012

sys.dont_write_bytecode = True  # no __pycache__ beside the scripts
sys.path.insert(0, str(Path(__file__).resolve().parent))
from check_refs import discover, is_frozen_copy  # noqa: E402  (shared discovery and $id precedence)

PATH_IDS = ("site_id", "template_id")
PUT_URLS = [
    "https://ledger-rocket.github.io/schemas/domain/template.put.schema.json",
    "https://ledger-rocket.github.io/schemas/domain/v1.0.0/template.put.schema.json",
]
TOP_LEVEL = {"$schema", "$id", "title", "description", "type", "version", "required", "properties", "additionalProperties"}
ANNOTATIONS = {"description", "examples", "$comment", "title"}
# Top-level keywords of the domain template that the PUT schema mirrors or that only annotate.
DOMAIN_TOP_LEVEL = TOP_LEVEL | {"examples"}


def load(path: Path) -> dict:
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def registry() -> Registry:
    """Every schema by $id, frozen copies first so a latest file wins, as in check_refs."""
    reg = Registry()
    for path in sorted(discover(), key=lambda p: (0 if is_frozen_copy(p) else 1, p)):
        doc = load(Path(path))
        reg = reg.with_resource(doc["$id"], Resource.from_contents(doc, default_specification=DRAFT202012))
    return reg


def shape_errors(path: Path, put: dict, domain: dict) -> list[str]:
    errors = []
    if set(domain) - DOMAIN_TOP_LEVEL:
        errors.append(f"{path}: the domain template has keywords {sorted(set(domain) - DOMAIN_TOP_LEVEL)} that a PUT schema does not mirror")
    if domain.get("type") != "object" or domain.get("additionalProperties") is not False:
        errors.append(f"{path}: the domain template is no longer a closed object")
    if set(put) - TOP_LEVEL:
        errors.append(f"{path}: unexpected top-level keywords {sorted(set(put) - TOP_LEVEL)}")
    if put.get("type") != "object":
        errors.append(f"{path}: type must be object")
    if put.get("additionalProperties") is not False:
        errors.append(f"{path}: additionalProperties must be false")
    if put.get("version") != domain.get("version"):
        errors.append(f"{path}: version {put.get('version')} != domain {domain.get('version')}")
    want_props = set(domain["properties"]) - set(PATH_IDS)
    have_props = set(put.get("properties", {}))
    if have_props != want_props:
        errors.append(f"{path}: properties differ from the domain minus ids: extra {sorted(have_props - want_props)}, missing {sorted(want_props - have_props)}")
    want_required = set(domain["required"]) - set(PATH_IDS)
    have_required = set(put.get("required", []))
    if have_required != want_required or len(put.get("required", [])) != len(have_required):
        errors.append(f"{path}: required differs from the domain minus ids: extra {sorted(have_required - want_required)}, missing {sorted(want_required - have_required)}")
    for name, sub in put.get("properties", {}).items():
        if not isinstance(sub, dict):
            errors.append(f"{path}: properties.{name} must be an object, not {sub!r}")
            continue
        if name == "$schema":
            if sub.get("type") != "string" or sub.get("enum") != PUT_URLS or set(sub) - ANNOTATIONS - {"type", "enum"}:
                errors.append(f"{path}: properties.$schema must be a string enum of exactly {PUT_URLS}")
            continue
        if sub.get("$ref") != f"template.schema.json#/properties/{name}":
            errors.append(f"{path}: properties.{name} must be a $ref to the domain property")
        if set(sub) - ANNOTATIONS - {"$ref"}:
            errors.append(f"{path}: properties.{name} adds {sorted(set(sub) - ANNOTATIONS - {'$ref'})} beyond the $ref")
    return errors


def self_test(put: dict, domain: dict) -> list[str]:
    """Each mutation must be refused by shape_errors."""
    mutations = {
        "an id published": lambda s: s["properties"].update(site_id={"$ref": "template.schema.json#/properties/site_id"}),
        "a property dropped": lambda s: s["properties"].pop("legs"),
        "a required field dropped": lambda s: s["required"].remove("legs"),
        "a sibling constraint": lambda s: s["properties"]["name"].update(maxLength=3),
        "a wrong $ref": lambda s: s["properties"].update(name={"$ref": "template.schema.json#/properties/product"}),
        "a top-level keyword": lambda s: s.update(minProperties=1),
        "additionalProperties open": lambda s: s.update(additionalProperties=True),
        "a version drift": lambda s: s.update(version="9.9.9"),
        "a looser $schema": lambda s: s["properties"].update({"$schema": {"$ref": "template.schema.json#/properties/$schema"}}),
        "an extra $schema URL": lambda s: s["properties"]["$schema"]["enum"].append("https://ledger-rocket.github.io/schemas/domain/template.schema.json"),
        "a constraint beside the $schema enum": lambda s: s["properties"]["$schema"].update(maxLength=10),
        "a type other than object": lambda s: s.update(type="array"),
        "a boolean property": lambda s: s["properties"].update(name=True),
    }
    domain_mutations = {
        "a domain allOf": lambda d: d.update(allOf=[{"required": ["name"]}]),
        "a domain dependentRequired": lambda d: d.update(dependentRequired={"name": ["product"]}),
    }
    errors = []
    for label, mutate in mutations.items():
        mutated = copy.deepcopy(put)
        mutate(mutated)
        if not shape_errors(Path("<self-test>"), mutated, domain):
            errors.append(f"self-test: the shape check accepts {label}")
    for label, mutate in domain_mutations.items():
        mutated = copy.deepcopy(domain)
        mutate(mutated)
        if not shape_errors(Path("<self-test>"), put, mutated):
            errors.append(f"self-test: the shape check accepts {label}")
    return errors


def main() -> int:
    put_files = sorted(Path(p) for p in discover() if p.endswith("/template.put.schema.json"))
    if not put_files:
        print("error: no template.put.schema.json found", file=sys.stderr)
        return 1

    errors: list[str] = []
    # A published PUT schema's $refs resolve by $id, which a latest template and
    # its frozen copy share, so those copies must be identical.
    by_id: dict[str, list[Path]] = {}
    for path in put_files:
        domain_path = path.with_name("template.schema.json")
        by_id.setdefault(load(domain_path)["$id"], []).append(domain_path)
    for uri, group in by_id.items():
        if len({json.dumps(load(p), sort_keys=True) for p in group}) > 1:
            errors.append(f"{[p.as_posix() for p in group]} share $id {uri} but are not identical")

    reg = registry()
    checked = 0
    for path in put_files:
        domain_path = path.with_name("template.schema.json")
        domain, put = load(domain_path), load(path)
        shape = shape_errors(path, put, domain)
        errors.extend(shape)
        if not shape:  # the self-test mutates a well-formed PUT schema
            errors.extend(self_test(put, domain))

        domain_validator = Draft202012Validator(domain, registry=reg)
        put_validator = Draft202012Validator(put, registry=reg)
        examples = domain.get("examples", [])
        if not examples:
            errors.append(f"{domain_path}: no examples to validate against")
        for i, example in enumerate(examples):
            for err in domain_validator.iter_errors(example):
                errors.append(f"{domain_path} examples[{i}]: refused by the domain schema: {err.message}")
            for url in PUT_URLS:
                body = {k: v for k, v in example.items() if k not in PATH_IDS} | {"$schema": url}
                for err in put_validator.iter_errors(body):
                    errors.append(f"{path} examples[{i}] as a PUT body: refused: {err.message}")
                for name in PATH_IDS:
                    if put_validator.is_valid(body | {name: example.get(name, 1)}):
                        errors.append(f"{path} examples[{i}] with {name}: accepted")
            checked += 1

    if errors:
        for line in errors:
            print(f"error: {line}", file=sys.stderr)
        return 1
    print(f"ok -- {len(put_files)} PUT schema(s) match their domain template minus {', '.join(PATH_IDS)}; {checked} example(s) checked")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
