---
name: geo-stichprobe
titel: Nennung und Zitat einer Domain in zwei KI-Suchen monatlich messen
ziel: Ein Skript stellt 13 feste Suchfragen und schreibt je Maschine und Frage ein datensparsames Trend-Signal in die Kartei.
stufe: 2
stand: durchdacht
version: 0.1.0
jnpt_ab: "0.91.0"
muster: [skript-als-abnehmer]
integrationen:
  - rolle: openai-websuche
    art: rest
    vertrag: januaport-integrations/connector-specs/openai-websuche.yaml
    werkzeuge: [ask]
  - rolle: gemini-websuche
    art: rest
    vertrag: januaport-integrations/connector-specs/gemini-websuche.yaml
    werkzeuge: [ask]
satzarten: [satzarten/geo_stichprobe.yaml]
beisteller: []
---

# GEO-Stichprobe über den Skript-Läufer

## 0. Stand und Einordnung

**Durchdacht**, Stufe 2 „Gemeinsam bauen“, JanuaPort/januaport#1293 Teil S/K/R.
Offline-Tests und ein synthetischer Durchstich durch den unveränderten Python-Bootstrap
des Läufers prüfen den Einstieg. Es gab keinen Anlagenlauf und keine echten Suchergebnisse.
Die beiden REST-Vorlagen entstehen parallel im Produkt; ihre Spiegel in
`januaport-integrations` folgen nach dessen Merge. `jnpt_ab: 0.91.0` bezeichnet
die früheste vorgesehene Version nach v0.90.0, keine Behauptung einer Auslieferung.

