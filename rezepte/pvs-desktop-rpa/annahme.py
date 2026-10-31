"""UC1-JSON-Einstieg; die direkte Ausführung verwendet ausschließlich den Mock."""

import sys
sys.dont_write_bytecode = True
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from pvs_rpa.codes import ergebnis_json
from pvs_rpa.eingabe import lesen
from pvs_rpa.kern_annahme import run_annahme
from pvs_rpa.mock import demo


def ausfuehren(eingabe: str, adapter=None) -> str:
    try:
        optionen = lesen(eingabe, annahme=True)
        adapter = demo() if adapter is None else adapter
        return ergebnis_json(run_annahme(adapter, **optionen, uhr=adapter.uhr))
    except BaseException:
        return ergebnis_json({"codes": {"intern": 1}})


def ergebnis_abgeben(ergebnis: str) -> None:
    """Offline-Ausgabe; Anbindung des fachlichen Läufer-Ergebniswegs ist offen."""
    try:
        import json
        ausgabe = ergebnis_json(json.loads(ergebnis))
    except BaseException:
        ausgabe = ergebnis_json({"codes": {"intern": 1}})
    try:
        print(ausgabe)
    except BaseException:
        # Auch ein kaputter Ausgabekanal erzeugt keinen Traceback/Fallback-Log.
        pass


def main():
    try:
        ergebnis = ausfuehren(sys.stdin.read())
    except BaseException:
        ergebnis = ergebnis_json({"codes": {"intern": 1}})
    ergebnis_abgeben(ergebnis)


if __name__ == "__main__":
    main()
