"""UC2-JSON-Einstieg; Eingabe enthält ausschließlich einen Setup-Namen."""

import sys
sys.dont_write_bytecode = True
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from annahme import ergebnis_abgeben
from pvs_rpa.codes import ergebnis_json
from pvs_rpa.eingabe import lesen
from pvs_rpa.kern_ansicht import run_ansicht
from pvs_rpa.mock import demo


def ausfuehren(eingabe: str, adapter=None) -> str:
    try:
        optionen = lesen(eingabe, annahme=False)
        adapter = demo() if adapter is None else adapter
        return ergebnis_json(run_ansicht(adapter, optionen["setup"], uhr=adapter.uhr))
    except BaseException:
        return ergebnis_json({"codes": {"intern": 1}})


def main():
    try:
        ergebnis = ausfuehren(sys.stdin.read())
    except BaseException:
        ergebnis = ergebnis_json({"codes": {"intern": 1}})
    ergebnis_abgeben(ergebnis)


if __name__ == "__main__":
    main()
