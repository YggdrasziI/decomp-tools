#!/usr/bin/env python3
"""Rebuild every matching unit with other compiler builds or flags and count the
units whose code changes: a way to narrow the exact compiler of a game once many
units match.

Each variant is the project's own compile commands (from build.ninja) with some
text replaced: another compiler folder, another flag. The objects go to their own
folder, built by ninja from a generated file; the project's build is not touched.
Each object is then compared with the project's object of the same unit (code
sections and their relocations; compiler-generated local names such as `@12` or
`.L5` are not compared, their numbering moves with unrelated code). Only units
that match 100 % in the objdiff report are used: a build that changes any of them
is not the game's.

Usage (from the project, after a full build and `ninja report`):
  python tools/common/compiler_sweep.py --compiler "mwccpsp_3.0.1_*"
  python tools/common/compiler_sweep.py --replace "-O4 " "-O3 " --replace "-O4 " "-O4,p "
  python tools/common/compiler_sweep.py --compiler GC/1.2.5 GC/1.3.2 --rule mwcc
  python tools/common/compiler_sweep.py --compiler mwccpsp_3.0.1_210 --list 20

--compiler NAME...  replace the [compiler] name of decomp.toml (or `--from TEXT`)
                    by NAME in the compile commands; a NAME with * or ? is
                    expanded against the folders of tools/compilers/
--replace OLD NEW   one more variant: OLD replaced by NEW (repeatable; applied to
                    the compile rules, their build statements and the file's
                    top-level variables)
--rule NAME         compile rule(s) of build.ninja; default: every rule whose
                    command names the [compiler] (its name, exe or path) and
                    reads `$in`
--data              also compare the non-code sections (data, read-only data)
--list N            print the first N differing units of each variant
--out DIR           where the variants are built (default build/compiler_sweep)
--jobs N            ninja jobs (default: [batch] jobs of decomp.toml, else all CPUs)

decomp.toml: [compiler] name / exe / path; [paths] report; objdiff.json at the
project root (base_path of each unit). Exit status 0; the counts are the result.
"""

import argparse
import fnmatch
import json
import os
import re
import struct
import subprocess
import sys
from pathlib import Path

import decomp_config as config

ROOT = config.ROOT


# --- ninja file ------------------------------------------------------------------

def read_statements(text):
    """[(first line, [lines])] of a ninja file, continuation and indented lines kept
    with the statement they belong to."""
    stmts, cur = [], None
    lines = text.split("\n")
    i = 0
    while i < len(lines):
        line = lines[i]
        block = [line]
        while block[-1].endswith("$") and i + 1 < len(lines):
            i += 1
            block.append(lines[i])
        if line.startswith((" ", "\t")) and cur is not None:
            cur[1].extend(block)
        else:
            cur = (line, block)
            stmts.append(cur)
        i += 1
    return stmts


def compile_rules(stmts, names, needles):
    rules = {}
    for first, block in stmts:
        m = re.match(r"rule (\S+)", first)
        if not m:
            continue
        if names:
            if m.group(1) in names:
                rules[m.group(1)] = block
        elif "$in" in "\n".join(block) and any(n and n in "\n".join(block) for n in needles):
            rules[m.group(1)] = block  # compiles an input (not a download rule)
    return rules


def escape_path(p: str) -> str:
    return p.replace("$", "$$").replace(" ", "$ ").replace(":", "$:")


def variant_ninja(stmts, rules, out: Path, pairs):
    """Text of a ninja file building the compile statements into `out`. The
    replacements apply to everything but the rewritten output paths."""
    def rep(text):
        for old, new in pairs:
            text = text.replace(old, new)
        return text

    head = [rep(first) for first, _ in stmts
            if re.match(r"^[A-Za-z_][\w.]* *=", first) and not first.startswith("builddir")]
    body = []
    for rule in rules.values():
        body.append(rep("\n".join(rule)))
        body.append("")
    count = 0
    for first, block in stmts:
        m = re.match(r"build (.+?): (\S+)( |$)", "\n".join(block))
        if not m or m.group(2) not in rules:
            continue
        outputs = m.group(1).split(" | ")[0].split()
        rest = "\n".join(block)[m.start(2):]
        body.append("build %s: %s" % (
            " ".join(escape_path((out / o.replace("$:", ":")).as_posix()) for o in outputs),
            rep(rest)))
        count += 1
    text = "\n".join(["ninja_required_version = 1.10"] + head
                     + ["builddir = " + escape_path(out.as_posix()), ""] + body) + "\n"
    return text, count


# --- objects ---------------------------------------------------------------------

ANON = re.compile(r"^(@|\.L|\$|L\.|\.\.)")


