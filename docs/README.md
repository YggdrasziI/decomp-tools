# Matching notes by compiler

Source forms that give a known code shape, condensed from the notes of the projects
that use these tools. Look a symptom up here when a function is stuck below 100 %.

| File | Compiler | Proven in |
|---|---|---|
| [metrowerks.md](metrowerks.md) | levers seen on more than one Metrowerks back-end | see each entry |
| [mwccpsp.md](mwccpsp.md) | Metrowerks mwccpsp 3.0.1 (PSP, MIPS) | mhfu-decomp |
| [mwccarm.md](mwccarm.md) | Metrowerks mwccarm 1.2 and 2.0 (Nintendo DS, ARM) | ts2-castaway-decomp, dqmj2-decomp |
| [mwcceppc.md](mwcceppc.md) | Metrowerks mwcceppc GC 3.0 (Wii, PowerPC) | mlab-decomp, spyro-dotd-decomp |
| [armcc.md](armcc.md) | ARM RVCT 4.1 / ARM Compiler 5 (3DS) | dqmj3-decomp |
| [snc.md](snc.md) | SN Systems SNC (PSP, MIPS), version not proven | jd-tlf-decomp |

## How to read them

- An entry is **proven only on the compiler and in the functions it names**. On
  another compiler, even of the same family, it is a hypothesis: try it, and once a
  function matches thanks to it, add that compiler and function to the entry (or to
  `metrowerks.md`).
- The tags (`[source-level]`, `[MIPS]`, `[ARM]`, `[back-end]`, with `?` when
  unsure) are an estimate of whether a lever depends on how the source is written or
  on the target architecture. They are not evidence.
- Several levers go both ways (own counter per loop or a shared one, a value in a
  local or written inline, a ternary or an `if`): the entry says "try both".
- The files are digests. Each project's `notes/MATCHING.md` holds the full entries
  with every witness function; what is specific to a game (its structures, its
  bounds) stays there.

## Adding to them

A technique that made a function match and does not depend on the game goes into
the file of its compiler, under the heading of its symptom, with the function that
proves it. When it confirms an entry of another compiler, record it in
`metrowerks.md`.