§3 des [Rezept-Formats](../../REZEPT-FORMAT.md#3-der-yaml-kopf) sagt „meist 3“,
erlaubt also Stufe 2. Der Aufbau folgt der Skript-Rezept-Ausnahme aus §2.
Das Muster `wissen_get muster/skript-als-abnehmer` trägt den eigenen Zugang,
werkzeuggenaue Rechte, strukturierte Daten und Zähler im Protokoll bei. Hier
ersetzt das Läufer-Modul den dort beschriebenen HTTP-Handshake; einzelne
Messfehler werden als Sätze erfasst und die nächste Frage wird bearbeitet.
Ein zusätzlicher Beisteller entfällt: Das Skript liegt vollständig im Rezept;
der vorhandene Skript-Läufer ist die Laufzeit-Voraussetzung.

## 1. Ziel und Passung

Monatlich und 28 Tage nach einem Beitrag erfassen, ob **januaport.ai** bei
13 unveränderten Suchfragen genannt oder als Quelle zitiert wird.
Das ist ein Trend-Signal der eingesetzten Suchwerkzeuge. Es passt für einen
Vergleich über die Zeit bei gleicher Fragenliste, Skript-Fassung und Konfiguration.
Es passt nicht für Aussagen über individuelle ChatGPT-/Gemini-Verbraucher-Apps,
Rankings, Reichweite, Kausalität eines Beitrags oder vollständige Web-Erwähnungen.

Das Rezept ist ausdrücklich für JanuaPort selbst gebaut. Die öffentliche
Domain ist das erlaubte Messziel, keine Kunden- oder Anlagenkennung.
`ZIEL_DOMAIN` in [`stichprobe.py`](skript/stichprobe.py) macht das Ziel sichtbar.
Für die eigene Domain ändert der Betreiber diese Konstante in seinem Repository,
passt Satzart-Beschreibungen und Prüftabelle an und erstellt eine **neue Fassung**.
Die Wortsuche verwendet den Teil vor dem ersten Punkt als Marke; eine Marke,
die davon abweicht, verlangt eine entsprechende Änderung und neue Tests.

## 2. Rollen

| Wer | Tut | Tut ausdrücklich nicht |
|---|---|---|
| Mensch/Betreiber | verantwortet Domain, Anbieterbudgets, Rechte, Fassung und Zeitpläne; genehmigt den Aufbau | Offline-Proben als Anlagenbeleg ausgeben |
| Inbound-KI | liest monatlich die Anweisung, startet T+28, wertet Kartei-Zähler aus | Antworten einsammeln, Fragen spontan ändern oder fehlende Werte als false behandeln |
| Skript | ruft festgelegte Werkzeuge auf, bewertet kurz im Speicher, schreibt flache Messsätze | Antworttexte speichern oder protokollieren, Schreibaufrufe wiederholen |
| JanuaPort/Läufer | pinnt die Fassung, schneidet Laufrechte, serialisiert und auditiert nach Produktvertrag | inhaltliche Qualität oder Vergleichbarkeit der Suchmaschinen garantieren |

**Geld-Schritt:** Die Suchaufrufe verursachen Anbieterkosten. Der Betreiber
richtet Budgets und Guthaben beim Anbieter ein; das Skript kauft kein Guthaben.

## 3. Bausteine

| Baustein | Vertrag / Aufgabe |
|---|---|
| `openai-websuche` | REST, Spec im YAML-Kopf, `ask` → `openai_websuche_ask` |
| `gemini-websuche` | REST, Spec im YAML-Kopf, `ask` → `gemini_websuche_ask` |
| [`geo_stichprobe.yaml`](satzarten/geo_stichprobe.yaml) | Ein Messsatz je UTC-Datum, Anlass, Maschine und Fragennummer |
| [`jnpt-script.yaml`](skript/jnpt-script.yaml), [`main.py`](skript/main.py) | Manifest und dünner Adapter für `januaport.input`, `call`, `log` |
| [`stichprobe.py`](skript/stichprobe.py), [`fragen.json`](skript/fragen.json) | Fachkern ohne SDK-Import, feste 13 Fragen |
| `tests.py`, `test.sh`, `mutationen.py` | Vertragsproben, Verbotsproben und serielle Mutationen |

Beide `ask` erhalten genau `{"frage":"<Text>"}` und liefern strukturiert
`{"text":string|null,"quellen":[{"url":string,"title":string}]|null}`.
Es werden nur die festen öffentlichen Fragen versandt; Pseudonymisierung
personenbezogener Eingaben wird hier nicht benötigt.

`januaport.call` liefert das vollständige MCP-`CallToolResult` als Dictionary,
kein ausgepacktes Nutzobjekt. Quelle: `januaport-plugins/script-runner/sandbox/bootstrap.py`,
Zeilen 69–80; `isError` wirft dort `ToolError`, dessen Text verworfen wird.
Der Kern bevorzugt vorhandenes `structuredContent`; ohne diesen Schlüssel liest
er JSON aus einem einzelnen `content`-Textblock. Eine vorhandene kaputte Struktur
wird nicht durch den Begleittext ersetzt. Fehlende Felder und falsche Typen sind
`antwort_unlesbar`; ausdrücklich `null` bedeutet hingegen leeren Text/leere Quellen.

**Bewertung:** `genannt` sucht das Wort `januaport` ohne Beachtung der Großschreibung
mit Wortgrenzen. `januaport.ai`, `www.januaport.ai` und `JanuaPort` zählen;
`nichtjanuaport` und `januaportal` zählen nicht. `zitiert` verlangt den Host
`januaport.ai` oder ein Suffix `.januaport.ai`. `januaport.ai.evil.example`
und `nichtjanuaport.ai` zählen nicht. OpenAI liefert die echte URL; der Host
wird daraus gelesen. Gemini liefert einen Google-Umleitungslink, und **nur `title`
als Domain** wird bewertet. Ein Domainwort im Query des Umleitungslinks zählt nicht.
URL-Zugangsdaten, Steuerzeichen und kaputte Hostformen werden abgewiesen.

Die Satzart hat neun Felder: `lauf`, `datum`, `anlass`, `maschine`, `frage_nr`,
`genannt`, `zitiert`, `quellen_januaport`, `fehler`. Die ersten fünf sind Pflicht
und Filter. `lauf` ist die einmal beim Start gebildete UTC-Startzeit in Sekunden
(`2026-11-01T06:00:05Z`, synthetisches Beispiel), für alle Sätze beider Maschinen
im selben Lauf gleich. Der aktuelle Läufer stellt im `januaport`-Modul keine
Lauf-ID bereit (`januaport-plugins/script-runner/sandbox/bootstrap.py:99`,
Modulbelegung bis Zeile 102); deshalb wird diese Ersatzkennung verwendet.
Es gibt keinen Status-Automaten: Sätze werden angelegt; das Skript aktualisiert
und löscht sie nicht. Bei Messfehlern fehlen beide Booleans. Nur passende
OpenAI-URLs bzw. Gemini-Domains kommen mit `, ` getrennt und auf 1000 Zeichen
gekappt in `quellen_januaport`. Herkunft: `source: "script geo_stichprobe"`,
`as_of` als UTC-ISO-Zeitpunkt; optionales `team` wird unverändert weitergereicht.

Die Kostengrenze bilden die Anbieterdeckel: OpenAI-Projektbudget und
Gemini-Guthaben beim Betreiber. Das Werkzeug hat keinen Tagesdeckel;
`daily_cap` gibt es nur an Schreibwerkzeugen (Details in §10).

## 4. Zugänge und Rechte

| Abnehmer | Besitzer / Zuschnitt | Scopes |
|---|---|---|
| Team-Token `<team-token>` für Start, Auswertung und Zeitpläne | verknüpfte Technical Identity mit Nutzer und Mitgliedschaft im vorgesehenen Team | `script:geo_stichprobe`, `openai-websuche:ask`, `gemini-websuche:ask`, `geo_stichprobe:geo_stichprobe_add`, `geo_stichprobe` (Lesen: search/get) |
| Kurzlebiges Lauf-Token | vom Gateway abgeleitet, kein Secret im Skript | Schnitt aus aktuellen Aufruferrechten und den drei Manifest-Werkzeugen |

`script:geo_stichprobe` ist tool-genau erforderlich, weil `_add` das Skript
schreibend macht. Ein Chat-Start verlangt die clientseitige Schreibbestätigung.
Für Zeitpläne trägt die vorherige bewusste Einrichtung die Freigabe; der Admin
bindet eine bestehende Technical Identity, ohne Token-Geheimnis beim Läufer.
Kartei-Schreibscopes verwenden den **qualifizierten** Namen
`geo_stichprobe:geo_stichprobe_add`; die REST-Integrationen verwenden `:ask`.

Der Zugang hat ausdrücklich kein `_update`, `_delete`, Schema-, Admin-,
Klartext-Rückwandlungs-, Anbieter-Schreib- oder Live-Umschaltrecht.
Die Satzart hat **keine `freigabe`-Ebene**, wie `zahlungseingang`: eine
Team-Freigabe würde add und delete zusätzlich erlauben. Vor Betrieb prüft der
Admin auch additive Team-Scopes, andere Tokens, weitere Pins und direkte
`ask`-/Kartei-Aufrufe. Die Rechte werden vom Produkt durchgesetzt; das Rezept
ist keine zusätzliche Rechte-Sandbox. Der echte Berechtigungs-Negativtest
gegen die eingerichtete Anlage bleibt Abnahmebedingung (§9).

## 5. Ablauf

1. Admin richtet Satzart, REST-Vorlagen, Anbieterzugänge und gepinnte Fassung ein.
2. Eingabe prüfen: `anlass` standardmäßig `monatlich`, sonst
   `T+28: <Beitragstitel>`, maximal 120 Zeichen, ohne Steuerzeichen;
   `maschine` ist `openai`, `gemini` oder standardmäßig `beide`; `team` ist
   optional eine nichtleere Zeichenkette. Zusatzfelder und ungültige Werte
   enden mit `eingabe_ungueltig`, Exit 1 und **null Werkzeugaufrufen**.
3. Einmal die UTC-Startzeit als `lauf` bilden. Je ausgewählter Maschine die
   Fragen 1–13 seriell stellen, unmittelbar bewerten und jeweils einmal
   `geo_stichprobe_add` rufen. Ausfälle betreffen
   die jeweilige Frage; die nächste wird trotzdem gestellt.
4. stdout liefert ausschließlich je Maschine die Zähler `genannt`, `zitiert`,
   `fehler`, jeweils von 13. Fehler zählt betroffene Fragen, höchstens einmal
   je Frage, auch wenn Messung und Speicherung beide scheitern. Trefferzähler
   beschreiben die Messung, auch wenn deren Speicherung scheitert.
5. `januaport.log` erhält dieselben Zähler und bei Fehlern feste Codes;
   keine Antwort, keine Frage-Antwort-Paare, keine Quellenlisten. Das Kartei-Schreiben
   ist der fachliche Ergebnisweg, stdout das technische Lauf-Ergebnis.
6. Inbound-KI liest monatlich [`anweisung.md`](anweisung.md) und wertet per
   `geo_stichprobe_search` aus (Filter Datum/Anlass/Maschine, nach `lauf` gruppieren,
   dann mit Filter `lauf`, `limit: 100` und bei Kappung zusätzlich je `frage_nr`;
   kein offset). Eine weiter gekappte Suche
   bleibt unvollständig. T+28 wird mit dem Beitragstitel als Anlass gestartet.

Für einen manuellen Start mit Vertragskennung 2 beispielsweise:

```json
{"name":"geo_stichprobe","input":{"anlass":"monatlich","maschine":"openai"},"wall_s":600,"max_tool_calls":26}
```

Das sind Argumente für `start_script_run`, nicht die Skripteingabe allein.
`start_script_run` übernimmt `timeout_s` nicht als Default: `wall_s` ausdrücklich
wählen. Bei `running` mit `get_script_run` abholen. Vertragskennung 1 unterstützt
diesen Startweg nicht; dort je Maschine das registrierte `script_geo_stichprobe`
innerhalb der verfügbaren Wandzeit verwenden.

**Idempotenz:** Das Skript ist absichtlich append-only und hat keinen Suchscope
im Manifest. Ein erneuter Start erzeugt weitere Sätze mit eigener Startzeit als
`lauf`. Vor Wiederholung per Suche
prüfen, welche Kombinationen aus Datum, Anlass, Maschine und Fragennummer schon
vorliegen. Ein unklar gescheitertes `_add` kann bereits geschrieben haben
(Produkt-Audit nach Dispatch); es wird deshalb nicht wiederholt. Dubletten
innerhalb eines Laufs bei der Auswertung getrennt ausweisen und vom Menschen
klären lassen. Wiederholungen anhand von `lauf` getrennt zählen; Teilbestände
mehrerer Läufe nicht zu einer vollständigen Messung zusammensetzen.
**Ein Lauf zur Zeit:** Der Läufer hat einen gemeinsamen Slot; bei `busy`
wird ein Zeitplan-Slot übersprungen, nicht nachgeholt. Das Skript legt keine Sperrdatei an.

## 6. Agenten-Anweisung

[`anweisung.md`](anweisung.md) im Inbound-Team einsetzen und monatlich lesen.
Platzhalter `<team>` und `<Beitragstitel>` lokal ersetzen, ohne Personendaten
oder Secrets. Die Anweisung steuert Auswertung und T+28-Start; der Admin
richtet die wiederkehrenden Zeitpläne ein. Keine echten Ergebnisse in dieses Repo übernehmen.

## 7. Aufbau-Handgriffe

| Wer / was | Wofür | Zuschnitt | Wann |
|---|---|---|---|
| Admin: zwei REST-Vorlagen und Anbieterzugänge | Suchwerkzeuge bereitstellen | vorgeschlagene Integrationsnamen, jeweils ask; Secrets nur im vorgesehenen Speicher | nach Auslieferung ab frühestens 0.91.0 |
| Admin: Satzart kopieren | Kartei bereitstellen | nach `JNPT_KARTEIEN_DIR`, ohne freigabe, `jnpt kartei check`, Neustart | vor Rechtevergabe |
| Bauer auf `/mcp`: Manifest und Tests prüfen | Skript vorbereiten | nur Standardbibliothek, Python 3.12; keine zusätzliche Connector-Spec im Rezept | vor jeder neuen Fassung |
| Admin: Ordner `rezepte/geo-stichprobe/skript` pinnen | Fassung bereitstellen | vollständiger Commit auf Standardzweig des Betreiber-Repos oder freigegebenes Speicherpaket | nach Review und ausdrücklicher Freigabe |
| Admin: Rechte und zwei Zeitpläne | regelmäßige Messung | je Maschine einer, monatlich am 1., 06:00 und 06:20, Zeitzone bewusst wählen | nach synthetischer Anlagen-Abnahme |
| Betreiber beim Anbieter | Kosten begrenzen | OpenAI-Projektbudget, Gemini-Guthaben | vor erstem kostenpflichtigem Lauf |

Quellen für Ablauf, Start, Protokoll, Zeitpläne und Kartei-Vertrag:
`januaport/docs/skript-laeufer.md`, `docs/skript-zeitplaene.md`, `docs/kartei.md`.
Läufer: `januaport-plugins/script-runner/sandbox/bootstrap.py` und
`probe/scripts/abbruch/jnpt-script.yaml`.

Vom Repository-Root:

```sh
bash rezepte/geo-stichprobe/test.sh
python -I -B rezepte/geo-stichprobe/mutationen.py
```

`test.sh` nutzt `PYTHON` (sonst `python3`); unter Windows ggf. `PYTHON=python`.
Die normale Suite braucht weder Netz noch SDK. Für die optionale echte
Bootstrap-Probe unter POSIX `JANUAPORT_BOOTSTRAP` auf die unveränderte Datei
setzen und sie nur lesend bereitstellen. Die entfernten Werkzeuge bleiben
synthetisch. Python wird mit `-I -B` gestartet. Mutationen verändern den
Quelltext nur im Speicher; jede muss mindestens eine Assertion verletzen.

**Neue Fragen = neue Skript-Fassung.** Dasselbe gilt für Ziel-Domain und
Bewertungsregeln. Tests aktualisieren, Review, neue Fassung freigeben.
Bei Speicherpins über die [Live-Umschaltung mit Betreiber-Mail und Rückweg](https://github.com/JanuaPort/januaport/blob/main/docs/skript-laeufer.md#speicher-live-zeiger-1048-k1-stufe-2-gebautunveröffentlicht)
wechseln; bekannte vorige Fassung für den Rückweg behalten. Git-Pins bleiben
beim administrativen Pin-Wechsel. Nach einem Fassungswechsel Zeitpläne bewusst
neu bestätigen; der Live-Zeiger bestätigt die Bindung nicht automatisch.

## 8. Fehlerfälle

| Fall | Erkennung | Verhalten / wer löst |
|---|---|---|
| Ungültige Eingabe | lokale Prüfung, zusätzlich Manifest-Schema | `eingabe_ungueltig`, kein Aufruf; Inbound-KI korrigiert |
| ask-Exception, einschließlich SDK-ToolError | Ausnahme ohne Übernahme des Texts | Satz mit `aufruf_fehlgeschlagen`, ohne Booleans; Admin prüft Zugang/Budget |
| Fehlende/kaputte Antwortstruktur oder URL | Typ-/Strukturprüfung | Satz mit `antwort_unlesbar`, ohne Booleans; Vorlagen-Verantwortlicher prüft Vertrag |
| `_add` scheitert | Exception oder MCP-isError | `speichern_fehlgeschlagen` im Log, Fehlerzähler erhöhen, nächste Frage; Admin prüft Kartei/Rechte/Deckel |
| Laufzeit-/Aufruflimit, Abbruch oder busy | technischer Laufabschluss/Audit | Teilbestand anhand erwarteter 13 Sätze prüfen; Mensch entscheidet Wiederholung |
| Fassung oder Rechte geändert | pausierter Zeitplan / abgewiesener Start | Admin prüft und bestätigt Bindung bewusst neu |

Ein technisches `ok` bestätigt nur den beendeten Prozess. Fachliche Fehler
stehen im Zähler und, bei erfolgreichem `_add`, im Messsatz.

## 9. Prüfsteine

- [x] 13 wörtliche, eindeutige Fragen mit lückenlosen Nummern geprüft.
- [x] Wortgrenzen, Host-Suffix, Gemini-title und Umleitungs-Query negativ geprüft.
- [x] Echten `main.py`-Adapter mit Fake des Läufer-Moduls ausgeführt;
  ungültige Eingaben provozieren null Aufrufe und festen Abbruchcode.
- [x] Kanarien-Antworten und Ausnahmetexte bleiben aus Kartei, stdout/stderr und Log;
  Booleans fehlen bei Ausfall, Satzart und geschriebene Felder stimmen überein.
- [x] Beide MCP-Antwortwege, Fortsetzen nach Mess-/Schreibfehlern, keine Schreib-Retries,
  UTC und Quellenkappung geprüft. 30/30 Mutationen rot, Original grün.
- [x] `lauf` ist bei fortschreitender Uhr und Tageswechsel in allen 26 Sätzen gleich;
  zwei verschiedene Startzeitpunkte liefern verschiedene Kennungen. Pflichtfeld,
  Filter und Feldabgleich geprüft; Neubildung je Satz wird als Mutation erkannt.
- [x] Unveränderter Läufer-Bootstrap mit echten Frames, input/call/log und ToolError
  im netzlosen Python-3.12-Container synthetisch geprüft.
- [x] Satzart mit echtem `jnpt kartei check` im lokalen Produkt-Image geprüft
  (neun gültige Felder, fünf Filter).
- [ ] Auf Anlage: registrierte Werkzeuge, minimale Rechte und
  additive Rechtewege prüfen; update/delete/Admin und Fremdteam-Zugriffe wirklich versuchen.
- [ ] Anbieter-Vorlagen, Zeitpläne, Widerruf, Limits und Lauf-Audit gegen die
  eingerichtete Anlage abnehmen. Kein Anlagenbeleg durch Offline-Tests.

## 10. Grenzen

`beide` bedeutet **52 Werkzeugaufrufe** (26 ask + 26 add). Das braucht
Läufer-Vertragskennung 2 mit Default-Deckel **200** und tatsächlich mindestens
52 erlaubten Aufrufen. Unter Kennung 1 (Deckel **50**) jede Maschine einzeln
laufen lassen (je 26); die verfügbare Wandzeit gesondert prüfen.

**Wandzeit:** Je Maschine 13 Suchaufrufe à bis zu 90 s ergeben bereits
1170 s zuzüglich Schreiben; beide Maschinen bis zu 2340 s. Das Manifest setzt
wie beauftragt **600 s**, daher garantiert es keinen vollständigen Durchlauf.
Zwei Zeitpläne, am 1. um 06:00 und 06:20, reduzieren die Last je Lauf, beseitigen
aber diese Grenze nicht. Mit Worst-Case-Latenzen wird ein Lauf abgeschnitten.
Fehlende Fragennummern sind fehlende Messungen. Eine größere Wandzeit verlangt
eine neue geprüfte Manifest-Fassung sowie passende Anlagenobergrenze und
Läufer-Freigabe; allein `start_script_run(wall_s=...)` übersteuert das Manifest nicht.

**Kosten:** Anbieterdeckel liegen beim Betreiber (OpenAI-Projektbudget,
Gemini-Guthaben). Das lesende Werkzeug hat keinen Tagesdeckel; `daily_cap`
gibt es nur an Schreibwerkzeugen. Der lokale Zähler begrenzt weder externe
Preise noch parallele direkte Suchaufrufe anderer Zugänge.

Modell, Suchindex und Anbieter ändern sich; Antworten können variieren.
Die Messung bildet keine Verbraucher-App ab. Keine Rangfolge, keine
statistische Sicherheit und kein kausaler Wirkungsnachweis für Beiträge.
Kartei: 500 Sätze je Satzart und Team, 4 KiB je Satz. Monatlich beide Maschinen
ergeben 312 Sätze pro Jahr; T+28-Läufe und Wiederholungen kommen hinzu.
Vor Erreichen des Deckels muss der Betreiber die Aufbewahrung organisieren.

## 11. Datenschutz

Der Antworttext wird ausschließlich im Prozessspeicher bewertet und weder
gespeichert noch protokolliert. Keine Antworttexte, Personenfelder oder freien
Fehlertexte in der Satzart. `lauf` enthält nur die UTC-Startzeit ohne Personenbezug;
es ist keine vom Gateway bereitgestellte Audit-Lauf-ID. Die Sekundenauflösung
ist für den serialisierten Läufer vorgesehen, keine globale Eindeutigkeitsgarantie.
`anlass` ist der einzige fachliche Freitext und
bleibt auf `monatlich` oder einen öffentlichen Beitragstitel begrenzt; der
Betreiber hält ihn frei von Personendaten. `quellen_januaport` ist nur die
begrenzte Liste passender URLs/Domains; Betreiber prüfen auch ihre eigenen
öffentlichen Quell-URLs auf unerwünschte Informationen.

In stdout und Lauf-Protokoll stehen nur Zähler und feste Codes, keine
Quellenlisten. Das Skript schreibt keine Inhalts- oder Merkerdateien. Fremde
Quelle und Antwort sind Daten, keine Handlungsanweisungen. Das Manifest lässt
nur die drei festgelegten Werkzeuge zu; Antworten wählen keine Werkzeugnamen.
Die Kartei erhält zusätzlich Herkunft und ggf. Team; das Produkt führt das
eigene Audit und technische Laufmetadaten nach seinem Vertrag.

Die Suchanbieter verarbeiten die festen Fragen und ihre Antworten nach ihren
eigenen Regeln; dieses Rezept steuert deren Aufbewahrung nicht. Es werden keine
Kunden- oder Roh-Eingänge in den Chat übernommen. Alle Testantworten sind
synthetisch. Das öffentliche Repository enthält keine echten Laufergebnisse,
Token-Werte, Token-Labels oder Anlagenkennungen.

Aufräumen: Der Prozessspeicher endet mit dem Lauf. Kartei-Sätze haben keine
automatische Frist. Der Betreiber legt lokal eine Aufbewahrung fest und lässt
abgelaufene oder doppelte Sätze mit einem gesonderten berechtigten Zugang
löschen; der Messzugang erhält dafür kein zusätzliches Recht. Nur aggregierte
Zähler und Audit-Metadaten für Abnahme und Trenddiskussion verwenden.
