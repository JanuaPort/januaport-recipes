# Umsetzung und Prüfung #1230

Stand 28.10.2026: Rezept **durchdacht**, Stufe 2 **im Bau** bis zum Merge.
Kein Anlagenbeleg. Das Nachbar-Repository wurde ausschließlich gelesen.

Die Baulogik liegt in `bauen.py`, aufgerufen durch `bauen.sh`. Workflow und
lokaler Weg benutzen denselben Einstieg. `pr-vorbereiten.sh` bereitet nur den
lokalen PR-Commit vor. Der Workflow bindet die Baulogik an einen konkreten
Quellcommit; dafür sind Implementierung und Workflow-Pin separate Commits.
Die endgültigen Commit-Hashes stehen im Übergabebericht.

## Offline-Verifikation

Unter Ubuntu 22.04/WSL, Python 3.10:

```text
$ bash rezepte/python-bibliotheken-bauen/test.sh
OK: gültige Linux-/Windows-Wheels und 67 Negativproben am echten CLI.
OK: 39/39 Mutationsproben rot; unveränderte Fassung wieder grün.
SKIP uv-Version: uv nicht installiert (Offline-Prüfung bleibt verfügbar).
OK: private Index-/Python-Umgebungsoptionen am echten Kindprozess entfernt; Mutation rot.
OK: echter Git-Adapter committet nur den PR-Zweig und zwei Ausgabepfade; main-Versuch abgewiesen; Mutation rot.
```

Unter Windows/Git Bash mit `PYTHON=python` (Python 3.14, uv 0.11.3):

```text
OK: gültige Linux-/Windows-Wheels und 62 Negativproben am echten CLI.
OK: 35/35 Mutationsproben rot; unveränderte Fassung wieder grün.
OK: falsche uv-Version am echten uv abgewiesen; Mutation rot.
OK: private Index-/Python-Umgebungsoptionen am echten Kindprozess entfernt; Mutation rot.
OK: echter Git-Adapter committet nur den PR-Zweig und zwei Ausgabepfade; main-Versuch abgewiesen; Mutation rot.
```

Die fünf Symlink-Proben wurden unter Windows mangels Symlink-Recht übersprungen;
unter WSL liefen alle fünf. Zusammen sind alle 40 benannten Ablehnungsregeln
getestet und mutiert. Dazu kommen Mutationen der Umgebungsbereinigung und des
Git-Zweigwechsels. Es werden echte ZIPs, Dateien, Unterprozesse und lokale
Git-Repositories benutzt, keine Adapter-Mocks. Die Git-Probe kontrolliert auch
die genaue Liste der geänderten Dateien und einen zweiten Lauf ohne neuen Commit.

Mutationen entstehen als Quellkopien im temporären Testordner: je Regel wird
der Ablehnungszweig deaktiviert und dieselbe Verbotsassertion erneut ausgeführt.
Sie muss rot werden. Danach wird die unveränderte Kopie wieder geprüft; die
Arbeitsfassung bleibt unverändert. Bei Formatregeln kann die entfernte
Abweisung auch einen nachgelagerten Parserfehler auslösen; die Probe fordert
die konkrete Abweisung samt Regelkennung und erkennt auch diesen Verlust.
Eine frühe Windows-Mutationsfassung ließ eine unbekannte Option in den Build
fallen und löste dadurch einen Netz-Build aus. Diese Verzweigung wurde korrigiert;
nur die oben dokumentierten abschließenden Läufe zählen als Offline-Beleg.

shellcheck **0.10.0**: alle drei Shell-Dateien, Exit 0, keine Befunde.
actionlint **1.7.7** unter WSL: neuer Workflow, Exit 0, keine Befunde.
Das vorhandene Windows-actionlint hing; für den Beleg wurde die veröffentlichte
Linux-Fassung verwendet. `git diff --check`: sauber. Neue/geänderte Dateien: LF.

## Echte Netzläufe

`bauen.sh` wurde mit uv 0.11.3 auf dem Windows-Baurechner für beide Zielplattformen
ausgeführt. Eingabe jeweils ausschließlich `pandas`. Alle Pakete wurden nur
geladen, nicht installiert/importiert. Die zweiten Downloads mit Hash-Pflicht
und ohne pip-Cache lieferten identische Dateinamen und SHA-256.

