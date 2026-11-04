# App-Rezepte prüfen

Vom Repository-Root mit Python 3 und der Go-Version des Kern-Moduls:

```text
python pruefung/app-rezepte/check.py --core <KERN_CHECKOUT> --mutations
```

Der Kern-Checkout wird nur gelesen. Ein temporäres Go-Modul unter dem
ignorierten `.arbeit/` importiert den echten Kern über `replace`. Quellregeln
und `ParseManifest` stehen als Prüfungen vor den Apps; der erste Lauf mit
fehlenden App-Ordnern war erwartungsgemäß rot. Die App-Quellen brauchen weder
Build noch Bibliotheken. Der Pakethelfer verwendet ausschließlich Python-Standardmodule.

Optional prüft ein echter Headless-Chromium/Edge die Oberfläche und den
HTTP-Aufrufweg. Dazu Node.js 22 und `RECIPE_BROWSER` als Pfad zum Browser setzen:

```text
python pruefung/app-rezepte/check.py --core <KERN_CHECKOUT> --mutations --browser
```

Der Browsertest verwendet synthetische MCP-Antworten eines lokalen HTTP-Servers.
Er ersetzt weder SSO- noch Berechtigungsprüfungen auf einer laufenden Anlage.
Der Importtest verwendet den **echten SQLite-Adapter**, keine Store-Mocks.

Prüflauf vom 04.11.2026: beide Apps bestehen Lade-Regel, Manifestprüfung nach
Zielbindung und Import als gestoppte Fassung. Steuer-App: 5 Dateien, 6782 Bytes,
TAR 20480 Bytes. Monitor-App: 5 Dateien, 5175 Bytes, TAR 10240 Bytes.
Alle 34 Mutationsproben wurden erkannt; anschließend liefen Quell-, Paket-,
Kern- und Browserprüfung wieder grün. Der Namens-Grep über den gesamten
Änderungsdiff ergab keine Treffer. Ein Anlagenbeleg steht weiterhin aus.

## Prüfumfang

| Prüfung | Nachweis |
|---|---|
| Beide Quellbäume | echte `skriptspeicher.PruefeAppDateien`; `ParseManifest` nach Zielbindung; echtes `pack.py`-TAR durch `PruefeRezept` und `ImportRecipe` |
| Budget, Dateizahl, Pfad, Dateimodus, Geheimnismuster, ausführbare Binär-Magic | `TestLoadReject`, teilweise zusätzlich `TestImportReject` und `TestArchiveReject` mit SQLite |
| Geschlossenes Manifest, EOF, 8 KiB, Trägerpflicht | `TestManifestReject`, `TestBindingAndExport` |
| Admin-Herkunft und Ausschluss eines App-Trägers | `TestImportReject`, Import mit tatsächlichem SQLite-Store |
| Import bleibt gestoppt, auch Wiederimport einer Live-App | `TestImportStopped`, für CLI-/REST-/Admin-MCP-Herkunft; `TestExamples` |
| Neue Bindung, leere Exportbindung, deterministischer Export | `TestBindingAndExport` |
| Links, Duplikate, Pfadausbruch, Mengenüberschreitung | `TestArchiveReject`, tatsächlich verbotene TARs an `ImportRecipe` |
| Inline-Script, Ereignisattribute, JavaScript-URL, PNG/ICO, NUL, ungültiges UTF-8 | zusätzliche echte Quellprüfung in `policy.py` mit Negativfällen in `test_policy.py` |
| Bestätigung, Abbrechen, Einfachversand, fehlende Deckung, Abweisung, Lesen, Textausgabe | `browser.mjs` im echten Browser; erwartete HTTP-Werkzeugnamen und Argumente werden verglichen |

Die Mutationsproben entfernen jede getestete Sperre in temporären Kopien oder
Go-Overlays, verlangen einen **roten Test** und prüfen zum Schluss wieder den
unveränderten Stand grün. Kompilierfehler gelten nicht als erfolgreiche Probe.
Bei Geheimnissen werden beide Speicherprüfungen gemeinsam deaktiviert; bei der
Trägerpflicht Importprüfung und Manifestprüfung. Für die Admin-Zulassung wird
die gemeinsame Herkunftsentscheidung von Import und Registrierung mutiert.
Die Kern-Dateien bleiben dabei unverändert.

Die Browser-Mutationen lösen einen Schreibaufruf vor Bestätigung aus, heben die
Deckungssperre auf, führen Antworttext als HTML aus, ersetzen das Monitor-Lesen
durch einen Schreiber und versenden denselben Schreibauftrag zweimal. Jede
dieser Änderungen muss den Browsertest rot machen.

## Offene Punkte im Kern

1. **Inline-Script-Prüfung fehlt im Austauschweg.** Der Kern hat sie in diesem
   Austauschumfang ausdrücklich ausgenommen. Die Beispiele liefern externe
   `.js`-Dateien; die zusätzliche Quellprüfung hält die Rezeptregel ein.
   Der Import selbst ist deshalb kein allgemeiner Nachweis gegen Inline-Scripts.
