#!/usr/bin/env python3
r"""Draw the README progress badges from the objdiff report, without decomp.dev.

Outputs, one folder per game version (shield-style SVG, one per measure, all code of
the built modules; regions come from decomp.toml):
  progress/<version>/fuzzy.svg    fuzzy match percentage    (fuzzy_match_percent)
  progress/<version>/perfect.svg  perfectly matched code    (matched_code_percent)
  progress/<version>/linked.svg   code linked from source (complete_code_percent)
  progress/<version>/card.svg     progress card: code, data and functions, then code
                                  by region (decomp.toml [regions]) and by module
                                  ([progress] module_files), or by the report's
                                  progress categories, each as a stacked bar
                                  (fuzzy, perfect, linked) with perfect / total counts
  progress/<version>/history.csv  one line per --record, for the HEAD commit: record
                                  after committing the unit, then commit progress/

Usage:
  python tools/common/progress_badges.py                      # draw from the objdiff report
  python tools/common/progress_badges.py --record             # also append the current state to history.csv
  python tools/common/progress_badges.py --version <ID>       # game version (default: first of decomp.toml)

decomp.toml `[paths] progress_report`: the report read here, when it is not
`[paths] report`. `[progress]` (all optional; without module_files the card has no
module rows):
  rows = "categories"                  # rows from the report's progress categories
                                       # (objdiff.json), then the code no category
                                       # claims; regions and modules are not read
  region_title = "Code by region"      # heading of the region rows
  module_files = "config/{version}/arm9/**/delinks.txt"
                                       # ds-decomp delinks files: the module of a source
                                       # unit is the folder of the file that lists it
  module_folders = { arm9 = "main" }   # folder -> module name, as in the gap unit names
  gap_unit = '_dsd_gap@(\w+?)_\d+$'    # module of an automatic unit, from its name
  apart = 'ov\d+'                      # modules whose addresses overlap (overlays): left
                                       # out of the regions; with regions, only these get
                                       # a module row
  module_title = "Code by module"      # heading of the module rows
  [progress.module_labels]             # row labels, in this order first
  main = "Main"
"""

import argparse
import csv
import datetime
import json
import os
import re
import subprocess
from xml.sax.saxutils import escape

import decomp_config as config

ROOT = str(config.ROOT)
GAME_TITLE = config.TITLE
DEFAULT_VERSION = config.DEFAULT_VERSION
PROGRESS = config.CONFIG.get("progress", {})

# (file name, label, report measure, color)
BADGES = [
    ("fuzzy", "Fuzzy", "fuzzy_match_percent", "#a28c64"),
    ("perfect", "Perfect", "matched_code_percent", "#3584e4"),
    ("linked", "Linked", "complete_code_percent", "#26a269"),
]


# Card colors (light, dark): bars are stacked fuzzy > perfect > linked.
CARD_COLORS = {
    "bg": ("#ffffff", "#0d1117"),
    "border": ("#d0d7de", "#30363d"),
    "text": ("#1f2328", "#e6edf3"),
    "muted": ("#656d76", "#8d96a0"),
    "track": ("#eaeef2", "#21262d"),
    "fuzzy": ("#a28c64", "#a28c64"),
    "perfect": ("#3584e4", "#3584e4"),
    "linked": ("#26a269", "#2ec27e"),
}

HISTORY_FIELDS = [
    "date", "commit", "code_fuzzy_pct", "code_matched_pct", "code_linked_pct",
    "functions_matched", "functions_total",
]


def pct(measures, key):
    return float(measures.get(key, 0.0) or 0.0)


def git(*args):
    try:
        return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    except OSError:
        return ""


def text_width(text):
    """Rough width of 11px Verdana text, enough to size a badge."""
    narrow = sum(1 for c in text if c in "ijlt.,: %1")
    return 7 * (len(text) - narrow) + 4 * narrow


