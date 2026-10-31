---
name: pvs-desktop-rpa
titel: Zwei Abläufe im Praxisverwaltungssystem (PVS) über den Desktop-Läufer vorbereiten
ziel: Ein Skript prüft Kartenanmeldungen und richtet zwei Detailprogramme ein, im Vorbau ausschließlich mit synthetischen Daten.
stufe: 2
stand: durchdacht
version: 0.1.0
jnpt_ab: "0.85.0"
muster: [arbeitsliste-rpa, skript-als-abnehmer]
integrationen: []
beisteller: [januaport-plugins/desktop-runner]
---

# RPA für ein Praxisverwaltungssystem (PVS) über den Desktop-Läufer

## 0. Stand und Einordnung

**Durchdacht**, Stufe 2 „Gemeinsam bauen“. Vorbau zu #1239, #1241 und #1242:
ausführbarer Python-Fachkern, semantischer Adapter-Vertrag und Offline-Tests.
Kein Anlagenlauf, keine echte Oberfläche angebunden. Lokale Tests begründen
keinen Stand `erprobt`. Ausschließlich Standardbibliothek, Python ab 3.10.

Das Muster `arbeitsliste-rpa` verbindet Auftrag, eindeutige Identität und
sichtbare Wirkung. `skript-als-abnehmer` begrenzt die Aufgaben eines Skripts
und beschreibt die Freigabe durch den Menschen. Beide sind als
`wissen_get muster/<name>` abrufbar.

