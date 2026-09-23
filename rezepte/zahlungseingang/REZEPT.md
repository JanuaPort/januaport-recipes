---
name: zahlungseingang
titel: Zahlungseingänge zuordnen und in einem Fachsystem ohne Schnittstelle buchen lassen
ziel: Die KI ordnet jeden Geldeingang aus dem Kontoauszug einem Beleg zu, ein Mensch gibt je Fall frei, ein Roboter bucht im Fachsystem.
stufe: 3
stand: belegt
version: 0.1.0
jnpt_ab: "0.53.0"
muster: [arbeitsliste-rpa, abholer-als-beisteller, skript-als-abnehmer, rueckfrage-per-entwurf]
integrationen:
  - rolle: kontoauszuege
    art: datei
    typ: camt053_v08
    vertrag: januaport-integrations/docs/file-connector-spec.md
    werkzeuge: [list_statements, read_statement]
  - rolle: postfach
    art: rest
    vertrag: januaport-integrations/connector-specs/microsoft-graph-mail.yaml
    werkzeuge: [create_draft]
    optional: true
satzarten: [satzarten/zahlungseingang.yaml]
beisteller:
  - januaport-plugins/ebics-abholer
---

# Rezept: Zahlungseingang

Die KI ordnet Zahlungseingänge den Belegen zu, ein Mensch gibt je Fall frei, und ein
Roboter bucht in einem Fachsystem, das weder Schnittstelle noch Import hat.

## 0. Stand und Einordnung

**Stand: belegt.** Das Rezept läuft bei einem Pilotkunden im Betrieb. Dort ist ein
ERP-System ohne Schnittstelle, Import und Export das Ziel, und Power Automate Desktop ist
der Roboter. Der Betrieb ist ab JanuaPort 0.53.0 belegt. Kunde, Ort und Fachsystem nennen wir
nicht. Satzart und Anweisung sind für die Veröffentlichung neu geschrieben; Feldnamen und
Texte weichen vom Pilotbetrieb ab, der Ablauf nicht.

**Stufe 3 — Use Cases bauen.** Das Rezept setzt vier Muster übereinander, die jede
JanuaPort-Anlage mitliefert (`wissen_get muster/<name>`):

| Muster | Was es hier beiträgt |
|---|---|
| `abholer-als-beisteller` | Die Kontoauszüge kommen als Datei in eine Ablage, nicht als Einfügung in den Chat. |
| `arbeitsliste-rpa` | Die Kartei ist die Arbeitsliste zwischen KI, Mensch und Roboter; der Status ist der Lock. |
| `skript-als-abnehmer` | Der Roboter ruft die Kartei über drei HTTP-Anfragen auf, mit eigenem Token. |
| `rueckfrage-per-entwurf` | Fehlt die Belegnummer, legt die KI einen Mail-Entwurf an; ein Mensch sendet. |

## 1. Ziel und Passung

**Ziel:** Die KI ordnet jeden Geldeingang einem Beleg zu, ein Mensch gibt je Fall frei, und
ein Roboter bucht die Zahlung im Fachsystem.

**Passt, wenn …**
- die Kontoauszüge als camt.053 (Version 001.08) vorliegen, egal ob über EBICS-Abholer,
  Bank-Export oder eine andere Dateilieferung;
- die Zahler die Rechnungs-, Auftrags- oder Belegnummer meistens in den Verwendungszweck
  schreiben;
- das Fachsystem eine Maske hat, in der sich ein Beleg per Nummer finden und eine Zahlung
  erfassen lässt, auch wenn das nur über die Oberfläche geht.

**Passt nicht, wenn …**
- das Fachsystem eine API oder einen Import hat: dann eine Integration bauen, keinen Roboter;
- der Abgleich gegen eine Liste offener Posten laufen soll: dieses Rezept kennt keine Quelle
  für offene Posten und prüft keinen Betrag gegen den Beleg;
- niemand je Fall freigeben will: Das Rezept hat keinen Modus ohne Freigabe.

## 2. Rollen

