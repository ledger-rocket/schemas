# LedgerRocket JSON Schemas

Hosted JSON Schemas describing LedgerRocket financial events, ledger templates, and supporting types. All schemas live at **https://ledger-rocket.github.io/schemas/** and are designed for direct consumption by editors, CI pipelines, and validation libraries.

## Latest Schemas

| Path | Description | URL |
| --- | --- | --- |
| `domain/event.schema.json` | Financial event requests submitted to the Event Service | https://ledger-rocket.github.io/schemas/domain/event.schema.json |
| `domain/template.schema.json` | Ledger templates that transform events into transfers | https://ledger-rocket.github.io/schemas/domain/template.schema.json |
| `domain/template.put.schema.json` | Body of the accounting-rule-engine template PUT: the template without `site_id` and `template_id` | https://ledger-rocket.github.io/schemas/domain/template.put.schema.json |
| `domain/workflow.schema.json` | Workflow definitions that chain template executions | https://ledger-rocket.github.io/schemas/domain/workflow.schema.json |
| `domain/expected-transfer.schema.json` | Expected transfer output for template validation/testing | https://ledger-rocket.github.io/schemas/domain/expected-transfer.schema.json |
| `common/defs.schema.json` | Shared `$defs` referenced by the domain schemas | https://ledger-rocket.github.io/schemas/common/defs.schema.json |

Recent template change: `domain/template.put.schema.json` (frozen copy `domain/v1.0.0/template.put.schema.json`) is new. It describes the body of accounting-rule-engine's `PUT /api/v1/sites/{site_id}/templates/{template_id}`: every property of the domain template except `site_id` and `template_id`, each a `$ref` to the domain property, with the same `required` list less the two ids and `additionalProperties: false`. Its `$schema` is an enum of its own two published URLs, `https://ledger-rocket.github.io/schemas/domain/template.put.schema.json` and `https://ledger-rocket.github.io/schemas/domain/v1.0.0/template.put.schema.json`. Since v7.0.0 accounting-rule-engine takes both ids from the path, writes them into the stored template and refuses a body that carries either; it publishes the same body as `TemplatePutRequest`. `domain/template.schema.json` is unchanged and keeps both ids, because it describes the stored template that a GET returns. A PUT body names the PUT schema in `$schema`; accounting-rule-engine stores the template with the domain schema URL in its place. `.github/scripts/check_put_schema.py` fails CI when a PUT schema drifts from the template schema in its own directory, when the template files that share an `$id` (and so answer the PUT's published `$ref`s) differ, or when the template gains a top-level keyword the PUT does not mirror. A GET response is a stored template, not a PUT body: send it back without `site_id` and `template_id` and with the PUT URL in `$schema`. Nothing existing changes, so the published version stays at **v1.0.0**.

Recent event change: each `accounts` entry now carries `account_id` XOR `external_account_id` (exactly one; `purpose` stays required). `external_account_id` is the customer-supplied external account id, resolved to a Ledger Service account for the site. This matches the contract both Event Service engines already enforce (supplying both or neither is a 422) and relaxes the schema, so existing instances stay valid and the published version stays at **v1.0.0**.

Recent event change: `$schema` is now an enum of the two published event schema URLs, `https://ledger-rocket.github.io/schemas/domain/event.schema.json` and `https://ledger-rocket.github.io/schemas/domain/v1.0.0/event.schema.json`, in place of the pattern `^https://ledger-rocket\.github\.io/schemas/.*$`. The pattern admitted any URL under the site, so `https://ledger-rocket.github.io/schemas/event/1.0.0`, which returns 404, passed validation. Event Service validates an event against this schema on `POST /api/v1/events:validate` and `POST /api/v1/events:validate:explain` only; the commit path `POST /api/v1/events` does not validate against it. accounting-rule-engine validates each template example's `event_request` against it through the template schema when a template is saved or validated. A value that these paths validate now names a schema that exists. This tightens validation only for `$schema` values outside the two published URLs, and the dashboard stops writing the dead value before this change merges, so the published version stays at **v1.0.0** and the frozen `domain/v1.0.0/` copy carries the same change.

Recent audit-slug change: `revision` now means the revision the record claims, not a count of approval attempts. Since v5.0.0, accounting-rule-engine stores each new audit record once per `site_id`, `model_name`, `model_id` and revision, and refuses a second writer at a taken revision. Within one `site_id`, `model_name` and `model_id`, no two records claim the same revision, and the claimed revisions order the history. Records written before revisions were claimed may repeat a revision; they are ordered by `transition_date` and come before every claimed record. Only the description changes; the type and the bounds stay, so every existing instance stays valid.