Vorlage für Paket, Start und Rechte:
[`drehbuch-desktop-schritt`](../drehbuch-desktop-schritt/REZEPT.md).
Der Quellcode hier ist die Skript-Rezept-Ausnahme aus
[`REZEPT-FORMAT.md` §2](../../REZEPT-FORMAT.md#2-aufbau-im-repository).

## 1. Ziel und Passung

**UC1 Annahme am Empfang:** Ein Minutentakt prüft neue Kartenanmeldungen.
Eindeutige Fälle können angenommen werden; Vorgabe ist `nur_melden=true`.
**UC2 Monitor-Ansichten:** Ein Menüklick wählt ein Setup für den gerade im PVS
offenen Patienten. Zwei bereits laufende Detailprogramme erhalten die passende
Kennung, einen Monitor und eine feste Ansicht.

Passt, wenn der spätere Adapter die eindeutige Kennung, vollständige Fakten
und die Wirkung sicher aus der Oberfläche lesen kann. Bei Namen als einzigem
Identitätsmerkmal, unklaren Dialogen oder unvollständigen Fenstern bleibt der
Fall liegen. Der Vorbau eignet sich für Entwicklung und Offline-Abnahme mit
dem Mock; der Betrieb verlangt die gesonderte Adapter- und Anlagen-Abnahme.

## 2. Rollen

| Wer | Tut | Tut ausdrücklich nicht |
|---|---|---|
| Mensch/Betreiber | legt Quartalsregel, Setups, Rechte und Pin fest; klärt liegen gebliebene Fälle | einen Testlauf als Betriebsfreigabe behandeln |
| KI | hilft beim Aufbau; sieht ausschließlich Codes und Zähler | Patientendaten entgegennehmen oder Identitäten erraten |
| Fachkern | bewertet Fakten, dedupliziert Kennungen, hält bei Unklarheit an | Namen vergleichen oder UI selbst bedienen |
| Adapter | liest nach Kennung; prüft unmittelbar vor der Wirkung nochmals | anmelden, Dialoge wegklicken, Programme starten oder zweite Instanzen öffnen |
| JanuaPort/Desktop-Läufer | pinnt, startet und serialisiert gemäß eigenem Vertrag | fachliche Klickwirkung aus technischem Laufende ableiten |

Es gibt keinen Geld-Schritt. Lizenzfreigabe und Betriebsfreigabe liegen beim Betreiber.

## 3. Bausteine

| Datei | Aufgabe |
|---|---|
| `pvs_rpa/kern_annahme.py` | reine UC1-Logik, keine UI-Bibliothek |
| `pvs_rpa/kern_ansicht.py` | reine UC2-Logik, unveränderliche Setup-Tabelle |
| `pvs_rpa/adapter.py` | Protocols für PVS und Detailprogramme, typisierte Fakten und Zustandssignale |
| `pvs_rpa/mock.py` | synthetischer Speicherzustand mit virtueller monotoner Uhr |
| `pvs_rpa/codes.py` | geschlossene Codes und letzte JSON-Ausgabesperre |
| `pvs_rpa/eingabe.py` | strikte JSON-Eingabe, auch doppelte Schlüssel werden abgewiesen |
| `annahme.py`, `ansicht.py` | ausführbare JSON-Einstiege und `ergebnis_abgeben` |
| `tests.py`, `test.sh`, `mutationen.py` | Offline-Vertrags-, Verbots- und serielle Mutationsproben |

Keine Integration, keine Kartei-Satzart, kein zusätzlicher Beisteller. Ein
Adapter erhält für jede Methode dieselbe absolute monotone Deadline: **5 Sekunden
für den ganzen Lauf**. Er muss auch eigene UI-Warteoperationen begrenzen; der
Fachkern kann einen blockierenden Fremdadapter nicht unterbrechen. Ein einzelner halb
geladener Eintrag wartet höchstens 1 Sekunde, damit die übrigen noch drankommen.
**Offen für Sprint 1:** 5 Sekunden sind für ein echtes PVS zu knapp. Als Platzhalter
gelten etwa 40 Sekunden für UC1 und etwa 20 Sekunden für UC2; die Werte legt die Abnahme fest.

Patienten werden ausschließlich über `kennung` identifiziert. Namen und
Geburtsjahre sind kein Teil der Schnittstelle; sie existieren nur als erkennbar
falsche Mock-Testdaten. Kennungen und Revisionsstände bleiben im Speicher.
`anmeldungen` liefert eine Momentaufnahme von Kennungen, niemals Zeilennummern.
Vor `annehmen` werden Kennung, vollständiger Zustand, Revision, Sperre und
Bereitschaft erneut geprüft. Die Wirkung wird bei unklarem Ausgang nicht wiederholt.

**UC1-Kategorien:** Die Quartalsregel ist ein Platzhalter. Sie ist nur für
ansonsten sichere Fälle mit gültiger Karte und Termin heute umschaltbar.

| Kategorie | Verhalten / Code |
|---|---|
| bekannt, Termin heute, Karte gültig, alle Prüfungen eindeutig | `angenommen`; bei `nur_melden=true`: `wuerde_annehmen` |
| bekannt, ohne Termin heute | liegen lassen: `kein_termin` |
| erste Kartenlesung im Quartal | liegen lassen: `quartal_erst`; `quartal_annehmen=true` schaltet die Regel um |
| Daten weichen ab | liegen lassen: `abweichung` |
| unbekannter Patient | liegen lassen: `neu` |
| Karte ungültig oder abgelaufen | liegen lassen: `karte` |
| bereits angenommen | keine UI-Wirkung: `schon_erledigt`, nur Zähler |
| dieselbe Karte mehrfach in der Momentaufnahme | einmal verarbeiten, weitere Vorkommen: `doppelt` |
| Kostenträger-Sonderfall | liegen lassen: `kostentraeger` |
| unbekannte Kategorie, ungültige Fakten oder verschwundener Eintrag | liegen lassen: `unbekannt` |
| Datensatz gesperrt | Lauf anhalten: `gesperrt` |

Bei kombinierten Merkmalen gilt: ungültige/unbekannte Fakten verhindern jede
Annahme; bereits erledigte Fälle werden nicht bearbeitet. Ungültige Karte,
unbekannter Patient, Abweichung, Sonderkostenträger und fehlender Termin sperren
vor einer Quartalsfreigabe. Ein Dialog, fehlende Bereitschaft, Zeitlimit oder
eine Ausnahme beendet den Lauf; übrige Einträge bleiben bis zum nächsten Takt.

**UC2-Setups:** Die folgenden Ansichten sind ausdrücklich synthetische
Platzhalter. Die fachlichen Werte aus dem referenzierten Kommentar sind hier
nicht belegt und müssen vor der Sprint-1-Abnahme im Betreiber-Repository
festgelegt werden. Die Eingabe wählt nur die Tabellenzeile.

| Setup | Programm | Monitor | Ansicht |
|---|---|---|---|
| `setup_a` | `programm_1` | 1 | `ansicht_a` |
| `setup_a` | `programm_2` | 2 | `ansicht_a` |
| `setup_b` | `programm_1` | 1 | `ansicht_b` |
| `setup_b` | `programm_2` | 2 | `ansicht_b` |
| `setup_c` | `programm_1` | 1 | `ansicht_c` |
| `setup_c` | `programm_2` | 2 | `ansicht_c` |

Monitore und Ansichten werden semantisch adressiert, ohne feste Koordinaten.
Der Mock parametrisiert beide DPI-Werte, beispielsweise 96 und 144. Ein bereits
anderer Patient im Detailprogramm wird in derselben Instanz umgeschaltet.
Vor jeder Wirkung prüft der Adapter nochmals den offenen PVS-Patienten.

**Eingabe und Ausgabe:**

```json
{"nur_melden":true,"quartal_annehmen":false}
```

UC1 akzeptiert auch `{}` mit beiden Vorgaben. UC2 verlangt genau:

```json
{"setup":"setup_a"}
```

Zusatzfelder, falsche Typen, doppelte Schlüssel und unbekannte Setups werden
vor Adapter-Aufrufen mit `intern` abgewiesen. Die Ausgabe besteht ausschließlich
aus festen Codes und nichtnegativen ganzzahligen Zählern:

```json
{"codes":{"wuerde_annehmen":1}}
```

UC1 verwendet die Tabellen-Codes sowie `dialog`, `pvs_nicht_bereit`, `zeitlimit`
und `intern`. UC2 verwendet `geoeffnet`, `teilweise`, `kein_patient`, `mehrdeutig`,
`programm_fehlt`, `pvs_nicht_bereit`, `dialog`, `zeitlimit`, `intern`.
`teilweise` steht zusätzlich zum Fehlercode, wenn schon ein Detailprogramm umgeschaltet war.
`geoeffnet` zählt erfolgreich eingerichtete Detailprogramme (normal 2).
Nach Teilwirkung bleiben die bestätigten Zähler neben dem Fehlercode erhalten.
Die gesamte geschlossene Menge steht in `codes.py`. Unerwartete Ausnahmen
einschließlich Abbruchsignalen werden als `intern` gezählt, ohne Ausnahmetext,
Fenstertitel, Kennung, Name oder Traceback. Typisierte Zustandssignale liefern
nur ihren festen Fehlercode. Das Skript führt keine Inhaltslogs.

**Ergebnisweg — offen:** Die lokale Vorlage beschreibt `januaport.input` und
`januaport.call` mit fachlichem Kartei-Schreiben; technisches `runs/result`
ersetzt dieses Schreiben nicht. Auch die gelesenen Quellen
[`desktop-runner/README.md`](https://github.com/JanuaPort/januaport-plugins/blob/main/desktop-runner/README.md)
und [`contract/README.md`](https://github.com/JanuaPort/januaport-plugins/blob/main/desktop-runner/contract/README.md)
dokumentieren kein `jnpt.ergebnis`. Darum heißt die Austauschstelle ausdrücklich
`ergebnis_abgeben`. Sie validiert erneut und gibt lokal das Zähler-JSON auf
stdout aus. Der Läufer verwirft stdout/stderr; **damit ist die fachliche
Läufer-Rückgabe noch nicht angebunden**. In Sprint 1 müssen die Übergabe der
Eingabe aus `januaport.input`, ein festgelegter Ergebnisempfänger samt Vertrag
und dessen Fehlerverhalten angebunden und geprüft werden. Keine erfundene SDK-API,
keine Inhaltsdatei und kein Log als Ersatzweg. Die Aufrufe `ausfuehren` erlauben
schon jetzt Tests des JSON-Einstiegs mit injiziertem Adapter.

## 4. Zugänge und Rechte

Der Offline-Vorbau braucht keine Token und keine Rechte auf ein Fremdsystem.
Direkte Skriptstarts verwenden immer den Mock. Die spätere Anbindung und das
Manifest gehören in das Betreiber-Repository; dieses Rezept ist kein pinfertiges
Betriebspaket. Keine Zugangsdaten in Eingabe, Konfiguration oder Ergebnis.

| Späterer Abnehmer | Zuschnitt / Besitzer | Abgrenzung |
|---|---|---|
| UC1-Zeitplan | Mensch/Admin bindet `<annahme-pin>` an `<geraet>` | ein Startweg, zunächst `nur_melden=true` |
| UC2-Menüauslöser | aufrufende Rolle mit `desktop:<ansicht-pin>` | Eingabe ausschließlich Setup-Name |
| Lauf-Token | Rechte des Aufrufers ∩ deklarierte Werkzeuge | Werkzeuge erst mit Ergebnisvertrag festlegen |
| Geräte-Token | Gerätebindung | kein eigenständiger fachlicher Ergebnisweg |

Auch additive Team-Rechte, andere Pins und zweite Startwege müssen vor Betrieb
geprüft werden. Alle Skripte desselben Gerätekontos teilen dessen Vertrauen;
dieser Fachkern ist keine Sicherheits- oder Netzwerksandbox. Er vergibt keine
Rechte und ändert den Läufer-Vertrag nicht.

## 5. Ablauf

1. Betreiber prüft Regeln und Offline-Proben mit ausschließlich synthetischen Daten.
2. UC1 im Minutentakt: Bereitschaft prüfen, Kennungen als Momentaufnahme lesen,
   frische Fakten nach Kennung bewerten. `nur_melden=true` ruft `annehmen` nie auf.
3. Bei ausdrücklich gesetztem `nur_melden=false` nur sichere Fälle mit erneut
   bestätigtem Zustand annehmen. Neue Einträge während eines Laufs kommen erst
   in den nächsten Lauf; Sortiersprünge ändern keine Zielkennung.
4. UC2 nach Menüklick: Bereitschaft prüfen, **passiv auf den Fokus beim PVS warten**,
   genau einen offenen Patienten prüfen und beide Programme/Monitore vorab prüfen.
5. Vor jeder UI-Wirkung Kontext erneut prüfen, vorhandene Instanz umschalten,
   Monitor und Ansicht einstellen. Keine Wiederholung nach unklarer Teilwirkung.
6. Ausschließlich das geschlossene Zähler-Ergebnis über `ergebnis_abgeben` abgeben.
   Im Betrieb erst nach Anbindung des offenen Ergebniswegs.

**Idempotenz:** UC1 prüft den aktuellen Annahmestatus bei jedem Lauf und
dedupliziert die Kennung innerhalb eines Laufs. Der zweite Lauf nimmt auf
demselben Zustand nichts doppelt an. UC2 verwendet dieselben Programm-Instanzen.
**Ein Lauf zur Zeit:** Der Läufer serialisiert die Starts. Dauert ein Lauf länger
als der Minutentakt, ist `busy` Sache des Läufers; der Vorbau legt keine Merkerdatei an.

## 6. Agenten-Anweisung

[`anweisung.md`](anweisung.md) im Bau-Client einsetzen. Sie enthält die Regeln
für beide Abläufe und die noch offenen Abnahmen. Der Vorbau benötigt keine
patientenbezogenen Platzhalter und keine Zugangsdaten.

## 7. Aufbau-Handgriffe

| Wer / was | Wofür | Zuschnitt | Wann |
|---|---|---|---|
| Bauer: Tests und Mutationen | Regeln und Verbote prüfen | Python-Standardbibliothek, offline | vor jeder Freigabe |
| Betreiber: Quartalsregel und Setups | Platzhalter fachlich ersetzen | getrenntes Betreiber-Repository | vor Sprint-1-Abnahme |
| Adapter-Verantwortlicher | Oberfläche und Deadline anbinden | echter Adapter außerhalb dieses öffentlichen Repositorys | Sprint 1 |
| Admin: Ergebnisvertrag, Manifest, Pin und Startwege | Läufer-Anbindung | minimale Rechte, synthetische Bauumgebung | nach Adapterprüfung |
| Mensch: Abnahme und Lizenzprüfung | Betrieb verantworten | zunächst nur melden | vor Annahmefreigabe |

Vom Repository-Root, vollständig offline:

```sh
python -I -B -m unittest discover -s rezepte/pvs-desktop-rpa -p tests.py
bash rezepte/pvs-desktop-rpa/test.sh
python -I -B rezepte/pvs-desktop-rpa/mutationen.py
```

`-I` isoliert Python von Benutzerpfaden und Umgebungsoptionen. `-B` und der
Bootstrap verhindern Bytecode-Dateien. `test.sh` respektiert `PYTHON`, falls der
Interpreter nicht `python3` heißt. Tests benötigen weder Netz noch Container.
Mutationen laufen seriell in getrennten Prozessen, mit verändertem Quelltext nur
im Speicher; die Dateien bleiben unverändert. Ein Importfehler allein genügt
als Mutationsnachweis nicht, mindestens eine Verbotsassertion muss scheitern.

Direkte Demo unter PowerShell, nur mit dem eingebauten synthetischen Mock:

```powershell
'{}' | python -I -B rezepte/pvs-desktop-rpa/annahme.py
'{"setup":"setup_a"}' | python -I -B rezepte/pvs-desktop-rpa/ansicht.py
```

## 8. Fehlerfälle

| Fall | Erkennung | Verhalten / wer löst |
|---|---|---|
| Fenster lädt zu lange oder bleibt halb gefüllt | gemeinsame Deadline, unvollständige Fakten | `zeitlimit`, keine weitere Wirkung; Mensch |
| unerwarteter Dialog | typisiertes Adapter-Signal | `dialog`, stehen lassen; Mensch |
| Datensatz gesperrt | frische Sperrprüfung vor Lesen und Wirkung | `gesperrt`, nur dieser Eintrag bleibt liegen, die übrigen laufen weiter; Mensch |
| einzelner Eintrag bleibt halb gefüllt | Wartegrenze je Eintrag (1 s im Vorbau) | `zeitlimit` für diesen Eintrag, die übrigen laufen weiter; Mensch |
| UC2: ein Monitor umgeschaltet, dann Abbruch | Zähler der Wirkungen | `teilweise` plus Fehlercode, kein zweiter Versuch; **beide Monitore prüfen**, ein Monitor zeigt noch den vorigen Patienten; Mensch |
| PVS nicht gestartet, Anmeldemaske, Sitzung gesperrt | Bereitschaftsprüfung | `pvs_nicht_bereit`, keine Selbstanmeldung; Mensch |
| kein oder mehrere Patienten offen | Anzahl eindeutiger Kennungen | `kein_patient` / `mehrdeutig`, keine UI-Wirkung; Mensch |
| Detailprogramm fehlt | Vorprüfung beider Ziele | `programm_fehlt`, kein Start; Mensch |
| Fokus kommt nicht zum PVS zurück | passives Warten bis Deadline | `zeitlimit`, keine UI-Wirkung; Mensch |
| Kontext wechselt vor UI-Schritt | erneute Kennungsprüfung | `mehrdeutig`, anhalten; Mensch |
| Monitor/DPI/Ansicht oder Eingabe ungültig, sonstige Ausnahme | strikte Prüfungen / äußerer Ausnahmefang | `intern`, nur Zähler; Bauer mit synthetischer Reproduktion |

## 9. Prüfsteine

- [x] Kategorien einschließlich Quartalsumschaltung, Doppelkarte und Sperre getestet.
- [x] Vorgabe `nur_melden=true`: Spy belegt null Annahmeaufrufe.
- [x] Idempotenz, Namensgleichheit und Listenänderung während des Laufs getestet.
- [x] Verzögerung, halbfertiges Fenster, Dialog und Bereitschaft negativ geprüft.
- [x] UC2: Fokus vor erster UI-Wirkung, Mehrdeutigkeit, Umschalten, fehlendes
  Programm und unterschiedliche DPI geprüft.
- [x] Ausnahme-Leckproben an jeder verwendeten Adapter-Methode, geschlossenes JSON,
  stdout/stderr sowie echter CLI-Prozess mit Dateivergleich und Audit-Hook geprüft.
- [x] Vier Pflichtmutationen und weitere Sperrenmutationen werden seriell erkannt;
  unveränderter Quelltext bleibt grün. Ausführbar über `mutationen.py`.
- [ ] Dieselben Verbotsproben und Mutationen am echten Adapter sowie am Läufer
  durchführen. Hier ist ausschließlich der Mock vorhanden.
- [ ] Ergebnisweg, tatsächliche Setup-Ansichten, Lizenzbedingungen und Anlagenlauf
  abnehmen. Bis dahin bleibt der Stand durchdacht.

## 10. Grenzen

### Was dieses Rezept nicht ist

Dies ist **kein Adapter für ein konkretes PVS**. Ob die Automatisierung zu den
Lizenzbedingungen passt, verantwortet der Betreiber. Der echte Adapter gehört
außerhalb dieses öffentlichen Repositorys. Es gibt keine UI-Automatisierungsbibliothek
und keine festen Klickkoordinaten im Vorbau.

Die Protokolle beschreiben Verpflichtungen eines späteren Adapters. Mock- und
Fachkerntests belegen weder dessen UI-Sicherheit noch eine Transaktion zwischen
PVS und zwei Programmen. Nach Teilwirkung wird nicht blind wiederholt oder
zurückgerollt. Mehrere Geräte sind durch den Fachkern nicht gegenseitig gesperrt.
Das Skript rät nicht, klickt keinen Dialog weg und meldet sich nicht selbst an.

## 11. Datenschutz

**Bauumgebung ausschließlich mit synthetischen Daten:** Testsystem, Testfenster,
Fehlerfälle und Testkonten sind von echten Betriebsdaten getrennt. Auch zur
Fehlersuche werden keine echten Oberflächeninhalte, Namen, Kennungen, Exporte
oder Screenshots in Bauwerkzeuge, Chat oder dieses Repository übernommen.
Testwerte sind ausdrücklich erfunden: `Test, Patient 07`, `T-0000-0007`,
Geburtsjahr `0`, `Kasse_A` und `Kasse_B`.

**Keine Patientendaten im Ergebnis:** Auch die eindeutige Kennung bleibt nur im
Arbeitsspeicher des Laufs. Das Ergebnis, stdout/stderr und etwaige spätere
Audit-Übergaben enthalten nur feste Codes und Zähler. Ausnahmetexte werden
verworfen. Der Fachkern führt keine Inhaltslogs; es gibt keine Inhaltsdateien,
keine Screenshots, keine TEMP-Dateien und keine Schreibzugriffe ins
Arbeitsverzeichnis. Auch eine inhaltslose Merkerdatei unter `%LOCALAPPDATA%`
wird hier nicht benötigt. Runtime und Mock schreiben gar keine Dateien.

Quellcode und Testwerkzeuge sind keine Sandbox für einen beliebigen späteren
Adapter. Dessen Dateiverhalten und alle alternativen Ergebnis-/Logwege müssen
vor Einsatz separat geprüft werden. Der Läufer hat eigene Lauf- und
Journaldateien nach seinem Vertrag; das Rezept erzeugt keine zusätzlichen.
Aufräumen fachlicher Dateien entfällt im Vorbau, der Prozessspeicher endet mit
dem Lauf. Der Betreiber prüft getrennt die Aufbewahrung der reinen Zähler.
