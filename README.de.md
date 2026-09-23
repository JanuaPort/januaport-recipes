# januaport-recipes

[English](README.md) · **Deutsch**

Rezepte für JanuaPort: Use-Case-Muster, die eine KI und ein Mensch gemeinsam auf einer JanuaPort-Anlage bauen.

JanuaPort ist ein self-hosted MCP-Gateway. Es verbindet KI-Assistenten fein berechtigt mit den
bestehenden Systemen eines Unternehmens und protokolliert die Zugriffe in einem append-only Audit-Log. Der
Kern von JanuaPort ist proprietäre Software der JanuaPort GmbH und nicht Teil dieses Repositorys. Dieses
Repository ist einer der offenen Ränder darum herum.

- **Lizenz:** Apache License 2.0 ([`LICENSE`](LICENSE), [`NOTICE`](NOTICE))
- **Links:** [januaport.ai](https://januaport.ai) · [Sicherheitsrichtlinie](SECURITY.md) · [Beiträge](CONTRIBUTING.md)

Keine Kundendaten, keine Schlüssel, keine Betreiberwerte in diesem Repository.

---

## Was hier liegt

Ein **Rezept** beschreibt, was eine KI zusammen mit einem Menschen braucht, um einen Use Case auf einer
JanuaPort-Anlage aufzubauen: Integrationen, Kartei-Satzarten, Zugänge, eine Agenten-Anweisung, Skripte und
Prüfsteine. Aufbau und Regeln: [`REZEPT-FORMAT.md`](REZEPT-FORMAT.md).

Jedes Rezept nennt seinen Stand ehrlich, in drei Stufen: **durchdacht** (ausgearbeitet, kein Lauf),
**erprobt** (gegen eine Anlage gelaufen) und **belegt** (im Betrieb bei einem Kunden).

| Rezept | Ziel | Stand |
|---|---|---|
| [`rezepte/zahlungseingang`](rezepte/zahlungseingang/REZEPT.md) | Die KI ordnet Zahlungseingänge aus dem Kontoauszug Belegen zu, ein Mensch gibt je Fall frei, ein Roboter bucht in einem Fachsystem ohne Schnittstelle. | **Erprobt.** Bei einem Pilotkunden gegen den echten Betrieb gelaufen; die Abnahme steht aus. Satzart, Anweisung und Roboter-Skripte sind für die Veröffentlichung neu geschrieben. |
