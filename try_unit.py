#!/usr/bin/env python3
"""Compile one source file outside the build and score one function against the
original.

  python tools/common/try_unit.py <function> <piece> <source> [--full]

The source is compiled with the `[try] compile` command of decomp.toml into an
object next to it, then `<function>` is compared with the original object
`[try] target` (objdiff, as asm_compare.py --objects). Prints the score, then only
the differing lines (original left, ours right); --full prints every line.

Neither the build nor the configuration is run or changed, so several of these can
run at once. The source must be outside the repository: the object written next to
it would otherwise land among the project's files.

decomp.toml:

    [try]
    compile = "{cc} -c {flags} -Iinclude -Isrc -o {obj} {src}"
    then = "{python} tools/prelink.py --unit {piece}{suffix} {obj} -o {obj}"   # optional
    target = "build/{version}/obj/{piece}.o"

    [try.suffix_flags]                 # optional: {suffix_flags} by source suffix
    ".c" = "-lang=c99"
    ".cpp" = "-lang=c++"

Placeholders of `compile`: {cc} and {flags} (the `[compiler]` command and flags),
{suffix_flags} (the `[try.suffix_flags]` entry of the source's suffix, none if
missing), {python} (this interpreter), {exe} (`.exe` on Windows, else empty), {src},
{obj}, {version}, {version_index} (the version's index in `versions` of
decomp.toml, e.g. for a BUILD_VERSION define). `then` (optional) runs after the
compile, with the same placeholders plus {piece} and {suffix} (the source's suffix,
e.g. `.cpp`): for a build that changes the compiled object before comparing it. Of
`target`: {version}, {piece} (the name of the original piece that holds the function).
"""

import argparse
import os
import shlex
import subprocess
import sys
from pathlib import Path

import decomp_config as config


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("function")
    parser.add_argument("piece", help="original piece that holds the function ({piece} of [try] target)")
    parser.add_argument("source", type=Path)
    parser.add_argument("--full", action="store_true", help="print every line, not only the differing ones")
    parser.add_argument("--version", default=config.DEFAULT_VERSION, choices=config.VERSIONS)
    parser.add_argument("--flags", help="code generation flags instead of [compiler] flags")
    parser.add_argument("--in-repo", action="store_true",
                        help="accept a source inside the repository (its object is written next to it)")
    args = parser.parse_args()

    settings = config.CONFIG.get("try")
    if not settings or "compile" not in settings or "target" not in settings:
        sys.exit("decomp.toml: [try] needs `compile` and `target`")
    src = args.source.resolve()
    if not src.is_file():
        sys.exit(f"{args.source}: not found")
    if config.ROOT in src.parents and not args.in_repo:
        sys.exit(f"{args.source} is inside the repository: work on a copy outside it "
                 "(or pass --in-repo)")
    obj = src.with_suffix(".o")
    target = config.ROOT / settings["target"].format(version=args.version, piece=args.piece)
    if not target.is_file():
        sys.exit(f"original object not found: {target}")

    cc, flags = config.compiler()
    if args.flags is not None:
        flags = shlex.split(args.flags)
    suffix_flags = shlex.split(settings.get("suffix_flags", {}).get(src.suffix, ""))
    many = {"{cc}": cc, "{flags}": flags, "{suffix_flags}": suffix_flags}
    one = {"{python}": sys.executable, "{src}": str(src), "{obj}": str(obj),
           "{version}": args.version, "{version_index}": str(config.VERSIONS.index(args.version)),
           "{exe}": ".exe" if os.name == "nt" else ""}

    def expand(line):
        command = []
        for token in shlex.split(line):
            if token in many:
                command += many[token]
                continue
            for key, value in one.items():
                token = token.replace(key, value)
            command.append(token)
        # A program given relative to the project root (build/tools/sjiswrap.exe):
        # Windows does not look it up from the working directory when it has slashes.
        if command and not os.path.isabs(command[0]) and (config.ROOT / command[0]).is_file():
            command[0] = str(config.ROOT / command[0])
        return command

    obj.unlink(missing_ok=True)
    res = subprocess.run(expand(settings["compile"]), capture_output=True, text=True, cwd=config.ROOT)
    if res.returncode or not obj.is_file():
        print("COMPILE ERROR")
        print((res.stdout + res.stderr)[-3000:])
        return 1
    if "then" in settings:
        one.update({"{piece}": args.piece, "{suffix}": src.suffix})
        res = subprocess.run(expand(settings["then"]), capture_output=True, text=True, cwd=config.ROOT)
        if res.returncode or not obj.is_file():
            print("THEN STEP ERROR")
            print((res.stdout + res.stderr)[-3000:])
            return 1

    diff = subprocess.run(
        [sys.executable, str(config.TOOLS / "asm_compare.py"), "--objects", str(target), str(obj),
         args.function], capture_output=True, text=True, cwd=config.ROOT)
    if diff.returncode:
        print((diff.stdout + diff.stderr).strip())
        return 1
    lines = diff.stdout.split("\n")
    print(lines[0])
    for line in lines[1:]:
        if args.full or not line.startswith("  "):
            print(line[:120])
    return 0


if __name__ == "__main__":
    sys.exit(main())
