"""Contract tests for the domain event schemas (PRO-16768).

Run from the repository root with the validators that CI pins:
    python -m unittest discover -s tests
Every schema is loaded from the working tree under its published URL, so a
cross-file $ref resolves to the copy under review, as check_refs.py does.
"""

import json
import pathlib
import unittest

from jsonschema import Draft202012Validator
from referencing import Registry, Resource

ROOT = pathlib.Path(__file__).resolve().parent.parent
BASE = "https://ledger-rocket.github.io/schemas/"


def _registry():
    registry = Registry()
    for path in ROOT.rglob("*.schema.json"):
        rel_path = path.relative_to(ROOT)
        if rel_path.parts[0] in (".tmp", ".git"):
            continue
        rel = rel_path.as_posix()
        registry = registry.with_resource(BASE + rel, Resource.from_contents(json.loads(path.read_text())))
    return registry


REGISTRY = _registry()


def errors(rel, document):
    schema = json.loads((ROOT / rel).read_text())
    return [e.message for e in Draft202012Validator(schema, registry=REGISTRY).iter_errors(document)]


REQUEST = {
    "$schema": BASE + "domain/v2.0.0/event.schema.json",
    "event_id": "0192b4f0-7abc-7def-8000-000000000001",
    "event_source": "contract-test",
    "occur_time": "2026-11-10T17:00:00.000Z",
    "amount_minor": "1500",
    "template_ids": ["532"],
    "reversal": False,
}
STORED = dict(REQUEST, site_id="1")
V1_EVENT = {
    "$schema": BASE + "domain/v1.0.0/event.schema.json",
    "event_id": "0192b4f0-7abc-7def-8000-000000000001",
    "event_source": "contract-test",
    "occurred_at": 1700000000000,
    "amount": 1500,
    "site_id": 1,
    "template_ids": [532],
}
REQUEST_SCHEMAS = ("domain/event.schema.json", "domain/v2.0.0/event.schema.json")
STORED_SCHEMAS = ("domain/stored-event.schema.json", "domain/v2.0.0/stored-event.schema.json")


class EventRequestSchema(unittest.TestCase):
    def test_accepts_an_aep_request(self):
        for rel in REQUEST_SCHEMAS:
            with self.subTest(rel):
                self.assertEqual(errors(rel, REQUEST), [])

    def test_refuses_site_id_in_the_request_body(self):
        for rel in REQUEST_SCHEMAS:
            with self.subTest(rel):
                self.assertIn("Additional properties are not allowed ('site_id' was unexpected)", errors(rel, STORED))

    def test_refuses_a_numeric_amount_minor(self):
        for rel in REQUEST_SCHEMAS:
            with self.subTest(rel):
                self.assertIn("1500 is not of type 'string'", errors(rel, dict(REQUEST, amount_minor=1500)))

    def test_refuses_a_v1_body(self):
        self.assertNotEqual(errors("domain/event.schema.json", V1_EVENT), [])


class StoredEventSchema(unittest.TestCase):
    def test_accepts_a_request_with_its_site_id(self):
        for rel in STORED_SCHEMAS:
            with self.subTest(rel):
                self.assertEqual(errors(rel, STORED), [])

    def test_requires_site_id(self):
        for rel in STORED_SCHEMAS:
            with self.subTest(rel):
                self.assertIn("'site_id' is a required property", errors(rel, REQUEST))


class FrozenV1Schema(unittest.TestCase):
    def test_v1_still_accepts_a_v1_body(self):
        self.assertEqual(errors("domain/v1.0.0/event.schema.json", V1_EVENT), [])


if __name__ == "__main__":
    unittest.main()
