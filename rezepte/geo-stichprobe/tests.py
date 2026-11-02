"""Synthetische Vertrags- und Verbotsproben am echten Skript-Einstieg."""
from contextlib import redirect_stdout, redirect_stderr
from datetime import datetime, timedelta, timezone
import importlib
import io
import json
import os
from pathlib import Path
import re
import runpy
import sys
import socket
import struct
import subprocess
import types
import unittest
from unittest.mock import patch

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
SKRIPT = HERE / "skript"
sys.path.insert(0, str(SKRIPT))
KANARIE = "KANARIENWORT_ANTWORT_1293"
FELDER = {"lauf", "datum", "anlass", "maschine", "frage_nr", "genannt", "zitiert",
          "quellen_januaport", "fehler"}
FRAGEN = [
    "Wie automatisiere ich eine Windows-Fachsoftware ohne Schnittstelle?",
    "Günstige Alternative zu klassischen RPA-Tools für kleine Unternehmen?",
    "Kann KI kaputte RPA-Bots reparieren?",
    "RPA-Skripte nach Windows-Update automatisch wieder starten?",
    "Python-Desktop-Automatisierung sicher im Unternehmen betreiben?",
    "MCP-Server für Google Analytics?",
    "Google Analytics sicher mit ChatGPT oder Claude verbinden?",
    "KI in Google Analytics schreiben lassen, ohne alles zu dürfen?",
    "Google Analytics mit KI auswerten?",
    "MCP-Server für die Google Search Console?",
    "Search Console sicher mit ChatGPT oder Claude verbinden?",
    "KI in der Search Console schreiben lassen, ohne alles zu dürfen?",
    "Kann eine KI eine Sitemap bei der Search Console einreichen?",
]


def antwort(text=KANARIE, url="https://example.com/", title="example.com", textblock=False):
    daten = {"text": text, "quellen": [{"url": url, "title": title}]}
    return ({"content": [{"type": "text", "text": json.dumps(daten)}]} if textblock
            else {"structuredContent": daten})


class Fake(types.ModuleType):
    """Wie bootstrap.py: input ist Objekt, call liefert MCP-Dict, log nimmt *parts."""
    def __init__(self, eingabe, reply=None):
        super().__init__("januaport")
        self.input = eingabe
        self.reply = reply or (lambda tool, args: antwort())
        self.aufrufe = []
        self.logs = []

    def call(self, tool, args):
        self.aufrufe.append((tool, args.copy()))
        if tool.endswith("_ask"):
            return self.reply(tool, args)
        return {"structuredContent": {"id": "synthetisch"}}

    def log(self, *parts):
        self.logs.append(" ".join(map(str, parts)))


def einstieg(eingabe, reply=None, fake=None):
    fake = fake or Fake(eingabe, reply)
    out, err = io.StringIO(), io.StringIO()
    with patch.dict(sys.modules, {"januaport": fake}), redirect_stdout(out), redirect_stderr(err):
        try:
            runpy.run_path(str(SKRIPT / "main.py"), run_name="__main__")
        except SystemExit as exc:
            code = exc.code
        except Exception as exc:
            raise AssertionError("Skript-Einstieg muss kontrolliert enden: " + type(exc).__name__) from None
        else:
            code = 0
    return fake, json.loads(out.getvalue()), err.getvalue(), code


