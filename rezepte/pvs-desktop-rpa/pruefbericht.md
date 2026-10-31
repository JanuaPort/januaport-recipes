# Prüfbericht zum PVS-Desktop-Vorbau

Lokaler Stand vom 2026-10-31, Bezug #1239, #1241, #1242. Kein Anlagenbeleg.
Der erste Commit `c977c08` enthält ausschließlich Tests und `test.sh`.
Sein Lauf war erwartungsgemäß rot, weil das Paket noch nicht existierte.
Fachkern, Mock, Testergänzungen und Dokumentation folgen im Umsetzungscommit.
Die vorhandene Commit-Identität wurde nicht geändert.

## Verifikation

| Prüfung | Ergebnis |
|---|---|
| `python -I -B -m unittest discover -s rezepte/pvs-desktop-rpa -p tests.py` | 49 Tests, 199 Unterfälle, 0 Fehler, 0 Fehlschläge |
| `bash rezepte/pvs-desktop-rpa/test.sh` mit `PYTHON` | derselbe Offline-Testweg |
| `python -I -B rezepte/pvs-desktop-rpa/mutationen.py` | 52/52 Mutationen durch mindestens eine Assertion erkannt; Original danach grün |
| echter CLI-Prozess | JSON-Ein-/Ausgabe, beide Abläufe und ungültige Eingabe geprüft |
| Dateiverhalten | Vorher-/Nachher-Vergleich im Arbeitsverzeichnis; Audit-Hook erkennt auch Schreibversuche außerhalb davon und in TEMP |
| Nebenkanäle | CLI-Audit-Hook würde Netz und Kindprozessstarts abweisen; alle Demo-Läufe erfolgreich ohne solche Versuche |
| Leckproben | 9 Methodeneinsatzstellen × 9 Ausnahmetypen, inklusive synthetischem Namen, Kennung und Fenstertitel; Ergebnis und stdout/stderr ohne Inhalte |
| Shell | `bash -n` erfolgreich; shellcheck lokal nicht vorhanden |
| Whitespace | `git diff --check` erfolgreich |
| Anweisung | 3.263 Bytes, unter 4 KiB |
| Namens-Grep gemäß Auftrag | leer; zusätzlich neue Dateien vor dem Staging geprüft |

Verwendet: Python 3.14.8, Windows und Git Bash. Keine externen Python-Pakete,
keine Container. Die referenzierte Läufer-Dokumentation wurde separat online
gelesen; die Tests selbst arbeiten vollständig offline. Keine Workflow-Änderung,
kein Push, kein PR, kein CI-Dispatch. Im Worktree und den geprüften übergeordneten
Verzeichnissen waren keine zusätzlichen CLAUDE.md-/AGENTS.md-Regeln vorhanden.

## Verbotsproben und Mutationen

Jede Mutation verändert genau ein Vorkommen im Quelltext im Speicher eines
isolierten Prozesses. Wiederholte Sperren werden getrennt entfernt, etwa die
Zeitprüfung vor Lesen und Schreiben und die Sperrprüfung vor Lesen und Annahme.
Es laufen keine Mutationsprozesse gleichzeitig. Ein Syntax-/Importfehler allein
genügt nicht: Der Harness verlangt mindestens eine fehlgeschlagene Assertion.
Quelltextdateien bleiben bytegleich; anschließend ist die Originalfassung grün.

| Pflichtmutation | Ergebnis |
|---|---|
| (a) `nur_melden` ignorieren | rot, 5 Assertions fehlgeschlagen |
| (b) Ausnahmetext in UC1-Ergebnis aufnehmen | rot, 54 Assertions fehlgeschlagen |
| (c) Namen statt Kennungen zur Erkennung verwenden | rot, 4 Assertions fehlgeschlagen |
| (d) unbekannte Kategorie annehmen | rot, 2 Assertions fehlgeschlagen |

Die weiteren 48 Proben prüfen Identität, leere Kennung, Revision, vollständige
und streng typisierte Fakten, bereits erledigte und doppelte Fälle, alle
fachlichen Ablehnungsgründe, Quartalsregel, Schaltertypen, beide UC1-Deadlines,
zulässige Adapter-Rückgaben, Setup-Auswahl, kein/mehrere Patienten, offene Kennung,
UC2-Deadline, Fokus, Ziel-Vorprüfung, zweite Instanz, UC2-Ausnahmetext und letzte
Ausgabesperre. Hinzu kommen die einzelnen Mock-Sperren für Deadline,
Bereitschaft, Dialog, Datensatzsperre an beiden Methoden, halbfertiges Fenster,
Zustandswechsel, Idempotenz, fehlendes Programm, DPI/Ansicht, Fokus und
Patientenwechsel sowie JSON-Objekt, erlaubte Felder, doppelte Schlüssel,
Schaltertypen, Code-Menge und Zähler. Die ausführbare Liste steht in
`mutationen.py`; für jedes passende Quelltextvorkommen wird eine Probe ausgeführt.

