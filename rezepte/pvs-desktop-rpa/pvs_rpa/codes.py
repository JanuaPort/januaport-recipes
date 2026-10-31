"""Geschlossene Ausgabe: ausschließlich feste Codes und ganzzahlige Zähler."""

from enum import Enum
import json


class Code(str, Enum):
    ANGENOMMEN = "angenommen"
    WUERDE_ANNEHMEN = "wuerde_annehmen"
    KEIN_TERMIN = "kein_termin"
    QUARTAL_ERST = "quartal_erst"
    ABWEICHUNG = "abweichung"
    NEU = "neu"
    KARTE = "karte"
    SCHON_ERLEDIGT = "schon_erledigt"
    DOPPELT = "doppelt"
    KOSTENTRAEGER = "kostentraeger"
    UNBEKANNT = "unbekannt"
    GESPERRT = "gesperrt"
    GEOEFFNET = "geoeffnet"
    TEILWEISE = "teilweise"
    KEIN_PATIENT = "kein_patient"
    MEHRDEUTIG = "mehrdeutig"
    PROGRAMM_FEHLT = "programm_fehlt"
    PVS_NICHT_BEREIT = "pvs_nicht_bereit"
    DIALOG = "dialog"
    ZEITLIMIT = "zeitlimit"
    INTERN = "intern"


def zaehle(ergebnis: dict, code: Code) -> None:
    codes = ergebnis["codes"]
    codes[code.value] = codes.get(code.value, 0) + 1


def ergebnis_json(ergebnis: dict) -> str:
    """Letzte Ausgabesperre, auch bei einer fehlerhaften internen Rückgabe."""
    try:
        if type(ergebnis) is not dict or set(ergebnis) != {"codes"}:
            raise ValueError
        codes = ergebnis["codes"]
        if type(codes) is not dict:
            raise ValueError
        for code, anzahl in codes.items():
            if type(code) is not str or code not in {c.value for c in Code}:
                raise ValueError
            if type(anzahl) is not int or anzahl < 0:
                raise ValueError
        return json.dumps(ergebnis, sort_keys=True, separators=(",", ":"))
    except BaseException:
        return '{"codes":{"intern":1}}'
