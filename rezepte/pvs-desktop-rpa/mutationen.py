"""Serielle Mutationsproben: Quelltext nur im Speicher ersetzen, nie auf Platte.

Jede Probe startet einen isolierten unittest-Prozess und muss mindestens eine
Assertion verletzen. Import-/Syntaxfehler allein gelten nicht als Nachweis.
"""

from pathlib import Path
import subprocess
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent

# (Bezeichnung, Modul, exakter Quelltext, Ersatz). Die ersten vier sind Pflicht.
PROBEN = [
    ("a-nur-melden-ignoriert", "pvs_rpa.kern_annahme", "if nur_melden:", "if False:"),
    ("b-ausnahmetext-im-ergebnis", "pvs_rpa.kern_annahme",
     "zaehle(ergebnis, fehlercode(fehler, annahme=True))",
     "zaehle(ergebnis, fehlercode(fehler, annahme=True)); ergebnis['text'] = str(fehler)"),
    ("c-name-statt-kennung", "pvs_rpa.kern_annahme",
     "if kennung in gesehen:\n                zaehle(ergebnis, Code.DOPPELT)\n                continue\n            gesehen.add(kennung)",
     "if adapter.namen[kennung] in gesehen:\n                zaehle(ergebnis, Code.DOPPELT)\n                continue\n            gesehen.add(adapter.namen[kennung])"),
    ("d-unbekannt-annehmen", "pvs_rpa.kern_annahme",
     "if not eintrag.kategorie_bekannt:\n        return Code.UNBEKANNT",
     "if not eintrag.kategorie_bekannt:\n        return Code.ANGENOMMEN"),
]


def sperre(name, modul, bedingung):
    PROBEN.append((name, modul, "if " + bedingung + ":", "if False:"))


for name, bedingung in (
    ("identitaet", "type(eintrag) is not Anmeldung or eintrag.kennung != kennung"),
    ("kennung-leer", "type(kennung) is not str or not kennung"),
    ("revision", "type(eintrag.revision) is not int or eintrag.revision < 0"),
    ("halb-gefuellt-kern", "not eintrag.vollstaendig"),
    ("schon-erledigt", "eintrag.schon_angenommen"),
    ("karte", "not eintrag.karte_gueltig"),
    ("neu", "not eintrag.bekannt"),
    ("abweichung", "not eintrag.daten_gleich"),
    ("kostentraeger", "not eintrag.kostentraeger_regulaer"),
    ("kein-termin", "not eintrag.termin_heute"),
    ("quartal", "eintrag.erste_lesung_quartal and not quartal_annehmen"),
    ("schalter-typ", "type(nur_melden) is not bool or type(quartal_annehmen) is not bool"),
    ("annahme-deadline", "uhr() >= deadline"),
    ("annahme-rueckgabe", "type(code) is not Code or code not in (Code.ANGENOMMEN, Code.SCHON_ERLEDIGT, Code.UNBEKANNT)"),
):
    sperre(name, "pvs_rpa.kern_annahme", bedingung)

PROBEN.append(("fakten-typ", "pvs_rpa.kern_annahme",
               'if any(type(getattr(eintrag, f.name)) is not bool for f in fields(Anmeldung)\n           if f.name not in ("kennung", "revision")):',
               "if False:"))
PROBEN.append(("doppelte-karte", "pvs_rpa.kern_annahme", "if kennung in gesehen:", "if False:"))

for name, bedingung in (
    ("setup-geschlossen", "type(setup) is not str or setup not in SETUPS"),
    ("kein-patient", "not offen"),
    ("mehrdeutig", "len(offen) != 1"),
    ("offene-kennung", "type(kennung) is not str or not kennung"),
    ("ansicht-deadline", "uhr() >= deadline"),
):
    sperre(name, "pvs_rpa.kern_ansicht", bedingung)
