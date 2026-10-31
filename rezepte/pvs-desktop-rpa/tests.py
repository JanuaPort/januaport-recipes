"""Offline-Vertragsproben am Fachkern und an den echten Einstiegspunkten."""

import contextlib
from dataclasses import replace
import importlib
import io
import json
from pathlib import Path
import subprocess
import sys
import unittest

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from pvs_rpa.adapter import Anmeldung, Dialog, Gesperrt, NichtBereit, Zeitlimit, Ziel
from pvs_rpa.adapter import KontextGewechselt, ProgrammFehlt
from pvs_rpa.codes import Code, ergebnis_json
from pvs_rpa.eingabe import lesen
from pvs_rpa.kern_annahme import bewerten, run_annahme
from pvs_rpa.kern_ansicht import SETUPS, run_ansicht
from pvs_rpa.mock import MockAdapter


KENNUNG = "T-0000-0007"
ANDERE = "T-0000-0008"
NAME = "Test, Patient 07"
LECK = f"Fenstertitel {NAME} {KENNUNG} AUSNAHME-INHALT"


def befund(**werte):
    return replace(Anmeldung(KENNUNG), **werte)


def annahme(mock, **optionen):
    return run_annahme(mock, uhr=mock.uhr, **optionen)


def ansicht(mock, setup="setup_a"):
    return run_ansicht(mock, setup, uhr=mock.uhr)


