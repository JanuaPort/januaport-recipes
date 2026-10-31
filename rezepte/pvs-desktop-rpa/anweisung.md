# Agenten-Anweisung: PVS-Desktop-Vorbau

Du hilfst beim Aufbau zweier Desktop-Abläufe für ein Praxisverwaltungssystem
(PVS). Die Detailprogramme heißen ausschließlich `programm_1` und `programm_2`.
Stand: durchdacht, nur Offline-Mock, kein freigegebener Betrieb.

Arbeite in der Bauumgebung ausschließlich mit offensichtlich synthetischen
Daten. Verwende keine echten Namen, Orte, Hersteller, Produktnamen, Kennungen,
Versicherungsdaten oder Oberflächeninhalte. Kein Export, Screenshot oder roher
Fehlertext gehört in Chat, Repository, Log oder Ergebnis.

UC1 prüft im Minutentakt Kartenanmeldungen. Vorgabe ist `nur_melden=true`:
keinen Annahmeaufruf ausführen, nur feste Codes zählen. `nur_melden=false`
braucht eine bewusste Betreiberentscheidung vor dem Pin. Nur bekannte Patienten
mit Termin heute, gültiger Karte, übereinstimmenden Daten und regulärem
Kostenträger kommen infrage. Erste Quartalslesung bleibt mit `quartal_erst`
liegen, solange der Betreiber `quartal_annehmen=true` nicht festlegt. Diese
Umschaltung umgeht keine andere Sperre. Unbekanntes bleibt liegen.

Identifiziere ausschließlich über eindeutige Kennungen, niemals über Namen.
Kennungen bleiben im Speicher. Pro Lauf eine stabile Kennungs-Momentaufnahme;
neue Einträge erst im nächsten Lauf, Sortierung ist keine Identität. Bereits
angenommene Fälle bleiben unverändert, doppelte Karten werden einmal verarbeitet.
Unmittelbar vor der Wirkung prüft der Adapter denselben Zustand erneut.

UC2 bekommt ausschließlich einen der Namen `setup_a`, `setup_b`, `setup_c`.
Die Tabellen-Ansichten sind synthetische Platzhalter bis zur fachlichen Abnahme.
Warte nach dem Menüklick passiv auf den Fokus beim PVS, bevor ein UI-Schritt
stattfindet. Genau ein Patient muss offen sein, beide Programme und Monitore
müssen bereit sein. Einen anderen Patienten im Detailprogramm in derselben
Instanz umschalten. Keine Programme starten, keine zweite Instanz, keine festen
Koordinaten. Unterschiedliche DPI sind Adapter-Parameter.

Jede Adapter-Methode bekommt dieselbe Deadline von fünf Sekunden pro Lauf.
Bei Dialog, Sperre, fehlender Bereitschaft, Zeitlimit oder unklarer Wirkung
anhalten. Nicht raten, ins Leere klicken, Dialoge wegklicken oder selbst anmelden.
Nach Teilwirkung keine automatische Wiederholung. Ein Lauf zur Zeit und `busy`
bei längerem Lauf organisiert der Läufer.

Nach außen ausschließlich JSON mit festen Codes und ganzzahligen Zählern.
Unerwartete Ausnahmen ergeben `intern`, nie Ausnahmetext oder Traceback.
Keine Dateien, auch keine TEMP-, Screenshot-, Inhalts- oder Merkerdatei.

Führe Offline-Tests und serielle Mutationsproben aus. Prüfe jeden Verbotsfall
auch durch tatsächliches Auslösen. Behaupte keine Prüfung am echten Adapter:
er kommt erst außerhalb dieses öffentlichen Repositorys in Sprint 1.
Der Ergebnisweg ist offen: `ergebnis_abgeben` gibt lokal nur Zähler-JSON aus;
stdout wird vom Läufer verworfen. Eingabe aus `januaport.input` und fachliche
Rückgabe erst nach bestätigtem Vertrag anbinden. `jnpt.ergebnis` ist nicht belegt.
Keine Zugangsdaten oder zusätzlichen Rechte erfinden.

Der Betreiber verantwortet Lizenzbedingungen, echte Setups und Betriebsfreigabe.
Der Vorbau bleibt bis zur Anlagen-Abnahme durchdacht.
