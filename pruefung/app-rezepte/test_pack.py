import io
import os
from pathlib import Path
import tarfile
import tempfile
import unittest
from pack import pack


class PackageRules(unittest.TestCase):
    def setUp(self):
        self.work = tempfile.TemporaryDirectory(dir=Path(os.environ["RECIPE_ROOT"]) / ".arbeit")
        self.addCleanup(self.work.cleanup)
        self.root = Path(self.work.name)

    def test_deterministic_headers(self):
        (self.root / "b.txt").write_text("b", encoding="utf-8")
        (self.root / "a.txt").write_text("a", encoding="utf-8")
        data = pack(self.root)
        self.assertEqual(data, pack(self.root))
        with tarfile.open(fileobj=io.BytesIO(data), mode="r:") as archive:
            self.assertEqual(archive.getnames(), ["a.txt", "b.txt"])
            for entry in archive.getmembers():
                self.assertTrue(entry.isfile())
                self.assertEqual((entry.mode, entry.uid, entry.gid, entry.mtime), (0o644, 0, 0, 0))

    def test_file_budget(self):
        for i in range(1001):
            (self.root / f"{i}.txt").touch()
        with self.assertRaises(ValueError):
            pack(self.root)

    def test_source_budget(self):
        (self.root / "large.txt").write_bytes(b"x" * ((4 << 20) + 1))
        with self.assertRaisesRegex(ValueError, "App-Budget"):
            pack(self.root)

    def test_archive_budget(self):
        (self.root / "large.txt").write_bytes(b"x" * (4 << 20))
        with self.assertRaisesRegex(ValueError, "TAR-Budget"):
            pack(self.root)