class AnnahmeTests(unittest.TestCase):
    def test_ungueltige_fakten_direkt_am_fachkern(self):
        for eintrag, kennung in ((None, KENNUNG), (befund(), ANDERE),
                                  (befund(kennung=""), ""), (befund(revision=-1), KENNUNG),
                                  (befund(bekannt="ja"), KENNUNG)):
            with self.subTest(eintrag=eintrag):
                self.assertEqual(bewerten(eintrag, kennung, False), Code.UNBEKANNT)
        with self.assertRaises(Zeitlimit):
            bewerten(befund(vollstaendig=False), KENNUNG, False)

    def test_kategorientabelle(self):
        faelle = [
            ({}, "angenommen"),
            ({"termin_heute": False}, "kein_termin"),
            ({"erste_lesung_quartal": True}, "quartal_erst"),
            ({"daten_gleich": False}, "abweichung"),
            ({"bekannt": False}, "neu"),
            ({"karte_gueltig": False}, "karte"),
            ({"schon_angenommen": True}, "schon_erledigt"),
            ({"kostentraeger_regulaer": False}, "kostentraeger"),
            ({"kategorie_bekannt": False}, "unbekannt"),
        ]
        for werte, code in faelle:
            with self.subTest(code=code):
                mock = MockAdapter([befund(**werte)])
                self.assertEqual(annahme(mock, nur_melden=False), {"codes": {code: 1}})
                self.assertEqual(len(mock.annahme_aufrufe), int(code == "angenommen"))

    def test_vorgabe_ist_nur_melden(self):
        mock = MockAdapter([befund()])
        self.assertEqual(annahme(mock), {"codes": {"wuerde_annehmen": 1}})
        self.assertEqual(mock.annahme_aufrufe, [])
        self.assertEqual(mock.angenommen, set())

    def test_melden_alle_kategorien_ohne_schreibaufruf(self):
        for feld in (None, "termin_heute", "bekannt", "daten_gleich", "karte_gueltig",
                     "kostentraeger_regulaer", "kategorie_bekannt", "erste_lesung_quartal",
                     "schon_angenommen"):
            with self.subTest(feld=feld):
                werte = {} if feld is None else {feld: feld in ("erste_lesung_quartal", "schon_angenommen")}
                mock = MockAdapter([befund(**werte)])
                annahme(mock, nur_melden=True, quartal_annehmen=True)
                self.assertEqual(mock.annahme_aufrufe, [])

    def test_quartal_schalter(self):
        for melden, code in ((True, "wuerde_annehmen"), (False, "angenommen")):
            with self.subTest(melden=melden):
                mock = MockAdapter([befund(erste_lesung_quartal=True)])
                self.assertEqual(annahme(mock, nur_melden=melden, quartal_annehmen=True), {"codes": {code: 1}})

    def test_quartal_umgeht_keine_weitere_sperre(self):
        for feld in ("termin_heute", "bekannt", "daten_gleich", "karte_gueltig",
                     "kostentraeger_regulaer", "kategorie_bekannt"):
            with self.subTest(feld=feld):
                mock = MockAdapter([befund(erste_lesung_quartal=True, **{feld: False})])
                result = annahme(mock, nur_melden=False, quartal_annehmen=True)
                self.assertNotIn("angenommen", result["codes"])
                self.assertEqual(mock.annahme_aufrufe, [])

    def test_idempotenz(self):
        mock = MockAdapter([befund()])
        self.assertEqual(annahme(mock, nur_melden=False), {"codes": {"angenommen": 1}})
        self.assertEqual(annahme(mock, nur_melden=False), {"codes": {"schon_erledigt": 1}})
        self.assertEqual(mock.annahme_aufrufe, [KENNUNG])

    def test_doppelte_karte(self):
        mock = MockAdapter([befund()], reihenfolge=[KENNUNG, KENNUNG])
        self.assertEqual(annahme(mock, nur_melden=False), {"codes": {"angenommen": 1, "doppelt": 1}})
        self.assertEqual(mock.annahme_aufrufe, [KENNUNG])

    def test_namensgleichheit_und_geburtsjahr(self):
        mock = MockAdapter([befund(), befund(kennung=ANDERE)])
        self.assertEqual(mock.namen[KENNUNG], mock.namen[ANDERE])
        self.assertEqual(mock.geburtsjahre[KENNUNG], mock.geburtsjahre[ANDERE])
        self.assertEqual(annahme(mock, nur_melden=False), {"codes": {"angenommen": 2}})
        self.assertEqual(mock.annahme_aufrufe, [KENNUNG, ANDERE])
        self.assertNotIn("name", Anmeldung.__dataclass_fields__)

    def test_sortiersprung_und_neuer_eintrag(self):
        mock = MockAdapter([befund(), befund(kennung=ANDERE)])
        neu = "T-0000-0009"
        def wechsel(adapter, kennung):
            adapter.eintraege[neu] = befund(kennung=neu)
            adapter.reihenfolge[:] = [neu, ANDERE, KENNUNG]
        mock.nach_lesen = wechsel
        self.assertEqual(annahme(mock, nur_melden=False), {"codes": {"angenommen": 2}})
        self.assertEqual(mock.annahme_aufrufe, [KENNUNG, ANDERE])
        mock.nach_lesen = None
        self.assertEqual(annahme(mock, nur_melden=False), {"codes": {"angenommen": 1, "schon_erledigt": 2}})

    def test_verschwundener_eintrag(self):
        mock = MockAdapter([befund()], reihenfolge=[ANDERE])
        self.assertEqual(annahme(mock, nur_melden=False), {"codes": {"unbekannt": 1}})
        self.assertEqual(mock.annahme_aufrufe, [])

    def test_falsche_kennung_aus_adapter(self):
        mock = MockAdapter([befund()])
        mock.lese_anmeldung = lambda *args: befund(kennung=ANDERE)
        self.assertEqual(annahme(mock, nur_melden=False), {"codes": {"unbekannt": 1}})
        self.assertEqual(mock.annahme_aufrufe, [])

    def test_zustand_aendert_sich_vor_schreiben(self):
        for modus in ("revision", "dialog", "gesperrt", "entfernt"):
            with self.subTest(modus=modus):
                mock = MockAdapter([befund()])
                def wechsel(adapter, kennung):
                    if modus == "revision":
                        adapter.eintraege[kennung] = befund(revision=1, karte_gueltig=False)
                    elif modus == "entfernt":
                        del adapter.eintraege[kennung]
                    elif modus == "dialog":
                        adapter.dialog = True
                    else:
                        adapter.gesperrt.add(kennung)
                mock.nach_lesen = wechsel
                result = annahme(mock, nur_melden=False)
                self.assertNotIn("angenommen", result["codes"])
                self.assertEqual(mock.angenommen, set())

    def test_dialog_gesperrt_zeitlimit_unvollstaendig(self):
        for modus, code in (("dialog", "dialog"), ("gesperrt", "gesperrt"),
                            ("verzoegert", "zeitlimit"), ("halb", "zeitlimit")):
            with self.subTest(modus=modus):
                mock = MockAdapter([befund(vollstaendig=modus != "halb")])
                mock.dialog = modus == "dialog"
                if modus == "gesperrt":
                    mock.gesperrt.add(KENNUNG)
                if modus == "verzoegert":
                    mock.verzoegerung["lese_anmeldung"] = 6
                self.assertEqual(annahme(mock, nur_melden=False), {"codes": {code: 1}})
                self.assertEqual(mock.angenommen, set())

    def test_verzoegert_aber_rechtzeitig(self):
        mock = MockAdapter([befund()])
        mock.verzoegerung["lese_anmeldung"] = 0.5
        self.assertEqual(annahme(mock, nur_melden=False), {"codes": {"angenommen": 1}})

    def test_ein_gemeinsames_zeitlimit(self):
        mock = MockAdapter([befund(), befund(kennung=ANDERE)])
        mock.verzoegerung["lese_anmeldung"] = 3
        self.assertEqual(annahme(mock, nur_melden=False), {"codes": {"angenommen": 1, "zeitlimit": 1}})
        self.assertEqual(mock.annahme_aufrufe, [KENNUNG])

    def test_kern_prueft_deadline_vor_lesen(self):
        mock = MockAdapter([befund()])
        zeiten = iter([0, 6])
        self.assertEqual(run_annahme(mock, nur_melden=False, uhr=lambda: next(zeiten)),
                         {"codes": {"zeitlimit": 1}})
        self.assertNotIn("lese_anmeldung", mock.aufrufe)

    def test_kern_prueft_deadline_vor_schreiben(self):
        mock = MockAdapter([befund()])
        zeiten = iter([0, 0, 6])
        self.assertEqual(run_annahme(mock, nur_melden=False, uhr=lambda: next(zeiten)),
                         {"codes": {"zeitlimit": 1}})
        self.assertEqual(mock.annahme_aufrufe, [])

    def test_ungueltige_kennung_in_momentaufnahme(self):
        for kennung in ("", 7, None):
            with self.subTest(kennung=kennung):
                mock = MockAdapter([befund()], reihenfolge=[kennung])
                self.assertEqual(annahme(mock, nur_melden=False), {"codes": {"unbekannt": 1}})
                self.assertNotIn("lese_anmeldung", mock.aufrufe)

    def test_pvs_nicht_bereit(self):
        for zustand in ("nicht_gestartet", "anmeldemaske", "gesperrt", "unbekannt"):
            with self.subTest(zustand=zustand):
                mock = MockAdapter([befund()], pvs_zustand=zustand)
                self.assertEqual(annahme(mock, nur_melden=False), {"codes": {"pvs_nicht_bereit": 1}})
                self.assertEqual(mock.annahme_aufrufe, [])

    def test_untypisierte_daten_werden_abgewiesen(self):
        for werte in ({"bekannt": "ja"}, {"termin_heute": 1}, {"kennung": ""},
                      {"revision": -1}, {"vollstaendig": "ja"}):
            with self.subTest(werte=werte):
                mock = MockAdapter([befund(**werte)])
                self.assertEqual(annahme(mock, nur_melden=False), {"codes": {"unbekannt": 1}})
                self.assertEqual(mock.angenommen, set())

    def test_ungueltige_schalter(self):
        for optionen in ({"nur_melden": "false"}, {"nur_melden": 0}, {"quartal_annehmen": 1}):
            with self.subTest(optionen=optionen):
                mock = MockAdapter([befund()])
                self.assertEqual(annahme(mock, **optionen), {"codes": {"intern": 1}})
                self.assertEqual(mock.aufrufe, [])

    def test_unerwartete_adapter_rueckgabe(self):
        for rueckgabe in (LECK, Code.GEOEFFNET, "angenommen"):
            with self.subTest(rueckgabe=rueckgabe):
                mock = MockAdapter([befund()])
                mock.annehmen = lambda *args: rueckgabe
                self.assertEqual(annahme(mock, nur_melden=False), {"codes": {"intern": 1}})