| Ziel | Wheels gesamt | Entpackte Bytes | Dateien | Ergebnis |
|---|---:|---:|---:|---|
| Linux/manylinux x86_64 | 29 200 890 | 100 766 153 | 3 150 | grün |
| Windows/amd64 | 23 775 846 | 81 990 408 | 3 216 | grün |

Aufgelöst für beide Ziele: pandas 3.1.0, numpy 2.5.4, python-dateutil 3.0.0,
six 1.17.0, tzdata 2026.6. Die ZIPs wurden gelesen, kein Import auf einem Läufer
ausgeführt. Build-Ergebnisse liegen nur lokal in einem ignorierten Arbeitsordner;
keine gebauten Wheels oder Locks sind Bestandteil der Rezept-Commits.

Echter sdist-Negativfall `odfpy==1.4.1`, Linux, Exit 1:

```text
Abbruch: Paket odfpy hat kein Wheel für Python 3.12/manylinux. Andere Version wählen oder weglassen.
```

## Annahmen und offene Belege

- uv 0.11.3 unterstützt die verlangten `--python-platform`-Werte; die echten
  Auflösungen für beide Ziele liefen erfolgreich. Zusätzlich `--no-build`,
  `--no-sources`, keine Konfigurationssuche, explizites PyPI. Vor dem ersten
  pip-Download wird auch das rohe uv-Lock formal geprüft.
- pip 26.0.1 läuft über eine isolierte uv-Python-3.12-Umgebung. Für Linux werden
  alle manylinux-Tags bis zur Auflösungsbasis glibc 2.28 explizit übergeben;
  die Prüfung erlaubt bis 2.41. Reine `py2.py3-none-any`-Wheels passen über py3.
  Ältere CPython-abi3-Tags sind bewusst enger als beim Läufer ausgeschlossen.
- uv kann mehr als 64 Hashes für ein Paket ausgeben. Das Pin-Lock wird nach
  Prüfung auf die tatsächlich gelieferten Wheels verdichtet, dann erneut geladen.
- Windows wurde als Build-Ziel geprüft, einschließlich Hash-Gegenprobe. Kein
  Desktop-Pin wurde gestartet; Windows-Pfade und Allowlist bleiben Aufgaben
  des Desktop-Läufers. Der dokumentierte Stand bleibt durchdacht.
- Kein Action-Lauf, kein GitHub-PR, kein Push oder Dispatch durch den Implementierer.
  GitHub-Rechte und gh-PR-Eröffnung sind mit actionlint und Quellprüfung vorbereitet,
  noch nicht am GitHub-Adapter belegt. Der Auftraggeber führt den pandas-Action-Lauf
  samt temporärem PR und den sdist-Negativfall aus. Test-Wheels nicht in den Katalog
  mergen. Danach Merge des Rezepts und separate Anlagenabnahme (`pending` → bereit).
- Der Verweis unter „Lock bauen“ liegt als `laeufer-readme.patch` vor;
  `git apply --check` gegen die gelesene Nachbarfassung war grün. Er ist dort
  noch nicht angewendet, weil Änderungen ausschließlich in diesem Worktree
  autorisiert sind. Vollständige Archivhärtung und anlagenweite 2-GiB-Grenze
  verbleiben unverändert im Läufer.

## Invarianten und weitere Wege: Suchtreffer

Repo-weit gesucht nach `Bibliotheken|Wheels|Lock|Skripte|Beisteller|Mehr Dateien`,
danach nach `300|30.000|cp312|py3|2\.41|require-hashes|only-binary|no-deps`,
sowie nach Workflow-Einstiegen, Schreibrechten, Veröffentlichungs- und Pin-Wegen.
Die folgenden Stellen sind die maßgeblichen Treffer (Pfad relativ zum Rezept-Repo;
bei `../januaport-plugins` nur gelesen). Bestehende fachfremde Kartei-„Locks“ in
`zahlungseingang` betreffen keine Python-Bibliotheken und bleiben unverändert.

