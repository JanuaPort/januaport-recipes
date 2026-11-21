"""Zusätzliche Quellregeln für die öffentlichen Browser-Beispiele."""
from html.parser import HTMLParser
from pathlib import Path


EMBEDDING_TAGS = {"object", "embed", "base"}
URL_ATTRIBUTES = {"href", "src", "action", "formaction", "xlink:href", "poster", "data", "background", "cite"}
URL_SCHEMES = {"http", "https", "mailto"}


def url_form(value):
    """Wie der URL-Parser der Browser: Tab, Zeilenumbruch und Steuerzeichen fallen weg."""
    return "".join(c for c in value or "" if c > " ").lower()


def is_allowed_url(value):
    """Relativer Pfad, Fragment oder ein Schema aus der positiven Liste."""
    head, colon, _ = url_form(value).partition(":")
    return not colon or bool(set(head) & set("/?#")) or head in URL_SCHEMES


def is_meta_refresh(tag, attrs):
    return tag == "meta" and any(key == "http-equiv" and (value or "").lower() == "refresh" for key, value in attrs)


def is_own_js_file(src):
    path = url_form(src).replace("\\", "/")
    return (
        path.endswith(".js")
        and ":" not in path
        and not path.startswith("/")
        and ".." not in path.split("/")
    )


class SourceHTML(HTMLParser):
    script = False

    def handle_starttag(self, tag, attrs):
        self.script = self.script or tag == "script"
        if tag in EMBEDDING_TAGS or is_meta_refresh(tag, attrs):
            raise ValueError("Eingebettetes Dokument")
        if tag == "script" and not any(key == "src" for key, _ in attrs):
            raise ValueError("Script braucht eine eigene .js-Datei")
        for key, value in attrs:
            if tag == "script" and key == "src" and not is_own_js_file(value):
                raise ValueError("Script braucht eine eigene .js-Datei")
            if key.startswith("on") or key == "srcdoc":
                raise ValueError("Inline-Script")
            if key in URL_ATTRIBUTES and not is_allowed_url(value):
                raise ValueError("Adresse mit unzulässigem Schema")

    def handle_data(self, data):
        if self.script and data.strip():
            raise ValueError("Inline-Script-Inhalt")

    def handle_endtag(self, tag):
        if tag == "script":
            self.script = False


def check_file(name, data):
    if Path(name).suffix.lower() not in {".html", ".js", ".css", ".json", ".svg", ".txt"}:
        raise ValueError("Dateityp außerhalb der Text-Quellen")
    text = data.decode("utf-8")
    if "\0" in text:
        raise ValueError("Binärinhalt")
    if Path(name).suffix.lower() in {".html", ".svg"}:
        SourceHTML().feed(text)


def check_tree(root):
    for path in root.rglob("*"):
        if path.is_symlink():
            raise ValueError("Link im Quellordner")
        if path.is_file():
            check_file(path.name, path.read_bytes())
