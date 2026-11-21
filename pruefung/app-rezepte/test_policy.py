import unittest
from policy import check_file


def html(markup):
    return markup.encode("utf-8")


class SourceRules(unittest.TestCase):
    def test_allowed_sources(self):
        for markup in [
            '<script src="app.js" defer></script>',
            '<script src="js/app.js"></script>',
            '<script src="./app.js"></script>',
            '<a href="https://example.org/x">X</a>',
            '<a href="#x">X</a>',
            '<a href="java-script.html">X</a>',
            '<a href="HTTP://example.org/x">X</a>',
            '<a href="mailto:hilfe@example.org">X</a>',
            '<a href="  htt&#9;ps://example.org/x&#10;">X</a>',
            '<a href="seite.html?x=a:b#y:z">X</a>',
            '<link rel="stylesheet" href="style.css">',
            '<img src="bild.svg">',
            '<form action="/senden"></form>',
        ]:
            with self.subTest(markup=markup):
                try:
                    check_file("index.html", html(markup))
                except ValueError as fehler:
                    self.fail(f"erlaubte Quelle abgewiesen: {fehler}")

    def test_script_source_rejections(self):
        for src in [
            "data:text/javascript,alert(1)//.js",
            "DATA:text/javascript,alert(1)//.js",
            "https://fremd.example/x.js",
            "HtTpS://fremd.example/x.js",
            "//fremd.example/x.js",
            "/abs.js",
            "../x.js",
            "a/../../x.js",
            "a/../x.js",
            "..\\x.js",
            "\\\\fremd.example\\x.js",
            "js/app.txt",
        ]:
            with self.subTest(src=src), self.assertRaises(ValueError):
                check_file("index.html", html(f'<script src="{src}"></script>'))

    def test_disguised_javascript_urls(self):
        for href in [
            "javascript:alert(1)",
            "jav&#x09;ascript:alert(1)",
            "jav&#10;ascript:alert(1)",
            "jav&Tab;ascript:alert(1)",
            "java\tscript:alert(1)",
            "java\nscript:alert(1)",
            "java\rscript:alert(1)",
            " JavaScript:alert(1)",
            "\x01javascript:alert(1)",
            "java\x1fscript:alert(1)",
        ]:
            with self.subTest(href=href), self.assertRaises(ValueError):
                check_file("index.html", html(f'<a href="{href}">X</a>'))

    def test_url_attributes_allow_only_known_schemes(self):
        for attr in ["href", "src", "action", "formaction", "xlink:href", "poster", "data", "background", "cite"]:
            for url in [
                "vbscript:x",
                "data:text/html,x",
                "file:///etc/passwd",
                "blob:https://x.example/1",
                "ftp://x.example/",
                "ja&#x0A;vascript:x",
            ]:
                with self.subTest(attr=attr, url=url), self.assertRaises(ValueError):
                    check_file("index.html", html(f'<div {attr}="{url}"></div>'))

    def test_case_and_quoting_variants(self):
        for markup in [
            '<SCRIPT SRC="data:text/javascript,alert(1)//.js"></SCRIPT>',
            '<A HREF="JaVaScRiPt:alert(1)">X</A>',
            "<a href=javascript:alert(1)>X</a>",
            "<a href='javascript:alert(1)'>X</a>",
            "<script src=https://fremd.example/x.js></script>",
            "<script src=data:text/javascript,alert(1)//.js></script>",
            "<a href=jav&#x09;ascript:alert(1)>X</a>",
        ]:
            with self.subTest(markup=markup), self.assertRaises(ValueError):
                check_file("index.html", html(markup))

    def test_embedded_documents(self):
        for markup in [
            '<iframe srcdoc="<script>alert(1)</script>"></iframe>',
            '<div SRCDOC="x"></div>',
            '<meta http-equiv="refresh" content="0;url=https://x.example">',
            '<META HTTP-EQUIV="Refresh" content="0">',
            '<object data="data:text/html,x"></object>',
            '<embed src="x.html">',
            '<base href="https://fremd.example/">',
        ]:
            with self.subTest(markup=markup), self.assertRaises(ValueError):
                check_file("index.html", html(markup))

    def test_other_meta_allowed(self):
        check_file("index.html", html('<meta charset="utf-8"><meta name="viewport" content="width=device-width">'))

    def test_rejections(self):
        for name, data in [
            ("index.html", b"<script></script>"),
            ("index.html", b"<script>alert(1)</script>"),
            ("index.html", b'<script src="app.js">alert(1)</script>'),
            ("index.html", b'<button onclick="alert(1)">X</button>'),
            ("index.html", b'<BUTTON ONCLICK="alert(1)">X</BUTTON>'),
            ("index.html", b"<SCRIPT>alert(1)</SCRIPT>"),
            ("index.html", b"<SCRIPT></SCRIPT>"),
            ("index.html", b'<a href="javascript:alert(1)">X</a>'),
            ("icon.svg", b'<svg onload="alert(1)"></svg>'),
            ("icon.png", bytes([137, 80, 78, 71, 13, 10, 26, 10])),
            ("icon.png", b"text"),
            ("icon.ico", bytes([0, 0, 1, 0])),
            ("app.js", b"a\0b"),
            ("app.js", bytes([255])),
        ]:
            with self.subTest(name=name, data=data), self.assertRaises(ValueError):
                check_file(name, data)


if __name__ == "__main__":
    unittest.main()
