"""Project settings shared by the tools, read from `decomp.toml` at the project root.

The tools live in a git submodule (usually `tools/common/`) of a decompilation
project. The project root is the first folder, from the current directory upwards,
that holds a `decomp.toml`; set DECOMP_ROOT to override it.

Keys read here (a platform tool set may read more from the same file):

    title = "Game title"                  # progress card
    versions = ["ULES01213", ...]         # first one is the default version

    [paths]                               # optional, {version} is replaced
    report = "build/{version}/report.json"
    report_base = "build/{version}/report_base.json"
    objdiff_cli = "objdiff-cli"           # .exe is added on Windows
    symbol_files = "config/{version}/symbol_addrs*.txt"   # `name = 0xADDR;` lines

    [regions.ULES01213]                   # optional: code regions of the progress card
    "Game" = [[0x08804000, 0x0890DE38]]

    [compiler]                            # optional: compiler of the C/C++ units
    name = "mwccpsp_3.0.1_219"            # tools/compilers/<name>/
    exe = "mwccpsp.exe"
    flags = "-O4"                         # code generation flags, no include paths

    [try]                                 # optional: try_unit.py
    compile = "{cc} -c {flags} -Iinclude -o {obj} {src}"
    target = "build/{version}/obj/{piece}.o"

    [traces]                              # optional: check_traces.py
    allow = ["text of a line to accept"]
"""

import os
import sys
import tomllib
from pathlib import Path

TOOLS = Path(__file__).resolve().parent

DEFAULT_PATHS = {
    "report": "build/{version}/report.json",
    "report_base": "build/{version}/report_base.json",
    "objdiff_cli": "objdiff-cli",
    "symbol_files": "config/{version}/symbol_addrs*.txt",
}


def find_root() -> Path:
    if env := os.environ.get("DECOMP_ROOT"):
        return Path(env).resolve()
    here = Path.cwd().resolve()
    for d in (here, *here.parents):
        if (d / "decomp.toml").is_file():
            return d
    sys.exit("decomp.toml not found (run from inside the project, or set DECOMP_ROOT)")


ROOT = find_root()
CONFIG = tomllib.loads((ROOT / "decomp.toml").read_text(encoding="utf-8"))

TITLE: str = CONFIG.get("title", ROOT.name)
VERSIONS: list[str] = CONFIG["versions"]
DEFAULT_VERSION: str = VERSIONS[0]


def path_setting(key: str, version: str = "") -> str:
    """A `[paths]` value (or its default) with {version} replaced, as written."""
    return CONFIG.get("paths", {}).get(key, DEFAULT_PATHS[key]).replace("{version}", version)


def report(version: str) -> Path:
    return ROOT / path_setting("report", version)


def report_base(version: str) -> Path:
    return ROOT / path_setting("report_base", version)


def objdiff_cli() -> Path:
    name = path_setting("objdiff_cli")
    if os.name == "nt" and not name.lower().endswith(".exe"):
        name += ".exe"
    return ROOT / name


def symbol_files(version: str) -> list[Path]:
    return sorted(ROOT.glob(path_setting("symbol_files", version)))


def regions(version: str) -> list:
    """[(label, [(start, end), ...])] code regions of the progress card."""
    return [(label, [tuple(r) for r in ranges])
            for label, ranges in CONFIG.get("regions", {}).get(version, {}).items()]


def compiler() -> tuple[list[str], list[str]]:
    """([command], [flags]) of the [compiler] of decomp.toml, wibo first off Windows.
    The flags are the code generation ones; include paths are added by the caller."""
    cc = CONFIG.get("compiler")
    if not cc:
        sys.exit("decomp.toml: no [compiler] section")
    exe = ROOT / "tools" / "compilers" / cc["name"] / cc["exe"]
    command = [str(exe)] if os.name == "nt" else [str(ROOT / "tools" / "wibo"), str(exe)]
    return command, cc.get("flags", "").split()
