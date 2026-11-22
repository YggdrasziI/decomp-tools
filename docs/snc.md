# SNC (SN Systems, PSP / MIPS): source forms by symptom

Every entry below comes from one PSP project, **jd-tlf**, at an early stage: a few C++ units and 16 hand-written probe functions. The compiler is SN Systems SNC; the only build tested is `pspsnc_1.2.7503.0`, which gives 15 of 16 byte-identical probes with `-O2 -g` (`-O3 -g` the same). **The game's exact compiler version is not proven**: the remaining mismatch may be a source difference or a version difference, and Metrowerks mwccpsp has not been ruled out by a probe yet. "The original" is the shipped module. The full notes are the project's `notes/MATCHING.md`; most entries here come from its `notes/COMPILER.md`.

Tags: `[source-level]` the lever is how the C/C++ is written and may behave the same on another back-end of the same compiler family; `[back-end]` it depends on MIPS / Allegrex or its ABI; `[source-level?]` unsure.

## Register allocation and declaration order

- **A temporary in the second argument register instead of the first, registers otherwise identical** (`$a1` instead of `$a0`) -> an argument passed through to a call keeps `$a0` live and moves temporaries to `$a1`: a register-only mismatch can mean a missing parameter -> jd-tlf: compiler probes (no function named for the fix). `[source-level]`

## Statement and expression order

- **An instruction moves into or out of a branch delay slot** -> the instruction after a branch or jump runs before the target and the compiler fills the slot, so a source reorder can move an instruction into or out of it -> jd-tlf (general rule). `[back-end]`

## Types, signedness and casts

- **Float code** -> the FPU is single precision only (`lwc1`, `mul.s`, `c.lt.s` + `bc1t`); there are no doubles in hardware -> jd-tlf (general rule). `[back-end]`

## Control flow: if / else, early returns, branches

- **A float constant reloaded on return, or a register reused** -> `if (b == 0.0f) return 0.0f;` reloads the constant, `return b;` reuses the register -> jd-tlf: compiler probes (no function named). `[source-level]`
- **Several returns in the build, one epilogue reached by chained jumps in the original** (duplicated `jr $ra`, branch-likely instructions) -> no source form found: nine variants (single return, `goto`, `bool`, `?:`) did not do it with `-O2` alone; the single epilogue comes from compiling with `-g` (see settings) -> jd-tlf: `func_0007E6D8` for the variants. `[source-level?]`

## Structures, arrays and addresses

- **A struct copy made of float loads and stores** (`lwc1` / `swc1` pairs) -> copy the float fields one by one; `*out = in` emits word moves -> jd-tlf: compiler probes (no function named). `[source-level?]`
- **A variable reached through the global pointer** (`$gp`-relative, `.sdata` / `.sbss`) -> variables small enough for the small-data threshold are addressed through `$gp`; the threshold is a compiler flag (`-G`) -> jd-tlf (general rule). `[back-end]`

## Data, constants and sections

- **String literals** -> they go to the file's `.rodata`, each padded to a multiple of 8 bytes (0x1B characters + NUL take 0x20) -> jd-tlf: `unit_0009E65C`. `[source-level?]`
- **A global whose `.data` value is 0 although the source gives it a value** -> a global initialized from another global (`float b = a * 0.5f;`) is a dynamic initialization: code in `__sti__<file>` and a 0 in the data. A non-static one goes to COMMON (`.bss`), a `static` one stays in `.data` after the file's initialized globals -> jd-tlf: `unit_0009B834`. `[source-level]`
- **Name of the static initialization function** -> SNC names it after the path given on the command line: `__sti__src_<unit>_cpp` -> jd-tlf: `unit_0009B834`. `[source-level]`
- **Where the static initialization lands** -> functions are emitted in source order, then `__sti__<file>` (constructors, `__record_needed_destruction`) last in `.text`, with one 8-byte entry (address, 0) in `__cplinit` -> jd-tlf: probe `snc_sti.cpp`. `[source-level?]`

## C++

- **A constructor that returns a value** -> constructors return `this` in `$v0` -> jd-tlf: `func_0007F95C`. `[back-end]`

## Compiler settings and pragmas

- **`-g` changes code generation** -> without it SNC duplicates returns, threads jumps and uses branch-likely; with it each function keeps a single epilogue and unthreaded jump chains (`b .L1; nop` to a `b .L2`), as in the original, where only 71 of 4048 functions have more than one `jr $ra`. Probes went from 7 of 16 with `-O2` to 15 of 16 with `-O2 -g` (after source fixes) -> jd-tlf: probes `snc_leaf.cpp`, `snc_branch.cpp`. `[source-level?]`
- **Optimization level** -> `-O2` and `-O3` give the same result on the probes; `-O0` and `-O1` match none of the 8 leaf probes, and `-O1 -g` none of the 16 -> jd-tlf: compiler probes. `[source-level?]`
- **Control variables** -> the `-O<n>` groups expand to control variables (`alias callmod constp copyp fcm flow inllev sinllev mopt reg sched unroll xopt zone`); setting one `-X<var>=0..5` at a time gave no improvement over `-O2` or `-O2 -g`, and `-Xretpts=0` / `=1` changed nothing -> jd-tlf: compiler probes. `[source-level?]`

## Compiler versions

- **Idioms of `pspsnc_1.2.7503.0` that the original shares** -> `or $rd, $rs, $zero` for register moves, `ori $rd, $zero, imm` for small constants, a 16-byte frame with `$ra` at `0($sp)`, `$a0` as the `%hi` scratch register for loads. Only this build was tested, so nothing is known about differences between SNC versions -> jd-tlf: compiler probes. `[back-end]`

## Open symptoms

- **A member load placed before the loop counter is zeroed** (the original loads `self->key` before `i = 0`) -> not reproduced -> jd-tlf: `func_0002D818`. `[source-level?]`
- **One probe function of 16 still differs with `-O2 -g`** (in the loops / early returns / floats probe) -> open; it may be the source or the compiler version -> jd-tlf: probe `snc_branch.cpp`. `[source-level?]`
- **VFPU code** -> it needs inline assembly or intrinsics in C; such functions stay in assembly until the compiler's VFPU support is known -> jd-tlf. `[back-end]`
