# armcc (ARM RVCT, 3DS): source forms by symptom

Every entry below comes from one 3DS project, **dqmj3**, whose executable holds code from at least two compiler builds: RVCT 4.1 build 921 (proven on a script library compiled with the game, 224 functions found) and ARM Compiler 5.04 build 82 (proven against b921 on two script-binding files; it is the only 5.x build tested, so a nearby 5.x build is not ruled out). A prebuilt SDK library in the same executable needs RVCT 4.1 build 1049, 1440 or 1454. Flags: `--cpu=MPCore --arm --apcs=/interwork --split_sections --no_rtti_data -O3 -Otime --fpmode=fast --signed_chars` (the last four proven by sweeps, the others consistent with every match but not tested one by one). "The original" is the shipped executable. The full notes are the project's `notes/MATCHING.md`, with the compiler evidence in `notes/COMPILER.md`.

Tags: `[source-level]` the lever is how the C/C++ is written and may behave the same on another back-end of the same compiler family; `[back-end]` it depends on ARM, its ABI or the CPU model; `[source-level?]` unsure.

## Register allocation and declaration order

- **A load happens at another point, registers differ, or two adjacent loads are not paired** (one `ldrd` in the original, two `ldr` in the build, or the reverse) -> read the value into a local, or bind a local reference, before using it: `const T &o = a->_values[i]; Append(o);` instead of `Append(a->_values[i])`; `cap = _values.capacity();` before the comparison -> dqmj3: `SQArray::Extend`, `base_array` (through the inline `SQArray::ShrinkIfNeeded`). `[source-level?]`
- **The loads before a call are scheduled differently, and a `bool` argument is built in a new register** (`movne r1, #1` + `moveq r1, #0` instead of `ldr r1, [sp]; cmp r1, #0; ...; movne r1, #1`) -> load the global object pointer into a local first: `void* self = g; fn(self, value);` instead of passing the global directly -> dqmj3: bindings of `FieldScriptFunc.cpp`. `[source-level?]`
- **Stack layout of locals** -> armcc does not follow the declaration order of locals when it lays out the stack: moving declarations did not change it -> dqmj3: `SetTalkCameraEyeOffset_`. `[source-level?]`
- **Byte temporaries passed by address sit below the other locals** (`strb r0, [sp, #4]; ...; mov r1, sp`) -> `unsigned char` locals declared before the other locals, assigned in reverse order (`y = a1; x = a0;`) and passed to `const unsigned char&` parameters -> dqmj3: bindings of `BattleScriptFunc.cpp`. `[source-level?]`

## Statement and expression order

- **Arguments are loaded before the object pointer** (`ldr r0, [sp, #4]; ldr r1, [sp]; sxtb ...; ldr r0, =lbl`) -> store the call result in a local before passing it on: `int r = fn(self, a0, a1); push(v, r);` -> dqmj3: bindings of `BattleScriptFunc.cpp`. `[source-level?]`

## Types, signedness and casts

- **The conversion before a call tells the parameter type** -> `and rN, rN, #0xff` is an `unsigned char` parameter, `sxtb` a `signed char`, `sxth` a `short`, `movne` / `moveq` a `bool`, a plain load an `int`, and `fsitos` an `int` passed to a `float` parameter; take only the last write of a register before the call -> dqmj3: bindings of `FieldScriptFunc.cpp`. `[back-end]`
- **Sign extension then a byte mask on one argument** (`sxtb` then `and #0xff`) -> a `signed char` local passed to an `unsigned char` parameter: `signed char idx = a0; fn(self, idx, ...)` -> dqmj3: bindings of `BattleScriptFunc.cpp`. `[source-level]`
- **A boolean built by comparing with 1** (`cmp rN, #1; movne rN, #0`, and `moveq rN, #1` when the register is not already 1) -> the source compares an integer boolean with 1 (`a1 == 1`); `cmp rN, #0; movne rN, #1` is the plain conversion (`a1 != 0`, or the value passed to a `bool` parameter) -> dqmj3: bindings of `BattleScriptFunc.cpp`. `[source-level]`
- **Floats converted to integers and stored next to each other, then their address passed** (`ftosis`) -> an `int` array initialized from the floats -> dqmj3: bindings of `BattleScriptFunc.cpp`. `[source-level]`

## Calls, arguments and inlining

