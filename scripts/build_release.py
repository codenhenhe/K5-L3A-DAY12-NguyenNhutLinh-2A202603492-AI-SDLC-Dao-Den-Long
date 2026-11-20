"""Build the runnable, dependency-free release for Python 3.10+."""
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

ROOT = Path(__file__).resolve().parents[1]
BOOTSTRAP = '''"""Extract bundled files for the loopback server and run the release."""
from pathlib import Path
import runpy
import sys
from tempfile import TemporaryDirectory
from zipfile import ZipFile

with TemporaryDirectory(prefix="dao-den-long-") as directory:
    with ZipFile(Path(sys.argv[0]).resolve()) as archive:
        archive.extractall(directory)
    sys.path.insert(0, directory)
    if len(sys.argv) == 1:
        sys.argv.append("play")
    runpy.run_module("lantern", run_name="__main__")
'''


def build():
    target = ROOT / "dist" / "dao-den-long-v1.0.0.pyz"
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("wb") as file:
        file.write(b"#!/usr/bin/env python3\n")
        with ZipFile(file, "a", ZIP_DEFLATED) as bundle:
            def add(name, data):
                item = ZipInfo(name, date_time=(2026, 1, 1, 0, 0, 0))
                item.compress_type = ZIP_DEFLATED
                bundle.writestr(item, data)

            add("__main__.py", BOOTSTRAP)
            paths = [*ROOT.joinpath("lantern").glob("*.py"), *ROOT.joinpath("web").glob("*"),
                     *(ROOT / name for name in ("game.contract.json", "LICENSE", "CREDITS.md"))]
            for path in sorted(paths):
                if path.is_file():
                    add(path.relative_to(ROOT).as_posix(), path.read_bytes())
    target.chmod(0o755)
    print(target)


if __name__ == "__main__":
    build()