| Verbot / Fehler | Tatsächlich ausgelöste Probe |
|---|---|
| Annahme im Melde-Modus | sichere Fälle und alle Kategorien mit Annahme-Spy, 0 Schreibaufrufe |
| Quartalsfreigabe umgeht Fachsperre | jede weitere Fachsperre zusammen mit erster Quartalslesung ausgelöst |
| Patient nach Name oder Zeilenposition gewählt | gleicher Name und Geburtsjahr 0 bei zwei Kennungen; Listenumsortierung und neuer Eintrag mitten im Lauf |
| falsche/veränderte/verschwundene Identität angenommen | falsche Rückgabekennung, geänderte Revision, verschwundener Datensatz und neue Sperre vor Wirkung |
| mehrfach annehmen | Doppelkarte im selben Lauf und zweiter Lauf auf identischem Zustand |
| Dialog schließen oder selbst anmelden | Dialog und alle Bereitschaftsfehler ausgelöst; Wirkung bleibt aus, Zustand wird nicht behoben |
| UI vor PVS-Fokus | verzögerter Fokus sowie Fokus nach der Deadline, keine frühe UI-Wirkung |
| mehrdeutigen Patienten verwenden | zwei offene Kennungen und Wechsel unmittelbar vor UI; keine Wirkung |
| fehlendes Programm starten / zweite Instanz | jeweils erstes und zweites Programm entfernt; keine UI-Wirkung; Umschaltung erhält Instanzzahlen |
| unklare Teilwirkung wiederholen | nach erstem Programm erscheint Dialog, genau eine bestätigte Wirkung, kein Retry |
| Zeitlimit überschreiten | verzögert, dauerhaft halb gefüllt, Gesamtbudget über mehrere Einträge, Budgetablauf vor UI |
| Inhalte nach außen geben | rohe Ausnahme mit Testinhalten, unzulässige Ergebnisfelder/Codes/Zähler, defekte Ein-/Ausgabekanäle |
| Patientendaten/unsichere Optionen als Eingabe | Zusatzfelder, falsche Typen, doppelte Schlüssel und ungültige Setups vor Adapter-Aufrufen abgewiesen |
| Dateien / Netz / Kindprozesse verwenden | echter CLI-Lauf unter Audit-Hook plus Vorher-/Nachher-Dateivergleich; keine Versuche im unveränderten Code |

**Grenze zu Pflicht 2:** Die Verbotsproben laufen am ausführbaren Fachkern,
an den echten JSON-Einstiegspunkten und am Mock. Ein echter PVS-Adapter ist
ausdrücklich ausgeschlossen und deshalb nicht geprüft. Die Dateiverhaltensprobe
belegt den vorhandenen Code, keine Sandbox für beliebigen Adaptercode.
Abwesende Fähigkeiten wie Login und Programmstart haben hier keine produktive
Implementierung, deren Sperre entfernt werden könnte. Alle Verbotsproben und
passenden Mutationen am echten Adapter bleiben verbindliche Sprint-1-Abnahme;
dieser Bericht behauptet dafür keinen Nachweis.

## Doku-Checkliste

- [x] Rezept-README mit YAML-Kopf, Stand `durchdacht` und Pflichtabschnitten 0–11.
- [x] „Was dieses Rezept nicht ist“ und Betreiberverantwortung für Lizenzbedingungen.
- [x] Datenschutz: nur synthetische Bauumgebung, keine Patientendaten im Ergebnis,
  Kennungen nur im Lauf-Speicher, keine Dateien.
- [x] `anweisung.md` unter 4 KiB.
- [x] `REZEPT-FORMAT.md` §2: eng begrenzte Ausnahme „Skript-Rezept“.
- [x] Zweite Code-Regel in §5 konsistent auf beide §2-Ausnahmen verwiesen
  (erforderliche Folgestelle aus Pflicht 1).
- [x] Inhaltsverzeichnis-Zeile in Root-README und README.de.
- [x] Andere Rezepte und `.github/` unverändert.

