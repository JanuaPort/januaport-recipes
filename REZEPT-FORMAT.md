# Das Rezept-Format

Ein **Rezept** beschreibt, was eine KI zusammen mit einem Menschen braucht, um einen Use Case
auf einer JanuaPort-Anlage aufzubauen: Integrationen, Kartei-Satzarten, Zugänge, eine
Agenten-Anweisung, Skripte und Prüfsteine. Diese Datei legt fest, wie ein Rezept aufgebaut
ist und was nie darin steht (Format abgestimmt in JanuaPort/januaport#784).

## 1. Rezept und Muster

JanuaPort liefert **Muster** mit (`wissen_get muster/<name>` auf jeder Anlage). Ein Muster
beschreibt einen Lösungstyp für eine Problemklasse: Rollen, Vertragsgerüst, Fehlerklassen,
wann er nicht passt. Ein **Rezept** liefert die konkreten Teile, um ihn aufzubauen.

| | Muster | Rezept |
|---|---|---|
| Frage | Welcher Lösungstyp passt zu dieser Problemklasse? | Welche Teile brauche ich, um ihn auf meiner Anlage aufzubauen? |
| Ort | im JanuaPort-Binary, abrufbar über `wissen_get` | dieses Repository |
| Leser | KI und Mensch beim Entwerfen | der Bauer auf `/mcp` (KI mit Mensch) und der Admin |

Ein Rezept **verweist** auf seine Muster und wiederholt sie nicht. Damit es auch ohne
laufende Anlage verständlich ist, sagt es zu jedem Muster in einem Satz, was es beiträgt.

## 2. Aufbau im Repository

```
rezepte/<name>/
  REZEPT.md                 YAML-Kopf und Pflichtabschnitte
  anweisung.md              Agenten-Anweisung zum Einsetzen, Platzhalter in <…>
  satzarten/<satzart>.yaml  Betreiber-Datei für JNPT_KARTEIEN_DIR (falls das Rezept eine Kartei nutzt)
```

Mehr Dateien gibt es nicht. Die Satzart ist eine eigene Datei, weil sie wörtlich in
`JNPT_KARTEIEN_DIR` gelegt und mit `jnpt kartei check` geprüft wird. Die Anweisung ist eine
eigene Datei, weil sie wörtlich in einen Client kopiert wird. Alles andere steht in
`REZEPT.md`. Richtwerte: `REZEPT.md` 10–16 KiB, `anweisung.md` unter 4 KiB.

## 3. Der YAML-Kopf

Der Kopf trägt nur, was ein späterer Katalog maschinell braucht. Alles andere steht im Text.

| Schlüssel | Pflicht | Bedeutung |
|---|---|---|
| `name` | ja | gleich dem Ordnernamen, `[a-z0-9-]` |
| `titel` | ja | ein Satz, was aufgebaut wird |
| `ziel` | ja | ein Satz Ziel, wer was tut |
| `stufe` | ja | Stufe des Stufenwegs, für Rezepte meist `3` |
| `stand` | ja | `durchdacht` (ausgearbeitet, kein Lauf) · `erprobt` (gegen eine Anlage gelaufen) · `belegt` (im Betrieb bei einem Kunden) |
| `version` | ja | SemVer des Rezepts |
| `jnpt_ab` | ja | kleinste JanuaPort-Version, gegen die der Stand gilt |
| `muster` | ja | Namen der Muster ohne Präfix `muster/` |
| `integrationen` | ja | je Integration: `rolle` (vorgeschlagener Name), `art` (`rest` · `upstream` · `sql` · `datei`), bei Datei `typ`, `vertrag` (Repo/Pfad), `werkzeuge` (ohne Integrationspräfix), optional `optional: true` |
| `satzarten` | nein | Pfade der Satzart-Dateien im Rezeptordner |
| `beisteller` | nein | Repo/Pfad wiederverwendbarer Programme |

Verweise auf andere Repositories schreiben `Repo/Pfad` und meinen `main`, bis die
Repositories Versionen tragen. Werkzeugnamen stehen ohne Präfix; auf der Anlage heißen sie
`<integration>_<werkzeug>`.

## 4. Pflichtabschnitte von `REZEPT.md`

| Nr. | Abschnitt | Inhalt |
|---|---|---|
| 0 | Stand und Einordnung | Stand ehrlich (woraus erprobt oder belegt, ohne Kunde und Ort), Stufe, Muster mit je einem Satz |
| 1 | Ziel und Passung | ein Satz Ziel · passt, wenn … · passt nicht, wenn … |
| 2 | Rollen | Mensch · KI · JanuaPort · Roboter oder Skript, je *tut* und *tut ausdrücklich nicht*; der Geld-Schritt ist benannt |
| 3 | Bausteine | Integrationen (Vertrag, Werkzeuge tool-genau, Pseudonymisierung) · Satzart (Status-Automat, Übergangsrechte) · Beisteller und Skripte (Verweis oder Schritt-Vertrag) |
| 4 | Zugänge und Rechte | je Abnehmer: Token als Platzhalter · Besitzer · Scopes tool-genau · was er ausdrücklich nicht hat |
| 5 | Ablauf | nummerierte Schritte; Idempotenz und „ein Lauf zur Zeit" ausdrücklich |
| 6 | Agenten-Anweisung | wofür, wohin, welche Platzhalter → `anweisung.md` |
| 7 | Aufbau-Handgriffe | Admin (Tabelle: was · wofür · Zuschnitt · wann) · Bauer auf `/mcp` · Mitspieler außerhalb der Anlage |
| 8 | Fehlerfälle | Fall · Erkennung · Verhalten · wer löst |
| 9 | Prüfsteine | abhakbar, nur Zähler und Audit, keine Inhalte |
| 10 | Grenzen | was Rezept, Produkt, KI und Roboter nicht halten |
| 11 | Datenschutz | was pseudonymisiert ankommt, was Klartext bleibt und warum, kein roher Eingang im Chat, Aufräumen |

## 5. Wie Bausteine referenziert werden

- **Integrationen** über ihren Vertrag oder ihre Spec in `januaport-integrations`. Ein Rezept
  legt **keine eigene Spec** an. Fehlt eine, gehört sie als Beitrag nach
  `januaport-integrations`, nicht als Anhang ins Rezept.
- **Kartei-Satzarten** als Datei im Rezeptordner, generisch benannt (kein Kunden- oder
  Produktname im Satzart- oder Feldnamen). Jede Datei muss `jnpt kartei check` bestehen.
- **Skripte und Beisteller:** Wiederverwendbare Programme liegen in `januaport-plugins` und
  werden per Repo/Pfad referenziert. Gibt es dort noch keins, beschreibt das Rezept die
  Schritte als **Vertrag** (Schritt · Eingabe · Ausgabe · Invarianten) und legt keinen
  eigenen Code bei.
- **Agenten-Anweisung** als reiner Text ohne Client-Syntax, Platzhalter in spitzen Klammern.
  Sie trägt die harten Regeln des Rezepts, vor allem die Freigabe durch den Menschen.

## 6. Was nie in einem Rezept steht

1. **Kundendaten:** keine Beträge, Verwendungszwecke, Beleg- oder Rechnungsnummern, IBANs,
   Namen, Postfach-Inhalte, auch nicht leicht verändert. Braucht es ein Beispiel, wird es
   erfunden und als erfunden gekennzeichnet (`RE-0000-BEISPIEL`).
2. **Kennungen einer Anlage oder eines Kunden:** kein Kundenname, kein Ort, keine Branche
   des Kunden, bei dem erprobt wurde, kein Produktname des Fachsystems, gegen das erprobt
   wurde, keine Hostnamen, Domains, IP-Adressen, Tenant- oder Client-IDs, keine Token-,
   Team- oder Nutzer-Labels, keine Zeitpläne und Mengengerüste aus dem Betrieb, keine
   Bildschirmfotos. Ein Fachsystem-Name ist nur erlaubt, wenn das Rezept für dieses Produkt
   gebaut ist **und** kein Rückschluss auf einen Kunden entsteht.
3. **Secrets:** keine Tokens, Schlüssel, Passwörter, EBICS-Schlüssel oder Zertifikate, auch
   nicht als Beispielwert in echter Form. Wo ein Wert hingehört, steht der Ort (Vault,
   Anmeldeinformationsspeicher), nie der Wert.

Geprüft wird das bei jedem Merge: Der Secret-Scan (gitleaks, samt IBAN- und Mail-Regel) läuft
über alle Branches, dazu kommen eine Suchliste im Prüfbericht und das Review.

## 7. Beiträge

Es gilt [`CONTRIBUTING.md`](CONTRIBUTING.md). Für Rezepte zusätzlich:

- **Neu schreiben, nicht bereinigen.** Ein Rezept entsteht aus der Erfahrung mit einem Use
  Case, nicht aus dessen Betriebsdokument. Wer eine Kundendatei „kundenfrei macht", lässt
  zuverlässig etwas stehen.
- **Stand ehrlich:** `erprobt` nur, wenn es gegen eine Anlage gelaufen ist; `belegt` nur im
  Betrieb bei einem Kunden. Im Abschnitt 0 steht, woraus.
- **Grenzen sind Pflicht.** Ein Rezept ohne Abschnitt „Grenzen" wird nicht aufgenommen.
- **Keine eigene Spec im Rezept** (§5).
- **Die drei Punkte aus §6.**
