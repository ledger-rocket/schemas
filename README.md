# LedgerRocket Schemas

Public JSON Schemas for LedgerRocket services. These contracts describe the shape of event ingress payloads, ledger templates, and supporting types.

## Hosted Schemas

| Schema | Description | URL |
| --- | --- | --- |
| `domain/event.schema.json` | Financial event requests submitted to the LedgerRocket event service | https://ledger-rocket.github.io/schemas/domain/event.schema.json |
| `domain/template.schema.json` | Ledger template definitions used to transform events into transfers | https://ledger-rocket.github.io/schemas/domain/template.schema.json |
| `domain/expected-transfer.schema.json` | Expected transfer output format for template validation and testing | https://ledger-rocket.github.io/schemas/domain/expected-transfer.schema.json |
| `common/defs.schema.json` | Shared reusable definitions referenced by other schemas | https://ledger-rocket.github.io/schemas/common/defs.schema.json |

The repository is automatically published via GitHub Pages at https://ledger-rocket.github.io/schemas/.

## Usage

Add the appropriate `$schema` declaration to your JSON files, for example:

```json
{
  "$schema": "https://ledger-rocket.github.io/schemas/domain/template.schema.json",
  "template_id": 125,
  "site_id": 1,
  ...
}
```

Schemas are versioned using semantic version numbers. Breaking changes will increment the major version. Historical versions are preserved in this repository under dedicated directories.
