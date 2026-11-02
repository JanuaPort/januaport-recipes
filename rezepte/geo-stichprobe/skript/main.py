"""Dünner Läufer-Adapter: januaport.input/call/log → Fachkern → Zähler-JSON."""
import json
from pathlib import Path
import januaport
from stichprobe import EingabeUngueltig, ausfuehren


def main():
    fragen = json.loads(Path(__file__).with_name("fragen.json").read_text(encoding="utf-8"))
    try:
        ergebnis = ausfuehren(januaport.input, fragen, januaport.call, januaport.log)
    except EingabeUngueltig:
        januaport.log("eingabe_ungueltig")
        print(json.dumps({"fehler": "eingabe_ungueltig"}))
        return 1
    print(json.dumps(ergebnis, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
