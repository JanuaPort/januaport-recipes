"""Zusätzliche Quellregeln für die öffentlichen Browser-Beispiele."""
from html.parser import HTMLParser
from pathlib import Path


class SourceHTML(HTMLParser):
    script = False

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        self.script = self.script or tag == "script"
        if tag == "script" and (not attrs.get("src") or not attrs["src"].endswith(".js")):
            raise ValueError("Script braucht eine eigene .js-Datei")
        for key, value in attrs.items():
            if key.lower().startswith("on") or (value or "").strip().lower().startswith("javascript:"):
                raise ValueError("Inline-Script")

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
