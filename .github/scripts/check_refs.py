#!/usr/bin/env python3
"""Offline integrity check for the published JSON schemas.

Every ``*.schema.json`` is loaded from the working tree and registered by its
``$id``, so ``$ref``s resolve against the PR's copies rather than the live
GitHub Pages site. The registry has no network retriever: any reference that
does not resolve to a local resource raises instead of silently fetching a
stale published schema.

The checker assumes the repo's schema shape — each file is a single flat
document (one root ``$id``, draft 2020-12, no nested ``$id`` rescoping refs).
Those assumptions are asserted up front, so a future schema that breaks them
fails loudly here rather than being resolved incorrectly.

Frozen ``vX.Y.Z/`` copies intentionally reuse the ``$id`` of their latest
sibling; that specific collision is allowed, any other ``$id`` reuse is not.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from referencing import Registry, Resource
from referencing.exceptions import Unresolvable
from referencing.jsonschema import DRAFT202012

META_2020_12 = "https://json-schema.org/draft/2020-12/schema"
FROZEN_SEGMENT = re.compile(r"^v\d+\.\d+\.\d+$")  # release-copy directory, e.g. v1.0.0
REF_KEYS = ("$ref", "$dynamicRef")


def is_frozen_copy(path: str) -> bool:
    return any(FROZEN_SEGMENT.fullmatch(part) for part in path.split("/"))


def logical_path(path: str) -> tuple[str, ...]:
    """Path with any frozen release segment stripped, so a latest schema and
    its ``vX.Y.Z`` copies collapse to the same identity."""
    return tuple(part for part in path.split("/") if not FROZEN_SEGMENT.fullmatch(part))


def iter_keyed(node, keys):
    """Yield every string value stored under one of ``keys`` anywhere in a document."""
    if isinstance(node, dict):
        for key, value in node.items():
            if key in keys and isinstance(value, str):
                yield value
            else:
                yield from iter_keyed(value, keys)
    elif isinstance(node, list):
        for item in node:
            yield from iter_keyed(item, keys)


def discover() -> list[str]:
    return sorted(
        p.as_posix() for p in Path(".").rglob("*.schema.json") if ".git" not in p.parts
    )


def main() -> int:
    docs: dict[str, dict] = {}
    for path in discover():
        with open(path, encoding="utf-8") as handle:
            docs[path] = json.load(handle)

    if not docs:
        print("error: no *.schema.json files found", file=sys.stderr)
        return 1

    errors: list[str] = []

    # Per-document invariants the flat resolver relies on.
    for path, doc in docs.items():
        if doc.get("$schema") != META_2020_12:
            errors.append(
                f"{path}: root $schema must be {META_2020_12!r}, got {doc.get('$schema')!r}"
            )
        root_id = doc.get("$id")
        if not root_id:
            errors.append(f"{path}: missing root $id")
        ids = list(iter_keyed(doc, ("$id",)))
        if len(ids) > 1 or (ids and ids[0] != root_id):
            errors.append(f"{path}: nested $id is not supported (found {ids})")

    # $id reuse is allowed only between a latest schema and its frozen copies.
    by_id: dict[str, list[str]] = {}
    for path, doc in docs.items():
        if doc.get("$id"):
            by_id.setdefault(doc["$id"], []).append(path)
    for uri, group in by_id.items():
        if len(group) == 1:
            continue
        latest = [p for p in group if not is_frozen_copy(p)]
        if len({logical_path(p) for p in group}) != 1 or len(latest) > 1:
            errors.append(f"$id {uri!r} reused by unrelated files: {sorted(group)}")

    if errors:
        for line in errors:
            print(f"error: {line}", file=sys.stderr)
        return 1

    # Frozen copies register first so the latest sibling wins each $id collision.
    registry = Registry()
    for path in sorted(docs, key=lambda p: (0 if is_frozen_copy(p) else 1, p)):
        doc = docs[path]
        registry = registry.with_resource(
            uri=doc["$id"],
            resource=Resource.from_contents(doc, default_specification=DRAFT202012),
        )

    for path, doc in docs.items():
        resolver = registry.resolver(base_uri=doc["$id"])
        for ref in iter_keyed(doc, REF_KEYS):
            try:
                resolver.lookup(ref)
            except Unresolvable:
                errors.append(f"{path}: unresolvable reference {ref!r}")

    if errors:
        for line in errors:
            print(f"error: {line}", file=sys.stderr)
        print(f"\n{len(errors)} unresolvable reference(s)", file=sys.stderr)
        return 1

    ref_count = sum(1 for doc in docs.values() for _ in iter_keyed(doc, REF_KEYS))
    print(f"ok -- {ref_count} reference(s) across {len(docs)} schema(s) resolve locally")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