PROBEN.extend([
    ("fokus-wartung", "pvs_rpa.kern_ansicht", "adapter.warte_fokus(deadline)", "pass"),
    ("ziele-vorab-pruefen", "pvs_rpa.kern_ansicht", "adapter.pruefe_ziel(ziel, deadline)", "pass"),
    ("zweite-instanz", "pvs_rpa.mock", "self.programme[ziel.programm] = kennung",
     "self.programme[ziel.programm] = kennung; self.instanzen[ziel.programm] += 1"),
    ("ausnahmetext-uc2", "pvs_rpa.kern_ansicht",
     "zaehle(ergebnis, fehlercode(fehler, annahme=False))",
     "zaehle(ergebnis, fehlercode(fehler, annahme=False)); ergebnis['text'] = str(fehler)"),
    ("letzte-ausgabesperre", "annahme", "ausgabe = ergebnis_json(json.loads(ergebnis))",
     "ausgabe = ergebnis"),
])
for name, bedingung in (
    ("mock-deadline", "self.zeit >= deadline"),
    ("mock-bereitschaft", 'self.pvs_zustand != "bereit"'),
    ("mock-dialog", "self.dialog"),
    ("mock-gesperrt", "kennung in self.gesperrt"),
    ("mock-halb-gefuellt", "eintrag is not None and eintrag.vollstaendig is False"),
    ("mock-zustandsvergleich", "aktuell is None or aktuell != erwartet or aktuell.kennung != kennung"),
    ("mock-idempotenz", "kennung in self.angenommen or aktuell.schon_angenommen"),
    ("mock-programm-fehlt", "ziel.programm not in self.programme"),
    ("mock-dpi-und-ansicht", 'type(dpi) is not int or dpi <= 0 or ziel.ansicht not in ("ansicht_a", "ansicht_b", "ansicht_c")'),
    ("mock-fokus-bestaetigt", "not self.fokus_bestaetigt"),
    ("mock-patient-gewechselt", "self.offene_patienten != [kennung]"),
):
    sperre(name, "pvs_rpa.mock", bedingung)

for name, bedingung in (
    ("eingabe-doppelte-schluessel", "schluessel in ergebnis"),
    ("eingabe-objekt", "type(eingabe) is not dict"),
    ("eingabe-uc1-felder", 'set(eingabe) - {"nur_melden", "quartal_annehmen"}'),
    ("eingabe-schalter-typ", "any(type(v) is not bool for v in eingabe.values())"),
    ("eingabe-uc2-felder", 'set(eingabe) != {"setup"} or type(eingabe["setup"]) is not str'),
):
    sperre(name, "pvs_rpa.eingabe", bedingung)
for name, bedingung in (
    ("ausgabe-felder", 'type(ergebnis) is not dict or set(ergebnis) != {"codes"}'),
    ("ausgabe-codes", "type(code) is not str or code not in {c.value for c in Code}"),
    ("ausgabe-zaehler", "type(anzahl) is not int or anzahl < 0"),
):
    sperre(name, "pvs_rpa.codes", bedingung)

BOOTSTRAP = r'''
import importlib.abc, importlib.util, io, pathlib, sys, unittest
sys.dont_write_bytecode = True
root, modul, alt, neu, index = sys.argv[1:]
root = pathlib.Path(root)
pfad = root.joinpath(*modul.split('.')).with_suffix('.py')
quelle = pfad.read_text(encoding='utf-8')
assert alt in quelle
teile = quelle.split(alt)
index = int(index)
mutiert = alt.join(teile[:index+1]) + neu + alt.join(teile[index+1:])
compile(mutiert, str(pfad), 'exec')
class Loader(importlib.abc.MetaPathFinder, importlib.abc.Loader):
    def find_spec(self, fullname, path=None, target=None):
        if fullname == modul:
            return importlib.util.spec_from_loader(fullname, self, origin=str(pfad))
    def create_module(self, spec):
        return None
    def exec_module(self, module):
        module.__file__ = str(pfad)
        exec(compile(mutiert, str(pfad), 'exec'), module.__dict__)
sys.meta_path.insert(0, Loader())
suite = unittest.defaultTestLoader.discover(str(root), pattern='tests.py')
result = unittest.TextTestRunner(stream=io.StringIO()).run(suite)
print(len(result.failures), len(result.errors), result.testsRun)
sys.exit(10 if result.failures else 1)
'''


def main():
    dateien = {p: p.read_bytes() for p in HERE.rglob("*") if p.is_file()}
    anzahl = 0
    for name, modul, alt, neu in PROBEN:
        quelle = HERE.joinpath(*modul.split('.')).with_suffix('.py').read_text(encoding="utf-8")
        vorkommen = quelle.count(alt)
        assert vorkommen > 0, name
        for index in range(vorkommen):
            result = subprocess.run([sys.executable, "-I", "-B", "-c", BOOTSTRAP,
                                     str(HERE), modul, alt, neu, str(index)],
                                    capture_output=True, text=True, timeout=30)
            if result.returncode != 10:
                raise AssertionError(f"Mutation nicht durch Assertion erkannt: {name}/{index+1}")
            print(f"ROT {name}/{index+1}: {result.stdout.strip()}")
            anzahl += 1
    assert dateien == {p: p.read_bytes() for p in HERE.rglob("*") if p.is_file()}
    result = subprocess.run([sys.executable, "-I", "-B", "-m", "unittest", "discover",
                             "-s", str(HERE), "-p", "tests.py"],
                            capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, "Unveraenderte Fassung nicht gruen"
    print(f"OK {anzahl}/{anzahl} rot; unveraenderte Fassung gruen; keine Quelldatei geaendert.")


if __name__ == "__main__":
    main()