## Offene Punkte

1. **Ergebnisweg / Läufer-Eingabe:** Kein `jnpt.ergebnis` in den gelesenen Quellen
   belegt. `ergebnis_abgeben` validiert und schreibt ausschließlich lokales
   Zähler-JSON auf stdout; das ist beim Läufer kein fachlicher Rückkanal.
   Übergabe aus `januaport.input`, Ergebnisempfänger, minimale Werkzeuge und
   Fehlerverhalten vor dem ersten Betrieb im Betreiber-Repository anbinden.
2. **Echter Adapter für Sprint 1:** außerhalb dieses öffentlichen Repositorys.
   Deadline, Zustandsbestätigung vor Wirkung, Kennungserkennung, Dateiverhalten,
   Fokus, Programme, Monitore/DPI sowie alle Negativ- und Mutationsproben dort
   erneut prüfen; danach gemeinsamer Anlagenlauf.
3. **Fachliche Setup-Werte:** Die Ansichten `ansicht_a` bis `ansicht_c` sind
   synthetische Platzhalter. Werte aus dem referenzierten Kommentar und
   Quartalsregel vor der Abnahme mit dem Betreiber festlegen.
4. **Betriebsfreigabe:** Lizenzbedingungen, Gerätevertrauen, additive Rechte und
   konkurrierende Startwege prüfen; zunächst ausschließlich melden.

## Invarianten und alternative Wege: Suchnachweis

Repo-weit gesucht wurden Rezept-Code-Ausnahmen, Kennungs-/Annahmewege,
Ergebnis-/Log-/Dateiwege, Fokus/Programmwege sowie Rechte, Komposition und
alternative Startwege. Die folgenden Treffer nennen Datei und Zeile.
Der Bericht selbst ist wegen seiner Selbstverweise aus der Suche ausgenommen.
Generische Bau-/Wheel-Schreiboperationen und das Zahlungsrezept sind eigene
Abläufe; sie übernehmen keinen PVS-Ergebnis- oder Adapterweg. Unveränderte
Desktop-Vorlagen bleiben für die spätere Läufer-Anbindung maßgeblich.

### Rezept-Code und Katalog

Die Treffer sind Zeilenangaben, keine Behauptung einer geänderten Berechtigung.

- `README.de.md:30`
- `README.md:31`
- `REZEPT-FORMAT.md:32` · `REZEPT-FORMAT.md:45` · `REZEPT-FORMAT.md:101` · `REZEPT-FORMAT.md:102`
- `rezepte/pvs-desktop-rpa/README.md:30` · `rezepte/pvs-desktop-rpa/README.md:229` · `rezepte/pvs-desktop-rpa/README.md:230` · `rezepte/pvs-desktop-rpa/README.md:231` · `rezepte/pvs-desktop-rpa/README.md:244` · `rezepte/pvs-desktop-rpa/README.md:245`

### Ergebnis, Logs und Speicherorte

Die Treffer sind Zeilenangaben, keine Behauptung einer geänderten Berechtigung.

