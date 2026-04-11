# LedgerRocket JSON Schemas

Hosted JSON Schemas describing LedgerRocket financial events, ledger templates, and supporting types. All schemas live at **https://ledger-rocket.github.io/schemas/** and are designed for direct consumption by editors, CI pipelines, and validation libraries.

## Latest Schemas

| Path | Description | URL |
| --- | --- | --- |
| `domain/event.schema.json` | Financial event requests submitted to the Event Service | https://ledger-rocket.github.io/schemas/domain/event.schema.json |
| `domain/template.schema.json` | Ledger templates that transform events into transfers | https://ledger-rocket.github.io/schemas/domain/template.schema.json |
| `domain/workflow.schema.json` | Workflow definitions that coordinate template execution | https://ledger-rocket.github.io/schemas/domain/workflow.schema.json |
| `domain/audit-slug.schema.json` | Maker-checker audit lifecycle records for ARE-managed models | https://ledger-rocket.github.io/schemas/domain/audit-slug.schema.json |
| `domain/expected-transfer.schema.json` | Expected transfer output for template validation/testing | https://ledger-rocket.github.io/schemas/domain/expected-transfer.schema.json |
| `common/defs.schema.json` | Shared `$defs` referenced by the domain schemas | https://ledger-rocket.github.io/schemas/common/defs.schema.json |

## Schema Ownership

The Accounting Rule Engine is the source of truth for template, workflow, audit-slug, and common definition schemas. Those files are copied here by the ARE release pipeline after a release is published. Make changes to those schemas in `ledger-rocket/accounting-rule-engine`.

Event and expected-transfer schemas are owned by the Event Service and are still maintained in this repository.

Recent change: template scopes now accept any lower snake case identifier defined by the template (beyond the legacy `primary` / `secondary` values), and the shared treatment-type enum documents the full adapter-supported set. These tighten validation but remain compatible with existing schema consumers, so the published version stays at **v1.0.0**.

Each schema exposes a top-level `"version"` field. When a breaking change is released, the major version increments and a frozen copy is published under `vX.Y.Z/`. The current release is **v1.0.0**:

```
common/v1.0.0/defs.schema.json
domain/v1.0.0/event.schema.json
domain/v1.0.0/template.schema.json
domain/v1.0.0/workflow.schema.json
domain/v1.0.0/expected-transfer.schema.json
```

## Editor Integration

Add a `$schema` declaration that points at the hosted URL—relative paths are intentionally unsupported:

```json
{
  "$schema": "https://ledger-rocket.github.io/schemas/domain/v1.0.0/template.schema.json",
  "template_id": 125,
  "site_id": 1,
  "name": "Universal Peer-to-Peer Transfer with Fee"
  /* … */
}
```

## Programmatic Validation Examples

### Python (`jsonschema` ≥ 4.18)

```python
import json
from urllib.request import urlopen
from jsonschema import Draft202012Validator, RefResolver

BASE = "https://ledger-rocket.github.io/schemas/domain/"
SCHEMAS = {
    "template": json.load(urlopen(f"{BASE}v1.0.0/template.schema.json")),
    "event": json.load(urlopen(f"{BASE}v1.0.0/event.schema.json")),
    "expected": json.load(urlopen(f"{BASE}v1.0.0/expected-transfer.schema.json")),
}
refs = {SCHEMAS[name]["$id"]: doc for name, doc in SCHEMAS.items()}
refs["https://ledger-rocket.github.io/schemas/common/defs.schema.json"] = json.load(
    urlopen("https://ledger-rocket.github.io/schemas/common/v1.0.0/defs.schema.json")
)
resolver = RefResolver.from_schema(SCHEMAS["template"], store=refs)

candidate = {
    "template_id": 125,
    "site_id": 1,
    "name": "Demo Template",
    "description": "Example template",
    "trigger": "demo_event",
    "accounting_treatments": [
        {
            "type": "cash_movement",
            "policy_refs": [{"id": "IFRS9.CASH"}],
            "description": "Cash movement"
        }
    ],
    "account_code_validations": [
        {"purpose": "from", "mask": "21010", "description": "Customer account"},
        {"purpose": "to", "mask": "21010", "description": "Counterparty account"}
    ],
    "product": "PAYMENTS",
    "event_type": "TRANSFER",
    "category": "TRANSFER",
    "variables": [
        {"name": "from_account", "description": "Debit account", "value": "accounts.from.account_id"},
        {"name": "to_account", "description": "Credit account", "value": "accounts.to.account_id"},
        {"name": "transfer_amount", "description": "Amount", "value": "event.amount"}
    ],
    "validations": [
        {"name": "amount_positive", "expression": "event.amount > 0", "description": "Amount must be positive"}
    ],
    "legs": [
        {
            "leg_number": 1,
            "debit_account": "from_account",
            "debit_account_type": "LIABILITY",
            "credit_account": "to_account",
            "credit_account_type": "LIABILITY",
            "amount": "transfer_amount",
            "description": "Move funds",
            "ledger_scope": "primary",
            "treatment_type": "cash_movement"
        }
    ],
    "metadata_schema": {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "properties": {
            "reference": {"type": "string"}
        },
        "additionalProperties": False
    },
    "examples": []
}

Draft202012Validator(SCHEMAS["template"], resolver=resolver).validate(candidate)
print("template is valid")
```

### Node.js (`ajv` ≥ 8)

```bash
npm install ajv@^8 ajv-formats node-fetch
```

```javascript
import fetch from "node-fetch"; // Node 18+ can use global fetch
import Ajv2020 from "ajv/dist/2020.js";
import addFormats from "ajv-formats";

const BASE = "https://ledger-rocket.github.io/schemas/";
const [defs, eventSchema, expectedSchema, templateSchema] = await Promise.all([
  fetch(`${BASE}common/v1.0.0/defs.schema.json`).then((res) => res.json()),
  fetch(`${BASE}domain/v1.0.0/event.schema.json`).then((res) => res.json()),
  fetch(`${BASE}domain/v1.0.0/expected-transfer.schema.json`).then((res) => res.json()),
  fetch(`${BASE}domain/v1.0.0/template.schema.json`).then((res) => res.json()),
]);

const ajv = new Ajv2020({ strict: false });
addFormats(ajv);
ajv.addSchema(defs);
ajv.addSchema(eventSchema);
ajv.addSchema(expectedSchema);
const validate = ajv.compile(templateSchema);

const candidate = { /* same structure as the Python example */ };

if (!validate(candidate)) {
  console.error(validate.errors);
  process.exit(1);
}

console.log("template is valid");
```

## Contributing

1. Update ARE-owned schemas in `ledger-rocket/accounting-rule-engine`.
2. Update Event Service-owned schemas in this repository.
3. Bump the relevant `"version"` field when the contract changes.
4. Commit to `main`; GitHub Pages republishes within ~60 seconds.
5. Copy manually managed schemas into the `vX.Y.Z/` directory when cutting a release tag.