def elf_sections(path: Path, data: bool):
    """{section name: bytes or relocation list} of an ELF32 object."""
    d = path.read_bytes()
    if d[:4] != b"\x7fELF" or d[4] != 1:
        return {"raw": d}
    e = "<" if d[5] == 1 else ">"
    shoff, = struct.unpack_from(e + "I", d, 0x20)
    shentsize, shnum, shstrndx = struct.unpack_from(e + "HHH", d, 0x2E)
    sh = [struct.unpack_from(e + "IIIIIIIIII", d, shoff + i * shentsize) for i in range(shnum)]

    def cstr(tab, off):
        end = d.index(b"\0", tab + off)
        return d[tab + off:end].decode("latin-1")

    shstr = sh[shstrndx][4]
    names = [cstr(shstr, s[0]) for s in sh]
    syms = []
    symtab = next((s for s in sh if s[1] == 2), None)
    if symtab:
        strtab = sh[symtab[6]][4]
        for k in range(symtab[5] // 16):
            st_name, _, _, st_info, _, st_shndx = struct.unpack_from(e + "IIIBBH", d, symtab[4] + k * 16)
            name = cstr(strtab, st_name)
            if st_info & 0xF == 3 and st_shndx < len(names):
                name = "section " + names[st_shndx]
            elif not name or ANON.match(name):
                name = "(local)"
            syms.append(name)

    def wanted(s):
        return s[1] == 1 and (s[2] & 4 or (data and s[2] & 2))  # PROGBITS, exec / alloc

    out = {}
    for i, s in enumerate(sh):
        if wanted(s):
            out[names[i]] = out.get(names[i], b"") + d[s[4]:s[4] + s[5]]
        elif s[1] in (4, 9) and s[7] < len(sh) and wanted(sh[s[7]]):  # RELA, REL
            size = 12 if s[1] == 4 else 8
            rel = []
            for k in range(s[5] // size):
                off, info = struct.unpack_from(e + "II", d, s[4] + k * size)
                add = struct.unpack_from(e + "i", d, s[4] + k * size + 8)[0] if size == 12 else 0
                sym = syms[info >> 8] if info >> 8 < len(syms) else "?"
                rel.append((off, info & 0xFF, sym, add))
            out["rel " + names[s[7]]] = out.get("rel " + names[s[7]], []) + rel
    return out


def matching_units(version):
    """[(unit name, object path)] of the units at 100 % in the objdiff report."""
    with open(ROOT / "objdiff.json", encoding="utf-8") as f:
        base = {u["name"]: u.get("base_path") for u in json.load(f)["units"]}
    with open(config.report(version), encoding="utf-8") as f:
        report = json.load(f)
    units = []
    for u in report["units"]:
        m = u.get("measures", {})
        total = int(m.get("total_code", 0) or 0)
        if total and int(m.get("matched_code", 0) or 0) == total and base.get(u["name"]):
            units.append((u["name"], base[u["name"]]))
    return units


# --- main ------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--compiler", nargs="+", default=[])
    ap.add_argument("--from", dest="from_text")
    ap.add_argument("--replace", nargs=2, action="append", default=[], metavar=("OLD", "NEW"))
    ap.add_argument("--rule", nargs="+", default=[])
    ap.add_argument("--data", action="store_true")
    ap.add_argument("--list", type=int, default=0)
    ap.add_argument("--out", default="build/compiler_sweep")
    ap.add_argument("--jobs", type=int,
                    default=config.CONFIG.get("batch", {}).get("jobs", os.cpu_count()))
    ap.add_argument("--version", default=config.DEFAULT_VERSION)
    ap.add_argument("--ninja", default="build.ninja")
    args = ap.parse_args()

    cc = config.CONFIG.get("compiler", {})
    current = args.from_text or cc.get("name") or cc.get("path")
    needles = [cc.get("name"), cc.get("exe"), cc.get("path")]

    variants = []
    for name in args.compiler:
        if any(c in name for c in "*?"):
            found = sorted(p.name for p in (ROOT / "tools" / "compilers").iterdir()
                           if p.is_dir() and fnmatch.fnmatch(p.name, name))
            if not found:
                sys.exit("no folder of tools/compilers/ matches " + name)
        else:
            found = [name]
        if not current:
            sys.exit("--compiler needs [compiler] name/path in decomp.toml or --from")
        variants += [(n, [(current, n)]) for n in found if n != current]
    for k, (old, new) in enumerate(args.replace, 1):
        variants.append(("replace%d" % k, [(old, new)]))
    if not variants:
        sys.exit("nothing to try: give --compiler or --replace")

    stmts = read_statements((ROOT / args.ninja).read_text(encoding="utf-8"))
    rules = compile_rules(stmts, args.rule, needles)
    if not rules:
        sys.exit("no compile rule found in %s: name it with --rule" % args.ninja)
    units = matching_units(args.version)
    if not units:
        sys.exit("no unit at 100 % in the report (run the build and `ninja report`)")
    print("rules: %s; %d matching units" % (", ".join(rules), len(units)))

    out_root = (ROOT / args.out).resolve()
    for tag, pairs in variants:
        out = out_root / re.sub(r"[^\w.-]", "_", tag)
        out.mkdir(parents=True, exist_ok=True)
        text, count = variant_ninja(stmts, rules, out, pairs)
        nf = out_root / (out.name + ".ninja")
        nf.write_text(text, encoding="utf-8", newline="\n")
        subprocess.run(["ninja", "-f", str(nf), "-j", str(args.jobs), "-k", "0"],
                       cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        same, diff, failed = 0, [], []
        for name, obj in units:
            ref, new = ROOT / obj, out / obj
            if not new.is_file():
                failed.append(name)
            elif elf_sections(ref, args.data) == elf_sections(new, args.data):
                same += 1
            else:
                diff.append(name)
        desc = "; ".join("%r -> %r" % p for p in pairs)
        print("%s (%s): identical %d, different %d, not built %d"
              % (tag, desc, same, len(diff), len(failed)))
        if args.list:
            for label, items in (("different", diff), ("not built", failed)):
                if items:
                    print("  %s: %s" % (label, " ".join(items[:args.list])))


if __name__ == "__main__":
    main()