- `.github/workflows/python-bibliotheken.yml:68` · `.github/workflows/python-bibliotheken.yml:69` · `.github/workflows/python-bibliotheken.yml:70` · `.github/workflows/python-bibliotheken.yml:74` · `.github/workflows/python-bibliotheken.yml:88` · `.github/workflows/python-bibliotheken.yml:108` · `.github/workflows/python-bibliotheken.yml:116` · `.github/workflows/python-bibliotheken.yml:121` · `.github/workflows/python-bibliotheken.yml:132` · `.github/workflows/python-bibliotheken.yml:141`
- `.github/workflows/secret-scan.yml:32` · `.github/workflows/secret-scan.yml:36`
- `CONTRIBUTING.md:12`
- `rezepte/drehbuch-desktop-schritt/REZEPT.md:110` · `rezepte/drehbuch-desktop-schritt/REZEPT.md:115` · `rezepte/drehbuch-desktop-schritt/REZEPT.md:159` · `rezepte/drehbuch-desktop-schritt/REZEPT.md:161` · `rezepte/drehbuch-desktop-schritt/REZEPT.md:249` · `rezepte/drehbuch-desktop-schritt/REZEPT.md:250`
- `rezepte/pvs-desktop-rpa/README.md:156` · `rezepte/pvs-desktop-rpa/README.md:157` · `rezepte/pvs-desktop-rpa/README.md:161` · `rezepte/pvs-desktop-rpa/README.md:163` · `rezepte/pvs-desktop-rpa/README.md:165` · `rezepte/pvs-desktop-rpa/README.md:271` · `rezepte/pvs-desktop-rpa/README.md:299` · `rezepte/pvs-desktop-rpa/README.md:304` · `rezepte/pvs-desktop-rpa/README.md:307` · `rezepte/pvs-desktop-rpa/README.md:309`
- `rezepte/pvs-desktop-rpa/annahme.py:23`
- `rezepte/pvs-desktop-rpa/anweisung.md:42` · `rezepte/pvs-desktop-rpa/anweisung.md:48` · `rezepte/pvs-desktop-rpa/anweisung.md:49`
- `rezepte/pvs-desktop-rpa/pvs_rpa/adapter.py:6`
- `rezepte/pvs-desktop-rpa/pvs_rpa/codes.py:35`
- `rezepte/pvs-desktop-rpa/tests.py:360` · `rezepte/pvs-desktop-rpa/tests.py:405` · `rezepte/pvs-desktop-rpa/tests.py:415` · `rezepte/pvs-desktop-rpa/tests.py:454` · `rezepte/pvs-desktop-rpa/tests.py:500` · `rezepte/pvs-desktop-rpa/tests.py:513` · `rezepte/pvs-desktop-rpa/tests.py:515` · `rezepte/pvs-desktop-rpa/tests.py:526`
- `rezepte/python-bibliotheken-bauen/README.md:134` · `rezepte/python-bibliotheken-bauen/README.md:149` · `rezepte/python-bibliotheken-bauen/README.md:153` · `rezepte/python-bibliotheken-bauen/README.md:244` · `rezepte/python-bibliotheken-bauen/README.md:249` · `rezepte/python-bibliotheken-bauen/README.md:282`
- `rezepte/python-bibliotheken-bauen/bauen.py:13` · `rezepte/python-bibliotheken-bauen/bauen.py:246` · `rezepte/python-bibliotheken-bauen/bauen.py:247`
- `rezepte/python-bibliotheken-bauen/tests.py:12` · `rezepte/python-bibliotheken-bauen/tests.py:314` · `rezepte/python-bibliotheken-bauen/tests.py:315`

### Kennung, Annahme und Quartal

Die Treffer sind Zeilenangaben, keine Behauptung einer geänderten Berechtigung.