- **Arguments past the fourth** -> they are stored to `[sp, #0]` and up: look for the conversion of the register stored there to find the parameter type -> dqmj3: bindings of `FieldScriptFunc.cpp`. `[back-end]`
- **Three floats stored from the float return registers after a call** (`fstmias r2, {s0, s1, s2}`) -> the callee returns a vector of three floats by value (VFP ABI); a result read with `ldmia r0` is a returned pointer -> dqmj3: bindings of `FieldScriptFunc.cpp`. `[back-end]`
- **Constant arguments after the forwarded ones** (`mov r2, #1`) -> one callee shared by several wrappers, each passing a kind number -> dqmj3: `AddBattleEventMessage_`. `[source-level]`
- **A `mov r0, r0` where a call is expected** (0xE1A00000) -> a call to an empty function that the linker (armlink) inlined; it is not a scheduling `nop` (0xE320F000, see settings) and needs a different fix -> dqmj3: `inflateInit2_`, `deflateInit2_` of the SDK's zlib. `[back-end]`
- **A change in a shared inline header fixes one function** -> compile every file that includes it: a form that fixes one function can break others (writing a container's capacity test as `_size >= _allocated` broke 17 matched functions) -> dqmj3: `push_back` of the script library. `[source-level]`

## Structures, arrays and addresses

- **Two adjacent float locals copied into a struct as one 64-bit pair** (`ldrd` / `strd`) -> with 4.1 b921, an inline member that assigns the fields (`offset.Set(0.0f, a1, a2)`); with 5.04 the same member gives the original stack layout but a VFP copy, and assigning a two-float struct gives the `ldrd` / `strd` copy with the vector below the arguments -> dqmj3: `SetTalkCameraEyeOffset_` (93.9 %, not matched). `[back-end]`

## Compiler settings and pragmas

- **Registers swapped over a whole function, the same instructions otherwise** (prebuilt library code) -> try other `--cpu` values (`6K`, `ARM1136J-S`, `MPCoreNoVFP`) before editing the source: it looks like a source change but is not -> dqmj3: SDK zlib (`deflate`, `updatewindow`), matched unchanged with `--cpu=MPCoreNoVFP`. `[back-end]`
- **`nop` words inside functions** (0xE320F000, for example between `subs` and `beq`) -> MPCore scheduling: `--cpu=MPCore` or `MPCoreNoVFP` emit them; `6`, `6K`, `6Z` and `ARM1136J-S` give the same register choices as `MPCoreNoVFP` without the `nop` -> dqmj3: `updatewindow`. `[back-end]`
- **Optimization level** -> `-O3 -Otime` finds 224 functions of the script library, `-O3 -Ospace` 30, `-O2 -Otime` 51 -> dqmj3: Squirrel sweep. `[source-level?]`
- **Flags that show in the code** -> without `--fpmode=fast` one function is lost (223 of 224), without `--signed_chars` five (219) -> dqmj3: Squirrel sweep. `[source-level?]`
- **Flags that do not show** -> `--no_rtti` makes no difference so far; `--no_dep_name` only affects template lookup, not code; `--data-reorder`, `--force_new_nothrow` and `--multibyte-chars --locale=japanese` changed nothing in the report (not proven, not ruled out) -> dqmj3. `[source-level?]`
- **Testing a changed header** -> `#include "..."` looks in the including file's directory first, so a changed header must replace the original in a copy of the whole directory; `-I` does not shadow it -> dqmj3. `[source-level]`
- **A prebuilt library** -> it may have its own compiler build and `--cpu`: sweep each library separately with every build and both `--cpu=MPCore` and `--cpu=MPCoreNoVFP` -> dqmj3: the SDK's zlib (4.1 b1049 / 1440 / 1454, `MPCoreNoVFP`, C90) against the game (`MPCore`). `[back-end]`

## Compiler versions

- **One instruction more or less than the original, with the right CPU** -> try the other builds before rewriting the source -> dqmj3: SDK zlib. `[source-level?]`
- **RVCT 4.0 and 4.1 b561 against later 4.1 builds** -> a large gap: 31 or 32 functions of the script library found with 4.0 b771 to b902 and 4.1 b561, 201 with 4.1 b713, 217 with b791, 220 with b844, 218 with b894, 224 with b921 -> dqmj3: Squirrel sweep. `[source-level?]`
- **4.1 b921 against b894 and against b1049 / b1440 / b1454** -> b921 finds every function the other 4.1 builds find; three functions are lost with the later builds and six with b894 -> dqmj3: `SQFunctionProto::Load`, `SQVM::ARITH_OP`. `[source-level?]`
- **4.1 b1049, b1440 and b1454** -> never told apart: the same functions match in every sweep -> dqmj3: Squirrel and zlib sweeps. `[source-level?]`
- **Library code that only later 4.1 builds match** -> `deflate` matches with b1049, b1440 and b1454 only; `inflate_table` with b791, b844, b1049, b1440 and b1454 but not b894 or b921 (both with `--cpu=MPCoreNoVFP`) -> dqmj3: SDK zlib. `[source-level?]`
- **ARM Compiler 5.04 b82 against 4.1 b921 on game files** -> on two files of script bindings every function that matches with b921 also matches with 5.04, and eleven match with 5.04 only (183 against 181 of 186, 114 against 105 of 140; 4.0 b902 gives 53 of 140): try 5.04 on a game file before rewriting a function. On the script library 5.04 finds only 71 functions, so one executable can hold code from both -> dqmj3: `GetPos_`, `SetHpMax_`. `[source-level?]`

## Open symptoms

- **A field load ordered before a paired load in the original, after it in the build** (`b._type` before the `ldrd` of `a`) -> not solved; a local pointer to the array start (`T *vals = &a->_values[0]; _Swap(vals[0], vals[i]);`) brings it from 9 to 2 differing words (96.6 %); swapped operands, local references, header variants of the swap and 15,000 random source permutations did not fix it -> dqmj3: `array_sort` (with `_hsort` inlined). `[source-level?]`
- **An `unsigned char` argument where the original loads the object pointer into a scratch register before masking the index, then moves it to `r0`** (`ldr r1, =lbl; ldr r0, [sp]; ldr r2, [r1]; and r1, r0, #0xff; mov r0, r2`) -> not solved with b921 or 5.04: object in a local or passed directly, casts, `& 0xff`, locals of each type, enums, inline wrappers and members, references, a `volatile` or reference object, result locals, `-O` levels -> dqmj3: 21 bindings of `BattleScriptFunc.cpp`. `[source-level?]`
- **A static initializer that matches with 5.04 only, in a library otherwise matched by 4.1 b921** -> open -> dqmj3: `__sti___11_sqstate_cpp__null_`. `[source-level?]`