| Invariante / weiterer Weg | Datei:Zeile |
|---|---|
| Katalog Englisch / Deutsch, ehrlicher Stand | `README.md:31`, `README.de.md:30` |
| Bisheriges Dateiformat, gezielte Build-Ausnahme, Code-Verweis | `REZEPT-FORMAT.md:32`, `REZEPT-FORMAT.md:37`, `REZEPT-FORMAT.md:91` |
| Zweiter Einsatzweg Desktop-Paket / manuelle Bereitstellung | `rezepte/drehbuch-desktop-schritt/REZEPT.md:105`, `rezepte/drehbuch-desktop-schritt/REZEPT.md:198`, `rezepte/drehbuch-desktop-schritt/REZEPT.md:200` |
| Neuer Status, Plattformen, Grenzen | `rezepte/python-bibliotheken-bauen/README.md:18`, `rezepte/python-bibliotheken-bauen/README.md:98`, `rezepte/python-bibliotheken-bauen/README.md:111` |
| Rechte, nur PR, Herkunft, menschliches Pinnen, lokaler Weg | `rezepte/python-bibliotheken-bauen/README.md:119`, `rezepte/python-bibliotheken-bauen/README.md:134`, `rezepte/python-bibliotheken-bauen/README.md:180`, `rezepte/python-bibliotheken-bauen/anweisung.md:8` |
| Gemeinsamer Einstieg, kein zweiter Build-Adapter | `rezepte/python-bibliotheken-bauen/bauen.sh:6`, `.github/workflows/python-bibliotheken.yml:63` |
| Eingabe / Ausgabe / eigener PR-Zweig | `rezepte/python-bibliotheken-bauen/bauen.py:38`, `rezepte/python-bibliotheken-bauen/bauen.py:48`, `rezepte/python-bibliotheken-bauen/bauen.py:52`, `rezepte/python-bibliotheken-bauen/bauen.py:62` |
| Lock-Format, Tags, Vollständigkeit, Hash, entpackte Grenzen | `rezepte/python-bibliotheken-bauen/bauen.py:82`, `rezepte/python-bibliotheken-bauen/bauen.py:115`, `rezepte/python-bibliotheken-bauen/bauen.py:153` |
| Verdichten, Gegenprobe, Herkunftsbericht | `rezepte/python-bibliotheken-bauen/bauen.py:192`, `rezepte/python-bibliotheken-bauen/bauen.py:201`, `rezepte/python-bibliotheken-bauen/bauen.py:210` |
| Bereinigte Umgebung, gepinnte Werkzeuge, beide Downloads | `rezepte/python-bibliotheken-bauen/bauen.py:221`, `rezepte/python-bibliotheken-bauen/bauen.py:241` |
| Einziger Commit-Adapter, Zweig vor Commit, enge Dateiliste | `rezepte/python-bibliotheken-bauen/pr-vorbereiten.sh:9`, `rezepte/python-bibliotheken-bauen/pr-vorbereiten.sh:12`, `rezepte/python-bibliotheken-bauen/pr-vorbereiten.sh:18` |
| Beide Workflow-Einstiege / Serialisierung | `.github/workflows/python-bibliotheken.yml:4`, `.github/workflows/python-bibliotheken.yml:14`, `.github/workflows/python-bibliotheken.yml:31` |
| Lesender Build / einziger schreibender Job / Veröffentlichung | `.github/workflows/python-bibliotheken.yml:43`, `.github/workflows/python-bibliotheken.yml:83`, `.github/workflows/python-bibliotheken.yml:127` |
| Wheels/Lock nicht im Katalog | `.gitignore:2`, `REZEPT-FORMAT.md:41` |
| Offline-Adapter, Negativfälle, Mutationen, echter Git-Adapter | `rezepte/python-bibliotheken-bauen/tests.py:38`, `rezepte/python-bibliotheken-bauen/tests.py:51`, `rezepte/python-bibliotheken-bauen/tests.py:215`, `rezepte/python-bibliotheken-bauen/tests.py:272` |
| Läufer-Grenzen, Lock bauen, Fehlerklassen, Lieferkette | `../januaport-plugins/script-runner/README.md:88`, `../januaport-plugins/script-runner/README.md:170`, `../januaport-plugins/script-runner/README.md:194`, `../januaport-plugins/script-runner/README.md:206` |
| Vorbereiteter Rückverweis statt Nachbaränderung | `rezepte/python-bibliotheken-bauen/laeufer-readme.patch:6` |

Weitere Identitäts-/Pin-/Berechtigungsadapter gibt es im neuen Build-Code nicht.
Die unveränderten Läuferverträge sind Referenzen, keine hier neu implementierten
Sperren. Deren Laufzeitbeleg und die Rechteprüfung bei GitHub stehen ausdrücklich aus.