- `rezepte/pvs-desktop-rpa/README.md:36` · `rezepte/pvs-desktop-rpa/README.md:77` · `rezepte/pvs-desktop-rpa/README.md:79` · `rezepte/pvs-desktop-rpa/README.md:89` · `rezepte/pvs-desktop-rpa/README.md:91` · `rezepte/pvs-desktop-rpa/README.md:129` · `rezepte/pvs-desktop-rpa/README.md:179` · `rezepte/pvs-desktop-rpa/README.md:193` · `rezepte/pvs-desktop-rpa/README.md:194` · `rezepte/pvs-desktop-rpa/README.md:265` · `rezepte/pvs-desktop-rpa/README.md:266`
- `rezepte/pvs-desktop-rpa/anweisung.md:12` · `rezepte/pvs-desktop-rpa/anweisung.md:13` · `rezepte/pvs-desktop-rpa/anweisung.md:17` · `rezepte/pvs-desktop-rpa/anweisung.md:21`
- `rezepte/pvs-desktop-rpa/mutationen.py:16` · `rezepte/pvs-desktop-rpa/mutationen.py:21` · `rezepte/pvs-desktop-rpa/mutationen.py:22` · `rezepte/pvs-desktop-rpa/mutationen.py:44` · `rezepte/pvs-desktop-rpa/mutationen.py:45` · `rezepte/pvs-desktop-rpa/mutationen.py:93`
- `rezepte/pvs-desktop-rpa/pvs_rpa/adapter.py:85` · `rezepte/pvs-desktop-rpa/pvs_rpa/adapter.py:89` · `rezepte/pvs-desktop-rpa/pvs_rpa/adapter.py:93` · `rezepte/pvs-desktop-rpa/pvs_rpa/adapter.py:99`
- `rezepte/pvs-desktop-rpa/pvs_rpa/eingabe.py:20`
- `rezepte/pvs-desktop-rpa/pvs_rpa/kern_annahme.py:11` · `rezepte/pvs-desktop-rpa/pvs_rpa/kern_annahme.py:37` · `rezepte/pvs-desktop-rpa/pvs_rpa/kern_annahme.py:42` · `rezepte/pvs-desktop-rpa/pvs_rpa/kern_annahme.py:43` · `rezepte/pvs-desktop-rpa/pvs_rpa/kern_annahme.py:46` · `rezepte/pvs-desktop-rpa/pvs_rpa/kern_annahme.py:61` · `rezepte/pvs-desktop-rpa/pvs_rpa/kern_annahme.py:63` · `rezepte/pvs-desktop-rpa/pvs_rpa/kern_annahme.py:65`
- `rezepte/pvs-desktop-rpa/pvs_rpa/mock.py:15` · `rezepte/pvs-desktop-rpa/pvs_rpa/mock.py:61` · `rezepte/pvs-desktop-rpa/pvs_rpa/mock.py:65` · `rezepte/pvs-desktop-rpa/pvs_rpa/mock.py:77`
- `rezepte/pvs-desktop-rpa/tests.py:69` · `rezepte/pvs-desktop-rpa/tests.py:72` · `rezepte/pvs-desktop-rpa/tests.py:85` · `rezepte/pvs-desktop-rpa/tests.py:92` · `rezepte/pvs-desktop-rpa/tests.py:99` · `rezepte/pvs-desktop-rpa/tests.py:103` · `rezepte/pvs-desktop-rpa/tests.py:105` · `rezepte/pvs-desktop-rpa/tests.py:106` · `rezepte/pvs-desktop-rpa/tests.py:109` · `rezepte/pvs-desktop-rpa/tests.py:111` · `rezepte/pvs-desktop-rpa/tests.py:114` · `rezepte/pvs-desktop-rpa/tests.py:118` · `rezepte/pvs-desktop-rpa/tests.py:122` · `rezepte/pvs-desktop-rpa/tests.py:129` · `rezepte/pvs-desktop-rpa/tests.py:132` · `rezepte/pvs-desktop-rpa/tests.py:136` · `rezepte/pvs-desktop-rpa/tests.py:139` · `rezepte/pvs-desktop-rpa/tests.py:142` · `rezepte/pvs-desktop-rpa/tests.py:145` · `rezepte/pvs-desktop-rpa/tests.py:159` · `rezepte/pvs-desktop-rpa/tests.py:173` · `rezepte/pvs-desktop-rpa/tests.py:179` · `rezepte/pvs-desktop-rpa/tests.py:184` · `rezepte/pvs-desktop-rpa/tests.py:190` · `rezepte/pvs-desktop-rpa/tests.py:197` · `rezepte/pvs-desktop-rpa/tests.py:201` · `rezepte/pvs-desktop-rpa/tests.py:205` · `rezepte/pvs-desktop-rpa/tests.py:212` · `rezepte/pvs-desktop-rpa/tests.py:220` · `rezepte/pvs-desktop-rpa/tests.py:224` · `rezepte/pvs-desktop-rpa/tests.py:235` · `rezepte/pvs-desktop-rpa/tests.py:246` · `rezepte/pvs-desktop-rpa/tests.py:431` · `rezepte/pvs-desktop-rpa/tests.py:443` · `rezepte/pvs-desktop-rpa/tests.py:444` · `rezepte/pvs-desktop-rpa/tests.py:456` · `rezepte/pvs-desktop-rpa/tests.py:493` · `rezepte/pvs-desktop-rpa/tests.py:535`

### Fokus, Programme, Monitore und Deadline

Die Treffer sind Zeilenangaben, keine Behauptung einer geänderten Berechtigung.