def badge(label, value, color):
    """A flat shield: grey label on the left, colored value on the right."""
    lw = text_width(label) + 12
    vw = text_width(value) + 12
    w = lw + vw
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="20" role="img" aria-label="{escape(label)}: {escape(value)}">
<title>{escape(label)}: {escape(value)}</title>
<linearGradient id="s" x2="0" y2="100%"><stop offset="0" stop-color="#bbb" stop-opacity=".1"/><stop offset="1" stop-opacity=".1"/></linearGradient>
<clipPath id="r"><rect width="{w}" height="20" rx="3" fill="#fff"/></clipPath>
<g clip-path="url(#r)"><rect width="{lw}" height="20" fill="#555"/><rect x="{lw}" width="{vw}" height="20" fill="{color}"/><rect width="{w}" height="20" fill="url(#s)"/></g>
<g fill="#fff" text-anchor="middle" font-family="Verdana,Geneva,DejaVu Sans,sans-serif" font-size="11">
<text x="{lw / 2}" y="15" fill="#010101" fill-opacity=".3">{escape(label)}</text><text x="{lw / 2}" y="14">{escape(label)}</text>
<text x="{lw + vw / 2}" y="15" fill="#010101" fill-opacity=".3">{escape(value)}</text><text x="{lw + vw / 2}" y="14">{escape(value)}</text>
</g>
</svg>
"""


def draw_badges(report, out_dir):
    m = report["measures"]
    for name, label, key, color in BADGES:
        with open(os.path.join(out_dir, name + ".svg"), "w", encoding="utf-8", newline="\n") as f:
            f.write(badge(label, "{:.2f}%".format(pct(m, key)), color))


def symbol_addresses(version):
    """{name: address} of the functions named in the symbol files of a version
    (`[paths] symbol_files`): splat lines `name = 0xADDR;`, or ds-decomp lines
    `name kind:function(...) addr:0xADDR` (data symbols of that format are skipped).
    The objdiff report gives section offsets, not addresses; func_<addr> names carry
    their address (function_address)."""
    addrs = {}
    for path in config.symbol_files(version):
        with open(path, encoding="utf-8") as f:
            for line in f:
                m = (re.match(r"\s*(\S+)\s*=\s*(0x[0-9a-fA-F]+);", line)
                     or re.match(r"(\S+) kind:function\S* addr:(0x[0-9a-fA-F]+)", line))
                if m:
                    addrs.setdefault(m.group(1), int(m.group(2), 16))
    return addrs


def function_address(name, addrs):
    m = re.fullmatch(r"func_([0-9A-Fa-f]{8})", name)
    return int(m.group(1), 16) if m else addrs.get(name, 0)


def unit_sources(version):
    """{source path: module} from the module files (`[progress] module_files`):
    `<path>:` lines of ds-decomp delinks.txt files; the module is the file's folder
    name, renamed by `module_folders`."""
    pattern = PROGRESS.get("module_files")
    if not pattern:
        return {}
    renames = PROGRESS.get("module_folders", {})
    sources = {}
    for path in sorted(config.ROOT.glob(pattern.replace("{version}", version))):
        module = renames.get(path.parent.name, path.parent.name)
        with open(path, encoding="utf-8") as f:
            for line in f:
                m = re.match(r"(\S+\.(?:c|cc|cp|cpp|s)):\s*$", line)
                if m:
                    sources[m.group(1)] = module
    return sources


def unit_module(unit, sources):
    """Module of a report unit: from its name for an automatic unit (`gap_unit`),
    else from the module file that lists its source; "other" when neither says."""
    m = re.match(PROGRESS.get("gap_unit", r"_dsd_gap@(\w+?)_\d+$"), unit["name"])
    if m:
        return m.group(1)
    return sources.get(unit.get("metadata", {}).get("source_path", ""), "other")


def is_apart(module):
    apart = PROGRESS.get("apart")
    return bool(apart) and re.fullmatch(apart, module) is not None


def module_measures(report, version, apart_only=False):
    """[(label, total, fuzzy, perfect, linked)] code bytes per module. Modules come
    from unit names and module files, not addresses: overlays share theirs."""
    if not PROGRESS.get("module_files"):
        return []
    sources = unit_sources(version)
    labels = PROGRESS.get("module_labels", {})
    sums = {}
    for unit in report.get("units", []):
        module = unit_module(unit, sources)
        if apart_only and not is_apart(module):
            continue
        total = int(unit.get("measures", {}).get("total_code", 0) or 0)
        if not total:
            continue
        acc = sums.setdefault(module, [0, 0.0, 0, 0])
        for fn in unit.get("functions", []):
            size = int(fn.get("size", 0))
            score = float(fn.get("fuzzy_match_percent", 0.0) or 0.0)
            acc[1] += size * score / 100
            acc[2] += size if score == 100 else 0
        acc[0] += total
        acc[3] += total if unit.get("metadata", {}).get("complete") else 0
    order = [k for k in labels if k in sums] + sorted(k for k in sums if k not in labels)
    return [(labels.get(k, k), *sums[k]) for k in order]


def region_measures(report, regions, version):
    """[(label, total, fuzzy, perfect, linked)] code bytes per region, from every
    function of the report (split or not), placed by its address. Units of the
    modules kept apart (overlays) are left out: their addresses overlap."""
    if not regions:
        return []
    addrs = symbol_addresses(version)
    sources = unit_sources(version) if PROGRESS.get("apart") else {}
    sums = {label: [0, 0.0, 0, 0] for label, _ in regions}
    other = [0, 0.0, 0, 0]
    for unit in report.get("units", []):
        if sources and is_apart(unit_module(unit, sources)):
            continue
        linked = bool(unit.get("metadata", {}).get("complete"))
        for fn in unit.get("functions", []):
            # The report gives the address when the objects carry it; otherwise
            # it comes from the name or the symbol files
            virtual = fn.get("metadata", {}).get("virtual_address")
            addr = int(virtual) if virtual else function_address(fn["name"], addrs)
            size = int(fn.get("size", 0))
            score = float(fn.get("fuzzy_match_percent", 0.0) or 0.0)
            acc = next((sums[label] for label, ranges in regions
                        if any(s <= addr < e for s, e in ranges)), other)
            acc[0] += size
            acc[1] += size * score / 100
            acc[2] += size if score == 100 else 0
            acc[3] += size if linked else 0
    rows = [(label, *sums[label]) for label, _ in regions]
    if other[0]:
        rows.append(("Other", *other))
    return rows


def category_measures(report):
    """[(label, total, fuzzy, perfect, linked)] code bytes per progress category of
    the report, then the code no category claims yet."""
    total = int(report["measures"].get("total_code", 0) or 0)
    rows, claimed = [], 0
    for cat in report.get("categories", []):
        m = cat.get("measures", {})
        size = int(m.get("total_code", 0) or 0)
        if not size:
            continue
        claimed += size
        rows.append((cat.get("name", cat.get("id", "?")), size, pct(m, "fuzzy_match_percent") / 100 * size,
                     int(m.get("matched_code", 0) or 0), int(m.get("complete_code", 0) or 0)))
    if total > claimed:
        rows.append(("Not attributed yet", total - claimed, 0, 0, 0))
    return rows


def linked_functions(report):
    return sum(len(u.get("functions", [])) for u in report.get("units", [])
               if u.get("metadata", {}).get("complete"))


def card(report, version, commit):
    """An SVG card: overall code, data and functions, then code by region; each
    bar is stacked (fuzzy, perfect, linked) with the raw counts beside it."""
    m = report["measures"]

    def num(key):
        return int(m.get(key, 0) or 0)

    overall = [
        ("Code", num("total_code"), pct(m, "fuzzy_match_percent") / 100 * num("total_code"),
         num("matched_code"), num("complete_code"), "bytes"),
        ("Data", num("total_data"), num("matched_data"), num("matched_data"),
         num("complete_data"), "bytes"),
        ("Functions", num("total_functions"), num("matched_functions"),
         num("matched_functions"), linked_functions(report), ""),
    ]
    by_category = PROGRESS.get("rows") == "categories"
    if by_category:
        regions = []
        modules = [(*row, "bytes") for row in category_measures(report)]
    else:
        regions = [(*row, "bytes") for row in region_measures(report, config.regions(version), version)]
        # With regions, the module rows keep the modules apart (overlays) only
        modules = [(*row, "bytes") for row in module_measures(report, version, apart_only=bool(regions))]

    width, bar_x, bar_w, row_h = 760, 186, 300, 26
    y = 34
    body = [f'<text class="t b" x="16" y="{y}">{GAME_TITLE} ({escape(version)})</text>',
            f'<text class="m" x="{width - 16}" y="{y}" text-anchor="end">commit {escape(commit)}</text>']

    def bar_row(label, total, fuzzy, perfect, linked, unit):
        nonlocal y
        y += row_h
        share = (perfect / total * 100) if total else 0.0
        parts = [f'<text class="t" x="16" y="{y}">{escape(label)}</text>',
                 f'<rect class="track" x="{bar_x}" y="{y - 11}" width="{bar_w}" height="12" rx="3"/>']
        for cls, value in (("fuzzy", fuzzy), ("perfect", perfect), ("linked", linked)):
            if value > 0 and total:
                # At least one pixel, so any progress shows.
                w = max(1.0, bar_w * value / total)
                parts.append(f'<rect class="{cls}" x="{bar_x}" y="{y - 11}" width="{w:.1f}" height="12" rx="2"/>')
        suffix = f" {unit}" if unit else ""
        parts.append(f'<text class="t" x="{width - 86}" y="{y}" text-anchor="end">'
                     f'{perfect:,.0f} / {total:,}{suffix}</text>')
        parts.append(f'<text class="m" x="{width - 16}" y="{y}" text-anchor="end">{share:.2f} %</text>')
        body.extend(parts)

    for row in overall:
        bar_row(*row)
    if regions:
        y += 16
        title = escape(PROGRESS.get("region_title", "Code by region"))
        body.append(f'<text class="t b" x="16" y="{y + row_h - 8}">{title}</text>')
        y += row_h - 8
        for row in regions:
            bar_row(*row)
    if modules:
        y += 16
        title = escape(PROGRESS.get("module_title", "Code by category" if by_category else "Code by module"))
        body.append(f'<text class="t b" x="16" y="{y + row_h - 8}">{title}</text>')
        y += row_h - 8
        for row in modules:
            bar_row(*row)
    y += 30
    lx = 16
    for cls, text in (("linked", "linked from source"), ("perfect", "perfect match"),
                      ("fuzzy", "fuzzy match")):
        body.append(f'<rect class="{cls}" x="{lx}" y="{y - 10}" width="12" height="12" rx="2"/>')
        body.append(f'<text class="m" x="{lx + 18}" y="{y}">{text}</text>')
        lx += 18 + text_width(text) + 18
    body.append(f'<text class="m" x="{width - 16}" y="{y}" text-anchor="end">'
                f'counts: perfect / total{"" if by_category else "; region bounds are approximate"}</text>')
    height = y + 18

    def rules(i):
        return "".join([
            f".bg{{fill:{CARD_COLORS['bg'][i]};stroke:{CARD_COLORS['border'][i]}}}",
            f".t{{fill:{CARD_COLORS['text'][i]}}}",
            f".m{{fill:{CARD_COLORS['muted'][i]}}}",
            f".track{{fill:{CARD_COLORS['track'][i]}}}",
            *(f".{k}{{fill:{CARD_COLORS[k][i]}}}" for k in ("fuzzy", "perfect", "linked")),
        ])

    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-label="Decompilation progress of {escape(version)}">
<title>Decompilation progress of {escape(version)}</title>
<style>
text{{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Helvetica,Arial,sans-serif;font-size:13px}}
.b{{font-weight:600}}
{rules(0)}
@media (prefers-color-scheme: dark){{{rules(1)}}}
</style>
<rect class="bg" x="0.5" y="0.5" width="{width - 1}" height="{height - 1}" rx="6"/>
{chr(10).join(body)}
</svg>
"""