class Vertrag(unittest.TestCase):
    def setUp(self):
        self.assertTrue((SKRIPT / "stichprobe.py").is_file(), "Fachkern fehlt noch (roter Test-Commit)")
        self.kern = importlib.import_module("stichprobe")

    def test_bewertung_tabelle(self):
        for text, host, genannt, zitiert in [
            ("januaport.ai", "januaport.ai", True, True),
            ("www.januaport.ai", "www.januaport.ai", True, True),
            ("", "januaport.ai.evil.example", False, False),
            ("nichtjanuaport", "nichtjanuaport.ai", False, False),
            ("JanuaPort", "example.com", True, False),
            ("januaportal", "example.com", False, False),
            ("JANUAPORT!", "WWW.JANUAPORT.AI", True, True),
            ("_januaport_", "example.com", False, False),
        ]:
            for maschine in ("openai", "gemini"):
                with self.subTest(text=text, host=host, maschine=maschine):
                    wert = self.kern.bewerten(maschine, antwort(text, "https://" + host + "/", host))
                    self.assertEqual(wert["genannt"], genannt)
                    self.assertEqual(wert["zitiert"], zitiert)

    def test_gemini_nur_title(self):
        for title, url, erwartet in [
            ("januaport.ai", "https://example.com/redirect?q=42", True),
            ("example.com", "https://example.com/redirect?q=januaport.ai", False),
            ("example.com", "https://januaport.ai/", False),
            ("januaport.ai.evil.example", "https://example.com/", False),
        ]:
            with self.subTest(title=title, url=url):
                wert = self.kern.bewerten("gemini", antwort("", url, title))
                self.assertEqual(wert["zitiert"], erwartet)
                self.assertEqual(wert.get("quellen_januaport", ""), title if erwartet else "")

    def test_antwortwege_und_null(self):
        for textblock in (False, True):
            self.assertTrue(self.kern.bewerten("openai", antwort("JanuaPort", textblock=textblock))["genannt"])
        for daten in ({"text": None, "quellen": None}, {"text": "", "quellen": []}):
            self.assertEqual(self.kern.bewerten("openai", {"structuredContent": daten}),
                             {"genannt": False, "zitiert": False})

    def test_quellen_verbotene_hostformen_am_einstieg(self):
        for m, url, title in [
            ("openai", "https://example.com/?q=januaport.ai", "januaport.ai"),
            ("openai", "https://januaport.ai@example.com/", "januaport.ai"),
            ("openai", "https://beispiel@januaport.ai/", "januaport.ai"),
            ("gemini", "https://example.com/", "example.com/januaport.ai"),
            ("gemini", "https://example.com/", "a@www.januaport.ai"),
            ("openai", "ftp://januaport.ai/", "januaport.ai"),
            ("openai", "https://januaport.ai/\n" + KANARIE, "januaport.ai"),
            ("openai", "https://[kaputt/", "januaport.ai"),
        ]:
            with self.subTest(m=m, url=url, title=title):
                fake, out, _, _ = einstieg({"maschine": m}, lambda *_: antwort("", url, title))
                saetze = [a for t, a in fake.aufrufe if t.endswith("_add")]
                self.assertTrue(all(not s.get("zitiert", False) for s in saetze))
                self.assertTrue(all("quellen_januaport" not in s for s in saetze))
                self.assertTrue(all(s.get("genannt") is False and "fehler" not in s for s in saetze))
                self.assertEqual(out[m]["fehler"], 0)
                self.assertNotIn(KANARIE, json.dumps([saetze, out, fake.logs]))

    def test_ungueltige_quellen_sind_keine_messfehler_am_einstieg(self):
        for maschine, url, title in [
            ("gemini", "https://example.com/redirect", "Some Page Title"),
            ("gemini", "https://example.com/redirect", "a@www.januaport.ai"),
            ("openai", "nicht-url", "Some Page Title"),
            ("openai", "januaport.ai/x", "januaport.ai"),
            ("openai", "https://januaport.ai/x y", "januaport.ai"),
            ("openai", "https://u:p@januaport.ai", "januaport.ai"),
            ("openai", "https://[kaputt/", "januaport.ai"),
            ("openai", "ftp://januaport.ai/x", "januaport.ai"),
        ]:
            ungueltig = {"url": url, "title": title}
            gueltig = {"url": "https://januaport.ai/x", "title": "januaport.ai"}
            for quellen in ([ungueltig], [ungueltig, gueltig], [gueltig, ungueltig]):
                for textblock in (False, True):
                    with self.subTest(maschine=maschine, quellen=quellen, textblock=textblock):
                        daten = {"text": "JanuaPort " + KANARIE, "quellen": quellen}
                        reply = ({"content": [{"type": "text", "text": json.dumps(daten)}]}
                                 if textblock else {"structuredContent": daten})
                        fake, out, err, code = einstieg({"maschine": maschine}, lambda *_: reply)
                        saetze = [a for t, a in fake.aufrufe if t.endswith("_add")]
                        zitiert = len(quellen) == 2
                        self.assertEqual(code, 0)
                        self.assertEqual(len(saetze), 13)
                        self.assertEqual(out[maschine], {"genannt": 13, "zitiert": 13 if zitiert else 0, "fehler": 0})
                        for satz in saetze:
                            self.assertNotIn("fehler", satz)
                            self.assertIs(satz["genannt"], True)
                            self.assertIs(satz["zitiert"], zitiert)
                            if zitiert:
                                self.assertEqual(satz["quellen_januaport"],
                                                 "januaport.ai" if maschine == "gemini" else gueltig["url"])
                            else:
                                self.assertNotIn("quellen_januaport", satz)
                        self.assertEqual([json.loads(x) for x in fake.logs], [out])
                        self.assertNotIn(KANARIE, json.dumps([saetze, out, fake.logs, err]))

    def test_ungueltige_struktur_am_einstieg(self):
        kaputt = [None, [], {}, {"structuredContent": {}},
                  {"structuredContent": {"text": 42, "quellen": []}},
                  {"structuredContent": []},
                  {"structuredContent": {"text": "", "quellen": {}}},
                  {"structuredContent": {"text": "", "quellen": [None]}},
                  {"structuredContent": {"text": "", "quellen": [{"url": 42, "title": ""}]}},
                  {"structuredContent": {"text": "", "quellen": [{"url": ""}]}},
                  {"content": [{"type": "text", "text": "kein JSON " + KANARIE}]},
                  {"content": "kein Block"},
                  {"content": []},
                  {"content": [42]},
                  {"content": [{"type": "image", "text": "{}"}]},
                  {"content": [{"type": "image", "text": json.dumps({"text": "", "quellen": []})}]},
                  {"content": [{"type": "text", "text": 42}]},
                  {"isError": True, "content": [{"text": KANARIE}]},
                  {"structuredContent": {}, "content": antwort(textblock=True)["content"]}]
        for reply in kaputt:
            with self.subTest(reply=reply):
                fake, out, err, code = einstieg({"maschine": "openai"}, lambda *_: reply)
                saetze = [a for t, a in fake.aufrufe if t.endswith("_add")]
                self.assertEqual(len(saetze), 13)
                self.assertTrue(all(s.get("fehler") in {"antwort_unlesbar", "aufruf_fehlgeschlagen"} for s in saetze))
                self.assertTrue(all("genannt" not in s and "zitiert" not in s for s in saetze))
                self.assertEqual(out["openai"]["fehler"], 13)
                self.assertNotIn(KANARIE, json.dumps([out, fake.logs, saetze, err]))

    def test_strukturtyp_wird_vor_bewertung_abgewiesen(self):
        for result in [
            {"structuredContent": {"text": 42, "quellen": []}},
            {"structuredContent": {"text": "", "quellen": [{"url": 42, "title": "x"}]}},
            {"structuredContent": {"text": "", "quellen": [None]}},
        ]:
            with self.subTest(result=result):
                try:
                    self.kern.bewerten("openai", result)
                except Exception as exc:
                    self.assertIsInstance(exc, ValueError)
                else:
                    self.fail("Kaputte Struktur akzeptiert")

    def test_ungueltige_eingabe_keine_aufrufe(self):
        for eingabe in [None, [], "text", {"extra": True}, {"maschine": "fremd"},
                        {"maschine": None}, {"maschine": []}, {"anlass": 1},
                        {"anlass": "x" * 121}, {"anlass": "beliebig"},
                        {"anlass": "T+28: "}, {"anlass": "T+28: a\nb"},
                        {"team": 42}, {"team": ""}, {"team": " "}]:
            with self.subTest(eingabe=eingabe):
                fake, out, err, code = einstieg(eingabe)
                self.assertEqual(fake.aufrufe, [])
                self.assertEqual(out, {"fehler": "eingabe_ungueltig"})
                self.assertNotEqual(code, 0)

    def test_grenzwerte_und_utc(self):
        fake = Fake({})
        zeit = datetime.fromisoformat("2026-01-02T00:30:00+02:00")
        self.kern.ausfuehren({"maschine": "openai", "anlass": "T+28: " + "a" * 114},
                             [{"nr": 1, "frage": FRAGEN[0]}], fake.call, fake.log, lambda: zeit)
        satz = fake.aufrufe[1][1]
        self.assertEqual(satz["datum"], "2026-01-01")
        self.assertEqual(satz["as_of"], "2026-01-01T22:30:00+00:00")
        self.assertEqual(satz.get("lauf"), "2026-01-01T22:30:00Z")
        self.assertNotIn("team", satz)

    def test_lauf_startzeit_am_einstieg_einmal_fuer_alle_saetze(self):
        # Sekundensprünge über Mitternacht erzwingen: keine Echtzeit-/Sleep-Abhängigkeit.
        basis = datetime.fromisoformat("2026-11-01T23:59:55.987654+00:00")
        laufkennungen = []
        for start in (basis, basis + timedelta(minutes=10)):
            with patch.object(self.kern, "datetime") as uhr:
                uhr.now.side_effect = [start + timedelta(seconds=i) for i in range(100)]
                fake, _, _, code = einstieg({})
            saetze = [a for t, a in fake.aufrufe if t.endswith("_add")]
            erwartet = start.isoformat(timespec="seconds").replace("+00:00", "Z")
            self.assertEqual(code, 0)
            self.assertEqual(len(saetze), 26)
            self.assertEqual({s.get("lauf") for s in saetze}, {erwartet})
            self.assertGreater(len({s["as_of"] for s in saetze}), 1)
            laufkennungen.append(saetze[0]["lauf"])
        self.assertNotEqual(*laufkennungen)

    def test_einstieg_schreibt_keine_dateien(self):
        vorher = {p.relative_to(HERE): p.read_bytes() for p in HERE.rglob("*") if p.is_file()}
        def verboten(*args, **kwargs):
            raise AssertionError("Datei-Schreibzugriff im Lauf")
        with patch("builtins.print", wraps=print), patch("pathlib.Path.write_text", verboten), \
             patch("pathlib.Path.write_bytes", verboten):
            einstieg({})
        nachher = {p.relative_to(HERE): p.read_bytes() for p in HERE.rglob("*") if p.is_file()}
        self.assertEqual(vorher, nachher)

    def test_datensparsam_und_ausgabe(self):
        for textblock in (False, True):
            fake, out, err, code = einstieg({}, lambda *_: antwort(KANARIE + " JanuaPort", "https://januaport.ai/beispiel", "januaport.ai", textblock))
            self.assertEqual(code, 0)
            self.assertEqual(out, {m: {"genannt": 13, "zitiert": 13, "fehler": 0} for m in ("openai", "gemini")})
            self.assertEqual(len(fake.aufrufe), 52)
            saetze = [a for t, a in fake.aufrufe if t.endswith("_add")]
            self.assertEqual(len(saetze), 26)
            for s in saetze:
                self.assertLessEqual(set(s), FELDER | {"source", "as_of", "team"})
                self.assertEqual(s["source"], "script geo_stichprobe")
                self.assertEqual(s["anlass"], "monatlich")
                self.assertEqual(datetime.fromisoformat(s["as_of"]).utcoffset().total_seconds(), 0)
                self.assertEqual(s["datum"], s["as_of"][:10])
            self.assertNotIn(KANARIE, json.dumps([saetze, out, fake.logs, err]))
            self.assertEqual(err, "")
            self.assertEqual([json.loads(x) for x in fake.logs], [out])

    def test_fragen_und_maschinen(self):
        fragen = json.loads((SKRIPT / "fragen.json").read_text(encoding="utf-8"))
        self.assertEqual(fragen, [{"nr": i, "frage": f} for i, f in enumerate(FRAGEN, 1)])
        self.assertEqual(len(set(f["frage"] for f in fragen)), 13)
        for m in ("openai", "gemini"):
            fake, out, _, _ = einstieg({"maschine": m, "anlass": "T+28: Beispielbeitrag", "team": "<team>"})
            self.assertEqual(set(out), {m})
            self.assertEqual([a for t, a in fake.aufrufe if t.endswith("_ask")], [{"frage": f} for f in FRAGEN])
            self.assertEqual({t for t, _ in fake.aufrufe}, {m + "_websuche_ask", "geo_stichprobe_add"})
            for t, s in fake.aufrufe:
                if t.endswith("_add"):
                    self.assertEqual(s["team"], "<team>")
                    self.assertEqual(s["anlass"], "T+28: Beispielbeitrag")

    def test_ausfall_und_weitermachen(self):
        calls = 0
        def reply(*_):
            nonlocal calls
            calls += 1
            if calls == 1:
                raise RuntimeError(KANARIE)
            return antwort()
        fake, out, err, _ = einstieg({"maschine": "openai"}, reply)
        saetze = [a for t, a in fake.aufrufe if t.endswith("_add")]
        self.assertEqual(saetze[0]["fehler"], "aufruf_fehlgeschlagen")
        self.assertNotIn("genannt", saetze[0])
        self.assertNotIn("zitiert", saetze[0])
        self.assertEqual(out["openai"], {"genannt": 0, "zitiert": 0, "fehler": 1})
        self.assertEqual(len(saetze), 13)
        self.assertNotIn(KANARIE, json.dumps([out, fake.logs, saetze, err]))

    def test_add_ausfall_einmal_je_frage(self):
        for mcp_fehler in (False, True):
            fake = Fake({"maschine": "gemini"}, lambda *_: antwort("JanuaPort"))
            original = fake.call
            def call(tool, args):
                result = original(tool, args)
                if tool.endswith("_add"):
                    if mcp_fehler:
                        return {"isError": True, "content": [{"text": KANARIE}]}
                    raise RuntimeError(KANARIE)
                return result
            fake.call = call
            fake, out, err, _ = einstieg(fake.input, fake=fake)
            self.assertEqual(len(fake.aufrufe), 26)
            self.assertEqual(out["gemini"], {"genannt": 13, "zitiert": 0, "fehler": 13})
            self.assertNotIn(KANARIE, json.dumps([out, fake.logs, err]))
            self.assertTrue(any("speichern_fehlgeschlagen" in x for x in fake.logs))

    def test_quellen_nur_treffer_gekappt(self):
        quellen = [{"url": "https://januaport.ai/" + "a" * 1100, "title": "januaport.ai"},
                   {"url": "https://example.com/" + KANARIE, "title": "example.com"}]
        for m in ("openai", "gemini"):
            wert = self.kern.bewerten(m, {"structuredContent": {"text": "", "quellen": quellen}})
            self.assertTrue(wert["zitiert"])
            self.assertLessEqual(len(wert["quellen_januaport"]), 1000)
            self.assertNotIn(KANARIE, json.dumps(wert))
        wert = self.kern.bewerten("openai", {"structuredContent": {"text": "", "quellen": [
            {"url": "https://januaport.ai/a", "title": "x"},
            {"url": "https://www.januaport.ai/b", "title": "y"}]}})
        self.assertEqual(wert["quellen_januaport"], "https://januaport.ai/a, https://www.januaport.ai/b")

    def test_satzart_und_manifest(self):
        # Absichtlich kleiner Leser für die feste YAML-Listenform; kein PyYAML im Skript.
        text = (HERE / "satzarten/geo_stichprobe.yaml").read_text(encoding="utf-8")
        self.assertEqual(set(re.findall(r"^  - name: (\w+)$", text, re.M)), FELDER)
        lauf_feld = re.search(r"(?ms)^  - name: lauf\n(.*?)(?=^  - name:|\Z)", text)
        self.assertIsNotNone(lauf_feld, "Pflichtfeld lauf fehlt")
        for deklaration in ("type: string", "required: true", "filter: true"):
            self.assertIn(deklaration, lauf_feld.group(1))
        self.assertNotRegex(text, r"(?m)^freigabe:")
        fake, _, _, _ = einstieg({"maschine": "openai"}, lambda *_: antwort("JanuaPort", "https://januaport.ai/"))
        good = set().union(*(set(a) for t, a in fake.aufrufe if t.endswith("_add")))
        fake, _, _, _ = einstieg({"maschine": "openai"}, lambda *_: {})
        bad = set().union(*(set(a) for t, a in fake.aufrufe if t.endswith("_add")))
        self.assertEqual((good | bad) - {"source", "as_of", "team"}, FELDER)
        manifest = (SKRIPT / "jnpt-script.yaml").read_text(encoding="utf-8")
        self.assertEqual(set(re.findall(r"^  - (\w+)$", manifest, re.M)),
                         {"openai_websuche_ask", "gemini_websuche_ask", "geo_stichprobe_add"})
        self.assertIn("timeout_s: 600", manifest)