2. **Binärregel ist enger als die Rezeptregel.** Der Kern sperrt ausführbare
   MZ-/ELF-Magic; PNG und ICO werden nicht allgemein abgewiesen. Die zusätzliche
   Textquellenprüfung weist sie ab. `TestCoreGaps` belegt den aktuellen Stand.
3. **Offene Punkte sind kein vollständiger Betriebscheck.** Der Import prüft
   Werkzeugnamen, Pin-Namen und leere Teams, aber keine vollständige Trägerdeckung,
   inhaltliche Pinbindung oder Browser-Infrastruktur. Auch vorhandene Pins bleiben
   ausdrücklich zu prüfen. Das Rezept vergibt dafür keine Ersatzrechte.
4. **Modus a braucht den neuen Träger schon beim Import.** Das exportierte
   Manifest ohne `token_id` ist absichtlich nicht für sich allein durch
   `ParseManifest` ladbar. Erst der Import bindet die neue ID. Kein Platzhalter
   wird als produktive ID in den Quellen hinterlegt.

Die Einrichtung von Träger, Teams, passenden Pins, Browser-Apphost und SSO sowie
das ausdrückliche Live-Schalten und der Anlagenbeleg bleiben Betreiberaufgaben.
Ein App-spezifisches Muster ist in den gelesenen Kernstellen nicht beschrieben;
die Musterlisten der Beispiele sind daher leer.

## Suchstellen für Invarianten und weitere Wege

Repo-weite Suche nach App-Rezept, Betriebsrezept, eigenem Code, Rezeptarten und
den Mengen-/Importregeln ergab die folgenden relevanten Stellen. Die generelle
Code-Ausnahme in §5 wurde neben dem neuen Formatabschnitt angepasst; die
produktbezogenen Integrations-Spec-Regeln bleiben unverändert.

| Ort | Bedeutung |
|---|---|
| `REZEPT-FORMAT.md:32`, `:55`, `:172` | Betriebsrezept, App-Ausnahme und weitere Code-Ausnahme |
| `README.md:26`, `README.de.md:25` | Katalog und Import-Lebenszyklus in beiden Sprachen |
| `.gitattributes:9` | LF für App-Quellen, damit Checkout-Zeilenenden das TAR nicht verändern |
| `rezepte/steuer-app/REZEPT.md:57`, `rezepte/steuer-app/anweisung.md:1` | Träger, Import und Betreiberhandgriffe |
| `rezepte/monitor-app/REZEPT.md:51`, `rezepte/monitor-app/anweisung.md:1` | Personenmodus, Import und Betreiberhandgriffe |
| `pruefung/app-rezepte/policy.py:1`, `pack.py:1`, `check.py:1`, `core_test.go:1`, `browser.mjs:1` | Quell-, Paket-, Kern- und Browserprüfung |

Zusätzlich wurden im **nur gelesenen Kern** die anderen Zugangs- und
Kompositionswege geprüft:

| Kernstelle | Zusammenhang |
|---|---|
| `internal/apps/CLAUDE.md:3`, `internal/apps/recipe.go:46`, `:108`, `:197`, `:222` | Austausch, gemeinsamer Export/Import, CLI-Vorprüfung und offene Punkte |
| `internal/apps/recipe_archive.go:16`, `:49`, `:75` | TAR lesen/schreiben und neue Bindung |
| `internal/apps/service.go:130`, `internal/apps/model.go:33` | zusätzliche Registrierungssperre und gemeinsamer Manifestparser |
| `internal/appmanifest/manifest.go:31`, `internal/skriptspeicher/service.go:179`, `:207`, `internal/objektspeicher/validate.go:43` | geschlossener Parser und beide Inhaltsprüfungen |
| `cmd/jnpt/CLAUDE.md:5`, `cmd/jnpt/app_recipe.go:31`, `cmd/jnpt/app_recipe_cli.go:19` | gemeinsame Fassade, Herkunft und CLI |
| `internal/adminmcp/app_recipe.go:36`, `:48`, `internal/httpapi/app_recipe.go:20`, `internal/httpapi/server.go:790` | weitere administrative Adapter |
| `internal/appsession/grant.go:28`, `cmd/jnpt/run_control.go:185`, `internal/adminmcp/run_control.go:82` | Pinzulassung, Steuerungswrapper und Werkzeugnamen/-schemata |
| `cmd/jnpt/usecase_monitor_api.go:119`, `internal/usecasemonitor/monitor.go:237` | Lese-Werkzeug und kuratierte Antwortfelder |
| `docs/security-model.md:5525`, `:5625`, `:5729` | App-Rezepte, Browser-Sitzung und Steuer-Werkzeuge |

Kernänderungen gehören in den Kern; dieses Repository verändert keine dortige
Sperre und fügt keinen weiteren Berechtigungsweg hinzu.
