---
name: python-bibliotheken-bauen
titel: Python-Bibliotheken bequem als Wheels und Hash-Lock bauen
ziel: Der Betreiber nennt Pakete, der Build liefert geprüfte Wheels und ein Lock als Pull Request für Skript-Pins.
stufe: 2
stand: durchdacht
version: 0.1.0
jnpt_ab: "0.85.0"
muster: [skript-als-abnehmer]
integrationen: []
beisteller: [januaport-plugins/script-runner, januaport-plugins/desktop-runner]
---

# Python-Bibliotheken bequem bauen

## 0. Stand und Einordnung

**Durchdacht**, Stufe 2 „Gemeinsam bauen“, **im Bau** bis dieses Rezept gemergt
ist (#1230). Nicht release-blockierend. `jnpt_ab` benennt die dokumentierte
Gateway-Basis, keinen mit diesem Rezept belegten Anlagenlauf. Der Status bleibt
auch nach einem erfolgreichen lokalen Build durchdacht: Erst der Anlagenbeleg
rechtfertigt **erprobt**. Für Desktop-Pins ist dieser Weg durchdacht, nicht belegt.

Das Muster `skript-als-abnehmer` (`wissen_get muster/skript-als-abnehmer`)
beschreibt Python als begrenzten Werkzeug-Abnehmer und die Freigabe durch einen
Menschen. Dieses Rezept bereitet dessen Bibliotheken beim Bauen vor. Wie bei
Amplify oder Lambda werden Abhängigkeiten beim Bau aufgelöst; ausgeliefert wird
das fertige Artefakt. Am Läufer ändert sich nichts.

Maßgeblicher Vertrag: [Python-Bibliotheken im Skript-Läufer](https://github.com/JanuaPort/januaport-plugins/blob/main/script-runner/README.md#python-bibliotheken-wheels-im-repository).
Die Prüfregeln aus #1041 gelten unverändert. Das Rezept ist ein offener Beitrag
unter Apache 2.0; die gewählten Pakete haben eigene Lizenzen.

## 1. Ziel und Passung

Der Betreiber schreibt beispielsweise nur `pandas` in `requirements.in`; der
Build erzeugt `requirements.lock` und `wheels/*.whl` im selben Skriptordner.

Passt für öffentliche Pakete von PyPI, Python 3.12, Linux/manylinux x86_64 oder
Windows/amd64 für Desktop-Pins. Linux und Windows bekommen getrennte Skriptordner,
weil sie unterschiedliche Auflösungen, Locks und Wheels haben können.
Private Indizes, arm64, musllinux und andere Python-Versionen sind außerhalb
dieses Rezepts. Die Paketauswahl bleibt eine Betreiberentscheidung.

```text
auswertung/
  requirements.in        # vom Betreiber: pandas
  requirements.lock      # gebaut, pip-Format mit SHA-256
  wheels/                # gebaut, genau ein Wheel je Lock-Eintrag
  jnpt-script.yaml       # separat: requirements: requirements.lock
  main.py                # separat: das eigentliche Skript
```

`beispiel/requirements.in` ist eine Baueingabe mit `pandas`, noch kein pinbares
Skript. Manifest und Fachlogik ergänzt der Betreiber in seinem Repository.

## 2. Rollen

| Wer | Tut | Tut ausdrücklich nicht |
|---|---|---|
| Mensch | wählt Pakete, prüft Lizenzen und PR, mergt, pinnt danach | ein Build-Ergebnis als Herkunftsbeweis behandeln |
| KI | unterstützt Paketwahl, Build und Fehlerklärung | automatisch pinnen |
| Build (Action oder lokales Skript) | löst auf, lädt, prüft, bereitet Artefakte vor | am Läufer installieren |
| JanuaPort und Läufer | prüfen den menschlich freigegebenen Pin nach ihrem Vertrag | pip oder Netz beim Pinnen bereitstellen |

Es gibt keinen Geld-Schritt. Der Build hat keinen JanuaPort-Zugang.

## 3. Bausteine

Keine Integration und keine Kartei-Satzart. Baulogik:
[`bauen.sh`](bauen.sh) ruft [`bauen.py`](bauen.py) mit Standardbibliothek auf.
Python ab 3.10 wird für die lokalen Prüfungen gebraucht. Für den Download nutzt
uv eine isolierte Python-3.12-Umgebung mit `pip==26.0.1`. Fehlendes Python 3.12
kann uv auf dem **Baurechner** nachladen.

| Schritt | Eingabe | Ausgabe / Invariante |
|---|---|---|
| Vorprüfung | requirements.in | ein Paket je Zeile; Name mit optionalem Versionsbereich; Kommentare und Leerzeilen erlaubt |
| Auflösen | uv **0.11.3**, PyPI | Python 3.12, Linux `x86_64-manylinux_2_28` bzw. Windows `x86_64-pc-windows-msvc`, Hashes |
| Laden | pip download | `--only-binary=:all: --require-hashes --no-deps`, Implementierung `cp`, Python 3.12 |
| Prüfen / verdichten | Lock und Wheels | genau ein Wheel je Eintrag, richtige Version und SHA-256; Pin-Lock enthält die Hashes der gelieferten Wheels |
| Gegenprobe | verdichtetes Lock | zweiter Download ohne pip-Cache in leeres Verzeichnis, identische Dateinamen und SHA-256 |
| Veröffentlichen | geprüfte Artefakte | lokales Skript ersetzt die Ausgabe; Action erzeugt einen Commit auf einem neuen PR-Zweig |

Die Auflösung entspricht:

```sh
uv pip compile requirements.in --python-version 3.12 \
  --python-platform x86_64-manylinux_2_28 --generate-hashes -o requirements.lock
```

Zusätzlich setzt das Skript explizit PyPI, deaktiviert Konfigurationssuche,
Quell-Builds und Projektquellen und entfernt Index-/pip-/Python-Umgebungsoptionen
aus den Unterprozessen. Eingabeoptionen wie `--index-url`, Includes, URLs,
Extras und Marker werden vor dem Netzaufruf abgewiesen. Der Auflöser wertet
transitive Plattformmarker für das Ziel aus; das Pin-Lock enthält keine Marker.

**Plattformgrenzen:** Das Rezept wählt bewusst eine Teilmenge der Läufer-Tags:
`cp312` mit ABI `cp312`, `abi3` oder `none` auf manylinux x86_64 bis glibc 2.41,
oder `py3-none-any`. Komprimierte Tags wie `py2.py3-none-any` enthalten ein
passendes Tag und sind zulässig. Windows erlaubt entsprechend `cp312` auf
`win_amd64` sowie reine Python-Wheels. Ältere CPython-abi3-Tags, die der lokale
Läufer teilweise ebenfalls akzeptiert, sind außerhalb dieses Build-Rezepts.

Die Linux-Auflösung ist auf glibc 2.28 ausgerichtet; pip bekommt explizit alle
PEP-600-Plattformen von 2.28 bis 2.5 und die alten manylinux-Aliasse. pip leitet
diese bei `--platform` nicht automatisch ab. Die lokale Tag-Prüfung lässt bis
2.41 zu, der reguläre Build fordert höchstens 2.28 an. Damit verspricht das Rezept
nicht, jedes auf dem Läufer mögliche Paket aufzulösen.

Die Grenzprüfung zählt die tatsächlich gelesenen ZIP-Bytes ohne Installation:
höchstens **300 MiB und 30 000 Dateien je Lock**, gegenseitige Vollständigkeit,
keine sdist, keine abweichenden Hashes. Zusätzlich werden Pfadausbrüche,
Symlinks/Sonderdateien und doppelte Pfade geprüft. Die vollständige gehärtete
Entpackprüfung des Läufers und dessen anlagenweite 2-GiB-Grenze bleiben dort.
Windows-Pfade, Wheel-SHA-256 und Allowlist prüft der Desktop-Läufer selbst.

## 4. Zugänge und Rechte

| Abnehmer | Zugang / Besitzer | Rechte |
|---|---|---|
| Build-Job | GITHUB_TOKEN des Betreiber-Repositories | `contents: read` |
| PR-Job | derselbe kurzlebige Token | nur hier `contents: write`, `pull-requests: write` |
| Lokaler Build | Betreiberkonto | PyPI lesen, Skriptordner schreiben |
| Pin-Freigabe | Mensch mit bestehendem Admin-Zugang | bisheriger Pin-Weg, separat vom Build |

Kein weiteres Secret. Der PR-Job pusht den Zweig und versucht dann, den PR
über `gh pr create` mit `GITHUB_TOKEN` zu öffnen. Dafür gibt es zwei Wege:

- **Automatischer PR:** Die Repository-Einstellung „Allow GitHub Actions to create
  and approve pull requests“ ist an. Viele Orgs oder Enterprises sperren sie, dann
  lässt sie sich im Repository nicht einschalten.
- **Compare-Link (Standard bei gesperrter Einstellung):** Scheitert `gh pr create`,
  bleibt der Zweig `wheels/<run_id>-<run_attempt>` stehen. Der Lauf bleibt grün,
  zeigt eine Warnung „PR nicht angelegt“ und schreibt in die Zusammenfassung einen
  Link „PR öffnen“ samt PR-Text. Ein Mensch legt den PR mit einem Klick an.
Ein wiederverwendbarer Aufrufer muss die beiden Schreibrechte erlauben; der
Build-Job reduziert sie ausdrücklich auf Lesen. Es gibt keinen zweiten
Veröffentlichungsweg per PAT, Deploy-Key oder direktem Commit auf main.

## 5. Ablauf

1. Mensch legt Paketnamen in `requirements.in` fest, z. B. `pandas` oder
   `pandas==3.0.*`; eine Zeile je Paket, Versionsbereiche sind erlaubt.
2. Workflow mit `ordner` und `ziel` starten; `ziel` ist standardmäßig `linux`,
   alternativ `windows`. Der Ordner ist relativ zum Repository ohne Punktsegmente
   oder Symlink-Anteile; je Segment Buchstaben/Zahlen/Unterstrich am Anfang,
   danach zusätzlich Bindestrich und Punkt.
3. Der lesende Job baut in einem temporären Ordner, prüft und lädt nur Lock und
   Wheels als kurzlebiges Workflow-Artefakt hoch. Die angeforderten Pakete werden
   nicht installiert.
4. Erst bei Erfolg lädt der PR-Job das Artefakt, prüft es erneut und legt einen
   neuen Zweig `wheels/<run_id>-<run_attempt>` an. Nur Lock und Wheels kommen in
   den Commit. Der PR zielt auf den beim Start gewählten Branch; die Eingabe und
   dessen Commit sind durch den Workflow-Snapshot gebunden.
5. Der PR-Text nennt Pakete, Versionen, Größe, Dateizahl und den Satz
   **„Herkunft ist PyPI, geprüft sind nur die Hashes“**. Der Betreiber prüft Auswahl,
   Schadpakete, Typosquatting und Lizenzen; Hashes belegen keine Herkunft.
6. Mensch mergt und pinnt anschließend den Commit auf dem Standard-Zweig wie
   bisher. Der Läufer arbeitet ohne pip und Netz; bis zur Vorbereitung der
   Bibliotheken steht der Pin auf `pending`.

**Ein Lauf zur Zeit:** Workflow-Concurrency serialisiert je Repository und
Skriptordner, auch bei unterschiedlichen Zielen. Lokale Betreiber starten je
Ordner nur einen Build. **Idempotenz:** Jeder Lauf löst die aktuelle passende
Paketmenge frisch auf. Für dieselben Wheels/Lock entsteht kein neuer Commit
oder PR; ein noch offener PR wird nicht automatisch wiederverwendet. Ohne
Versionsangaben kann ein späterer Lauf neuere Versionen liefern. Bei Build- oder
Prüffehlern vor der Veröffentlichung bleibt die bisherige Ausgabe erhalten;
das Ersetzen beider Ausgaben ist keine Dateisystemtransaktion.

## 6. Agenten-Anweisung

[`anweisung.md`](anweisung.md) in den Bau-Client übernehmen und `<ordner>` sowie
`<linux oder windows>` einsetzen. Paketwahl, PR-Review und Pin-Freigabe bleiben
beim Menschen. Der Läufer bekommt keine Build-Werkzeuge.

## 7. Aufbau-Handgriffe

| Wer / was | Wofür | Zuschnitt | Wann |
|---|---|---|---|
| Admin: Actions-PR-Erlaubnis (optional) | automatischer PR mit GITHUB_TOKEN; ohne sie Compare-Link | nur Betreiber-Repository | vor erstem Workflow |
| Betreiber: requirements.in | Paketauswahl | öffentlicher PyPI-Name, optional Version | vor Build |
| Betreiber: Manifest/Skript | späterer Pin | `requirements: requirements.lock` | vor Freigabe |
| Bauer: Workflow oder uv lokal | Artefakte erzeugen | Ordner und Ziel | nach Paketwahl |
| Mensch: PR und Pin prüfen | Freigabe | Merge in Standard-Zweig, danach Pin | nach Gegenprobe |

**Ohne GitHub**, unter Linux oder WSL mit uv 0.11.3 und Python ab 3.10, aus
dem ausgecheckten Rezept-Repository (Zielordner darf außerhalb liegen):

```sh
bash rezepte/python-bibliotheken-bauen/bauen.sh /pfad/zum/skript linux
# Windows-Artefakte, ebenfalls vom Linux-/WSL-Baurechner aus:
bash rezepte/python-bibliotheken-bauen/bauen.sh /pfad/zum/desktop-skript windows
# Vorhandene Artefakte ausschließlich offline prüfen:
bash rezepte/python-bibliotheken-bauen/bauen.sh --pruefen /pfad/zum/skript linux
```

**GitHub:** [`python-bibliotheken.yml`](../../.github/workflows/python-bibliotheken.yml)
unter Actions manuell starten (`workflow_dispatch`) oder als wiederverwendbaren
Workflow (`workflow_call`) aufrufen. Nach Veröffentlichung den geprüften vollen
Commit statt `<REZEPT-COMMIT>` einsetzen:

```yaml
jobs:
  bibliotheken:
    permissions:
      contents: write
      pull-requests: write
    uses: JanuaPort/januaport-recipes/.github/workflows/python-bibliotheken.yml@<REZEPT-COMMIT>
    with:
      ordner: skripte/auswertung
      ziel: linux
```

Der Workflow checkt das Betreiber-Repository und separat eine fest gepinnte
Fassung der Baulogik aus. Actions haben SHA-Pins mit Versionskommentar,
uv und pip feste Versionen. Änderungen der Baulogik verlangen ein Update ihres
Commit-Pins im Workflow. Der Lauf braucht Netz nur beim Bauen und für GitHub.

Das README des Skript-Läufers (`januaport-plugins/script-runner/README.md`,
Abschnitt „Lock bauen“) verweist auf dieses Rezept. Dieses Rezept ändert dort
weder Code noch Prüfregeln.

## 8. Fehlerfälle

| Fall | Erkennung | Verhalten / wer löst |
|---|---|---|
| Paket nur als sdist / kein passendes Wheel | uv oder pip findet kein Binary | „Paket X hat kein Wheel für Python 3.12/manylinux. Andere Version wählen oder weglassen.“; Betreiber wählt neu (Windows meldet Windows/amd64) |
| Eingabeoption, URL oder privater Index | lokale Eingabeprüfung | Abbruch vor Auflösung; Betreiber korrigiert |
| Lock-/Tag-/Hash-Abweichung, fehlendes oder zusätzliches Wheel | lokale Prüfung bzw. Gegenprobe | Abbruch; Betreiber prüft Paket/Version und baut neu |
| Größe oder Dateizahl überschritten | ZIP-Inhalt gelesen | Abbruch; Paketmenge verkleinern |
| uv-Version anders | Versionsprüfung | uv 0.11.3 bereitstellen |
| PyPI/GitHub nicht erreichbar | Unterprozessfehler | Lauf gescheitert, nach Klärung erneut starten |
| Token darf keinen PR öffnen | gh-Schritt | Warnung „PR nicht angelegt“, Lauf bleibt grün; Mensch öffnet den PR über den Link in der Zusammenfassung |
| Zweig lässt sich nicht pushen | git-push-Schritt | Lauf rot; Admin prüft `contents: write` des Aufrufers |
| Pin bleibt pending / ungültig | Pin-Liste des Läufers | Admin prüft Grund nach Läufer-README, keine Nachinstallation |

## 9. Prüfsteine

- [ ] `bash rezepte/python-bibliotheken-bauen/test.sh`: Offline-Fixtures für gültige
  Tags, falsche Python-Fassung, musllinux, glibc 2.42, arm64, sdist, Lock ↔ Wheels,
  Hashabweichungen, Größen-/Dateigrenze, unzulässige Eingaben und Git-PR-Zweig.
- [ ] Mutationsproben entfernen jede geprüfte Sperre in einer temporären Kopie;
  die zugehörige Verbotsassertion wird rot, unveränderte Fassung wieder grün.
- [ ] shellcheck für Shell-Dateien, actionlint für Workflow.
- [ ] Echter pandas-Build im Rezept-Repository per Action: PR (dort per
  Compare-Link, die Org sperrt Actions-PRs) und Gegenprobe grün;
  Wheels ausschließlich im temporären Test-PR, nicht in den Rezeptkatalog mergen.
- [ ] Echter sdist-Negativlauf mit verständlicher Meldung.
- [ ] Nach Merge: Abnahme am Showcase, Pin eines so gebauten Skriptordners
  freigeben; `pending` → bereit. Erst dann Stufenweg „gebaut“ und Rezept „erprobt“.
- [ ] Separater Desktop-Beleg: bis dahin Windows ausdrücklich durchdacht.

Lokale Messungen und Suchtreffer stehen im Umsetzungsbericht. Ein lokaler
pandas-Lauf ersetzt weder einen Action-Lauf mit PR noch den Anlagenbeleg.

## 10. Grenzen

Kein Build-Dienst im Kern, privater Index, arm64, musllinux, andere Python-Version
oder automatisches Pinnen. Die Action wird nur manuell bzw. von einem autorisierten
Workflow aufgerufen. Der Build ist keine Herkunfts-, Schadcode- oder Lizenzprüfung.
Die Hash-Pflicht bindet die ausgewählten Bytes an das Lock, der menschliche Pin an
den Commit. Auch ein korrekt gehashtes Paket kann schädlich sein.

Das Rezept installiert keine Wheels und führt keinen Code aus den angeforderten
Paketen aus. Seine lokale
Prüfung ersetzt die Prüfung des Läufers nicht: vollständige Archivhärtung,
anlagenweiter Platz und bei Desktop-Pins Windows-Pfade/Allowlist bleiben dort.
Große Betreiber-Wheels können GitHub-Datei-/Repository-Grenzen erreichen; dafür
liefert dieses Rezept keine andere Artefaktablage. Der Desktop-Paketabruf hat
zusätzliche Grenzen im Läufervertrag.

## 11. Datenschutz

Eingabe, Lock, Wheels und PR enthalten öffentliche Paketnamen und Versionen.
Es gibt keine Kundendaten, Betreiberwerte oder Zugangsdaten im Beispiel.
Private Pakete und Indizes gehören außerhalb dieses Rezepts. Build-Logs können
öffentliche Paketnamen und Fehlermeldungen enthalten. Kein roher fachlicher
Eingang im Chat; Berichte beschränken sich auf Pakete, Versionen und Zähler.

Temporäre Build- und Testordner werden beim normalen Ende entfernt; Workflow-
Artefakte laufen nach einem Tag ab. Alte Ausgaben ersetzt ein erfolgreicher
Build, die Historie bleibt im Betreiber-Repository. Der Betreiber bestimmt
dessen Sichtbarkeit. Der Läufer räumt unbenutzte Bibliotheks-Locks nach seinem
Vertrag auf; dieses Rezept greift dort nicht ein.
