# januaport-recipes

Rezepte, Use-Case-Muster und Best Practices fuer JanuaPort (Apache 2.0)

**Status:** privat bis zum GoLive von JanuaPort (Flip in der GoLive-Checkliste JanuaPort/januaport#788). Teil des Open-Core-Pivots (JanuaPort/januaport#773).

**Lizenz:** Apache License 2.0 (`LICENSE`), Copyright 2026 JanuaPort GmbH (`NOTICE`). Beitraege: `CONTRIBUTING.md`.

**Zustaendig:** USECASE + Lead (#784) — Ownership je Unterordner; Inhalte kommen mit den genannten Tickets.

Keine Kundendaten, keine Schluessel, keine Betreiberwerte in diesem Repository.

---

## Was hier liegt

Ein **Rezept** beschreibt, was eine KI zusammen mit einem Menschen braucht, um einen Use Case
auf einer JanuaPort-Anlage aufzubauen: Integrationen, Kartei-Satzarten, Zugänge, eine
Agenten-Anweisung, Skripte und Prüfsteine. Aufbau und Regeln: [`REZEPT-FORMAT.md`](REZEPT-FORMAT.md).

| Rezept | Ziel | Stand |
|---|---|---|
| [`rezepte/zahlungseingang`](rezepte/zahlungseingang/REZEPT.md) | Die KI ordnet Zahlungseingänge aus dem Kontoauszug Belegen zu, ein Mensch gibt frei, ein Roboter bucht in einem Fachsystem ohne Schnittstelle. | erprobt |
