---
name: drehbuch-desktop-schritt
titel: Ein Drehbuch mit einem Desktop-Schritt über die Kartei verbinden
ziel: Ein Drehbuch-Agent bereitet in der Kartei vor, ein gepinntes Python-Skript führt den Desktop-Schritt aus und die KI wertet das Kartei-Ergebnis aus.
stufe: 2
stand: durchdacht
version: 0.1.0
jnpt_ab: "0.85.0"
muster: [arbeitsliste-rpa, skript-als-abnehmer]
integrationen: []
satzarten: [satzarten/desktop-auftrag.yaml]
beisteller: [januaport-plugins/desktop-runner]
---

# Rezept: Drehbuch mit Desktop-Schritt

KI → Kartei → Desktop-Läufer/Python → Kartei → KI, für Software ohne Schnittstelle.

## 0. Stand und Einordnung

**Stand: durchdacht**, kein Anlagenlauf. Geräte, Kopplung, Auftragskanal und Ausfall-Alarm
sind seit JanuaPort 0.85.0 gebaut. Client `desktop-runner`: gebaut, **noch kein Release,
unsigniert**, gemeinsame Live-Abnahme offen. Klickfolge entsteht vor Ort.

**Stufe 2 — Gemeinsam bauen** (Stufenweg seit #1046). Muster über `wissen_get muster/<name>`:

| Muster | Was es hier beiträgt |
|---|---|
| `arbeitsliste-rpa` | Identität, Status und Ergebnis verbinden KI und Skript; hängende Zustände verlangen Nachprüfung. |
| `skript-als-abnehmer` | Python ist ein begrenzter Werkzeug-Abnehmer; Schreibfehler verlangen Nachlesen statt Wiederholen. |

Quellen auf `main`: `januaport/docs/kartei.md` und die Desktop-Abschnitte in
`januaport/docs/admin-api.md`, `januaport/docs/admin-mcp.md`,
`januaport/docs/mcp-client-anbindung.md`, `januaport/docs/security-model.md`,
`januaport/docs/skript-laeufer.md`; Client: `januaport-plugins/desktop-runner/README.md`
und `januaport-plugins/desktop-runner/contract/README.md`.

## 1. Ziel und Passung

**Ziel:** KI bereitet vor, Skript führt aus, KI wertet aus.

**Passt, wenn …** eine reproduzierbare Windows/amd64-Klickfolge nötig ist und ein Mensch
Fehler prüft. Python, etwa pywinauto, ist der Standardweg des Musters.

**Passt nicht, wenn …** API/Import genügt, eine Desktop/Kartei-Transaktion oder
Offline-Kartei-Zugriff verlangt wird.

**Erfundenes Beispiel:** `kennung = DESKTOP-0000-BEISPIEL` beauftragt eine Bedienfolge
in namenloser Desktop-Software; der Mensch legt das sichtbare Erfolgskriterium fest.

## 2. Rollen

| Wer | Tut | Tut ausdrücklich nicht |
|---|---|---|
| **Mensch** | beauftragt, prüft Klickfolge und unklare Wirkungen | Geld pauschal freigeben |
| **Drehbuch-Agent** (KI) | bereitet vor, startet, wertet Kartei aus | Desktop bedienen, Skript-Status setzen |
| **JanuaPort** | hält Kartei, prüft Rechte, vermittelt Aufträge, auditiert | eigener Kartei-Weg für Desktop-Ergebnis, Klickwirkung prüfen |
| **Desktop-Läufer** | holt Pakete, startet Skript, vermittelt Aufrufe, meldet Ende | als KI handeln, fachlich entscheiden |
| **Python-Skript** | liest, sperrt, klickt, schreibt `erledigt`/`fehler` | anlegen, löschen, `ausgewertet` setzen |

Kein Geld-Schritt im Beispiel. Bei Ergänzung: ausdrückliche Freigabe der betroffenen
Kennungen durch den Menschen **vor** `vorbereitet` und Start.

## 3. Bausteine

**Integrationen:** Kartei genügt, Liste im Kopf leer. Zusätzliche Quellen brauchen einen
eigenen Integrationsvertrag samt Pseudonymisierung.

**Satzart „Desktop-Auftrag“:** `satzarten/desktop-auftrag.yaml`, Name `desktop_auftrag`.
Felder aus `arbeitsliste-rpa`: `kennung`, `quelle`, `status`, `lauf`, `ergebnis`,
`fehler_text`, `notiz`; `lauf` ist eine eigene Skript-Kennung.

`<satzart>` meint den technischen Namen. Werkzeuge: `search`, `get`, `add`, `update`,
`delete`; qualifizierte Namen aus `tools/list` der Satzart übernehmen.
Ohne `freigabe` und `owner_team` gelten Scopes plus Team-Mitgliedschaft.

```text
vorbereitet ──(Skript)──▶ in_arbeit ──(Skript)──▶ erledigt ──(KI)──▶ ausgewertet
                             └─────(Skript)──▶ fehler ────(KI)──▶ ausgewertet
```

| Übergang | Zuständig | Voraussetzung im Ablaufvertrag |
|---|---|---|
| — → `vorbereitet` | KI, `add` | Mensch hat beauftragt; Suche nach `kennung` ohne Treffer |
| `vorbereitet → in_arbeit` | Skript, `update` | frisch gelesen, `lauf` gesetzt, kein anderer Satz in `in_arbeit` |
| `in_arbeit → erledigt` | Skript, `update` | eigener `lauf`, Erfolg im Ziel abgelesen, `ergebnis` gesetzt |
| `in_arbeit → fehler` | Skript, `update` | eigener `lauf`, Wirkung geklärt, `fehler_text` ohne Inhalte |
| `erledigt` oder `fehler → ausgewertet` | KI, `update` | gelesen, bewertet, `notiz` gesetzt; Fehler bleibt als solcher erkennbar |

`ausgewertet` heißt „bewertet“, auch nach Fehler. Ergebnis, Fehler und Lauf bleiben
erhalten. Bei unklarer Wirkung bleibt `in_arbeit`; der Mensch entscheidet nach Zielprüfung.
Kein automatischer Rücksprung oder Wiederholversuch.

**Echte Kartei-Logik:** `enum` prüft Werte, **keine Übergangsrechte**. Kein feldgenaues
Schreibrecht, Eindeutigkeitszwang oder If-Match: Mit `update` wäre jeder gültige Status
setzbar. Diese Rollen sind Anweisungs- und Skriptvertrag.

`update` führt Teiländerungen zusammen: vorher `get`, geänderte Felder mit `id`,
`source`, `as_of` senden. Weggelassenes bleibt; optionale Felder ausdrücklich mit `null`
oder leerem String leeren. Herkunft ist bei jedem Schreiben Pflicht, gilt für den ganzen
Satz; `as_of` ist ein Datum.

**Paket:** Pin bindet Ordner und vollen Commit. `jnpt-desktop.yaml` trägt `name`,
`description`, `entry`, `input_schema`, `tools`, `timeout_s`, `python`; gegebenenfalls
`requirements: requirements.lock` und `wheels/*.whl`. Python-ZIP im Pin muss zur
Client-Allowlist passen; `tools` stimmt mit `declared_tools` überein.

Nur `search`, `get`, `update` der Satzart qualifiziert deklarieren. `input_schema`
erlaubt ein Objekt mit `id` für Einzelaufträge, ein leeres für Zeitpläne: Skript-Eingaben,
kein Kern-Endpunkt. `januaport.input` liefert die Eingabe, `januaport.call` ruft Werkzeuge
über den Desktop-Läufer mit dem Lauf-Token.

| Schritt | Eingabe | Ausgabe | Invariante |
|---|---|---|---|
| Vorprüfen | `januaport.input`, Suche | Satz oder Liste | bei irgendeinem `in_arbeit` anhalten; unklare Auswahl klären |
| Sperren | frische `id`, Lauf-Kennung | `in_arbeit` + `lauf` | erst nach bestätigtem Schreiben klicken |
| Ausführen | eigener gesperrter Satz | sichtbarer Nachweis | Kennung zuerst im Ziel prüfen; bestehende Wirkung übernehmen |
| Zurückschreiben | Nachweis / Fehler | `erledigt` + `ergebnis` / `fehler` + `fehler_text` | Skript ruft selbst `update`; unklar bleibt `in_arbeit` |

## 4. Zugänge und Rechte

Kartei-Zugänge: Besitzer im Team. `<satzart>` = `desktop_auftrag`.

| Token | Besitzer | Scopes bzw. Bindung | Hat ausdrücklich nicht |
|---|---|---|---|
| `<drehbuch-token>` | Person/Dienst-Nutzer im Team | `<satzart>` · `<satzart>:<satzart>_add` · `<satzart>:<satzart>_update` · direkt: `desktop:<pin>` | `delete`, Schema/Admin |
| `<zeitplan-token>` (alternativ) | Dienst-Nutzer im Team | `<satzart>` · `<satzart>:<satzart>_update` · `desktop:<pin>` | `add`, `delete`, Schema/Admin |
| `<auswertung-token>` (eigene KI) | Person/Dienst-Nutzer im Team | `<satzart>` · `<satzart>:<satzart>_update` | `add`, `delete`, Desktop-Start |
| `<geraete-token>` | Gerätebindung, kein Tool-Besitzer | Geräte-API, keine Tool-Scopes | eigenständigen Kartei-Zugriff |
| `<lauf-token>` | Start-/Zeitplan-Identität | deklarierte Werkzeuge ∩ aktuelle Aufruferrechte, geräte-/pin-gebunden, kurzlebig | darüber hinausgehende/dauerhafte Rechte |

Satzart-Scope öffnet `search`/`get`, Schreiben braucht den qualifizierten Werkzeugnamen.
Nur Admins vergeben `desktop:<pin>`; `start_desktop_run` liegt auf `/mcp`. `desktop_*`
ist die Werkzeugfamilie, kein pauschaler Scope. `get_script_run`/`cancel_script_run`
nutzen `run`, kein eigenes Scope-Recht.

**Zweite Berechtigungswege prüfen:** Team-Bündel und Freigabe-Ebenen wirken additiv;
`freigabe: team` gäbe auch `delete`. Aufräumrechte nur auf gesonderten menschlichen Zugang.

**SEC A1: Ein Gerät ist eine Vertrauensdomäne.** Das Skript läuft als derselbe Nutzer
wie der Desktop-Läufer und kann den Geräte-Token lesen. Alle Pins eines Geräts teilen
Vertrauen und Werkzeugrechte. Wer getrennte Werkzeugrechte braucht, nimmt getrennte
Geräte bzw. Konten. Diese Scope-Tabelle isoliert nicht gegen Skriptcode desselben Geräts.

## 5. Ablauf

1. **Mensch/KI:** Auftrag, Kennung, Nachweis und erforderliche Freigabe festlegen.
2. **KI:** `kennung` suchen, Treffer lesen statt neu anlegen. Sonst `add` mit
   `vorbereitet`, `kennung`, `quelle`, `source`, `as_of`. Unklare Antwort nachlesen.
3. **Ein Startweg:** Zeitplan mit Ziel **„Gerät“** oder nach bestätigtem Kartei-Eintrag
   `start_desktop_run(name,input,wall_s?,max_tool_calls?,start_within_s?)` auf `/mcp`.
   `name` ist der Pin, `input` enthält Satz-`id`. **Kein Kartei-Watcher als Auslöser
   in v1.** Ein Eintrag allein startet nichts.
4. **Desktop-Läufer:** holt Ad-hoc-Aufträge; Zeitpläne takten auf dem Gerät. Beide
   teilen **einen aktiven Platz**, höchstens **zehn Aufträge warten pro Gerät**;
   diese Grenze dedupliziert nicht.
5. **Skript:** Vorprüfung (§3), frisch lesen, `in_arbeit` + `lauf` schreiben. Nach
   bestätigter Sperre Zielwirkung prüfen und klicken. Listen seriell leeren (`search`: max. 100).
6. **Skript:** Nachweis prüfen und **selbst über `januaport.call` mit seinem Lauf-Token
   in die Kartei schreiben**. Das ist die fachliche Rückgabe.
7. **Desktop-Läufer:** meldet technisches Ende über `runs/result`; Nachlieferung aus
   seinem Journal ersetzt keinen Kartei-Schreibaufruf.
8. **KI:** direkt gestarteten Lauf mit `get_script_run`/`run`, Kartei stets separat
   prüfen. Beim Zeitplan fragt die KI in ihrem eigenen Ablauf ab; keine automatische
   Fortsetzung zugesagt. `erledigt`/`fehler` bewerten, `notiz` und `ausgewertet` setzen;
   Hängendes dem Menschen vorlegen.

**Idempotenz:** Ein serieller Vorbereiter bildet dieselbe Kennung je Vorgang und sucht
vor `add`. Das Skript prüft die Kennung vor der Zieländerung; bei unklarem Ausgang
entscheidet der Mensch. Schreib- und Startaufrufe nach Timeout nicht blind wiederholen:
Kartei und, soweit vorhanden, `run` zuerst prüfen.

**Ein Lauf zur Zeit:** Arbeitsliste an genau einem Pin/Gerät, ohne zweite Instanz.
Gemeinsamer Platz serialisiert, `in_arbeit` bremst nach Abbruch. Auch KI-Schreibzugriffe
nacheinander; Status ist keine atomare Reservierung konkurrierender Clients.

## 6. Agenten-Anweisung

`anweisung.md` in den Drehbuch-Client einsetzen: `<satzart>`, `<pin>`,
`<freigebende Rolle>`, `<startweg>` füllen. Getrennte Auswertungs-KI: nur ihr Teil und §4-Zugang.

## 7. Aufbau-Handgriffe

**Admin**, in dieser Reihenfolge. Betreiber-Details: `januaport/docs/desktop-laeufer.md`.

| Was | Wofür | Zuschnitt | Wann |
|---|---|---|---|
| 1. Gerät anlegen, koppeln | Geräte-Vertrauen | Art und erwartetes Konto festlegen; Code über GUI, REST oder CLI, am Client einlösen | zuerst |
| 2. Client einrichten | Desktop-Läufer betreiben | ohne Release, unsigniert; vorgesehenes Konto, Installation und Bereitschaft nach Client-README | vor dem Pin |
| 3. Pin `desktop` mit Gerät setzen | Commit und Ziel binden | nur Admin; `kind: desktop`, `target_device`; alle Pins gemeinsam beurteilen | vor Startfreigabe |
| 4. Zeitplan oder Recht auf `start_desktop_run` für den Drehbuch-Token | einen Auslöser wählen | Ziel „Gerät“ aus Pin; alternativ `desktop:<pin>` administrativ; Kartei-Scopes nach §4 vormerken | vor Produktivstart |
| 5. Satzart in `JNPT_KARTEIEN_DIR` | Übergabe laden | `jnpt kartei check`, Neustart, Scopes nach §4 setzen; Katalog prüfen, ohne `freigabe` | vor erstem Lauf |
| 6. Alarmregel `device_ready` | Ausfall erkennen | Geräte-ID als `subject`, Empfänger und Use Case; Bereitschaft ist kein fachlicher Erfolg | vor Abnahme |

**Bauer auf `/mcp`:** Platzhalter, Katalog, Skriptvertrag (§3) mit erfundenen Daten prüfen.

**Außerhalb:** Mensch prüft Konto, Sitzung, Klickwirkung; Paket-Verantwortlicher
liefert Python-ZIP, gegebenenfalls Lock und Wheels.

Für Lock und Windows-Wheels gibt es das Build-Rezept
[`python-bibliotheken-bauen`](../python-bibliotheken-bauen/README.md) mit Ziel `windows`.
Es bereitet Artefakte vor; Windows-Pfade, SHA-256 und Allowlist prüft weiterhin der
Desktop-Läufer. Dieser Weg ist durchdacht, ein gemeinsamer Desktop-Beleg steht aus.

## 8. Fehlerfälle

| Fall | Erkennung | Verhalten | Wer löst |
|---|---|---|---|
| Startantwort verloren | kein sicheres `run` | vor Neustart Geräteweg/Kartei klären | Mensch/Admin |
| Belegt / Schlange voll | Auftragsgrenze | Kapazität prüfen, kein zweiter Weg | Admin |
| Startfrist verpasst | `expired` | vorbereitet lassen, klären | Mensch |
| Paket/Konto/Offline-Bedingung | `refused`: `hash`, `runtime`, `account`, `manifest`, `offline` | Ursache beheben | Admin |
| Satz ungültig | Kartei-Argumentfehler | korrigieren, neu lesen | Bauer |
| Wirkung geklärt | Skriptfehler | `fehler` + `fehler_text` | Mensch/KI |
| Wirkung unklar | `in_arbeit`, etwa `error`, `timeout`, `limit`, `cancelled`, `interrupted`, `lost` | anhalten, Zielprüfung, kein Retry | Mensch |
| Recht entzogen | `denied` / Werkzeugfehler | Ziel/Kartei getrennt prüfen | Admin/Mensch |
| Geräteausfall | `device_ready` | Bereitschaft/Arbeitsliste prüfen | Admin |

## 9. Prüfsteine

Mit erfundenen Daten abhaken; nur Zähler/Audit-Bezüge berichten. Diese Betriebsproben
sind mit **durchdacht** noch nicht bestanden.

- [ ] Zweite Vorbereitung: 0 neue Sätze; normal N Ergebnisse/N Auswertungen im Audit.
- [ ] Unbekannter Status/Pflichtfeld leeren: Abweisung; Teiländerung erhält Ausgelassenes.
- [ ] Bot: `delete`, Zeitplan: `add` wirklich aufrufen; Abweisung trotz Prüfung aller
  Berechtigungswege, nicht nur Fehlen in `tools/list`.
- [ ] `in_arbeit`, fremden `lauf`, falschen Status provozieren: echter Skriptlauf mit
  0 neuen Klickwirkungen. Ohne Freigabe erzeugt die KI 0 vorbereitete Sätze.
- [ ] Ad-hoc/Zeitplan gleichzeitig: höchstens 1 aktiv; mehr als zehn wartende versuchen.
- [ ] Abbruch vor/nach Klick, Kartei-Schreibfehler: kein automatischer Retry, Zielprüfung.
- [ ] Rechtentzug, nicht deklariertes Werkzeug, Geräte-Token allein: Abweisung am echten
  Geräte-MCP bzw. Kartei-Zugang prüfen.
- [ ] Jede Sperre isoliert kurz entfernen: Verbotsprobe muss rot werden; wiederherstellen.
  Rollen am Skript, Freigabe im KI-Ablauf prüfen, nicht als Kartei-Schutz ausgeben.

## 10. Grenzen

- **Ein Gerät ist eine Vertrauensdomäne (SEC A1).** Das Skript läuft als derselbe Nutzer
  wie der Desktop-Läufer und kann den Geräte-Token lesen. Alle Pins eines Geräts teilen
  Vertrauen und Werkzeugrechte. Wer getrennte Werkzeugrechte braucht, nimmt getrennte
  Geräte bzw. Konten. Das Job Object ist keine Sicherheits- oder Netzwerksandbox.
- **Keine Desktop/Kartei-Transaktion:** Klick kann wirken, bevor Schreiben scheitert.
  Status und Kennung ergeben keine Exactly-once-Garantie oder atomare Sperre.
- **Keine Übergangsrechte:** Rollen sind Vertrag; Rechte begrenzen ganze Werkzeuge.
  Ein zweites Gerät umginge die lokale Serialisierung.
- **Online-Pflicht:** Kartei-Werkzeuge brauchen Lauf-Token und Anlage. Werkzeuglose
  Offline-Pins tragen diese Übergabe nicht.
- **Laufmeldung ersetzt kein Ergebnis:** Journal liefert `runs/result` nach, keinen
  Kartei-Aufruf. `januaport.log` ist im gebauten Client wirkungslos; stdout/stderr werden
  verworfen. Diagnose/Ergebnis in die vorgesehenen Felder schreiben.
- **Audit belegt keine Klickwirkung.** KI bewertet den gelesenen Nachweis, nicht selbst
  den Desktop. Kein Kartei-Watcher in v1, keine zugesagte automatische KI-Fortsetzung.
- **Client ohne Release und unsigniert;** keine gemeinsame Anlagen-Abnahme des Rezepts.

## 11. Datenschutz

Alle sieben Felder sind ohne `privacy`-Etiketten und kommen im Klartext an. Nur Kennungen,
Quellenverweise und knappe Nachweise ablegen. Pseudonyme in unetikettierten Feldern bleiben
unverändert. Klartextbedarf vor Vertragserweiterung klären; KI-Pseudonymisierung begrenzt
die OS-Rechte der Sitzung nicht.

**Kein roher Eingang im Chat:** keine Exporte, Oberflächeninhalte, Bildschirmfotos.
`input` trägt die Satzreferenz, keine Credentials. Auftragsinput wird bei Ende gelöscht
und nicht auditiert; Kartei-Aufrufe und unetikettierte Felder können dagegen im Audit
stehen. Prüfberichte nur mit Zählern und Audit-Bezügen.

**Aufräumen:** Betreiber legt Frist fest, Mensch bestätigt abgeschlossene Sätze und
löscht mit gesondertem, qualifiziertem `delete`-Recht. Hängendes zuerst klären. Keine
automatische Kartei-Frist; Laufjournal und Sicherungen haben eigene Aufräumregeln.
