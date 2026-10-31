"""Striktes JSON, damit Schalter und Setup die einzigen Eingaben bleiben."""

import json


def _eindeutig(paare):
    ergebnis = {}
    for schluessel, wert in paare:
        if schluessel in ergebnis:
            raise ValueError
        ergebnis[schluessel] = wert
    return ergebnis


def lesen(text: str, *, annahme: bool) -> dict:
    eingabe = json.loads(text, object_pairs_hook=_eindeutig)
    if type(eingabe) is not dict:
        raise ValueError
    if annahme:
        if set(eingabe) - {"nur_melden", "quartal_annehmen"}:
            raise ValueError
        if any(type(v) is not bool for v in eingabe.values()):
            raise ValueError
    else:
        if set(eingabe) != {"setup"} or type(eingabe["setup"]) is not str:
            raise ValueError
    return eingabe