class AnsichtTests(unittest.TestCase):
    def test_kern_prueft_deadline_vor_ui(self):
        mock = MockAdapter(offene_patienten=[KENNUNG])
        zeiten = iter([0, 6])
        self.assertEqual(run_ansicht(mock, "setup_a", uhr=lambda: next(zeiten)),
                         {"codes": {"zeitlimit": 1}})
        self.assertNotIn("zeige", mock.aufrufe)

    def test_ungueltige_offene_kennung(self):
        for kennung in ("", 7, None):
            with self.subTest(kennung=kennung):
                mock = MockAdapter(offene_patienten=[kennung])
                self.assertEqual(ansicht(mock), {"codes": {"intern": 1}})
                self.assertNotIn("pruefe_ziel", mock.aufrufe)
                self.assertEqual(mock.ui_schritte, [])

    def test_setup_tabelle(self):
        erwartet = {
            "setup_a": (("programm_1", 1, "ansicht_a"), ("programm_2", 2, "ansicht_a")),
            "setup_b": (("programm_1", 1, "ansicht_b"), ("programm_2", 2, "ansicht_b")),
            "setup_c": (("programm_1", 1, "ansicht_c"), ("programm_2", 2, "ansicht_c")),
        }
        self.assertEqual(set(SETUPS), set(erwartet))
        for setup, ziele in erwartet.items():
            with self.subTest(setup=setup):
                mock = MockAdapter(offene_patienten=[KENNUNG], monitor_dpi={1: 96, 2: 144})
                self.assertEqual(ansicht(mock, setup), {"codes": {"geoeffnet": 2}})
                self.assertEqual([(z.programm, z.monitor, z.ansicht) for z in SETUPS[setup]], list(ziele))
                self.assertEqual(mock.ui_schritte, [(KENNUNG, *ziel) for ziel in ziele])

    def test_kein_patient_und_mehrdeutig(self):
        for offen, code in (([], "kein_patient"), ([KENNUNG, ANDERE], "mehrdeutig")):
            with self.subTest(code=code):
                mock = MockAdapter(offene_patienten=offen)
                self.assertEqual(ansicht(mock), {"codes": {code: 1}})
                self.assertEqual(mock.ui_schritte, [])
                self.assertNotIn("pruefe_ziel", mock.aufrufe)
                self.assertNotIn("zeige", mock.aufrufe)

    def test_programm_fehlt_auch_zweites_vor_erster_ui(self):
        for programm in ("programm_1", "programm_2"):
            with self.subTest(programm=programm):
                mock = MockAdapter(offene_patienten=[KENNUNG])
                del mock.programme[programm]
                self.assertEqual(ansicht(mock), {"codes": {"programm_fehlt": 1}})
                self.assertEqual(mock.ui_schritte, [])

    def test_anderer_patient_wird_umgeschaltet(self):
        mock = MockAdapter(offene_patienten=[KENNUNG])
        mock.programme.update({"programm_1": ANDERE, "programm_2": ANDERE})
        instanzen = mock.instanzen.copy()
        self.assertEqual(ansicht(mock), {"codes": {"geoeffnet": 2}})
        self.assertEqual(set(mock.programme.values()), {KENNUNG})
        self.assertEqual(mock.instanzen, instanzen)

    def test_fokus_wartung_vor_erster_ui(self):
        mock = MockAdapter(offene_patienten=[KENNUNG], fokus_nach=2)
        self.assertEqual(ansicht(mock), {"codes": {"geoeffnet": 2}})
        self.assertGreaterEqual(mock.erste_ui_zeit, 2)
        self.assertLess(mock.aufrufe.index("warte_fokus"), mock.aufrufe.index("zeige"))

    def test_fokus_kehrt_nicht_zurueck(self):
        mock = MockAdapter(offene_patienten=[KENNUNG], fokus_nach=6)
        self.assertEqual(ansicht(mock), {"codes": {"zeitlimit": 1}})
        self.assertEqual(mock.ui_schritte, [])

    def test_dialog_pvs_zeitlimit(self):
        for modus, code in (("dialog", "dialog"), ("nicht_gestartet", "pvs_nicht_bereit"),
                            ("anmeldemaske", "pvs_nicht_bereit"), ("gesperrt", "pvs_nicht_bereit"),
                            ("zeitlimit", "zeitlimit")):
            with self.subTest(modus=modus):
                mock = MockAdapter(offene_patienten=[KENNUNG])
                if modus == "dialog":
                    mock.dialog = True
                elif modus == "zeitlimit":
                    mock.verzoegerung["offene_kennungen"] = 6
                else:
                    mock.pvs_zustand = modus
                self.assertEqual(ansicht(mock), {"codes": {code: 1}})
                self.assertEqual(mock.ui_schritte, [])

    def test_patient_wechselt_waehrend_des_laufs(self):
        mock = MockAdapter(offene_patienten=[KENNUNG])
        def wechsel(adapter):
            adapter.offene_patienten[:] = [ANDERE]
        mock.vor_zeige = wechsel
        self.assertEqual(ansicht(mock), {"codes": {"mehrdeutig": 1}})
        self.assertEqual(mock.ui_schritte, [])

    def test_abbruch_nach_erster_wirkung_ohne_wiederholung(self):
        mock = MockAdapter(offene_patienten=[KENNUNG])
        def wechsel(adapter):
            if adapter.ui_schritte:
                adapter.dialog = True
        mock.vor_zeige = wechsel
        self.assertEqual(ansicht(mock), {"codes": {"geoeffnet": 1, "dialog": 1}})
        self.assertEqual(len(mock.ui_schritte), 1)

    def test_fehlender_monitor_oder_ungueltige_dpi(self):
        for dpi in ({1: 96}, {1: 96, 2: 0}, {1: 96, 2: "144"}):
            with self.subTest(dpi=dpi):
                mock = MockAdapter(offene_patienten=[KENNUNG], monitor_dpi=dpi)
                self.assertEqual(ansicht(mock), {"codes": {"intern": 1}})
                self.assertEqual(mock.ui_schritte, [])

    def test_ungueltiges_setup(self):
        for setup in ("unbekannt", "../setup_a", None, []):
            with self.subTest(setup=setup):
                mock = MockAdapter(offene_patienten=[KENNUNG])
                self.assertEqual(ansicht(mock, setup), {"codes": {"intern": 1}})
                self.assertEqual(mock.aufrufe, [])


