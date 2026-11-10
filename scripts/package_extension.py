"""Copy the shared UI and build a dependency-free, allowlisted extension ZIP.

Run from any directory: python scripts/package_extension.py
The ZIP contains only the explicit extension files below, never the local DB,
environment files, dependencies, or test fixtures.
"""

from __future__ import annotations

from pathlib import Path
from shutil import copyfile
from zipfile import ZIP_DEFLATED, ZipFile


WEB_FILES = ("index.html", "app.js", "style.css", "mochi.svg", "whale.png", "sample.js")
EXTENSION_FILES = ("manifest.json", "background.js")


def build_extension(project_root: Path) -> Path:
    root = project_root.resolve()
    extension = root / "extension"
    source_files = [root / "web" / name for name in WEB_FILES]
    extension_files = [extension / name for name in EXTENSION_FILES]
    # Validate the complete input before copying or creating an archive.
    for source in [*source_files, *extension_files]:
        if not source.is_file():
            raise FileNotFoundError(f"Required extension input is missing: {source}")
        if source.is_symlink() or not source.resolve().is_relative_to(root):
            raise ValueError(f"Extension input must be a regular project file: {source}")

    shared = extension / "web"
    shared.mkdir(parents=True, exist_ok=True)
    for source in source_files:
        destination = shared / source.name
        if destination.is_symlink() or not destination.resolve().is_relative_to(root):
            raise ValueError(f"Extension destination must stay in the project: {destination}")
        copyfile(source, destination)

    archive = root / "dist" / "mochi-reader-extension.zip"
    archive.parent.mkdir(parents=True, exist_ok=True)
    if archive.is_symlink() or not archive.resolve().is_relative_to(root):
        raise ValueError("Extension archive must stay in the project")
    with ZipFile(archive, "w", ZIP_DEFLATED) as package:
        for name in EXTENSION_FILES:
            package.write(extension / name, name)
        for name in WEB_FILES:
            package.write(shared / name, f"web/{name}")
    return archive


if __name__ == "__main__":
    project = Path(__file__).resolve().parents[1]
    result = build_extension(project)
    print(f"Load unpacked: {project / 'extension'}")
    print(f"Extension ZIP: {result}")
