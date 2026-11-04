---
name: monitor-app
titel: Den kuratierten Use-Case-Monitor im Browser lesen
ziel: Ein Mensch sieht Zähler und kuratierte Hinweise für seine sichtbaren Use Cases.
stufe: 3
stand: durchdacht
version: 0.1.0
jnpt_ab: "0.92.0"
muster: []
integrationen: []
beisteller: []
---

# Monitor-App

## 0. Stand und Einordnung

**Durchdacht**, Stufe 3 „Überblick behalten“. Lade-Regel, Manifest und gestoppter
Import sind mit dem echten Kern geprüft; ein Anlagenbeleg einschließlich
Browser-Anmeldung steht aus. Ein passendes App-Muster fehlt im Kern, daher
`muster: []`. Format: [App-Rezept](../../REZEPT-FORMAT.md#app-rezept).

## 1. Ziel und Passung

Kuratierten Monitor für eine eingegebene Referenz oder alle sichtbaren Use
Cases lesen. Zeitraum: 1 bis 90 Tage, Vorgabe 7. Passt für einen Überblick
über Grün/Rot/Wartend, geplante Kettenstarts, letzten Fehler, Annahme und
Hinweise. Kein Ersatz für eine Prüfung der fachlichen Ergebnisse.

## 2. Rollen

| Wer | Aufgabe | Grenze |
|---|---|---|
| Mensch | Referenz und Zeitraum wählen, Hinweise einordnen | die App enthält keine Eingriffsbedienung |
| KI beim Aufbau | Aufbau und Leseprüfung begleiten | Anleitung in `anweisung.md` |
| Betreiber | Teams, Personenzugang und Live-Fassung verwalten | prüft sichtbare Use Cases und Aufbewahrung |
| JanuaPort | Besitz, Rechte und kuratierte Sicht prüfen | Zähler sind durch Quellenaufbewahrung begrenzt |

Ein Geld-Schritt ist in dieser Oberfläche nicht enthalten.

## 3. Bausteine

`app/` enthält fünf Textdateien ohne Abhängigkeiten oder Build-Schritt.
Einziges Werkzeug der Oberfläche: `usecase_monitor` mit `days` und optional
`ref`. Ohne `ref` ist die Antwort eine Liste, mit `ref` eine einzelne Sicht.
Verwendet werden `name`, `green`, `red`, `waiting`, `paused`, `last_error`,
`assumption`, `notices`. Weitere Felder bleiben unangezeigt.
Maßgeblich: `januaport/cmd/jnpt/usecase_monitor_api.go` und
`januaport/internal/usecasemonitor/monitor.go`. Keine eigene Integration oder Kartei.

## 4. Zugänge und Rechte

Manifest: `fenster=browser`, `modus=b`, `teams=[]`, ohne `token_id` und mit
leerer Pinliste. Der Träger ist die angemeldete Person, kein separates
App-Token. Sie benötigt `usecase:usecase_monitor` und die vorhandene
Besitzzulassung auf die betreffenden Use Cases. Teams auf der Live-App
begrenzen zusätzlich die App-Zulassung. Die Manifestliste ist Information,
keine Rechtequelle. Für diese Oberfläche genügt der schmale Lesezuschnitt.

## 5. Ablauf

1. Referenz bei Bedarf eintragen, Zeitraum wählen.
2. „Stand laden“ ruft einmal `usecase_monitor` auf.
3. Die aktuelle Antwort als Text lesen. Ein weiterer Abruf ersetzt sie.
4. Pro Seite läuft ein Abruf zur Zeit. Lesen ist wiederholbar; es gibt
   weder Polling noch automatische Wiederholungen.

## 6. Agenten-Anweisung

[`anweisung.md`](anweisung.md) begleitet den Aufbau mit Platzhaltern für die
Teams und Personenzugänge der Zielanlage.

## 7. Aufbau-Handgriffe

Vom Repository-Root, nach der [Prüfung](../../pruefung/app-rezepte/README.md):

```text
python pruefung/app-rezepte/pack.py rezepte/monitor-app/app <ARCHIV>
jnpt app import <ARCHIV> --name monitor_app
```

Die CLI verwendet die Konfiguration der Zielanlage. Bei bereits geprüften
Teams ergänzt der Betreiber wiederholte `--team <TEAM>`-Argumente.
Die Antwort enthält `fassung` und `offene_punkte`:

| Offener Punkt | Betreiberaufgabe |
|---|---|
| `Werkzeug usecase_monitor fehlt` | Kernversion und registriertes Lesewerkzeug prüfen, danach Personenrecht und Besitz |
| `Teams leer` | berechtigte Teams der Zielanlage zuordnen |

Die Pinliste ist leer; bei einer eigenen Erweiterung kommen die Pinmeldungen
aus dem Rezept-Format hinzu. **Die App ist nach Import nie live**; auch
Wiederimport stoppt sie. Träger (hier die Person), Teams und gegebenenfalls
Pins bleiben Betreiberaufgaben. Eine leere Liste offener Punkte beweist
keine vollständige Betriebsbereitschaft.

Der Betreiber richtet Browser-Apphost, privaten App-Listener, TLS und SSO ein,
prüft alle Zuordnungen und schaltet die importierte Fassung ausdrücklich live.
CLI: `jnpt live lesen`, danach JSON an `jnpt live app_live_schalten` mit `name`,
`fassung`, aktueller `basis_fassung`, `ja: true`. Anschließend mit einer
berechtigten Person anmelden und die Sicht prüfen.

## 8. Fehlerfälle

| Fall | Verhalten | Zuständig |
|---|---|---|
| Kein sichtbarer Use Case | leere Übersicht | Betreiber prüft Besitz und Teams |
| Sitzung/Recht fehlt, fremde Referenz oder ungültiger Zeitraum | Sicht leeren, Fehlerhinweis | Mensch prüft Zugang oder Eingabe |
| Quellenhistorie verkürzt | Hinweis und begrenzte Zähler | Betreiber prüft Aufbewahrung |

## 9. Prüfsteine

- [ ] Kernprüfung und Mutationsproben bestehen.
- [ ] Importantwort abgearbeitet, Zustand `gestoppt` geprüft.
- [ ] Träger, Teams und leere Pinliste geprüft, Fassung ausdrücklich live geschaltet.
- [ ] Auf Anlage: Einzelreferenz und Liste laden, fremde Referenz und
  fehlendes Leserecht abweisen; im Audit nur den Leseaufruf zählen.
- [ ] Fehlerhinweise mit HTML-Zeichen werden als Text angezeigt.

## 10. Grenzen

Kein Anlagenbeleg. Die Oberfläche liest ausschließlich `usecase_monitor` und
bietet keine Pause, Wiederholung oder Freigabe an. Das ist ein Zuschnitt der
Oberfläche; die effektiven Rechte des Trägers begrenzt der Kern. Die App zeigt
eine Auswahl der kuratierten Felder. `paused` betrifft geplante Kettenstarts,
nicht sämtliche Skript- oder Gerätezeitpläne.
Offene Kernthemen: [Prüfung](../../pruefung/app-rezepte/README.md#offene-punkte-im-kern).

## 11. Datenschutz

Antwortfelder einschließlich Fehlermeldungen sind Daten. Sie erscheinen über
`textContent` als Text und werden nicht als HTML oder Anweisung ausgeführt.
Die App speichert Antworten nur im aktuellen Seitenzustand. Audit und
Aufbewahrung liegen auf der Anlage; Inhalte gehören nicht in den Chat.