| Wer | Tut | Tut ausdrücklich nicht |
|---|---|---|
| **Mensch** (freigebende Rolle) | gibt jede Zuordnung frei (**Geld-Schritt**, §5 Schritt 6) · entscheidet Sonderfälle · sendet Mail-Entwürfe · prüft fehlgeschlagene und hängende Buchungen im Fachsystem | tippt Standardfälle nicht selbst · legt keine Sätze von Hand an |
| **KI** (Token „KI") | liest Auszüge · legt je Geldeingang einen Satz an · zieht Nummer und Art aus dem Verwendungszweck · schlägt vor · setzt nach Freigabe `geprueft` · legt Mail-Entwürfe an | bucht nicht · setzt `in_buchung` nicht · prüft nichts im Fachsystem (kann es nicht) · löscht keine Sätze · sendet keine Mail |
| **JanuaPort** | liefert Auszüge pseudonymisiert · hält die Kartei · erzwingt tool-genaue Rechte · protokolliert jeden Aufruf | entscheidet nichts fachlich · kennt das Fachsystem nicht · plant keine Läufe |
| **Roboter** (Token „Roboter") | holt freigegebene Sätze · sperrt · bucht im Fachsystem · schreibt `verbucht` oder `fehler` | liest keine Auszüge und kein Postfach · legt keine Sätze an · löscht nichts · bucht nie zweimal · räumt hängende Sätze nicht auf |

## 3. Bausteine

**Integration `kontoauszuege`** (Datei, Typ `camt053_v08`, Vertrag
`januaport-integrations/docs/file-connector-spec.md`). Werkzeuge:
`kontoauszuege_list_statements`, `kontoauszuege_read_statement`. Die Pseudonymisierung ist
Pflicht:

```yaml
privacy:
  read:
    - { field: konto_iban,       label: iban }
    - { field: gegenpartei_iban, label: iban }
    - { field: gegenpartei_name, label: name }
  scan:
    - { field: verwendungszweck, patterns: [iban, email] }
```

**Integration `postfach`** (optional, REST-Spec
`januaport-integrations/connector-specs/microsoft-graph-mail.yaml`). Werkzeug:
`postfach_create_draft`. Ohne sie entfallen die Rückfragen per Entwurf (§5 D).

**Satzart `zahlungseingang`**, Datei `satzarten/zahlungseingang.yaml`. Sie ist eine
Betreiber-Datei für `JNPT_KARTEIEN_DIR` und hat keine `freigabe`-Ebene: Zugriff entsteht nur
über Scopes, weil der Roboter als Team-Mitglied sonst auch `add` und `delete` bekäme.

Status-Automat:

```
neu ──(Freigabe, KI setzt)──▶ geprueft ──(Roboter)──▶ in_buchung ──▶ verbucht
                                 ▲                         │
                                 └──(Mensch entscheidet)───┴──▶ fehler
```

| Übergang | Wer | Voraussetzung |
|---|---|---|
| — → `neu` | KI (`add`) | Schlüssel nicht vorhanden (vorher gesucht) |
| `neu → geprueft` | KI | Bestätigung des Menschen für genau diesen Satz; `beleg_nummer` und `nummer_art` gesetzt; `trefferart` ist `eindeutig` oder `manuell` |
| `geprueft → in_buchung` | Roboter | `roboter_lauf` gesetzt; kein anderer Satz in `in_buchung` |
| `in_buchung → verbucht` | Roboter | `buchungs_nr` aus dem Fachsystem abgelesen |
| `in_buchung → fehler` | Roboter | `fehler_text` gesetzt; Fachsystem für diesen Beleg nicht verändert |
| `fehler → geprueft` | KI | Der Mensch hat geprüft und sagt „erneut"; `fehler_text` nach `notiz`, leeren |
| `in_buchung → verbucht` oder `→ geprueft` | KI | nur im Nachlauf, nach Prüfung des Menschen im Fachsystem |
| `verbucht → *` | niemand | Endzustand |

**Beisteller.** Der EBICS-Abholer (`januaport-plugins/ebics-abholer`) legt die Auszüge in
die Ablage. Er ist optional, denn jede Lieferung von camt-Dateien in das Verzeichnis der
Integration genügt.

**Roboter-Schritte (Vertrag).** Eine Referenz-Implementierung für Power Automate Desktop
ist in Arbeit (JanuaPort/januaport#806, `januaport-plugins/kartei-rpa`). Bis dahin gilt
dieser Vertrag. Jede RPA-Aktion ist ein eigener Prozess ohne geteilten Zustand; jeder
Schritt gibt deshalb **eine Zeile JSON** aus, und die Schleife lebt im Flow.

| Schritt | Eingabe | Ausgabe (eine Zeile JSON) | Invariante |
|---|---|---|---|
| 1 Arbeitsliste | – | `lauf`, `anzahl`, `saetze[]` mit `id`, `beleg_nummer`, `nummer_art`, `betrag`, `buchungsdatum` | bricht ab, wenn ein Satz in `in_buchung` steht; holt in Schleifen bis leer (Suche liefert höchstens 100) |
| 2 Satz sperren | `lauf`, `id` | `id`, `beleg_nummer`, `nummer_art`, `betrag`, `buchungsdatum`, frisch gelesen | liest vorher; nur `geprueft` mit leerer `buchungs_nr` → `in_buchung` + `roboter_lauf` |
| 3 Satz verbuchen | `lauf`, `id`, `buchungs_nr` | `id`, `status` | liest vorher; nur eigener Lauf; `buchungs_nr` war leer |
| 4 Satz-Fehler | `lauf`, `id`, Schrittname, Meldung | `id`, `status` | liest vorher; nur eigener Lauf; Meldung ohne Kundendaten → `fehler_text` |

Scheitert ein Schritt (fremder Lauf, falscher Status, Anlage nicht erreichbar), bricht er mit einem
Skriptfehler ab, und der Flow beendet den Lauf.

Für alle vier gilt: Jedes Schreiben liest vorher und schickt alle Felder zurück (`update`
überschreibt vollständig), `source = roboter:buchung`, `as_of` = Laufdatum, kein Retry auf
Schreibaufrufe, und der Token erscheint nie in Log oder Ausgabe. Den Transport (drei
HTTP-Anfragen gegen `/mcp`) beschreibt das Muster `skript-als-abnehmer`, die PAD-Fallen das
mitgelieferte Wissen `power-automate-desktop`.

## 4. Zugänge und Rechte

Jeder Abnehmer bekommt einen eigenen Token mit Besitzer. Namen hier sind Rollen; die echten
Labels vergibt der Betreiber.

| Token | Besitzer | Scopes (tool-genau) | Hat ausdrücklich nicht |
|---|---|---|---|
| `<ki-token>` | die freigebende Person | `kontoauszuege` · `zahlungseingang` · `zahlungseingang:zahlungseingang_add` · `zahlungseingang:zahlungseingang_update` · optional `postfach:create_draft` | `delete`, Senden, Satzart anlegen oder ändern |
| `<roboter-token>` | ein Dienst-Nutzer im Team der Kartei, mit Ablaufdatum | `zahlungseingang` · `zahlungseingang:zahlungseingang_update` | `add`, `delete`, Auszüge, Postfach |
| Team der freigebenden Rolle | – | zusätzlich `zahlungseingang:zahlungseingang_delete` | – `delete` ist nur zum Aufräumen da (§11), nie im Bot-Token |

Ohne Besitzer sieht ein Token keine Kartei; der Besitzer muss im Team der Sätze sein. Jeder
Token belegt einen Seat.

## 5. Ablauf

**A · Eingang** (KI, auf Zuruf des Menschen)
1. `kontoauszuege_list_statements`; neu ist, was nicht als `kontoauszug` in der Kartei steht.
2. Je Datei `kontoauszuege_read_statement`, je Buchung mit `richtung = CRDT` und
   `status = BOOK`: Schlüssel bilden, suchen, bei Treffer überspringen, sonst `add` mit `neu`.
3. Zähler melden: gelesen, neu, bereits bekannt.

**B · Abgleich** (KI, nur aus dem Verwendungszweck)
4. Je Satz `neu`: `beleg_nummer`, `nummer_art` und `trefferart` setzen.
5. Vorschlagsliste an den Menschen.

**C · Freigabe** (Mensch, im Chat): **der Geld-Schritt**
6. Bestätigung je Satz oder als ausdrückliche Liste von Schlüsseln; keine Pauschale.
7. Erst danach setzt die KI `geprueft`.

**D · Rückfrage** (KI, optional)
8. Bei `kein_treffer` oder `mehrdeutig` auf Wunsch ein Mail-Entwurf; der Mensch sendet.

**E · Buchung** (Roboter, nach seinem eigenen Zeitplan)
9. Schritt 1; steht ein Satz in `in_buchung`, bricht der Lauf ab und meldet das.
10. Je Satz: Schritt 2 → Klickfolge im Fachsystem (Maske nach `nummer_art`, Nummer suchen,
    Zahlung mit `betrag` und `buchungsdatum` erfassen, Buchungsnummer ablesen) → Schritt 3.
    Gibt es die Nummer nicht, ist sie mehrdeutig oder kommt ein Dialog: Schritt 4, das
    Fachsystem bleibt unverändert, weiter zum nächsten Satz.

**F · Nachlauf** (Mensch und KI)
11. Die KI meldet auf Zuruf Sätze in `fehler` und `in_buchung`. Der Mensch prüft sie im
    Fachsystem und entscheidet: Nummer korrigieren und `geprueft`, oder die KI setzt
    `verbucht` mit der Buchungsnummer, die der Mensch nennt.

**Idempotenz.** Nie doppelt anlegen (Schlüssel-Suche vor `add`, die Kartei selbst erzwingt
keine Eindeutigkeit). Nie doppelt buchen (nur selbst gesperrte Sätze, `buchungs_nr` leer).
Ein Lauf zur Zeit (kein überlappender Zeitplan, dazu die Vorprüfung in Schritt 9). Die Kartei
hat keinen Konflikt-Schutz; der Lock ist der Status.

## 6. Agenten-Anweisung

`anweisung.md` enthält den Text für die KI des Abgleichs. Er wird in die Projekt-, Skill-
oder Systemanweisung des Clients eingesetzt. Zu füllen sind die Namen der Integrationen, der
Satzart und die freigebende Rolle. Die Anweisung trägt die harten Regeln: Freigabe je Satz,
nie Roboter-Status setzen, nie behaupten, was die KI nicht prüfen kann, und kein roher
Eingang im Chat.

## 7. Aufbau-Handgriffe

**Admin** (Admin-GUI, Admin-MCP oder CLI):

| Was | Wofür | Zuschnitt | Wann |
|---|---|---|---|
| Datei-Integration `kontoauszuege` anlegen | Auszüge lesbar machen | Typ `camt053_v08`, Ablage außerhalb des Spec-Verzeichnisses, `privacy` wie §3 | vor dem ersten Lauf |
| Satzart-Datei nach `JNPT_KARTEIEN_DIR`, `jnpt kartei check`, Neustart | Arbeitsliste | ohne `freigabe`-Ebene | vor dem ersten Lauf |
| Mail-Integration (optional) | Rückfragen als Entwurf | nur `create_draft` freigeben | bei Bedarf |
| `<ki-token>` anlegen, Besitzer setzen, Scopes nach §4 | Zugang der KI | ohne `delete` | vor dem ersten Lauf |
| Dienst-Nutzer ins Team, `<roboter-token>` mit Ablaufdatum | Zugang des Roboters | nur `update` | vor dem ersten Roboter-Lauf |
| Anlage-Rechte für Satzarten aus dem Team nehmen | keine wilden Satzarten neben der Datei | – | nach der Abnahme |

**Bauer** (KI mit Mensch, auf `/mcp`): Anweisung einsetzen und Platzhalter füllen ·
Probelauf A–C mit einem Auszug · Prüfsteine 1 und 2 abhaken. Den Client nach dem Anlegen der
Satzart neu verbinden (manche holen die Werkzeugliste nur beim Verbinden).

**Mitspieler außerhalb der Anlage:** der Roboter-Rechner (Erreichbarkeit der Anlage, bei
eigener Zertifizierungsstelle deren Wurzel im Zertifikatspeicher, Token nur im
Anmeldeinformationsspeicher des Flow-Kontos) · der Flow mit der Klickfolge, die ein Mensch vor
Ort aufnimmt · der Zeitplan des Roboters.

## 8. Fehlerfälle

| Fall | Erkennung | Verhalten | Wer löst |
|---|---|---|---|
| Auszug `falsches_format` oder `nicht_lesbar` | `list_statements` | Datei überspringen, dem Menschen nennen | Admin (Lieferung prüfen) |
| Keine Nummer im Verwendungszweck | Abgleich | `kein_treffer`, Rückfrage anbieten | Mensch |
| Mehrere Nummern, Sammelzahlung, Abzug | Abgleich | `mehrdeutig` mit Notiz; Freigabe nur als `manuell` | Mensch |
| Dieselbe Buchung in zwei Auszügen | Schlüssel-Suche | zweiter Fund übersprungen | – |
| Pauschal-Freigabe („alle") | Chat | KI verlangt Liste oder Einzelbestätigung | Anweisung |
| Nummer im Fachsystem nicht gefunden oder mehrdeutig | Roboter | `fehler`, Fachsystem unverändert | Mensch (Nachlauf) |
| Klickfolge scheitert (Dialog, Sperre) | Roboter | `fehler`, nächster Satz | Mensch (Nachlauf) |
| Roboter stirbt zwischen Sperren und Verbuchen | Satz bleibt `in_buchung` | nächster Lauf bricht ab | Mensch prüft, KI setzt nach |
| Anlage nicht erreichbar, Token abgelaufen | HTTP-Fehler, `invalid_token` | Lauf abbrechen, Fachsystem nicht anfassen | Admin |
| Deckel der Kartei erreicht | `add` abgewiesen | aufräumen (§11) | Mensch mit KI |
| Feld fehlt, Enum-Wert unbekannt | `argument_error` | Vertrag verletzt: Satzart und Flow abgleichen | Bauer |

## 9. Prüfsteine

Ohne Inhalte im Protokoll, nur Zähler und Audit:

1. Zwei Eingangsläufe hintereinander: Der zweite legt **0** Sätze an.
2. Kein Satz erreicht `geprueft` ohne Bestätigung im Chat (Stichprobe: Update-Ereignisse des
   KI-Tokens gegen die Bestätigungen).
3. Roboter-Lauf: N Sätze `geprueft` → N Sätze `verbucht` mit `buchungs_nr`, 0
   Doppelbuchungen im Fachsystem.
4. Abbruchtest: Ein Satz von Hand auf `in_buchung` → der nächste Lauf bricht ab und meldet.
5. Fehlertest: Eine nicht existierende Nummer → `fehler`, das Fachsystem bleibt unverändert;
   nach Korrektur → `geprueft` → `verbucht`.
6. Rechte-Test: In `tools/list` des Roboter-Tokens fehlen `add`, `delete`, Auszüge und
   Postfach.
7. Jeder Zustandswechsel steht als Write-Ereignis mit dem richtigen Token im Audit.

## 10. Grenzen

- **Kein Abgleich gegen offene Posten, keine Betragsprüfung.** Die KI kennt nur den
  Verwendungszweck; ob die Nummer existiert, zeigt erst der Roboter.
- **Pull statt Push.** Freigegebene Sätze werden erst beim nächsten Roboter-Lauf gebucht.
  JanuaPort hat keinen Zeitplan und stößt nichts an.
- **Kein Konflikt-Schutz in der Kartei** (kein If-Match). Die Sicherheit hängt an der
  Ein-Lauf-Regel und am Status.
- **Keine Aufbewahrungsfrist im Produkt.** Das Aufräumen ist ein Handgriff (§11).
- **Die Klickfolge ist nicht Teil des Rezepts.** Sie hängt am Fachsystem und wird vor Ort
  aufgenommen; eine KI kann den Flow nicht bauen.
- **Klicks im Fachsystem außerhalb des Protokolls:** Das Audit belegt die Kartei-Schritte,
  nicht, was der Roboter in der Oberfläche getan hat.

## 11. Datenschutz

- **Pseudonymisierung:** IBANs und Name der Gegenpartei kommen als Kürzel an. Der
  Verwendungszweck wird nur nach IBAN und E-Mail durchsucht, damit die Belegnummer im Klartext
  bleibt; sonst wäre kein Abgleich möglich. Die Kartei wandelt Kürzel nie zurück, und der
  Roboter braucht sie nicht, denn er tippt nur Nummer, Betrag und Datum.
- **Kein roher Eingang im Chat:** keine camt-Datei, kein CSV-Export der Kartei, kein
  Bildschirmfoto aus dem Fachsystem. Jede Einfügung geht an der Pseudonymisierung vorbei.
- **Aufräumen:** Sätze in `verbucht` nach einer Frist, die der Betreiber festlegt, löschen:
  die KI listet Zähler, der Mensch bestätigt, gelöscht wird über das Team-Recht und nie über
  einen Bot-Token. Jede Löschung steht im Audit.
- **Fehlertexte** tragen Schrittname und Meldung der Oberfläche, nie Kundendaten.