class GrenzenTests(unittest.TestCase):
    def test_uhr_ausnahme_bleibt_intern(self):
        def kaputt():
            raise RuntimeError(LECK)
        for funktion, argumente in ((run_annahme, ()), (run_ansicht, ("setup_a",))):
            mock = MockAdapter([befund()], offene_patienten=[KENNUNG])
            self.assertEqual(funktion(mock, *argumente, uhr=kaputt), {"codes": {"intern": 1}})
            self.assertEqual(mock.aufrufe, [])

    def test_eingabekanal_wirft_ohne_leck(self):
        from unittest.mock import patch
        class Kaputt:
            def read(self):
                raise RuntimeError(LECK)
        for name in ("annahme", "ansicht"):
            out, err = io.StringIO(), io.StringIO()
            with patch.object(sys, "stdin", Kaputt()), contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                importlib.import_module(name).main()
            self.assertEqual(json.loads(out.getvalue()), {"codes": {"intern": 1}})
            self.assertEqual(err.getvalue(), "")

    def test_exakte_code_menge(self):
        self.assertEqual({c.value for c in Code}, {
            "angenommen", "wuerde_annehmen", "kein_termin", "quartal_erst", "abweichung",
            "neu", "karte", "schon_erledigt", "doppelt", "kostentraeger", "unbekannt",
            "gesperrt", "geoeffnet", "kein_patient", "mehrdeutig", "programm_fehlt",
            "pvs_nicht_bereit", "dialog", "zeitlimit", "intern",
        })

    def test_mock_sperren_direkt_an_der_wirkung(self):
        mock = MockAdapter([befund()], offene_patienten=[KENNUNG])
        ziel = Ziel("programm_1", 1, "ansicht_a")
        with self.assertRaises(Zeitlimit):
            mock.zeige(KENNUNG, ziel, 5)
        self.assertEqual(mock.ui_schritte, [])
        mock.warte_fokus(5)
        with self.assertRaises(ValueError):
            mock.pruefe_ziel(Ziel("programm_1", 1, "unbekannt"), 5)
        mock.angenommen.add(KENNUNG)
        self.assertEqual(mock.annehmen(KENNUNG, befund(), 5), Code.SCHON_ERLEDIGT)
        mock.angenommen.clear()
        mock.gesperrt.add(KENNUNG)
        with self.assertRaises(Gesperrt):
            mock.lese_anmeldung(KENNUNG, 5)
        with self.assertRaises(Gesperrt):
            mock.annehmen(KENNUNG, befund(), 5)
        self.assertEqual(mock.angenommen, set())
        mock.gesperrt.clear()
        mock.eintraege[KENNUNG] = befund(vollstaendig=False)
        with self.assertRaises(Zeitlimit):
            mock.lese_anmeldung(KENNUNG, 5)
        with self.assertRaises(Zeitlimit):
            mock.bereit(0)

    def test_ausgabekanal_wirft_ohne_traceback(self):
        import annahme as modul
        class Kaputt(io.StringIO):
            def write(self, text):
                raise RuntimeError(LECK)
        err = io.StringIO()
        with contextlib.redirect_stdout(Kaputt()), contextlib.redirect_stderr(err):
            modul.ergebnis_abgeben('{"codes":{"intern":1}}')
        self.assertEqual(err.getvalue(), "")

    def test_ausgabe_validiert_auch_direkte_aufrufe(self):
        import annahme as modul
        for text in (LECK, json.dumps({"text": LECK}), '{"codes":{"unbekannter_code":1}}'):
            out, err = io.StringIO(), io.StringIO()
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                modul.ergebnis_abgeben(text)
            try:
                wert = json.loads(out.getvalue())
            except ValueError:
                self.fail("Ausgabe ist kein geschlossenes JSON")
            self.assertEqual(wert, {"codes": {"intern": 1}})
            self.assertEqual(err.getvalue(), "")

    def test_parser_weist_verbotene_eingaben_ab(self):
        for text, uc1 in (('[]', True), ('null', True), ('{"patient":"T-0000-0007"}', True),
                          ('{"patient":true}', True),
                          ('{"nur_melden":0}', True), ('{}', False), ('{"setup":0}', False),
                          ('{"setup":"setup_a","patient":"T-0000-0007"}', False)):
            with self.subTest(text=text, uc1=uc1):
                try:
                    lesen(text, annahme=uc1)
                except BaseException as fehler:
                    self.assertIs(type(fehler), ValueError)
                else:
                    self.fail("Verbotene Eingabe akzeptiert")

    def test_eingabe_doppelte_schluessel_und_falsche_typen(self):
        for name, texte in (
            ("annahme", ('{"nur_melden":0}', '{"quartal_annehmen":1}',
                         '{"nur_melden":true,"nur_melden":false}')),
            ("ansicht", ('{"setup":1}', '{"setup":"setup_a","setup":"setup_b"}', '{}')),
        ):
            for text in texte:
                with self.subTest(name=name, text=text):
                    mock = MockAdapter([befund()], offene_patienten=[KENNUNG])
                    self.assertEqual(json.loads(importlib.import_module(name).ausfuehren(text, mock)),
                                     {"codes": {"intern": 1}})
                    self.assertEqual(mock.aufrufe, [])

    def test_alle_ausnahmen_ohne_leck_an_jeder_adapter_methode(self):
        for funktion, methoden in (
            (lambda m: annahme(m, nur_melden=False), ("bereit", "anmeldungen", "lese_anmeldung", "annehmen")),
            (ansicht, ("bereit", "warte_fokus", "offene_kennungen", "pruefe_ziel", "zeige")),
        ):
            for methode in methoden:
                signale = [(RuntimeError, "intern"), (SystemExit, "intern"), (KeyboardInterrupt, "intern"),
                           (Dialog, "dialog"), (NichtBereit, "pvs_nicht_bereit"), (Zeitlimit, "zeitlimit"),
                           (Gesperrt, "intern" if funktion is ansicht else "gesperrt"),
                           (ProgrammFehlt, "programm_fehlt" if funktion is ansicht else "intern"),
                           (KontextGewechselt, "mehrdeutig" if funktion is ansicht else "intern")]
                for typ, code in signale:
                    fehler = typ(LECK)
                    with self.subTest(methode=methode, typ=type(fehler).__name__):
                        mock = MockAdapter([befund()], offene_patienten=[KENNUNG])
                        mock.fehler[methode] = fehler
                        out, err = io.StringIO(), io.StringIO()
                        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                            result = funktion(mock)
                            encoded = ergebnis_json(result)
                        self.assertEqual(result, {"codes": {code: 1}})
                        self.assertEqual(out.getvalue() + err.getvalue(), "")
                        for verboten in (NAME, KENNUNG, "Fenstertitel", "AUSNAHME-INHALT", "Traceback"):
                            self.assertNotIn(verboten, encoded + out.getvalue() + err.getvalue())

    def test_ergebnis_hat_nur_codes_und_zaehler(self):
        self.assertEqual(json.loads(ergebnis_json({"codes": {c.value: 1 for c in Code}})),
                         {"codes": {c.value: 1 for c in Code}})
        for result in ({"codes": {LECK: 1}}, {"codes": {"intern": LECK}},
                       {"codes": {"intern": True}}, {"codes": {"intern": -1}},
                       {"codes": {}, "text": LECK}, {"codes": []}, None):
            with self.subTest(result=result):
                self.assertEqual(json.loads(ergebnis_json(result)), {"codes": {"intern": 1}})

    def test_einstiegspunkte_eingabepruefung(self):
        for name in ("annahme", "ansicht"):
            modul = importlib.import_module(name)
            ungueltig = ["kein JSON " + LECK, "[]", "null", '{"patient":"' + KENNUNG + '"}',
                         '{"setup":"setup_a","patient":"' + NAME + '"}',
                         '{"nur_melden":"false"}', '{"nur_melden":false,"nur_melden":true}']
            for eingabe in ungueltig:
                with self.subTest(name=name, eingabe=eingabe):
                    mock = MockAdapter([befund()], offene_patienten=[KENNUNG])
                    self.assertEqual(json.loads(modul.ausfuehren(eingabe, mock)), {"codes": {"intern": 1}})
                    self.assertEqual(mock.aufrufe, [])

    def test_einstiegspunkte_erfolg_und_leck(self):
        for name, eingabe, code in (("annahme", "{}", "wuerde_annehmen"),
                                    ("ansicht", '{"setup":"setup_b"}', "geoeffnet")):
            modul = importlib.import_module(name)
            mock = MockAdapter([befund()], offene_patienten=[KENNUNG])
            self.assertIn(code, json.loads(modul.ausfuehren(eingabe, mock))["codes"])
            mock.fehler["bereit"] = RuntimeError(LECK)
            out, err = io.StringIO(), io.StringIO()
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                modul.ergebnis_abgeben(modul.ausfuehren(eingabe, mock))
            self.assertEqual(json.loads(out.getvalue()), {"codes": {"intern": 1}})
            self.assertEqual(err.getvalue(), "")

    def test_cli_offline_dateifrei_und_ohne_nebenkanaele(self):
        # Audit-Hook im echten Prozess: auch Schreibversuche außerhalb des cwd,
        # Netz, Kindprozesse und TEMP würden die Probe abbrechen.
        probe = r'''
import io, json, os, pathlib, runpy, sys
sys.dont_write_bytecode = True
root = pathlib.Path(sys.argv[1]).resolve()
before = {str(p) for p in pathlib.Path.cwd().rglob('*')}
def audit(event, args):
    if event == 'open':
        mode, flags = args[1], args[2]
        if (isinstance(mode, str) and any(c in mode for c in 'wax+')) or (isinstance(flags, int) and flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND)):
            raise AssertionError('schreibversuch')
    if event in ('os.mkdir', 'os.remove', 'os.rename', 'os.rmdir', 'os.link', 'os.symlink', 'subprocess.Popen', 'tempfile.mkstemp', 'tempfile.mkdtemp') or event.startswith('socket.'):
        raise AssertionError('nebenkanal')
sys.addaudithook(audit)
sys.stdin = io.StringIO(sys.argv[3])
runpy.run_path(str(root / sys.argv[2]), run_name='__main__')
assert before == {str(p) for p in pathlib.Path.cwd().rglob('*')}
'''
        before = {p.relative_to(HERE) for p in HERE.rglob("*")}
        for name, eingabe, erwartet in (("annahme.py", "{}", {"wuerde_annehmen": 1}),
                                         ("annahme.py", '{"nur_melden":false}', {"angenommen": 1}),
                                         ("ansicht.py", '{"setup":"setup_a"}', {"geoeffnet": 2}),
                                         ("annahme.py", LECK, {"intern": 1})):
            with self.subTest(name=name, eingabe=eingabe):
                result = subprocess.run([sys.executable, "-I", "-B", "-c", probe, str(HERE), name, eingabe],
                                        cwd=HERE, capture_output=True, text=True, timeout=15)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(json.loads(result.stdout), {"codes": erwartet})
                self.assertEqual(result.stderr, "")
        self.assertEqual(before, {p.relative_to(HERE) for p in HERE.rglob("*")})


if __name__ == "__main__":
    unittest.main()
