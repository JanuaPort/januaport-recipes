# Python-Bibliotheken bauen

Arbeite im Skriptordner `<ordner>` für Ziel `<linux oder windows>`.
Schlage Paketnamen und erforderliche Versionsgrenzen in `requirements.in` vor.
Verwende eine Anforderung je Zeile. Starte den Build nach der Paketwahl durch
den Menschen. Lege den PR mit Lock und Wheels zur Prüfung vor; berichte nur
Paketnamen, Versionen, Größe und Prüfergebnis.

Herkunft ist PyPI, geprüft sind nur die Hashes.
Der Betreiber prüft Auswahl und Lizenzen. Der Mensch prüft und mergt den PR
und pinnt anschließend den Commit wie bisher. Baue und pinne nicht am Läufer.
Bei fehlendem Wheel eine andere Paketversion vorschlagen oder das Paket weglassen.
Bei einem Fehler vor der Veröffentlichung die letzte erfolgreiche Ausgabe behalten.
Ein lokaler Build zur Zeit; Linux- und Windows-Ziele in getrennte Skriptordner legen.