- `rezepte/pvs-desktop-rpa/README.md:54` · `rezepte/pvs-desktop-rpa/README.md:206`
- `rezepte/pvs-desktop-rpa/mutationen.py:68` · `rezepte/pvs-desktop-rpa/mutationen.py:85`
- `rezepte/pvs-desktop-rpa/pvs_rpa/adapter.py:16` · `rezepte/pvs-desktop-rpa/pvs_rpa/adapter.py:103` · `rezepte/pvs-desktop-rpa/pvs_rpa/adapter.py:107` · `rezepte/pvs-desktop-rpa/pvs_rpa/adapter.py:113` · `rezepte/pvs-desktop-rpa/pvs_rpa/adapter.py:117` · `rezepte/pvs-desktop-rpa/pvs_rpa/adapter.py:121`
- `rezepte/pvs-desktop-rpa/pvs_rpa/kern_ansicht.py:11`
- `rezepte/pvs-desktop-rpa/pvs_rpa/mock.py:24` · `rezepte/pvs-desktop-rpa/pvs_rpa/mock.py:36` · `rezepte/pvs-desktop-rpa/pvs_rpa/mock.py:90` · `rezepte/pvs-desktop-rpa/pvs_rpa/mock.py:94` · `rezepte/pvs-desktop-rpa/pvs_rpa/mock.py:96` · `rezepte/pvs-desktop-rpa/pvs_rpa/mock.py:100` · `rezepte/pvs-desktop-rpa/pvs_rpa/mock.py:108` · `rezepte/pvs-desktop-rpa/pvs_rpa/mock.py:113`
- `rezepte/pvs-desktop-rpa/tests.py:163` · `rezepte/pvs-desktop-rpa/tests.py:181` · `rezepte/pvs-desktop-rpa/tests.py:187` · `rezepte/pvs-desktop-rpa/tests.py:194` · `rezepte/pvs-desktop-rpa/tests.py:239` · `rezepte/pvs-desktop-rpa/tests.py:268` · `rezepte/pvs-desktop-rpa/tests.py:277` · `rezepte/pvs-desktop-rpa/tests.py:285` · `rezepte/pvs-desktop-rpa/tests.py:288` · `rezepte/pvs-desktop-rpa/tests.py:291` · `rezepte/pvs-desktop-rpa/tests.py:293` · `rezepte/pvs-desktop-rpa/tests.py:299` · `rezepte/pvs-desktop-rpa/tests.py:304` · `rezepte/pvs-desktop-rpa/tests.py:319` · `rezepte/pvs-desktop-rpa/tests.py:336`

### Rechte, Komposition und weitere Startwege

Die Treffer sind Zeilenangaben, keine Behauptung einer geänderten Berechtigung.

- `rezepte/drehbuch-desktop-schritt/REZEPT.md:106` · `rezepte/drehbuch-desktop-schritt/REZEPT.md:126` · `rezepte/drehbuch-desktop-schritt/REZEPT.md:127` · `rezepte/drehbuch-desktop-schritt/REZEPT.md:133` · `rezepte/drehbuch-desktop-schritt/REZEPT.md:137` · `rezepte/drehbuch-desktop-schritt/REZEPT.md:140` · `rezepte/drehbuch-desktop-schritt/REZEPT.md:150` · `rezepte/drehbuch-desktop-schritt/REZEPT.md:191` · `rezepte/drehbuch-desktop-schritt/REZEPT.md:227` · `rezepte/drehbuch-desktop-schritt/REZEPT.md:239`
- `rezepte/drehbuch-desktop-schritt/anweisung.md:25` · `rezepte/drehbuch-desktop-schritt/anweisung.md:48`
- `rezepte/pvs-desktop-rpa/README.md:179` · `rezepte/pvs-desktop-rpa/README.md:180` · `rezepte/pvs-desktop-rpa/README.md:184`
- `rezepte/pvs-desktop-rpa/annahme.py:8` · `rezepte/pvs-desktop-rpa/annahme.py:9` · `rezepte/pvs-desktop-rpa/annahme.py:10` · `rezepte/pvs-desktop-rpa/annahme.py:11` · `rezepte/pvs-desktop-rpa/annahme.py:14`
- `rezepte/pvs-desktop-rpa/ansicht.py:8` · `rezepte/pvs-desktop-rpa/ansicht.py:9` · `rezepte/pvs-desktop-rpa/ansicht.py:10` · `rezepte/pvs-desktop-rpa/ansicht.py:11` · `rezepte/pvs-desktop-rpa/ansicht.py:12` · `rezepte/pvs-desktop-rpa/ansicht.py:15`
- `rezepte/pvs-desktop-rpa/pvs_rpa/adapter.py:76` · `rezepte/pvs-desktop-rpa/pvs_rpa/adapter.py:112` · `rezepte/pvs-desktop-rpa/pvs_rpa/adapter.py:132`
- `rezepte/pvs-desktop-rpa/pvs_rpa/mock.py:10`
- `rezepte/pvs-desktop-rpa/tests.py:17` · `rezepte/pvs-desktop-rpa/tests.py:18` · `rezepte/pvs-desktop-rpa/tests.py:19` · `rezepte/pvs-desktop-rpa/tests.py:20` · `rezepte/pvs-desktop-rpa/tests.py:21` · `rezepte/pvs-desktop-rpa/tests.py:22` · `rezepte/pvs-desktop-rpa/tests.py:23`
