#!/usr/bin/env python3
"""Show one function of a unit next to the original, from objdiff's own diff.

Runs `objdiff-cli diff` (same disassembly and matching as the objdiff GUI and
report) and prints the original (left) and our build (right) side by side:

  ' ' same   '|' argument differs   'o' opcode differs   'r' replaced
  '<' only in the original           '>' only in our build

Usage:
  python tools/common/asm_compare.py unit_000960A4 func_000960D0
  python tools/common/asm_compare.py text_0009630C func_0009630C      # assembly piece: original only
  python tools/common/asm_compare.py --objects <original.o> <ours.o> func_000960D0
  python tools/common/asm_compare.py unit_8032E43C <our symbol> <original symbol>

A third name is the original's symbol when ours is named differently (before the
symbol file is renamed): objdiff does not pair the two, so each side comes from its
own diff and only the opcodes are compared ('o').

Needs `objdiff.json` (`python tools/configure.py`) and a built unit (`ninja`); with
--objects any two ELF objects are compared (e.g. a scratch variant against the
original functions of a unit, build/<version>/target/<unit>.o).
"""

import argparse
import json
import os
import subprocess
import sys
import tempfile

import decomp_config as config

ROOT = str(config.ROOT)
OBJDIFF = str(config.objdiff_cli())

MARKS = {
    None: " ",
    "DIFF_ARG_MISMATCH": "|",
    "DIFF_OP_MISMATCH": "o",
    "DIFF_REPLACE": "r",
    "DIFF_DELETE": "<",
    "DIFF_INSERT": ">",
}


def unit_name(short):
    """Full objdiff unit name from a short one (text -> asm/<module>/text)."""
    with open(os.path.join(ROOT, "objdiff.json"), encoding="utf-8") as f:
        names = [u["name"] for u in json.load(f)["units"]]
    if short in names:
        return short
    matches = [n for n in names if n.endswith("/" + short)]
    if len(matches) != 1:
        sys.exit(f"unit {short!r}: {len(matches)} matches in objdiff.json")
    return matches[0]


def run_diff(cmd_head, symbol):
    """objdiff-cli's JSON diff of one symbol; cmd_head selects the unit or the
    objects (unit_cmd, objects_cmd). Other tools import these three."""
    with tempfile.TemporaryDirectory() as tmp:
        out_json = os.path.join(tmp, "diff.json")
        cmd = cmd_head + [symbol, "-o", out_json, "--format", "json"]
        res = subprocess.run(cmd, capture_output=True, text=True, cwd=ROOT)
        if res.returncode != 0 or not os.path.exists(out_json):
            sys.exit(res.stderr.strip() or "objdiff-cli diff failed")
        with open(out_json, encoding="utf-8") as f:
            return json.load(f)


def unit_cmd(unit):
    return [OBJDIFF, "diff", "-p", ROOT, "-u", unit_name(unit)]


def objects_cmd(original, ours):
    # objdiff-cli runs in ROOT: paths are taken from the caller's directory
    return [OBJDIFF, "diff", "-1", os.path.abspath(original), "-2", os.path.abspath(ours)]


def rows(symbol_json):
    out = []
    for ins in symbol_json.get("instructions", []):
        text = ins.get("instruction", {}).get("formatted", "")
        out.append((ins.get("diff_kind"), text))
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0],
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("args", nargs="+",
                        help="<unit> <symbol> [<original symbol>], or <symbol> [<original symbol>] with --objects")
    parser.add_argument("--objects", nargs=2, metavar=("ORIGINAL", "OURS"))
    opts = parser.parse_args()

    if opts.objects:
        cmd_head, names = objects_cmd(*opts.objects), opts.args
    else:
        cmd_head, names = unit_cmd(opts.args[0]) if opts.args else None, opts.args[1:]
    if not 1 <= len(names) <= 2:
        sys.exit(__doc__)
    symbol = names[0]
    original = names[1] if len(names) == 2 else symbol

    def side(diff, side_name, name):
        # An assembly piece (asm/<module>/text*) has no right side.
        found = [s for s in diff.get(side_name, {}).get("symbols", []) if s.get("name") == name]
        return found[0] if found else {}

    diff = run_diff(cmd_head, symbol)
    if original == symbol:
        sides = [side(diff, "left", symbol), side(diff, "right", symbol)]
    else:
        sides = [side(run_diff(cmd_head, original), "left", original), side(diff, "right", symbol)]
        if not sides[0]:
            sys.exit(f"{original} not found in the original")
        if not sides[1]:
            sys.exit(f"{symbol} not found in our build")
    if not sides[0] and not sides[1]:
        sys.exit(f"{symbol} not found")
    left, right = rows(sides[0]), rows(sides[1])
    pct = sides[1].get("match_percent", sides[0].get("match_percent"))
    if original != symbol:
        print(f"{symbol} (original {original}): names differ, opcodes compared only")
    elif pct is not None:
        print(f"{symbol}: {pct:.2f} %")
    else:
        print(f"{symbol}: no match data")
    print(f"  {'original':<44} | ours")
    for i in range(max(len(left), len(right))):
        kind, a = left[i] if i < len(left) else (None, "")
        kind_b, b = right[i] if i < len(right) else (None, "")
        if original == symbol:
            mark = MARKS.get(kind or kind_b, "?")
        else:
            mark = " " if a.split(" ")[0] == b.split(" ")[0] else "o"
        print(f"{mark} {a[:44]:<44} | {b}")


if __name__ == "__main__":
    main()