@unittest.skipUnless(os.name == "posix" and os.environ.get("JANUAPORT_BOOTSTRAP"),
                     "Optionaler Durchstich: echten Läufer-Bootstrap read-only bereitstellen")
class EchterBootstrap(unittest.TestCase):
    def test_echter_bootstrap_mit_fehlern_und_beiden_antwortwegen(self):
        # Nur die entfernten Werkzeuge sind synthetisch; SDK, Rahmung und Einstieg sind echt.
        for eingabe in ({}, {"maschine": "fremd"}):
            with self.subTest(eingabe=eingabe):
                parent, child = socket.socketpair()
                parent.settimeout(15)
                wrapper = "import os,sys; os.dup2(int(sys.argv[1]),3); os.execv(sys.executable,[sys.executable,'-I','-B',*sys.argv[2:]])"
                proc = subprocess.Popen([sys.executable, "-I", "-B", "-c", wrapper,
                                         str(child.fileno()), os.environ["JANUAPORT_BOOTSTRAP"],
                                         str(SKRIPT), "main.py"], pass_fds=(child.fileno(),),
                                        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                child.close()
                logs, saetze, ask = [], [], 0
                def recv_exact(n):
                    buf = b""
                    while len(buf) < n:
                        part = parent.recv(n - len(buf))
                        if not part:
                            raise EOFError
                        buf += part
                    return buf
                try:
                    proc.stdin.write(json.dumps(eingabe).encode())
                    proc.stdin.close()
                    while True:
                        try:
                            msg = json.loads(recv_exact(struct.unpack(">I", recv_exact(4))[0]))
                        except EOFError:
                            break
                        if msg["type"] == "log":
                            logs.append(msg["data"])
                            continue
                        self.assertEqual(msg["type"], "tool_call")
                        if msg["name"].endswith("_ask"):
                            ask += 1
                            reply = antwort(KANARIE + " JanuaPort", "https://januaport.ai/", "januaport.ai", ask % 2 == 0)
                            daten = (reply["structuredContent"] if ask % 2 else
                                     json.loads(reply["content"][0]["text"]))
                            daten["quellen"].insert(0, {"url": "nicht-url", "title": "Some Page Title"})
                            if ask % 2 == 0:
                                reply["content"][0]["text"] = json.dumps(daten)
                            if ask == 1:
                                reply = {"isError": True, "content": [{"type": "text", "text": KANARIE}]}
                        else:
                            self.assertEqual(msg["name"], "geo_stichprobe_add")
                            saetze.append(msg["arguments"])
                            reply = {"content": []}
                            if len(saetze) == 1:
                                reply = {"isError": True, "content": [{"type": "text", "text": KANARIE}]}
                        body = json.dumps({"type": "tool_result", "id": msg["id"], "result": reply}).encode()
                        parent.sendall(struct.pack(">I", len(body)) + body)
                    proc.wait(timeout=15)
                    out, err = proc.stdout.read().decode(), proc.stderr.read().decode()
                    self.assertNotIn(KANARIE, json.dumps([out, err, logs, saetze]))
                    if eingabe:
                        self.assertEqual(ask, 0)
                        self.assertEqual(saetze, [])
                        self.assertEqual(json.loads(out), {"fehler": "eingabe_ungueltig"})
                        self.assertEqual(proc.returncode, 1)
                    else:
                        self.assertEqual(ask, 26)
                        self.assertEqual(len(saetze), 26)
                        laufkennungen = {s.get("lauf") for s in saetze}
                        self.assertEqual(len(laufkennungen), 1)
                        self.assertRegex(laufkennungen.pop() or "", r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
                        self.assertEqual(proc.returncode, 0)
                        self.assertEqual(json.loads(out)["openai"], {"genannt": 12, "zitiert": 12, "fehler": 1})
                        self.assertEqual(json.loads(out)["gemini"], {"genannt": 13, "zitiert": 13, "fehler": 0})
                        self.assertNotIn("genannt", saetze[0])
                        self.assertNotIn("zitiert", saetze[0])
                        self.assertIn("speichern_fehlgeschlagen", "".join(logs))
                finally:
                    parent.close()
                    if proc.poll() is None:
                        proc.kill()
                        proc.wait(timeout=5)
                    for stream in (proc.stdin, proc.stdout, proc.stderr):
                        stream.close()


if __name__ == "__main__":
    unittest.main()
