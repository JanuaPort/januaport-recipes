"""Serielle Mutationsproben am Fachkern UND echten main.py-Adapter.

Nur im Speicher veränderter Quelltext. Eine Assertion muss scheitern;
Import-, Syntax- oder Laufzeitfehler allein sind kein Mutationsnachweis.
"""
from pathlib import Path
import subprocess
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
PROBEN = [
    ("lauf-je-satz-neu", "stichprobe", '"lauf": lauf,',
     '"lauf": zeit.isoformat(timespec="seconds").replace("+00:00", "Z"),'),
    ("a-teilstring-statt-hostsuffix", "stichprobe",
     'host == ZIEL_DOMAIN or host.endswith("." + ZIEL_DOMAIN)', 'ZIEL_DOMAIN in host'),
    ("b-ausfall-als-false", "stichprobe", '{"fehler": "aufruf_fehlgeschlagen"}',
     '{"fehler": "aufruf_fehlgeschlagen", "genannt": False, "zitiert": False}'),
    ("c-antworttext-im-log", "stichprobe", 'satz.update(wert)',
     'log(str(result)); satz.update(wert)'),
    ("d-gemini-url-statt-title", "stichprobe", 'host = quelle["title"].strip().lower()',
     'host = urlsplit(quelle["url"]).hostname or ""'),
    ("wortgrenzen", "stichprobe", r'r"\b" + re.escape(marke) + r"\b"', 're.escape(marke)'),
    ("keine-kappung", "stichprobe", '", ".join(treffer)[:1000]', '", ".join(treffer)'),
    ("fremde-quellen", "stichprobe", 'if ziel_host(host):', 'if True:'),
    ("ausnahmetext", "stichprobe", 'log("speichern_fehlgeschlagen")', 'log(str(__import__("sys").exc_info()[1]))'),
    ("add-wiederholen", "stichprobe", 'log("speichern_fehlgeschlagen")',
     'log("speichern_fehlgeschlagen"); call("geo_stichprobe_add", satz)'),
    ("adapter-eingabe-ignoriert", "main", 'ausfuehren(januaport.input,', 'ausfuehren({},'),
    ("adapter-ausgabe-leckt", "main", 'print(json.dumps(ergebnis, ensure_ascii=False, sort_keys=True))',
     'print(json.dumps({**ergebnis, "text": "KANARIENWORT_ANTWORT_1293"}))'),
]

# Jede Validierungs-Sperre einzeln entfernen; die Tests provozieren jede davon.
for name, bedingung in [
    ("eingabe-objekt-und-felder", 'type(eingabe) is not dict or set(eingabe) - {"anlass", "maschine", "team"}'),
    ("anlass-typ-laenge", 'type(anlass) is not str or not 1 <= len(anlass) <= 120'),
    ("anlass-steuerzeichen", 'any(ord(c) < 32 or ord(c) == 127 for c in anlass)'),
    ("anlass-format", 'anlass != "monatlich" and not (anlass.startswith("T+28: ") and anlass[6:].strip())'),
    ("maschine", 'type(maschine) is not str or maschine not in (*MASCHINEN, "beide")'),
    ("team", '"team" in eingabe and (type(eingabe["team"]) is not str or not eingabe["team"].strip())'),
    ("mcp-fehler", 'type(result) is not dict or result.get("isError")'),
    ("textblock-liste", 'type(content) is not list or len(content) != 1'),
    ("textblock-form", 'type(block) is not dict or block.get("type") != "text" or type(block.get("text")) is not str'),
    ("antwort-felder", 'type(daten) is not dict or not {"text", "quellen"} <= set(daten)'),
    ("antwort-text-typ", 'text is not None and type(text) is not str'),
    ("antwort-quellen-typ", 'quellen is not None and type(quellen) is not list'),
    ("antwort-quellen-element", 'type(quelle) is not dict or any(type(quelle.get(f)) is not str for f in ("url", "title"))'),
    ("host-syntax", r'not re.fullmatch(r"[a-z0-9-]+(?:\.[a-z0-9-]+)*", host)'),
    ("url-steuerzeichen", 'any(ord(c) <= 32 or ord(c) == 127 for c in url)'),
    ("url-protokoll", 'parsed.scheme not in ("http", "https") or not host'),
    ("url-zugangsdaten", 'parsed.username is not None or parsed.password is not None'),
    ("add-mcp-fehler", 'type(geschrieben) is not dict or geschrieben.get("isError")'),
]:
    PROBEN.append((name, "stichprobe", "if " + bedingung + ":", "if False:"))

BOOTSTRAP = r'''
import importlib.abc, importlib.util, io, pathlib, runpy, sys, unittest
sys.dont_write_bytecode = True
root, modul, alt, neu = sys.argv[1:]
root = pathlib.Path(root)
pfad = root / 'skript' / (modul + '.py')
quelle = pfad.read_text(encoding='utf-8')
assert quelle.count(alt) == 1
mutiert = quelle.replace(alt, neu)
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
original = runpy.run_path
def run_path(path, *args, **kwargs):
    if modul == 'main' and pathlib.Path(path) == pfad:
        namespace = {'__file__': str(pfad), '__name__': kwargs.get('run_name', '<run_path>')}
        exec(compile(mutiert, str(pfad), 'exec'), namespace)
        return namespace
    return original(path, *args, **kwargs)
runpy.run_path = run_path
suite = unittest.defaultTestLoader.discover(str(root), pattern='tests.py')
result = unittest.TextTestRunner(stream=io.StringIO()).run(suite)
print(len(result.failures), len(result.errors), result.testsRun)
sys.exit(10 if result.failures else 1)
'''


def main():
    dateien = {p: p.read_bytes() for p in HERE.rglob("*") if p.is_file()}
    for name, modul, alt, neu in PROBEN:
        result = subprocess.run([sys.executable, "-I", "-B", "-c", BOOTSTRAP,
                                 str(HERE), modul, alt, neu],
                                capture_output=True, text=True, timeout=30)
        if result.returncode != 10:
            raise AssertionError(f"Nicht durch Assertion erkannt: {name}: {result.stdout} {result.stderr}")
        print(f"ROT {name}: {result.stdout.strip()}")
    assert dateien == {p: p.read_bytes() for p in HERE.rglob("*") if p.is_file()}
    result = subprocess.run([sys.executable, "-I", "-B", "-m", "unittest", "discover",
                             "-s", str(HERE), "-p", "tests.py"],
                            capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stderr
    print(f"OK {len(PROBEN)}/{len(PROBEN)} rot; unveränderte Fassung grün; Quelldateien unverändert.")


if __name__ == "__main__":
    main()
