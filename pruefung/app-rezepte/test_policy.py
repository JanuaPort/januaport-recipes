import unittest
from policy import check_file


class SourceRules(unittest.TestCase):
    def test_external_script(self):
        check_file("index.html", b'<script src="app.js" defer></script>')

    def test_rejections(self):
        for name, data in [
            ("index.html", b"<script></script>"),
            ("index.html", b"<script>alert(1)</script>"),
            ("index.html", b'<script src="app.js">alert(1)</script>'),
            ("index.html", b'<button onclick="alert(1)">X</button>'),
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
