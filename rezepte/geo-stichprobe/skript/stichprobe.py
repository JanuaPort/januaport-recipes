"""GEO-Trend-Signal; Standardbibliothek, keine Abhängigkeit vom Läufer-Modul."""
from datetime import datetime, timezone
import json
import re
from urllib.parse import urlsplit

ZIEL_DOMAIN = "januaport.ai"
MASCHINEN = ("openai", "gemini")


class EingabeUngueltig(ValueError):
    pass


def eingabe_pruefen(eingabe):
    if type(eingabe) is not dict or set(eingabe) - {"anlass", "maschine", "team"}:
        raise EingabeUngueltig("eingabe_ungueltig")
    anlass = eingabe.get("anlass", "monatlich")
    maschine = eingabe.get("maschine", "beide")
    if type(anlass) is not str or not 1 <= len(anlass) <= 120:
        raise EingabeUngueltig("eingabe_ungueltig")
    if any(ord(c) < 32 or ord(c) == 127 for c in anlass):
        raise EingabeUngueltig("eingabe_ungueltig")
    if anlass != "monatlich" and not (anlass.startswith("T+28: ") and anlass[6:].strip()):
        raise EingabeUngueltig("eingabe_ungueltig")
    if type(maschine) is not str or maschine not in (*MASCHINEN, "beide"):
        raise EingabeUngueltig("eingabe_ungueltig")
    if "team" in eingabe and (type(eingabe["team"]) is not str or not eingabe["team"].strip()):
        raise EingabeUngueltig("eingabe_ungueltig")
    return anlass, MASCHINEN if maschine == "beide" else (maschine,)


def antwort_lesen(result):
    """MCP-Dict des Bootstrap: structuredContent hat Vorrang vor JSON-Text."""
    if type(result) is not dict or result.get("isError"):
        raise ValueError("antwort_unlesbar")
    if "structuredContent" in result:
        daten = result["structuredContent"]
    else:
        content = result.get("content")
        if type(content) is not list or len(content) != 1:
            raise ValueError("antwort_unlesbar")
        block = content[0]
        if type(block) is not dict or block.get("type") != "text" or type(block.get("text")) is not str:
            raise ValueError("antwort_unlesbar")
        daten = json.loads(block["text"])
    if type(daten) is not dict or not {"text", "quellen"} <= set(daten):
        raise ValueError("antwort_unlesbar")
    text, quellen = daten["text"], daten["quellen"]
    if text is not None and type(text) is not str:
        raise ValueError("antwort_unlesbar")
    if quellen is not None and type(quellen) is not list:
        raise ValueError("antwort_unlesbar")
    for quelle in quellen or []:
        if type(quelle) is not dict or any(type(quelle.get(f)) is not str for f in ("url", "title")):
            raise ValueError("antwort_unlesbar")
    return text or "", quellen or []


def ziel_host(host):
    host = host.lower()
    if not re.fullmatch(r"[a-z0-9-]+(?:\.[a-z0-9-]+)*", host):
        return False
    return host == ZIEL_DOMAIN or host.endswith("." + ZIEL_DOMAIN)


def bewerten(maschine, result):
    text, quellen = antwort_lesen(result)
    marke = ZIEL_DOMAIN.split(".", 1)[0]
    genannt = re.search(r"\b" + re.escape(marke) + r"\b", text, re.IGNORECASE) is not None
    treffer = []
    for quelle in quellen:
        if maschine == "gemini":
            host = quelle["title"].strip().lower()
            wert = host
        else:
            url = quelle["url"]
            if any(ord(c) <= 32 or ord(c) == 127 for c in url):
                continue
            try:
                parsed = urlsplit(url)
                host = parsed.hostname or ""
            except ValueError:
                continue
            if parsed.scheme not in ("http", "https") or not host:
                continue
            if parsed.username is not None or parsed.password is not None:
                continue
            wert = url
        if ziel_host(host):
            treffer.append(wert)
    ergebnis = {"genannt": genannt, "zitiert": bool(treffer)}
    if treffer:
        ergebnis["quellen_januaport"] = ", ".join(treffer)[:1000]
    return ergebnis


def ausfuehren(eingabe, fragen, call, log, jetzt=None):
    """Je Frage ask → bewerten → add. Fehlerzähler zählt betroffene Fragen (max. 13)."""
    anlass, maschinen = eingabe_pruefen(eingabe)
    uhr = jetzt or (lambda: datetime.now(timezone.utc))
    lauf = uhr().astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    ergebnis = {}
    for maschine in maschinen:
        zaehler = {"genannt": 0, "zitiert": 0, "fehler": 0}
        ergebnis[maschine] = zaehler
        for frage in fragen:
            zeit = uhr().astimezone(timezone.utc)
            satz = {"lauf": lauf, "datum": zeit.date().isoformat(), "anlass": anlass,
                    "maschine": maschine, "frage_nr": frage["nr"],
                    "source": "script geo_stichprobe", "as_of": zeit.isoformat()}
            if "team" in eingabe:
                satz["team"] = eingabe["team"]
            try:
                result = call(maschine + "_websuche_ask", {"frage": frage["frage"]})
            except Exception:
                wert = {"fehler": "aufruf_fehlgeschlagen"}
            else:
                try:
                    wert = bewerten(maschine, result)
                except (ValueError, TypeError, RecursionError):
                    wert = {"fehler": "antwort_unlesbar"}
            satz.update(wert)
            if "fehler" in wert:
                log(wert["fehler"])
            for feld in ("genannt", "zitiert"):
                zaehler[feld] += int(wert.get(feld, False))
            fehler = "fehler" in wert
            try:
                geschrieben = call("geo_stichprobe_add", satz)
                if type(geschrieben) is not dict or geschrieben.get("isError"):
                    raise ValueError("speichern_fehlgeschlagen")
            except Exception:
                fehler = True
                log("speichern_fehlgeschlagen")
            zaehler["fehler"] += int(fehler)
    log(json.dumps(ergebnis, ensure_ascii=False, sort_keys=True))
    return ergebnis
