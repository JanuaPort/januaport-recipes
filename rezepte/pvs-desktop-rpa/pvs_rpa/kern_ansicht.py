"""UC2: feste Setups, keine Patientendaten in der Eingabe."""

from time import monotonic
from types import MappingProxyType
from typing import Callable

from .adapter import DesktopAdapter, ZEITLIMIT_S, Zeitlimit, Ziel, fehlercode
from .codes import Code, zaehle

# Synthetische Platzhalter; fachliche Ansichten vor Sprint-1-Abnahme festlegen.
SETUPS = MappingProxyType({
    "setup_a": (Ziel("programm_1", 1, "ansicht_a"), Ziel("programm_2", 2, "ansicht_a")),
    "setup_b": (Ziel("programm_1", 1, "ansicht_b"), Ziel("programm_2", 2, "ansicht_b")),
    "setup_c": (Ziel("programm_1", 1, "ansicht_c"), Ziel("programm_2", 2, "ansicht_c")),
})


def run_ansicht(adapter: DesktopAdapter, setup: str, *, uhr: Callable[[], float] = monotonic) -> dict:
    ergebnis = {"codes": {}}
    gezeigt = 0
    try:
        if type(setup) is not str or setup not in SETUPS:
            raise ValueError
        deadline = uhr() + ZEITLIMIT_S
        adapter.bereit(deadline)
        adapter.warte_fokus(deadline)
        offen = tuple(adapter.offene_kennungen(deadline))
        if not offen:
            zaehle(ergebnis, Code.KEIN_PATIENT)
            return ergebnis
        if len(offen) != 1:
            zaehle(ergebnis, Code.MEHRDEUTIG)
            return ergebnis
        kennung = offen[0]
        if type(kennung) is not str or not kennung:
            raise ValueError
        for ziel in SETUPS[setup]:
            adapter.pruefe_ziel(ziel, deadline)
        for ziel in SETUPS[setup]:
            if uhr() >= deadline:
                raise Zeitlimit
            adapter.zeige(kennung, ziel, deadline)
            gezeigt += 1
            zaehle(ergebnis, Code.GEOEFFNET)
    except BaseException as fehler:
        if gezeigt:
            # Ein Monitor zeigt schon den neuen, der andere noch den vorigen Patienten.
            zaehle(ergebnis, Code.TEILWEISE)
        zaehle(ergebnis, fehlercode(fehler, annahme=False))
    return ergebnis