Recent audit-slug change: `description` now carries `pattern: \S`, so a value made only of whitespace is refused. It satisfied `minLength: 1` while recording no reason for the change, and accounting-rule-engine has refused it where the slug is written since v1.41.15 and publishes the same pattern on `AuditSlug.description`. This tightens validation only for whitespace-only descriptions, and none is stored: of 14,260 audit slugs across every dev site, none has a whitespace-only description. The 1,109 blank ones are empty strings, which `minLength: 1` already refused. As the note below says, this schema carries no `version` field to bump.

Recent audit-slug change: `description` now carries `maxLength: 1000` in place of `maxLength: 500`. accounting-rule-engine enforces `1..1000` where the slug is written and publishes the same bound on `AuditSlug.description`, and the reject path copies a `rejection_reason` this schema already bounds at 1000 characters into that field, so 500 refused records the service accepts. This relaxes validation, so every existing instance stays valid. This schema carries no `version` field and no frozen copy under `domain/v1.0.0/`, unlike the schemas in the table above, so there is no version line to hold or to bump; PRO-6563 decides whether it joins that set.
Recent audit-slug change: `common/defs.schema.json#/$defs/modelName`, which only `domain/audit-slug.schema.json` references, now enumerates `workflow` alongside `template` and `rule`. accounting-rule-engine stores workflow audit slugs with `model_name: workflow` and publishes all three values on `ModelName`, so the two-value enum refused every workflow audit record the service writes. This relaxes validation, so every existing instance stays valid, and the frozen `common/v1.0.0/` copy carries the same change so a pinned consumer is not left refusing them.

Recent audit-slug change: `description` now carries `maxLength: 1000` in place of `maxLength: 500`. accounting-rule-engine enforces `1..1000` where the slug is written and publishes the same bound on `AuditSlug.description`, and the reject path copies a `rejection_reason` this schema already bounds at 1000 characters into that field, so 500 refused records the service accepts. This relaxes validation, so every existing instance stays valid. This schema carries no `version` field and no frozen copy under `domain/v1.0.0/`, unlike the schemas in the table above, so there is no version line to hold or to bump; PRO-6563 decides whether it joins that set. A whitespace-only description stays admitted here and refused by the service, which publishes `pattern: \S` on the same field; that tightening is tracked separately as PRO-6562.

Recent template change: `accounting_treatments[].policy_refs[].version` now carries `maximum: 9999` alongside its existing `minimum: 1`. Policy versions are edition years (IAS 1 2023, CONCEPTUAL_FRAMEWORK 2018) or small revision numbers, so four digits admit every real version, and accounting-rule-engine already enforces the same `1..9999` bound in code and in its OpenAPI document. This tightens validation only for versions of five or more digits, which no real policy carries, so the published version stays at **v1.0.0**.

Recent template change: `common/defs.schema.json#/$defs/policyId`, which `accounting_treatments[].policy_refs[].id` references, now carries `pattern: ^[A-Z0-9][A-Z0-9./_-]*[A-Z0-9]$` in place of the mixed-case `^[A-Za-z0-9][A-Za-z0-9./_-]*[A-Za-z0-9]$`; `minLength: 1` and `maxLength: 100` are unchanged. accounting-rule-engine enforces exactly this pattern and this length on every template it accepts and every template it serves, and publishes both on `PolicyRef.id`, so the schema and the service now state one shape instead of two. This refuses a lowercase letter, which two dev templates carried (`IFRS15.Revenue`) before they were repaired to the spelling four other templates already used; every remaining policy id on dev and every example in this repo is uppercase, so the published version stays at **v1.0.0**.

Recent workflow change: workflow schema **v1.0.0** requires top-level `accounting_treatment` and `category` fields. `accounting_treatment` is workflow-level prose; detailed accounting policies remain on referenced templates. `category` is an open-vocabulary `UPPER_SNAKE_CASE` business category.

Recent change: template scopes now accept any lower snake case identifier defined by the template (beyond the legacy `primary` / `secondary` values), and the shared treatment-type enum documents the full adapter-supported set. These tighten validation but remain compatible with existing schema consumers, so the published version stays at **v1.0.0**.

Each schema exposes a top-level `"version"` field. When a breaking change is released, the major version increments and a frozen copy is published under `vX.Y.Z/`. The current published version is **v1.0.0**:

```
common/v1.0.0/defs.schema.json
domain/v1.0.0/event.schema.json
domain/v1.0.0/template.schema.json
domain/v1.0.0/template.put.schema.json
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

1. Update the relevant schema under `common/` or `domain/`.
2. Bump the `"version"` field when the contract changes.
3. Commit to `main`; GitHub Pages republishes within ~60 seconds.
4. Copy the updated schema into the `vX.Y.Z/` directory when cutting a release tag.
