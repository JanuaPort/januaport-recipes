# januaport-recipes

**English** · [Deutsch](README.de.md)

Recipes for JanuaPort: use-case patterns that an AI and a human build together on a JanuaPort installation.

JanuaPort is a self-hosted MCP gateway. It connects AI assistants to a company's existing systems with
fine-grained permissions and records access in an append-only audit log. The core of JanuaPort is
proprietary software of JanuaPort GmbH and is not part of this repository. This repository is one of the
open edges around it.

- **License:** Apache License 2.0 ([`LICENSE`](LICENSE), [`NOTICE`](NOTICE))
- **Links:** [januaport.ai](https://januaport.ai) · [Security policy](SECURITY.md) · [Contributing](CONTRIBUTING.md)
- **Language:** The recipes and the format description are currently written in German.

No customer data, no keys, no operator values in this repository.

---

## What lives here

A **recipe** describes what an AI working together with a human needs in order to build a use case on a
JanuaPort installation: integrations, Kartei record types (structured records), access rights, an agent
instruction, scripts and checkpoints. Structure and rules: [`REZEPT-FORMAT.md`](REZEPT-FORMAT.md).

Every recipe states its status honestly, in three levels: **thought through** (worked out, not run),
**tried** (ran against an installation) and **proven** (in operation at a customer).

| Recipe | Goal | Status |
|---|---|---|
| [`rezepte/zahlungseingang`](rezepte/zahlungseingang/REZEPT.md) | The AI matches incoming payments from the bank statement to documents, a human approves each case, a robot books them in a business system that has no interface. | **Tried.** Ran at a pilot customer against real operations; acceptance is pending. The published record type, instruction and robot scripts were rewritten for publication. |
