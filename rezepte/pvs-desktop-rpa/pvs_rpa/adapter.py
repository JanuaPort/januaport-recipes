"""Semantischer Vertrag für spätere Adapter, ohne Koordinaten und Namen.

Jede Methode erhält dieselbe absolute monotone Deadline des Laufs. Auch Warten
und das Lesen halbfertiger Fenster enden spätestens dort mit Zeitlimit.
Adapter geben ausschließlich Kennungen und typisierte Fakten zurück. Sie
protokollieren keine Inhalte und schreiben keine Dateien. UI-Voraussetzungen
werden unmittelbar vor jeder Wirkung erneut geprüft; eine unklare Wirkung
wird als Fehler zurückgegeben und nicht automatisch wiederholt.
"""

from dataclasses import dataclass
from typing import Protocol

from .codes import Code

ZEITLIMIT_S = 5.0


@dataclass(frozen=True, slots=True)
class Anmeldung:
    kennung: str
    revision: int = 0
    bekannt: bool = True
    termin_heute: bool = True
    erste_lesung_quartal: bool = False
    daten_gleich: bool = True
    karte_gueltig: bool = True
    schon_angenommen: bool = False
    kostentraeger_regulaer: bool = True
    kategorie_bekannt: bool = True
    vollstaendig: bool = True


@dataclass(frozen=True, slots=True)
class Ziel:
    programm: str
    monitor: int
    ansicht: str


class Dialog(Exception):
    pass


class Gesperrt(Exception):
    pass


class NichtBereit(Exception):
    pass


class Zeitlimit(Exception):
    pass


class ProgrammFehlt(Exception):
    pass


class KontextGewechselt(Exception):
    pass


def fehlercode(fehler: BaseException, *, annahme: bool) -> Code:
    # Nur diese expliziten Zustandssignale sind fachliche Fehler.
    # Alle anderen Ausnahmen, einschließlich Abbruchsignalen, ergeben intern.
    typ = type(fehler)
    gemeinsam = {Dialog: Code.DIALOG, NichtBereit: Code.PVS_NICHT_BEREIT,
                 Zeitlimit: Code.ZEITLIMIT}
    speziell = ({Gesperrt: Code.GESPERRT} if annahme else
                {ProgrammFehlt: Code.PROGRAMM_FEHLT, KontextGewechselt: Code.MEHRDEUTIG})
    return (gemeinsam | speziell).get(typ, Code.INTERN)


class PVSAdapter(Protocol):
    def uhr(self) -> float:
        """Monotone Sekunden; echte Adapter verwenden time.monotonic."""
        ...

    def bereit(self, deadline: float) -> None:
        """Nur prüfen; bei Dialog oder fehlender Sitzung abbrechen, nie anmelden."""
        ...

    def anmeldungen(self, deadline: float) -> tuple[str, ...]:
        """Momentaufnahme stabiler Kartenkennungen; keine Zeilenindizes."""
        ...

    def lese_anmeldung(self, kennung: str, deadline: float) -> Anmeldung | None:
        """Frische, vollständige Fakten; verschwunden = None, halbfertig = Zeitlimit."""
        ...

    def annehmen(self, kennung: str, erwartet: Anmeldung, deadline: float) -> Code:
        """Vor Wirkung Kennung, Revision, Sperre, Dialog und Bereitschaft prüfen.

        Nur identischer Zustand darf wirken. Rückgaben: angenommen,
        schon_erledigt oder unbekannt (geändert/verschwunden). Keine Suche nach
        Namen, kein Retry bei unklarem Ausgang. Der Aufrufer entscheidet über
        nur_melden und die Quartalsregel; der Adapter bestätigt den Zustand.
        """
        ...

    def warte_fokus(self, deadline: float) -> None:
        """Passiv bis Fokus beim PVS; keine Aktivierung und kein UI-Schritt."""
        ...

    def offene_kennungen(self, deadline: float) -> tuple[str, ...]:
        """Alle offenen Patienten des PVS, ausschließlich eindeutige Kennungen."""
        ...


class ProgrammAdapter(Protocol):
    def pruefe_ziel(self, ziel: Ziel, deadline: float) -> None:
        """Vor UI alle Programme/Monitore/Ansichten prüfen; kein Programm starten.

        Monitor und DPI über semantische UI-/Monitor-Schnittstellen auflösen;
        die Schnittstelle und der Kern verwenden keine festen Koordinaten.
        """
        ...

    def zeige(self, kennung: str, ziel: Ziel, deadline: float) -> None:
        """Bestehende Instanz umschalten, Monitor und feste Ansicht einstellen.

        Vor jeder Wirkung Kontext (genau dieser Patient), Dialog, Ziel und
        Deadline erneut prüfen. Erster UI-Schritt erst nach warte_fokus.
        Keine zweite Instanz, kein Dialogwegklicken, kein Klick auf Verdacht.
        Bei Verlust einer Voraussetzung abbrechen; Teilwirkung nicht zurückrollen.
        """
        ...


class DesktopAdapter(PVSAdapter, ProgrammAdapter, Protocol):
    pass
