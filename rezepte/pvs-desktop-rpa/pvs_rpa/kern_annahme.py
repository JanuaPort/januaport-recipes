"""UC1: im Zweifel liegen lassen, ausschließlich nach Kennung."""

from dataclasses import fields
from time import monotonic
from typing import Callable

from .adapter import Anmeldung, PVSAdapter, ZEITLIMIT_S, Zeitlimit, fehlercode
from .codes import Code, zaehle


def bewerten(eintrag: Anmeldung | None, kennung: str, quartal_annehmen: bool) -> Code:
    if type(eintrag) is not Anmeldung or eintrag.kennung != kennung:
        return Code.UNBEKANNT
    if type(kennung) is not str or not kennung:
        return Code.UNBEKANNT
    if type(eintrag.revision) is not int or eintrag.revision < 0:
        return Code.UNBEKANNT
    if any(type(getattr(eintrag, f.name)) is not bool for f in fields(Anmeldung)
           if f.name not in ("kennung", "revision")):
        return Code.UNBEKANNT
    if not eintrag.vollstaendig:
        raise Zeitlimit
    if not eintrag.kategorie_bekannt:
        return Code.UNBEKANNT
    if eintrag.schon_angenommen:
        return Code.SCHON_ERLEDIGT
    if not eintrag.karte_gueltig:
        return Code.KARTE
    if not eintrag.bekannt:
        return Code.NEU
    if not eintrag.daten_gleich:
        return Code.ABWEICHUNG
    if not eintrag.kostentraeger_regulaer:
        return Code.KOSTENTRAEGER
    if not eintrag.termin_heute:
        return Code.KEIN_TERMIN
    if eintrag.erste_lesung_quartal and not quartal_annehmen:
        return Code.QUARTAL_ERST
    return Code.ANGENOMMEN


def run_annahme(adapter: PVSAdapter, *, nur_melden: bool = True,
                quartal_annehmen: bool = False, uhr: Callable[[], float] = monotonic) -> dict:
    ergebnis = {"codes": {}}
    try:
        if type(nur_melden) is not bool or type(quartal_annehmen) is not bool:
            raise ValueError
        deadline = uhr() + ZEITLIMIT_S
        adapter.bereit(deadline)
        kennungen = tuple(adapter.anmeldungen(deadline))
        gesehen = set()
        for kennung in kennungen:
            if uhr() >= deadline:
                raise Zeitlimit
            if type(kennung) is not str or not kennung:
                zaehle(ergebnis, Code.UNBEKANNT)
                continue
            if kennung in gesehen:
                zaehle(ergebnis, Code.DOPPELT)
                continue
            gesehen.add(kennung)
            eintrag = adapter.lese_anmeldung(kennung, deadline)
            code = bewerten(eintrag, kennung, quartal_annehmen)
            if code == Code.ANGENOMMEN:
                if nur_melden:
                    code = Code.WUERDE_ANNEHMEN
                else:
                    if uhr() >= deadline:
                        raise Zeitlimit
                    code = adapter.annehmen(kennung, eintrag, deadline)
                    if type(code) is not Code or code not in (Code.ANGENOMMEN, Code.SCHON_ERLEDIGT, Code.UNBEKANNT):
                        raise ValueError
            zaehle(ergebnis, code)
    except BaseException as fehler:
        zaehle(ergebnis, fehlercode(fehler, annahme=True))
    return ergebnis
