---
name: steuer-app
titel: Vorhandene Zeitpläne und Geräte-Setups im Browser und PC-Fenster steuern
ziel: Ein Mensch sieht Zeitpläne, schaltet sie an oder aus und löst ein vorhandenes Geräte-Setup aus.
stufe: 2
stand: durchdacht
version: 0.1.0
jnpt_ab: "0.92.0"
muster: []
integrationen: []
beisteller: []
---

# Steuer-App

## 0. Stand und Einordnung

**Durchdacht**, Stufe 2 „Gemeinsam bauen“. Browser-Quellen ohne Build-Schritt und
Abhängigkeiten. Lade-Regel, Manifest nach Trägerzuordnung und gestoppter Import
sind gegen den echten Kern geprüft; Browser-Anmeldung und Betrieb auf einer Anlage
sind noch offen. Ein passendes App-Muster ist im Kern nicht beschrieben; daher
bleibt die Musterliste leer. Format: [App-Rezept](../../REZEPT-FORMAT.md#app-rezept).

Die Brücke für das PC-Fenster ist gebaut: `mcp.js` nutzt dort `werkzeug` über
`chrome.webview`; im Browser bleibt der bisherige MCP-Aufrufweg erhalten.
Die Steuer-App ist für beide Fenster deklariert, im PC-Fenster aber noch nicht
nativ geprüft. Der Monitor bleibt im Browser; Modus b am PC folgt später.

## 1. Ziel und Passung

Passt für vorhandene Server-Zeitpläne und Geräte-Setups mit einem explizit
berechtigten App-Träger. Die App bietet Zeitplan an/aus und die Auslösung von
Setups mit leerem `frei` an. Für Setups, die freie Pflichtwerte brauchen, muss
der Betreiber eine eigene Eingabeoberfläche und Prüfung ergänzen.

## 2. Rollen

| Wer | Aufgabe | Grenze |
|---|---|---|
| Mensch | Ziel und Wirkung prüfen, jeden Schreibauftrag bestätigen | Auslösung kann fachliche oder finanzielle Wirkung haben; Verantwortung liegt beim Betreiber |
| KI beim Aufbau | Quellbaum und Rechtebedarf erklären | arbeitet nach `anweisung.md` |
| Betreiber | Träger, Teams, Pins, Zeitpläne, Setups und Live-Fassung einrichten | Rezept liefert diese Anlagenwerte nicht |
| JanuaPort | aktuelle Rechte, Zielbindung, Basis, Audit und Wirkung prüfen | UI-Bestätigung ist eine Bedienhilfe, keine Berechtigungsgrenze |

## 3. Bausteine

`app/` enthält Manifest, HTML, CSS und zwei eigene JavaScript-Dateien.
Der Bedarf ist werkzeuggenau:

| Werkzeug | Eingabe der App | Verwendete Antwort |
|---|---|---|
| `run_control_read` | `{}` | `items`: `kind`, `name`, `device`, `pin`, `basis`, `cron`, `timezone`, `enabled`, `covered` |
| `run_control_set_schedule` | `name`, aktuelle `basis`, umgekehrtes `enabled` | neue `basis`, danach neu lesen |
| `run_control_trigger_setup` | `device`, `pin`, `setup`, `frei: {}` | `run` und `hint`, danach neu lesen |

Maßgeblich: `januaport/internal/adminmcp/run_control.go`,
`januaport/internal/runcontrol/control.go`, `januaport/cmd/jnpt/run_control*.go`.
Auslösen betrifft ein **Geräte-Setup**, keinen beliebigen Server-Zeitplan.
Der synthetische Pinname `beispiel_lauf` ist ein absichtlich offener Bedarf,
kein mitgelieferter Lauf. Keine Kartei und keine zusätzliche Integration.

## 4. Zugänge und Rechte

Manifest: `fenster=beide`, `modus=a`, `teams=[]`, ohne `token_id`.
Der Betreiber stellt vor dem Import eine Technical Identity bereit und übergibt
deren **ID**, nicht das Secret. Browser-Anmeldung verwendet zusätzlich eine
berechtigte Person. Die drei Werkzeugrechte stehen als
`run_control:run_control_read`, `run_control:run_control_set_schedule` und
`run_control:run_control_trigger_setup` auf dem Träger. Hinzu kommen die Rechte
auf die betroffenen `script_<pin>` beziehungsweise `desktop_<pin>` und die
vollständige Deckung der deklarierten Laufrechte einschließlich Klartext und
Datenfiltern. `werkzeuge` im Manifest vergibt keine Rechte.

`skripte` muss zu den tatsächlich freigegebenen Pins passen. Für andere Pins
erstellt der Betreiber eine geprüfte eigene Fassung. Die App verwendet bewusst
keine Use-Case-Pause; der Kern schließt App-Träger dort aus.

## 5. Ablauf

1. „Zeitpläne und Setups laden“ liest die aktuelle Sicht.
2. Bei einem Ziel mit `covered=true` an/aus oder Auslösen wählen.
3. Ziel und Wirkung im Bestätigungsbereich prüfen, bestätigen oder abbrechen.
4. Zeitplanänderung verwendet die gelesene CAS-`basis`; danach wird neu gelesen.
5. Pro Seite ist ein Auftrag zur Zeit aktiv. Eine Setup-Auslösung ist nicht
   idempotent: bei unklarem Versand zuerst den Monitor prüfen, bevor erneut
   ausgelöst wird. Es gibt keinen automatischen Wiederholungsversuch.

## 6. Agenten-Anweisung

[`anweisung.md`](anweisung.md) ist die reine Aufbauanweisung für KI und Mensch.
Platzhalter bezeichnen ausschließlich Betreiberwerte der Zielanlage.

## 7. Aufbau-Handgriffe

Vom Repository-Root, nach der [Prüfung](../../pruefung/app-rezepte/README.md):

```text
python pruefung/app-rezepte/pack.py rezepte/steuer-app/app <ARCHIV>
jnpt app import <ARCHIV> --name steuer_app --token-id <TRAEGER_ID>
```

Die CLI läuft mit der Konfiguration der Zielanlage. Sie liefert `fassung` und
`offene_punkte`. Ohne neue Träger-ID wird Modus a vor dem Speichern abgewiesen.
Bei bereits geprüften Teams kann der Betreiber `--team <TEAM>` wiederholen.

| Offener Punkt | Betreiberaufgabe |
|---|---|
| `Werkzeug run_control_read fehlt` | Kernversion und Werkzeugregistrierung prüfen |
| `Werkzeug run_control_set_schedule fehlt` | ebenso, danach Schreibrecht prüfen |
| `Werkzeug run_control_trigger_setup fehlt` | ebenso, danach Auslöserecht prüfen |
| `Skript-Pin beispiel_lauf fehlt` | passenden eigenen Pin einrichten und App-Deklaration prüfen |
| `Skript-Pin beispiel_lauf vorhanden, bitte pruefen` | Ziel, Fassung, deklarierte Rechte und Bindung inhaltlich prüfen |
| `Teams leer` | berechtigte Teams der Zielanlage zuordnen |

Die Meldungen hängen vom Zielkatalog ab. Sie sind keine vollständige
Betriebsprüfung. Trägerdeckung, vorhandene Zeitpläne/Setups, synchronisiertes
Gerätemanifest, Browser-Apphost, privater App-Listener, TLS und SSO richtet der
Betreiber ein. Träger, Teams und Pins sind Betreiberaufgaben.
**Nach dem Import ist die App nie live**, auch ein Wiederimport stoppt sie.
Erst nach Prüfung der offenen Punkte und Bindungen wird die importierte
Fassung über den administrativen Live-Weg ausdrücklich live geschaltet.
Bei CLI-Verwaltung: `jnpt live lesen`, dann ein JSON-Auftrag an
`jnpt live app_live_schalten` mit `name`, `fassung`, aktueller `basis_fassung`
und `ja: true`. Danach Browser-Anmeldung und Funktionsprobe durchführen.

## 8. Fehlerfälle

| Fall | Verhalten | Zuständig |
|---|---|---|
| Abgewiesen, Sitzung abgelaufen, Basis veraltet | Sicht leeren, Hinweis anzeigen, frisch laden | Mensch prüft Rechte und Stand |
| `covered=false` | Schaltfläche gesperrt | Betreiber prüft vollständige Trägerdeckung |
| Freigabepflicht aktiv | Kern verweist an Admin-Weg | Betreiber entscheidet dort |
| Versand unklar | keine automatische Wiederholung | Mensch prüft vorhandenen Lauf im Monitor |

## 9. Prüfsteine

- [ ] Kernprüfung und Mutationsproben nach Prüfanleitung bestehen.
- [ ] Importausgabe abgearbeitet, Zustand `gestoppt` kontrolliert.
- [ ] Teams, Trägerdeckung, Pinbindung und Geräteabgleich geprüft.
- [ ] Nach ausdrücklichem Live-Schalten: Zeitplan lesen, an/aus bestätigen,
  CAS-Konflikt prüfen, Setup einmal auslösen; Audit und Betreiber-Mail zählen.
- [ ] Abbrechen erzeugt keinen Schreibaufruf; fehlende Deckung bleibt gesperrt.

## 10. Grenzen

Kein Anlagenbeleg. Die App setzt an/aus ausschließlich bei vorhandenen
Zeitplänen und löst vorhandene Geräte-Setups aus. Sie legt diese nicht an.
Eine Setup-Auslösung hat keinen Rückweg; Zeitplanänderungen nutzen den
vorhandenen administrativen Rückweg. Die Monitor-Pause ist ein eigener Vertrag.
Kernlücken für Rezepte: [offene Punkte](../../pruefung/app-rezepte/README.md#offene-punkte-im-kern).

## 11. Datenschutz

Die Sicht enthält Betriebsmetadaten. Die App zeigt Namen, Zeiten und Zustand,
verarbeitet aber die mögliche `input`-Antwort nicht. Antworten werden mit
`textContent` als Text angezeigt. Speicherung beschränkt sich auf den
aktuellen Seitenzustand; beim Neuladen entfällt dieser. Audit und
Aufbewahrung der Anlage verantwortet der Betreiber. Inhalte gehören nicht in den Chat.