def draw_card(report, out_dir, version):
    commit = git("rev-parse", "--short=7", "HEAD") or "unknown"
    with open(os.path.join(out_dir, "card.svg"), "w", encoding="utf-8", newline="\n") as f:
        f.write(card(report, version, commit))


def read_history(path):
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def record(report, history_path):
    rows = read_history(history_path)
    commit = git("rev-parse", "--short=7", "HEAD")
    if commit and rows and rows[-1].get("commit") == commit:
        rows.pop()
    m = report["measures"]
    rows.append({
        "date": git("log", "-1", "--format=%cs") or datetime.date.today().isoformat(),
        "commit": commit,
        "code_fuzzy_pct": "{:.2f}".format(pct(m, "fuzzy_match_percent")),
        "code_matched_pct": "{:.2f}".format(pct(m, "matched_code_percent")),
        "code_linked_pct": "{:.2f}".format(pct(m, "complete_code_percent")),
        "functions_matched": m.get("matched_functions", 0),
        "functions_total": m.get("total_functions", 0),
    })
    # Keep the columns of older rows (game/SDK split) so no recorded value is lost.
    fields = list(HISTORY_FIELDS)
    for row in rows:
        fields += [k for k in row if k not in fields]
    with open(history_path, "w", encoding="utf-8", newline="\n") as f:
        w = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
        w.writeheader()
        for row in rows:
            w.writerow({k: row.get(k, "") for k in fields})


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--version", default=DEFAULT_VERSION,
                        help="game version (default: %(default)s)")
    parser.add_argument("--report", help="objdiff report (default: `[paths] progress_report`, else `report`, of decomp.toml)")
    parser.add_argument("--out", help="badge folder (default: progress/<version>)")
    parser.add_argument("--history", help="history file (default: progress/<version>/history.csv)")
    parser.add_argument("--record", action="store_true", help="append the current state to history.csv")
    args = parser.parse_args()

    if args.report is None:
        args.report = str(config.progress_report(args.version))
    if args.out is None:
        args.out = os.path.join(ROOT, "progress", args.version)
    if args.history is None:
        args.history = os.path.join(ROOT, "progress", args.version, "history.csv")
    os.makedirs(args.out, exist_ok=True)
    with open(args.report, encoding="utf-8") as f:
        report = json.load(f)
    if args.record:
        record(report, args.history)
    draw_badges(report, args.out)
    draw_card(report, args.out, args.version)
    print("wrote fuzzy.svg, perfect.svg, linked.svg and card.svg to", args.out)


if __name__ == "__main__":
    main()
