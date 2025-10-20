# LedgerRocket JSON Schemas

Public JSON Schemas describing LedgerRocket event ingestion, ledger templates, and related transfer outputs. All schemas are hosted at **https://ledger-rocket.github.io/schemas/** and can be consumed directly by editors, build tooling, or validation libraries.

## Latest Schemas

| Path | Description | URL |
| --- | --- | --- |
| `domain/event.schema.json` | Financial event requests submitted to the LedgerRocket event service | https://ledger-rocket.github.io/schemas/domain/event.schema.json |
| `domain/template.schema.json` | Ledger templates that transform events into ledger transfers | https://ledger-rocket.github.io/schemas/domain/template.schema.json |
| `domain/expected-transfer.schema.json` | Expected transfer output used by template validation | https://ledger-rocket.github.io/schemas/domain/expected-transfer.schema.json |
| `common/defs.schema.json` | Shared `$defs` referenced by the other schemas | https://ledger-rocket.github.io/schemas/common/defs.schema.json |

Each schema advertises its semantic version via the top-level `"version"` field. Breaking changes bump the major version, with historical copies published under `vX.Y.Z/` directories when necessary.

## Editor Integration

Add a `$schema` declaration to your JSON file so editors (VS Code, JetBrains, etc.) can fetch the hosted contract:

```json
{
  "$schema": "https://ledger-rocket.github.io/schemas/domain/template.schema.json",
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

BASE = "https://ledger-rocket.github.io/schemas/"
schema = json.load(urlopen(f"{BASE}domain/template.schema.json"))
refs = {}
for path in [
    "common/defs.schema.json",
    "domain/event.schema.json",
    "domain/expected-transfer.schema.json",
]:
    doc = json.load(urlopen(f"{BASE}{path}"))
    refs[doc["$id"]] = doc

resolver = RefResolver.from_schema(schema, store=refs)

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

Draft202012Validator(schema, resolver=resolver).validate(candidate)
print("template is valid")
```

> Install requirements with `pip install jsonschema>=4.18`.

### Node.js (`ajv` ≥ 8)

```bash
npm install ajv@^8 ajv-formats
```

```javascript
import fetch from "node-fetch"; // Node 18+ can use the built-in global fetch
import Ajv2020 from "ajv/dist/2020.js";
import addFormats from "ajv-formats";

const BASE = "https://ledger-rocket.github.io/schemas/";
const [schema, defs, eventSchema, expectedSchema] = await Promise.all([
  fetch(`${BASE}domain/template.schema.json`).then(res => res.json()),
  fetch(`${BASE}common/defs.schema.json`).then(res => res.json()),
  fetch(`${BASE}domain/event.schema.json`).then(res => res.json()),
  fetch(`${BASE}domain/expected-transfer.schema.json`).then(res => res.json())
]);

const ajv = new Ajv2020({ strict: false });
addFormats(ajv);
[defs, eventSchema, expectedSchema].forEach((doc) => ajv.addSchema(doc));
const validate = ajv.compile(schema);

const candidate = {
  template_id: 125,
  site_id: 1,
  name: "Demo Template",
  description: "Example template",
  trigger: "demo_event",
  accounting_treatments: [
    {
      type: "cash_movement",
      policy_refs: [{ id: "IFRS9.CASH" }],
      description: "Cash movement"
    }
  ],
  account_code_validations: [
    { purpose: "from", mask: "21010", description: "Customer account" },
    { purpose: "to", mask: "21010", description: "Counterparty account" }
  ],
  product: "PAYMENTS",
  event_type: "TRANSFER",
  category: "TRANSFER",
  variables: [
    { name: "from_account", description: "Debit account", value: "accounts.from.account_id" },
    { name: "to_account", description: "Credit account", value: "accounts.to.account_id" },
    { name: "transfer_amount", description: "Amount", value: "event.amount" }
  ],
  validations: [
    { name: "amount_positive", expression: "event.amount > 0", description: "Amount must be positive" }
  ],
  legs: [
    {
      leg_number: 1,
      debit_account: "from_account",
      debit_account_type: "LIABILITY",
      credit_account: "to_account",
      credit_account_type: "LIABILITY",
      amount: "transfer_amount",
      description: "Move funds",
      ledger_scope: "primary",
      treatment_type: "cash_movement"
    }
  ],
  metadata_schema: {
    $schema: "https://json-schema.org/draft/2020-12/schema",
    type: "object",
    properties: {
      reference: { type: "string" }
    },
    additionalProperties: false
  },
  examples: []
};

if (!validate(candidate)) {
  console.error(validate.errors);
  process.exit(1);
}

console.log("template is valid");
```

## Contributing

1. Update the relevant schema under `common/` or `domain/`.
2. Bump the `"version"` field when you change the contract.
3. Commit to `main`; GitHub Pages republishes within ~60 seconds.
4. Optionally tag releases (`git tag v1.0.0`) for traceability.
