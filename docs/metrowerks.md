# Metrowerks: levers recorded on more than one back-end

Levers that the notes of at least two Metrowerks compilers record independently.
Each line says where it was seen; the entries themselves, with their witness
functions, are in [mwccpsp.md](mwccpsp.md), [mwccarm.md](mwccarm.md) and
[mwcceppc.md](mwcceppc.md). "Seen on" means a function matched thanks to it on that
compiler; on the others it is still a hypothesis. This list is a first pass over
the three files, not an exhaustive comparison: add to it when a lever of one file
is confirmed on another compiler.

## Seen on mwccpsp, mwccarm and mwcceppc

- **Declaration order of the locals sets their saved registers.** Swapped saved
  registers are first a matter of permuting declarations. The direction is recorded
  per compiler (mwccpsp: pointer locals take saved registers in reverse declaration
  order; mwccarm: the first declared takes the lower register) and must not be
  assumed to carry over. On mwccarm the order has no effect for locals that belong
  to an inlined function.
- **Compound against plain assignment changes operand order and registers**
  (`x += n` against `x = x + n`, an initialisation followed by a compound
  assignment against one expression). It goes both ways: try both.

## Seen on mwccpsp and mwccarm

- **Stack slots follow the order of declaration**: the first local declared (or
  created) gets the higher offset.
- **Loop counters**: one counter per loop against one counter shared by several
  loops changes which saved registers the counters and stepped pointers take. Both
  compilers have functions fixed by each form: try both.
- **A `static inline` helper around a loop or a test changes the register
  colouring of the whole caller**, where no declaration order does.
- **`volatile` for a value read again with no store in between** (proven on
  mwccpsp; recorded as a hypothesis on mwccarm).

## Seen on mwccarm and mwcceppc

- **`const` on a pointee or on a member function changes reloads and load
  scheduling**: the compiler assumes stores do not change data read through a
  pointer to `const`, so a `const T *` view removes a reload and a non-`const` one
  keeps it.
- **An all-zero initialised object goes to the zero-initialised section** unless
  `#pragma explicit_zero_data on` (proven on mwcceppc; recorded as a hypothesis on
  mwccarm).
- **`-ipa file` and deferred inlining change the order in which functions are
  emitted and how deep inlining goes**; a unit may need a setting the rest of the
  code does not. (mwccpsp has its own inlining lever: `-inline bottomup`.)

## Not compared yet

Switch forms, C++ (constructors, vtables, static initialisers), data and section
order, and the search tools are recorded per compiler only.
