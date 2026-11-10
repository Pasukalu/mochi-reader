"""Packaging must not accidentally distribute local secrets or reading data."""

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from zipfile import ZipFile

from scripts.package_extension import EXTENSION_FILES, WEB_FILES, build_extension


class ExtensionPackagingTests(unittest.TestCase):
    def test_local_data_and_extra_files_are_excluded(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "web").mkdir()
            (root / "extension").mkdir()
            for name in WEB_FILES:
                (root / "web" / name).write_text(f"fixture:{name}", encoding="utf-8")
            for name in EXTENSION_FILES:
                (root / "extension" / name).write_text(f"fixture:{name}", encoding="utf-8")
            # A developer can leave local files inside either directory. They must
            # not leak merely because the extension is packaged recursively.
            (root / "web" / ".env").write_text("DEEPSEEK_API_KEY=test-secret")
            (root / "extension" / "mochi.sqlite3").write_bytes(b"private article")
            archive = build_extension(root)
            with ZipFile(archive) as package:
                self.assertEqual(
                    set(package.namelist()),
                    {*EXTENSION_FILES, *(f"web/{name}" for name in WEB_FILES)},
                )
                self.assertNotIn(b"test-secret", b"".join(package.read(n) for n in package.namelist()))

    def test_missing_ui_fails_before_writing_archive(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            with self.assertRaises(FileNotFoundError):
                build_extension(root)
            self.assertFalse((root / "dist").exists())


if __name__ == "__main__":
    unittest.main()
