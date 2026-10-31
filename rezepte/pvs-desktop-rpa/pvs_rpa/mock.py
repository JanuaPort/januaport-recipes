"""Ausschließlich synthetischer Zustand im Speicher, virtuelle monotone Uhr."""

from dataclasses import replace

from .adapter import (Anmeldung, Dialog, Gesperrt, KontextGewechselt, NichtBereit,
                      ProgrammFehlt, Zeitlimit, Ziel)
from .codes import Code


class MockAdapter:
    def __init__(self, eintraege=(), *, reihenfolge=None, offene_patienten=None,
                 pvs_zustand="bereit", monitor_dpi=None, fokus_nach=0):
        self.eintraege = {e.kennung: e for e in eintraege}
        self.reihenfolge = list(self.eintraege) if reihenfolge is None else list(reihenfolge)
        # Nur Testdaten zur Namensgleichheit, außerhalb des Adapter-Vertrags.
        self.namen = {k: "Test, Patient 07" for k in self.eintraege}
        self.geburtsjahre = {k: 0 for k in self.eintraege}
        self.kassen = {k: "Kasse_A" if i % 2 == 0 else "Kasse_B"
                       for i, k in enumerate(self.eintraege)}
        self.offene_patienten = list(offene_patienten or [])
        self.pvs_zustand = pvs_zustand
        self.monitor_dpi = {1: 96, 2: 144} if monitor_dpi is None else dict(monitor_dpi)
        self.programme = {"programm_1": None, "programm_2": None}
        self.instanzen = {"programm_1": 1, "programm_2": 1}
        self.dialog = False
        self.gesperrt = set()
        self.angenommen = set()
        self.annahme_aufrufe = []
        self.ui_schritte = []
        self.aufrufe = []  # Nur feste Methodennamen, keine Inhalte.
        self.fehler = {}
        self.verzoegerung = {}
        self.nach_lesen = None
        self.vor_zeige = None
        self.fokus_nach = fokus_nach
        self.fokus_bestaetigt = False
        self.erste_ui_zeit = None
        self.zeit = 0.0

    def uhr(self):
        return self.zeit

    def _schritt(self, methode, deadline):
        self.aufrufe.append(methode)
        if methode in self.fehler:
            raise self.fehler[methode]
        self.zeit += self.verzoegerung.get(methode, 0)
        self._sicher(deadline)

    def _sicher(self, deadline):
        if self.zeit >= deadline:
            raise Zeitlimit
        if self.pvs_zustand != "bereit":
            raise NichtBereit
        if self.dialog:
            raise Dialog

    def bereit(self, deadline):
        self._schritt("bereit", deadline)

    def anmeldungen(self, deadline):
        self._schritt("anmeldungen", deadline)
        return tuple(self.reihenfolge)

    def lese_anmeldung(self, kennung, deadline):
        self._schritt("lese_anmeldung", deadline)
        if kennung in self.gesperrt:
            raise Gesperrt
        eintrag = self.eintraege.get(kennung)
        if eintrag is not None and eintrag.vollstaendig is False:
            self.zeit = deadline
            raise Zeitlimit
        if self.nach_lesen is not None:
            self.nach_lesen(self, kennung)
        return replace(eintrag, schon_angenommen=True) if eintrag is not None and kennung in self.angenommen else eintrag

    def annehmen(self, kennung, erwartet, deadline):
        self.annahme_aufrufe.append(kennung)
        self._schritt("annehmen", deadline)
        if kennung in self.gesperrt:
            raise Gesperrt
        aktuell = self.eintraege.get(kennung)
        if aktuell is None or aktuell != erwartet or aktuell.kennung != kennung:
            return Code.UNBEKANNT
        if kennung in self.angenommen or aktuell.schon_angenommen:
            return Code.SCHON_ERLEDIGT
        self.angenommen.add(kennung)
        return Code.ANGENOMMEN

    def warte_fokus(self, deadline):
        self._schritt("warte_fokus", deadline)
        self.zeit = max(self.zeit, min(self.fokus_nach, deadline))
        self._sicher(deadline)
        self.fokus_bestaetigt = True

    def offene_kennungen(self, deadline):
        self._schritt("offene_kennungen", deadline)
        return tuple(self.offene_patienten)

    def pruefe_ziel(self, ziel: Ziel, deadline):
        self._schritt("pruefe_ziel", deadline)
        if ziel.programm not in self.programme:
            raise ProgrammFehlt
        dpi = self.monitor_dpi.get(ziel.monitor)
        if type(dpi) is not int or dpi <= 0 or ziel.ansicht not in ("ansicht_a", "ansicht_b", "ansicht_c"):
            raise ValueError

    def zeige(self, kennung, ziel, deadline):
        if self.vor_zeige is not None:
            self.vor_zeige(self)
        self._schritt("zeige", deadline)
        self.pruefe_ziel(ziel, deadline)
        if not self.fokus_bestaetigt:
            raise Zeitlimit
        if self.offene_patienten != [kennung]:
            raise KontextGewechselt
        if self.erste_ui_zeit is None:
            self.erste_ui_zeit = self.zeit
        self.programme[ziel.programm] = kennung
        self.ui_schritte.append((kennung, ziel.programm, ziel.monitor, ziel.ansicht))


def demo():
    """Offensichtlich erfunden; kein Produktzugriff und kein Einlesen von Dateien."""
    return MockAdapter([Anmeldung("T-0000-0007")], offene_patienten=["T-0000-0007"])
