decomp-tools
============

> [!IMPORTANT]
> AI Disclosure:
> AI was used for the following tasks:
> - Writing commentary (primarily translating into English and formatting).
> - Documenting and citing the various sources used in the project.
> - Writing code (C, C++, Python, etc.—I used it as a tool) and reviewing my own work (yes, some code was written by AI, but it was verified by a human; I didn't simply type "Claude, decompile this for me").

Tooling shared by matching decompilation projects, whatever the platform: what
only needs an [objdiff](https://github.com/encounter/objdiff) report, two objects
or a git repository. It is meant to be used as a git submodule at `tools/common/`
of a project, next to the tools of its platform (for PSP:
[psp-decomp-tools](https://github.com/YggdrasziI/psp-decomp-tools)).

Projects using it:

- [mhfu-decomp](https://github.com/YggdrasziI/mhfu-decomp): Monster Hunter Freedom Unite (PSP)
- [jd-tlf-decomp](https://github.com/YggdrasziI/jd-tlf-decomp): Jak and Daxter: The Lost Frontier (PSP)
- [ts2-castaway-decomp](https://github.com/YggdrasziI/ts2-castaway-decomp): The Sims 2: Castaway (Nintendo DS)
- [dqmj2-decomp](https://github.com/YggdrasziI/dqmj2-decomp): Dragon Quest Monsters: Joker 2 (Nintendo DS)

Setup
=====

```sh
git submodule add https://github.com/YggdrasziI/decomp-tools.git tools/common
python tools/common/check_traces.py --install-hooks
```

The tools find the project from the current directory upwards through a
`decomp.toml` (see `decomp_config.py` for every key and its default):

```toml
title = "Game title"
versions = ["ULES01213"]   # first one is the default version

[paths]                    # optional
report = "build/{version}/report.json"
objdiff_cli = "objdiff-cli"
```

Tools
=====

| Tool | Purpose |
|---|---|
| `asm_compare.py` | One function side by side, from `objdiff-cli diff`; `--objects` compares any two objects |
| `try_unit.py` | Compile one source file outside the build and score one function against the original (`[try]` in `decomp.toml`); safe to run many at once |
| `report_diff.py` | Regression gate between two objdiff reports |
| `progress_badges.py` | README badges, progress card and history from the objdiff report (`[regions]` and `[progress]` in `decomp.toml`: code by region, and by module or overlay for ds-decomp projects) |
| `check_traces.py` | Pre-commit / CI guard against local paths, attribution trailers and private files |
| `sha1.py` | Check the files of a sha1sum-format list, or one file against its first checksum (`-c`) |
| `ninja_syntax.py` | Writer for `build.ninja` |
| `decomp_config.py` | Settings read from `decomp.toml` |

Matching notes
==============

[`docs/`](docs/README.md) holds matching notes per compiler (Metrowerks mwccpsp,
mwccarm and mwcceppc, ARM armcc, SN Systems SNC): source forms that give a known
code shape, by symptom. Each entry names the compiler and the functions it was
proven on; on another compiler it is a hypothesis until a function confirms it.

Provenance
==========

- `ninja_syntax.py` comes from [ninja](https://github.com/ninja-build/ninja)
  (Apache-2.0, header kept).
- Everything else is original work released under CC0-1.0 (`LICENSE`).
