# mwcceppc (Metrowerks, Wii / PowerPC): source forms by symptom

Every entry below made a function or a unit match in one of two Wii projects, and each was checked by a build. **mlab**: game code compiled with mwcc GC 3.0a5.2 (the GC 3.0 family is proven; 3.0a5.2 itself is a working hypothesis for the game code), base flags `-proc gekko -O4,p -inline auto -fp_contract off -str reuse -Cpp_exceptions off -RTTI off`. **spyro-dotd**: GC/3.0a5.2, proven on one linked game unit built with `-RTTI on -opt nopeephole`, plus MSL and Wii SDK library units (GC/3.0a5.2, a few files GC/3.0a5). "The original" is the shipped executable. The full catalogues, with more context per entry, are each project's `notes/MATCHING.md`; the compiler evidence is in each `notes/COMPILER.md`.

Tags: `[source-level]` the lever is how the C/C++ is written and may behave the same on another back-end of the same compiler family; `[back-end]` it depends on PowerPC or its ABI; `[source-level?]` unsure.

## Register allocation and declaration order

- **Saved registers of locals numbered differently from the original** -> the declaration order of locals sets their register numbers (a result declared before the object pointer, for example); a local declared at the top of its block but assigned later takes a different saved register -> mlab: `flag` in `fn_800D8280`. `[source-level]`
- **Two locals in each other's registers** -> declare first the one the original numbers higher, even uninitialized (`int page;`, or `f32 minY;` before `f32 minX = mMin.x;` for a float pair copy) -> mlab: `Recipes::fn_801205EC`, `unit_8007C4AC`. `[source-level]`
- **Several saved registers permuted in a loop over a switch** (case constants and vtables hoisted) -> declare the loop pointer before the count and the index, at the top of the function; script the permutations -> mlab: `fn_8012FD0C`. `[source-level]`
- **A result that lands in the register of the wrong operand, or operands in the wrong registers** -> split the expression into an initialization and a compound assignment: `int element = mElement; element += delta;`, `f32 t = x - a; t /= range;`, `int r = a; r -= b * 4; return r;`, `d = b * b; d -= a * c;` (the result stays in the register of `b * b`) -> mlab: `fn_80119538`, `fn_800B20A4`. `[source-level]`
- **A run of lookups `w = find(obj, key); if (w) set(w, ...);` with the object and the results in the wrong saved registers** -> give each lookup its own local (or its own block) instead of reusing one variable -> mlab: `fn_8013C6CC`. `[source-level]`
- **A constant stored through a call result is kept in a saved register across the call** (the original loads it after the call, `li r0`) -> store through a local pointer first: `p = vf10()->m; p->f = 0;` instead of `vf10()->m->f = 0;` -> mlab: `unit_800A34C0`. `[source-level?]`
- **A float constant kept in a saved FP register across a call** (`f31`) -> it is a local variable: `f32 duration = 5.0f;` -> mlab (no function named). `[source-level?]`
- **A pointer taken through an inline accessor and null-checked gets the last register number instead of the first** -> store the accessor result in a `void*` local, test that, and cast it to a second local -> mlab: `fn_800B20A4`. `[source-level]`
- **A struct field copied into a local and used for several indexes gets the wrong registers** -> read the field itself at each use (`part.mSlot - 1`) instead of `u8 slot = part.mSlot;` -> mlab: `IngredientSelection::fn_8011A04C`. `[source-level]`
- **Registers differ around a cached pointer `ctx = self->m0`** -> drop the local and write `self->m0->` each time; the compiler still loads it once -> mlab: `fn_800D6A24`. `[source-level]`
- **Register allocation of a whole function tail is off** -> compute a local pointer before the updates it depends on (`u8* p = base + used;` before `free -= size; used += size;`) -> mlab: `fn_80044634`. `[source-level]`
- **A comparison result kept in a local flag (`u8 flag = x == 1;`) gives a shift with the wrong register order** (`srwi`) -> make it a `bool` member, set before the other member update and read back from the member: `mFlag = mTab == 1; mTab += d;` -> mlab: `fn_80118FC0`. `[source-level?]`
- **Array index and base in the wrong registers** (original: `mulli r0` for the index, the base in `r3`) -> store the call result in a local before indexing (`int index = model->fn(...);`); a local pointer to the member object (`T* model = &m94;`) also keeps the stack stores of a dead vector copy -> mlab: `fn_80098700`. `[source-level]`
- **A member the original reloads where the build reuses the register of an earlier inlined load** -> read it through a local reference: `int& tailRef = mTail;` -> mlab: `UnkDvdRequestQueue::PopBack`. `[source-level]`
- **Fields of a stack copy of a struct reloaded after each call in the original, kept in saved registers by the build** -> pass the copy by reference to an inline function, or bind a local reference to it in place (`T& desc = temp;`) -> mlab: `unit_8011C460`, `Parts::fn_8011B060`. `[source-level]`
- **A global pointer the original reloads after every call** -> it must stay a global in the source; passing it to an inline helper keeps it in a saved register -> mlab: `fn_8013CFA8`. `[source-level]`
- **Accesses made through a reloaded global** (`lwz rX, lbl@sda21` again after a loop) **although a local copy exists** -> write those accesses through the global; the compiler shares the other loads with the local copy -> mlab: `fn_800D7394`. `[source-level]`
- **Stack slots of locals in the wrong order** -> the first declared local gets the higher address; compiler temporaries created later get lower ones -> mlab (general rule, no function named). `[source-level?]`
- **Two stack temporaries in swapped slots** -> a named local (`Vec d = a - b;`) gets its slot before the temporaries of later expressions; writing it as an expression (`(a - b).LengthSq()`) makes it a temporary with a lower slot -> mlab: `fn_800B182C`. `[source-level?]`
- **The last vectors of a function sit at the lowest stack addresses** -> move that code into an inline member function (its locals take slots below the caller's temporaries); one named vector assigned twice (`p = a + b; e->SetPosition(p);`) gives a single slot shared by two such calls -> mlab: `UpdateBounds` in `unit_8007C4AC`. `[source-level?]`
- **A returned value passed by address once sits in the lowest stack slot, below the named locals of later blocks** -> it is a compiler temporary: pass the call result through an inline function taking a `const&` -> mlab: `XBaseActionSelectionCallback::Select`, `vf0C` of `unit_80040090`. `[source-level]`
- **Struct copies in the wrong stack slots (the original sorts them by size)** -> get them from an inline function that returns the struct by value -> mlab: `GetAbilityInfo` in `unit_8011A778`. `[source-level?]`

## Statement and expression order

- **A value is stored to a global, then the stored register is compared (no reload)** -> compare the local, not the member again: `int id = p->mId; global = id; if (id == -1)`; comparing `p->mId` reloads it after the store -> mlab: `unit_8001EE48`. `[source-level]`
- **Two stores of one value in the wrong order** -> `a = b = x;` stores `b` first: swap the chain -> mlab: `fn_80109A20`. `[source-level]`
- **Three components of a vector stored z, y, x** -> chained assignment `v.x = v.y = v.z = 1.0f`; stored x, y, z -> the three-float constructor -> mlab: `fn_8000C508`, `BuzzsawGate::vfBC`. `[source-level]`
- **A copy of a global const vector loaded x, z, y before `+=`** -> build it with the three-float constructor: `Vec v(k.x, k.y, k.z); pos += v;` -> mlab: `fn_8013E898`. `[source-level?]`
- **Several values read and stored straight into a struct in reading order** -> assign the members one by one; constructor arguments are evaluated right to left -> mlab: `fn_8009875C`. `[source-level]`
- **A sum of many call results is added in the wrong order** -> mwcc reassociates the sum and parentheses change nothing; successive `n += ...;` statements keep one add after each call. Operands of equal weight are evaluated right first (`a() * b()` calls `b` first) -> mlab: `GetBlockCount` in `unit_801088C0`. `[source-level]`
- **Float compare with zero: member loaded before or after the constant** -> `if (x)` loads the member first (`fcmpu x, 0`); `x != 0.0f` loads the constant first -> mlab: `fn_8000C604`. `[source-level?]`
- **Multiply operands swapped** (`mullw rD, rD, rB` versus `mullw rD, rB, rD`) -> swap the operands of `*` in the source (`size * nmemb`) -> spyro-dotd: `calloc` in `alloc.c`. `[source-level?]`
- **Add operands swapped in an inlined rounding macro, and swapping the source operands does not fix it** -> use a version of the function written with separate statements -> spyro-dotd: `OSAllocFromMEM1ArenaLo` in `OSArena.c`. `[source-level?]`
- **A value written to a hardware register is computed before the command byte written just before it** -> make the value the argument of an inline function that does both writes -> mlab: `UnkLoadBP`, `UnkLoadXF` in `unit_800445E4`. `[source-level]`
- **Results written back into a vector's own stack slots, no temporary** -> subtract component by component (`v.x -= c.x; ...`); `v = v - c` adds temporaries and enlarges the frame -> mlab (no function named). `[source-level]`

## Types, signedness and casts

- **A load through a pointer parameter is scheduled above the prologue's stack stores** -> the parameter is `const T*` (the stack stores cannot alias it); a load through `T*` cannot move there. Flags, `-proc` models and compiler versions do not change this -> mlab: `unit_80018C04`, `unit_80077B50`. `[source-level]`
- **A member load above the prologue in a member function** (`lfs` before `stwu`), **or a member reused where a non-const `this` reloads it** -> declare the function `const`, in the whole hierarchy for a virtual (mangled names become `...CFv`) -> mlab: `ExWorldTile::vfD0() const` in `unit_800C4530`, `UnkTileRing::GetHead() const`. `[source-level]`
- **A character reloaded after the stores of a copy loop** -> the source pointer is `char*`, not `const char*` (mwcc assumes stores do not change data read through a pointer to const) -> mlab: `fn_80121508`. `[source-level]`
- **Logical not of a byte member: masked result or plain shift** -> `x = !x` on a `u8` member masks the result (`rlwinm`); a plain `srwi` comes from a `bool` member -> mlab (no function named). `[source-level?]`
- **Float to integer conversion before a modulo: inline conversion after the call, or a runtime call before it** -> `u32 % (int)(float)` gives the call-first order with an inline `fctiwz`; a `(u32)` cast of the float calls `__cvt_fp2unsigned` before the call -> mlab: `fn_8003CE20`. `[back-end]`
- **A float call result stored to a global and passed on: store then round, or round then store** -> callee returning `f32` gives `stfs` then `frsp` (the returned value is rounded again for the argument); an `f64` return gives `frsp` first -> mlab: `fn_8013E4D0`. `[back-end]`
- **An extra rounding to single precision (`frsp`) after a select or a clamp, or right before a value is used as a scale** -> the value went through a `double`: an inline helper that compares floats but returns `double`, or an argument cast to `double` (`Scaled(v, (double)step)`); a `double` local instead pools a double constant -> mlab: `UnkMaxD` in `unit_8000C478`, `UnkClampD` in `unit_8009F66C`. `[source-level?]`
- **A square root rounded once where the build rounds twice** (`fmul` then a single `frsp`) -> a helper that returns `f32`; a helper returning `double` cast with `(f32)` gives two `frsp` when the caller returns a float -> mlab: `ExWorldCurvedTile::vfD0`. `[source-level?]`

## Control flow: if / else, early returns, branches

- **Two conditional branches to the epilogue in the original, one inverted branch over a jump in the build** (`beq`, `beq` versus `bne` over `b`) -> two separate early returns, not `if (a == 0 || f() == 0) return;` -> mlab: `fn_8013DE7C`, `fn_8013CFA8`. `[source-level]`
- **Which path falls through is inverted** -> `if (ok) { ...; return x; } return 0;` versus an early `return 0` -> mlab: `fn_801F5BB8`. `[source-level]`
- **A bounds-checked getter loads the element after the branch that returns 0** -> `i >= count ? 0 : data[i]` -> mlab: `UnkList::Get` in `unit_8012F6B0`. `[source-level]`
- **A clamp inlined everywhere numbers its registers differently** -> write it as a conditional expression `v < lo ? lo : (v > hi ? hi : v)`, not as if/return -> mlab: accessors of `PathAPI.h`. `[source-level]`
- **Branch order inverted on a boolean array test** -> `if (mUsed[i] == false)` gives the original order where `!mUsed[i]` inverts it -> mlab: accessors of `PathAPI.h`. `[source-level]`
- **Pointer to a member at a non-zero offset, taken with a null check** (`addi` / `b` / `li 0`) -> explicit `if (p) q = &p->m; else q = 0;`; a ternary or an implicit base-class conversion adds a second compare -> mlab: `fn_8003FC6C`. `[source-level]`
- **An add-and-test of an offset on a pointer already tested for null** (`addic. r0, rX, off` / `beq`) -> the address of a member struct compared with 0: `if (&part->mLink == 0)`; a base-class conversion adds a second compare -> mlab: `vf0C` of `unit_8004AC68`. `[source-level?]`
- **A jump over unreachable code (a call and a test) right after a member is set to 0** -> write the store, then `if (member != 0) { ... }`; the compiler folds the condition but keeps the dead block -> mlab: constructor of `unit_800D7F24`. `[source-level?]`
- **A dead test kept by the original** (a check whose result is overwritten with the same value, `cntlzw` / `srwi.` then `li 1`) -> reproduce it as written -> mlab: `IsOnPath`. `[source-level]`
- **Three conditional branches on one float compare, no reload in between** (three `bne` on one `fcmpu`) -> the source compares the same value three times (a copy-paste slip such as `-1.0f == x && -1.0f == x && -1.0f == x`) -> mlab: `fn_8013E898`. `[source-level]`
- **A zero test materialized as a value before an `&&`** (`cntlzw` / `srwi.` on a call result) -> a local `bool b = f() == 0;` tested as `!b` -> mlab: `fn_80010CAC`. `[source-level?]`

## Switch

- **Compare tree in the wrong shape** -> list the cases in descending order (an empty `case 4` included) -> mlab (no function named). `[source-level?]`
- **A compare tree for cases 1 and 2 that starts at 1** -> add `case 0:` together with the default label -> mlab: `fn_80121B08`, `fn_801091EC`. `[source-level?]`
- **Dead compare trees** -> an inline function containing a `switch`, whose result is unused -> mlab (no function named). `[source-level]`
- **Two copies of the same code inside a switch** -> two separate groups of `case` labels; the compiler does not merge them -> mlab: `fn_800A0FB4`. `[source-level]`
- **One null test before a switch, reused in every case** (`cmpwi cr1` before, `beq cr1` in each case) -> `if (p != 0) switch (...) { new (p) T; }` with placement new; without the outer test each case gets its own compare -> mlab: `fn_8012F818`. `[source-level?]`
- **A conditional branch over an unconditional jump to the common return** (`beq` over `b`) -> a `switch` with a single `case 0`, under `-opt nopeephole`; `if (!x)` gives `bne` -> spyro-dotd: `vf30__8IKAnchor`. `[source-level?]`

## Loops

- **A counted loop whose counter is unused, counting down** (`subic.`) -> `int n = 4; ... do { } while (--n);` with `n` declared at the top of the block -> mlab (no function named). `[source-level]`
- **Descending loop compares the index with -1** (`cmpwi i, -1`) -> `for (i = n - 1; i > -1; i--)`; `i >= 0` gives `addic.` / `blt` -> mlab: `unit_800D3428`. `[source-level?]`
- **A `while` loop tested at the bottom, with a flag built before the test** (`li 0` / `li 1` / `cmpwi`) -> `while (test) { advance; }` is laid out as a branch to the test at the bottom; a test that needs a flag is written `int free = 0; if (...) free = 1;` -> mlab: `fn_80109600`. `[source-level]`
- **A search loop that sets a flag and jumps out** (flag cleared before the loop, set to 1 and a branch out) -> `bool found = false; ... { found = true; break; } return found;`, not an early `return true` -> mlab: `BuzzsawTileSetPool::vf20`. `[source-level]`
- **A result kept in the return register through a loop** (`li r3, -1` before it, the loop end falling through to the return) -> assign the call to the result variable, `result = f(); if (result != -1) return i;`, and break out of the loop rather than returning inside -> mlab: `fn_800D5DE4`, `fn_800D5FDC`. `[source-level]`
- **A field of a parameter loaded once before a search loop** -> copy it to a local before the loop: `u32 id = entry->m0;` -> mlab: `fn_800D70EC`. `[source-level]`
- **A value read in the condition of one loop is reused by the next** -> assign inside the condition: `while (less(i->mName, key = mid->mName)) i++; while (less(key, j->mName)) j--;` -> mlab (no function named). `[source-level]`
- **A byte loop with a pointer increment but other registers** -> index the row (`row[x] &= mask;`); an explicit `p++` gives the same code with other registers -> mlab: `fn_8007C50C`. `[source-level?]`
- **A 0.0 constant loaded inside a loop (not hoisted) and shared with a result variable** -> initialize the variable in the loop: `f32 t = 0.0f;` before an inline that may leave it unchanged -> mlab: `fn_800B20A4`. `[source-level]`
- **The unroll factor tells the loop** -> a 64-word loop gives 2 iterations of 32 stores (zeroing) or 4 iterations of 16 copies, where a loop over four 16-word structs is unrolled by 2 -> mlab: `unit_800D4C64`. `[source-level?]`

## Calls, arguments and inlining

- **A small function is inlined, or a call is kept, against the original** -> with `-inline auto`, small functions defined earlier in the file are inlined and a slightly larger body keeps a call; small setters the original calls out of line are defined after their caller -> mlab: `fn_80016CEC`, `fn_80016DB0`. `[source-level]`
- **A function too large for `-inline auto` that the original inlines anyway** -> write its body as calls to the smaller functions it dispatches to (each inlined in turn), so it fits the size limit; the `inline` keyword drops the out-of-line copy the original also has, and `#pragma inline_max_size` had no effect -> mlab: `fn_80118858` in `unit_80117AE4`. `[source-level]`
- **Two loads feeding an inlined call come in the wrong order** -> arguments of an inlined call are evaluated right to left: the inline may take its parameters in the other order -> mlab: `SweepSpheres` in `unit_800B1EDC`. `[source-level]`
- **A compare of a value with itself kept by the original** (`cmpw r7,r7`) **but folded by the build** (`i <= tail`, both from the same member load) -> pass the index to the inline function by `const int&` and copy it into a local -> mlab: `UnkDvdRequestQueue::Contains` in `unit_801E47D8`. `[source-level]`
- **Saved registers in the wrong order in a loop `m = t->items[i]; f(t, i, 0); g(m);`** -> an inline helper doing the three steps -> mlab: `ReleaseModel`. `[source-level]`
- **Two identical loops with different register numbers** -> the second function just calls the first, which is inlined -> mlab: `fn_80160AFC` calls `fn_80160A28`. `[source-level]`
- **Identical bodies in the original, different registers in the build when one goes through an inline helper** -> write the loop out in the function instead of calling the helper -> mlab: `fn_80109A20`. `[source-level]`
- **A member is read again in each branch of a clamp** (a load in both arms) -> a macro on the member, not an inline function taking the value -> mlab: `UNK_CLAMP_BETWEEN` in `Parts::fn_8011B898`. `[source-level]`
- **An array base kept in a saved register through an inlined function** (instead of recomputing `r1 + offset`) -> copy the parameter into a local inside the inline function -> mlab (no function named). `[source-level]`
- **A value kept in the second argument register across a call that takes the object in the first** (`r4`, not `r0`) -> the callee takes it as a second argument: add the parameter -> mlab: `unit_80117090`. `[source-level]`
- **A call whose float result is never stored, followed by a call that reads the float return register** (`f1`) -> one call passing the result of the other, `vf24(vf20())`: check the callee for a float argument before writing a `void` signature -> mlab: `ExWorldTrack::vf1C/vf20/vf24` in `unit_800C52B4`. `[back-end]`
- **A matrix-vector product whose scheduling and stack slots do not match as `Vec end = mtx.Transform(v);`** -> write it through an output pointer: `Vec end; mtx.Transform(v, &end);` -> mlab: `fn_8013EDFC`, `fn_80139CC4`. `[source-level]`
- **A pointer to a vector temporary kept in a register where the original reads the stack slot** -> vector helpers written as free functions taking `const Vec&`, not the member forms (`v.Normalized() * s`) -> mlab (no function named). `[source-level]`
- **A global reloaded, or values not kept in saved registers, across `strlen` / `strcmp`** -> declare the function yourself (`unsigned long strlen(const char*)`) instead of including `<string.h>`, whose declaration lets mwcc treat the call as pure -> mlab: `fn_80121508`, `unit_8011D5C4`. `[source-level]`
- **An 8-byte struct returned through a hidden pointer** (the caller passes a stack slot in `r3`) **where the build returns it in two registers** (`r3`/`r4`) -> give the struct a user-defined copy constructor -> mlab: `UnkTreeRange` in `unit_800A34C0`. `[back-end]`

## Static functions and unit bounds

- **Where inline and weak functions land** -> inline functions used by a unit are emitted after the function that first needs them; weak functions after a unit's `__sinit` belong to the unit before them -> mlab (general rule). `[source-level?]`
- **A weak-looking function between two units** -> look at the `.sdata2` constants it uses: functions after a unit's static initializer that load the constant of the next static initializer are their own unit -> mlab: `unit_800D4C64`. `[source-level?]`
- **Small constructors and destructors after the last function of a unit, in definition order** -> define them out of line at the end of the file; generated copies are placed right after their first user instead -> mlab: `unit_800D3428`. `[source-level]`
- **Virtual functions that exist only in another unit of the original** (probably inline in the original header) -> declare them out of line so this unit does not emit copies -> spyro-dotd: `vfC`, `vf5C` of IKAnchor. `[source-level]`
- **A `static inline` function that the original also keeps as a global function** -> make it a plain global function; under `-ipa file` it is still inlined into earlier callers -> spyro-dotd: `VIGetScanMode` into `VIInit`. `[source-level]`
- **A function the original lacks but that a kept function inlines** -> mark it `inline`: still inlined, not emitted -> spyro-dotd: `strtol` in `strtoul.c`. `[source-level]`
- **Library sources define functions the original lacks** -> leave them in, the linker dead-strips unreferenced functions; put them under `#if 0` when they leave something the linker would have stripped with them but the object still holds: `extab` / `extabindex` entries (`-Cpp_exceptions on`), string literals, `.sdata2` float constants -> spyro-dotd: `ptmf.c`, `SIGetTypeString` in `SIBios.c`. `[source-level?]`
- **A unit that holds only a static initializer is dropped at link time** -> nothing references it and `FORCEACTIVE` cannot name a local `__sinit`: keep it with `FORCEFILES` in the linker script -> mlab: `unit_80006B40`, `unit_80042C18`. `[source-level?]`

## Structures, arrays and addresses

- **Only the base address of a global is kept in a register** -> the source takes the address of a real member of the global; a cast of the base plus an offset is kept whole -> mlab (no function named). `[source-level]`
- **A global addressed absolutely instead of through the small-data base** (`lis` / `@l` instead of `@sda21`) -> it is larger than 8 bytes: declare it as an array or struct with its full size; an external object declared with 8 bytes or less is addressed through `r13` -> mlab: `unit_800445E4`, `fn_80121B08`. `[back-end]`
- **A global's address built in a scratch register, then moved to a saved one** (`lis r9` then `addi r31, r9`) -> use the global directly (the compiler keeps the common address in a saved register); a local `T* g = &global;` gives `lis r31` -> mlab: `fn_80121508`. `[source-level?]`
- **A static initializer addresses each object with its own high half instead of one base** (one `lis` per object) -> `#pragma pool_data off` -> mlab: `unit_8013CA74`. `[source-level?]`
- **Locals that look like an 8-byte array but whose stack order does not match** -> they may be a 12-byte struct: type the output as the full parameter struct -> mlab: `fn_801606A4`. `[source-level]`
- **A struct assignment that copies float members as floats** (`lfs` / `stfs`) -> copy the members one by one; the implicit assignment of a struct of vectors copies words (`lwz` / `stw`), and placement `new` with the copy constructor adds a null check -> mlab: `UnkCopyInfo` in `unit_8010C750`. `[source-level?]`
- **A copy whose loads all come before the stores** (many saved registers, no stack) -> straight-line member assignments let the scheduler hoist the loads; a loop in the middle stops it, and the implicit `operator=` or copy constructor interleaves loads and stores -> mlab: `Unk800D4C64::operator=`. `[source-level?]`
- **A struct copied to the stack with a word loop, then read member by member with spills** -> the words are separate members, not an array -> mlab: `UnkOpponentData`, `fn_8013CA74`. `[source-level]`
- **An array searched through a pointer to its start, with the count read at an offset from that pointer** -> the array and its count form a sub-struct with its own inline search method -> mlab: `UnkCreatureList::IndexOf`. `[source-level]`
- **Bit insertion: shift, mask and or, or a single insert instruction** -> `(x & ~mask) | (v << shift)` gives `slwi` + `rlwinm` + `or`; real bit fields give `rlwimi`; use the form the original shows -> mlab: `UnkMsgHeader`. `[source-level?]`

## Data, constants and sections

- **Float constants pooled in the wrong order** -> constants are pooled in `.sdata2` in parse order: a header that defines a constant vector puts its constants first when it is included first; an unused static function can give the pool its original order (the original files likely had dead code) -> mlab (general rule). `[source-level]`
- **String literals pooled in the wrong order** -> they are pooled in parse order (small ones in `.sdata`, others in `.data`): an unused static function that uses them first gives the order. `static const char* const` pointers are not folded and become `.sdata2` objects -> mlab: `UnusedArchiveNames` in `unit_801091EC`. `[source-level]`
- **A string literal placed before an earlier function's jump table** -> a named file-scope array defined before that function -> mlab: `sDiscReadError`. `[source-level]`
- **Small local arrays initialized with constants** -> they are copied from compiler-made `.sdata2` objects of the array's full size; the symbol sizes must be the array size for the section to match -> mlab: `unit_8001A17C`. `[source-level?]`
- **An all-zero object kept in `.sdata` / `.data`** -> `#pragma explicit_zero_data on` around its definition; objects are emitted in definition order, so define it after the functions whose literals come before it -> mlab: `unit_80010B5C`. `[source-level]`
- **A global from a shared header is the last `.bss` object of every unit although its initializer runs first** -> `.bss` follows definition order, except that objects coming from a precompiled header are emitted after the unit's own objects: build that header as a precompiled header and include it first, only in the units that have the object (tested with every GC 3.0 version; `-ipa file` and `-inline deferred` change nothing). It also fixed the order of a registered object and of function-local statics -> mlab: `unit_8013CA74`, `unit_80098664`. `[source-level]`
- **A unit whose `.rodata` cannot be split (link order cycle)** -> it can still match and link: its tables stay in the unsplit `.rodata` and the source declares them `extern` -> mlab: `unit_800B1498`. `[source-level]`
- **Strings of dead-stripped functions that the original keeps in `.data`** (the linker strips the function, not the string pool) -> emit them from a stand-in function at the same place in the file -> spyro-dotd: `OSLaunch.c`. `[source-level]`

## C++

- **Vtables in the wrong order** -> vtables (with their class name strings and base lists) are emitted in reverse order of the class declarations: the last class declared is the first vtable -> mlab: `unit_800A5BCC`. `[source-level]`
- **A 0 entry in a vtable** -> a pure virtual function; the class can still have an out-of-line constructor called by derived classes -> mlab: `BuzzsawItem::vfC4`. `[source-level]`
- **The vtable pointer sits after some data members, not at offset 0** -> it goes where the first virtual function is declared: declare those members before the first virtual function (for a class whose base has no vtable; declared after, the pointer lands at offset 0) -> mlab: `Exploration::PathAPI`. `[source-level]`
- **Telling a member at offset 0 from a base class** -> member subobject destructors are called with -1, base class destructors with 0 -> mlab (general rule). `[source-level?]`
- **Several null tests of one pointer before a member's destructor body** (five `beq`) -> that many nested destructor calls, one `this` test each: the member's class sits that many levels down a hierarchy -> mlab: the MSL `__tree` owner. `[source-level]`
- **`if (p) delete p;` tests the pointer twice** (`beq` twice) -> the class has a declared, empty destructor; without a destructor the pointer is tested once -> mlab: `unit_800D6B0C`. `[source-level]`
- **Saved registers differ around `if (g != 0) { delete g; g = 0; }`** -> put the cleanup in an inline destructor; the same code written out before `delete` numbers them differently -> mlab: `fn_8001EF50`. `[source-level]`
- **A vector assigned from a member through a stack temporary** (copied to the stack, then to the local) -> a copy-constructor temporary: `pos = Vec(obj->m27C);` -> mlab: `fn_800B182C`. `[source-level]`
- **A small struct copied through registers, no stack temporary, in a swap** -> give the type an inline copy constructor; the implicit copy goes through a stack temporary -> mlab: `UnkStatRow` in `unit_8011D5C4`. `[source-level?]`
- **Calls through a member object's vtable with `this + offset` recomputed for each call** -> an inline accessor returning a base pointer; a local pointer keeps it in a saved register -> mlab: `BuzzSawExperiment::GetTrack`. `[source-level]`
- **An empty static initializer** (`__sinit` is a lone `blr`) -> a global object whose class has an empty inline constructor -> mlab: `unit_801604FC`. `[source-level]`
- **Destructors registered by a static initializer in the wrong order** -> they are emitted after `__sinit` in reverse order of use; their order follows the order in which the objects are defined (class definitions, `extern` declarations, template or plain classes, `-inline deferred` and inlined explicit destructor calls do not change it: only the out-of-line reference made for the registration counts). `-ipa file` per unit is the only setting found that gives registration order -> mlab: `unit_801F59F0`. `[source-level?]`
- **Extra weak destructors or RTTI in the compiled object** -> a constructor makes the compiler emit unreferenced weak copies of the members' inline destructors (container templates too), and RTTI (`__RTTI__<class>` in `.sdata`, name strings and base lists in `.data`) is emitted as weak or local copies in every unit that emits a vtable; the linker strips them or keeps the first unit's copy, and the unit still links byte for byte -> mlab: `unit_800D3428`; spyro-dotd: `unit_8032E43C`. `[source-level]`
- **A template function shared by two units** -> it must have the same mangled name in both; the earlier unit emits it (an explicit instantiation is enough) -> mlab: `unit_8009F66C`, `unit_8006F794`. `[source-level]`

## Compiler settings and pragmas

- **Functions defined later in the file are inlined, and functions are emitted in reverse order of definition** -> `-inline auto,deferred` on that unit; applied to all game code it breaks other units -> mlab: `unit_8011EA20`. `[source-level]`
- **Recursive destructors inlined several levels deep, element destructor chains inlined in full** (MSL map) -> `-ipa file` on that unit; `inline_depth`, `inline_max_size`, `nobottomup` and `deferred` each fix one function and break another. With it, implicit destructors of templates are inlined too, an inline function defined last is still inlined earlier and the inline functions it needs are emitted at the end; on all game code it reverses the inline functions of other units -> mlab: `unit_8009F66C`, `unit_8006F794`. `[source-level]`
- **Peephole optimizer off** -> signs of `-opt nopeephole`: a vtable address built in `r0` (`addi r0, r4, ...`), epilogue `lwz r0` before `lwz r31`, `extsh` + `cmpwi` kept apart, no `mr.`; other code of the same executable has the opposite, so flag sets can differ by region -> spyro-dotd: `unit_8032E43C`. `[back-end]`
- **Fused multiply-add instructions absent from the original** (`fmadds` / `fnmsub`) -> `-fp_contract off`; with `on` every compiler tested emits them -> mlab: `fn_8007DD7C`, `fn_800E2DF4`. `[back-end]`
- **A static initializer with one address computation per object** -> `#pragma pool_data off` (see Structures) -> mlab: `unit_8013CA74`. `[source-level?]`
- **A zero-initialized object outside `.bss` / `.sbss`** -> `#pragma explicit_zero_data on` (see Data) -> mlab: `unit_80010B5C`. `[source-level]`
- **References in `.ctors` / `.dtors` stripped by the linker, shifting both sections** -> `#pragma force_active on` around the references -> spyro-dotd: `__init_cpp_exceptions.cpp`. `[source-level?]`
- **Exception tables left in an object** -> a function compiled with `-Cpp_exceptions on` leaves `extab` / `extabindex` entries even when the linker strips the function -> spyro-dotd: `ansi_files.c`, `buffer_io.c`. `[source-level?]`

## Compiler versions

- **GC 2.x against GC 3.0** -> GC 2.0 to 2.7 fail on small functions that every GC 3.0 and Wii compiler matches; the differences are `cmplwi` versus `cmpwi` on pointers and the merged `mr.` -> mlab: `fn_8018E8D8`, `fn_8018EE3C`. `[back-end]`
- **GC 3.0 against the Wii compilers (1.0RC1 to 1.7): jump table threshold** -> the Wii compilers need 8 `case` values for a jump table at every optimization level tried (only `-O0` goes down to 4) and emit a compare chain for 7; GC 3.0 emits the table. A single-`case 0` switch under `-opt nopeephole` is also one instruction shorter with the Wii compilers -> mlab: `fn_80207D40`; spyro-dotd: `fn_8032E520`. `[source-level?]`
- **Inside GC 3.0, only two classes exist: {3.0a5.2} and {3.0a3, 3.0a3p1, 3.0a3.2, 3.0a3.3, 3.0a3.4, 3.0a5}** -> 240 fuzzed functions under four flag sets gave identical code inside the second class, and no difference at all at `-O2`. 3.0a5.2 removes int-to-float conversions whose result is dead: the older class emits `fcmpo`, a conditional branch over two dead conversion stores and a 0x20 frame, 3.0a5.2 a dead `fcmpo` with no branch, no stores and a 0x10 frame -> mlab: fuzzing; no game function of mlab shows either signature. `[back-end]`
- **A library function one version makes too short** -> some MSL math files (`e_pow.c`, `e_rem_pio2.c`, `k_tan.c`, `s_atan.c`) match only with 3.0a3 / 3.0a5 (3.0a5.2 removes dead stores), while `printf.c` needs 3.0a5.2: one executable can hold code from both classes, so set the version per object -> mlab and spyro-dotd: MSL_C. `[source-level?]`
- **A constructor under `-opt nopeephole` that separates 3.0a5.2 from 3.0a3 to 3.0a5** -> an empty-bodied constructor of a class with a vtable matches with 3.0a5.2 and the Wii compilers only; together with the single-case switch above, 3.0a5.2 is the only compiler matching both -> spyro-dotd: `fn_8032E43C`, `fn_8032E520`. `[back-end]`
- **Paired-single save in the prologue** -> GC 3.0a5.2 emits the `psq_st f31` prologue -> mlab: `fn_80207DCC`. `[back-end]`
- **`.comment` section version byte** -> GC 2.7 writes 11, 3.0a3 writes 14, 3.0a5 and 3.0a5.2 write 15 (byte 0xB of `.comment` in a compiled object) -> mlab. `[source-level?]`
- **Linker family** -> every GC 3.0 linker reproduces the executable from the same objects; the Wii linkers give a different header and section layout (32 bytes longer), GC 2.6 fails and GC 2.7 stops on an internal error -> spyro-dotd: linker test. `[source-level?]`

## Open symptoms

- **Search loops whose count is reloaded every iteration (no counter-register loop) while the group index stays in a register** (`li 0` / `mullw`) -> not reproduced -> mlab: `fn_800D8724`, `ExWorldWireTile::vfBC`. `[source-level?]`
- **A struct copied twice on the stack, word by word then member by member** (`lha` / `lbz`), **both copies kept and the base pointer reloaded every iteration** -> copy constructor, assignment, a second type, by-value or member predicate all let the compiler drop the copies -> mlab: `Recipes::fn_80120990`. `[source-level?]`
- **An inlined member function whose stack temporaries come out in the opposite order of its out-of-line copy** -> not reproduced (shared inline helper, inline getter, argument by value tried) -> mlab: `fn_8009875C` inlined in `fn_800988F0`. `[source-level?]`
- **Empty debug branches that keep a jump and a dead compare in the original** -> the build removes them -> mlab: GameSpy units. `[source-level?]`
- **An identity matrix built on the stack as four 12-byte temporaries in row order, each copied into the matrix right after it** -> no spelling found -> mlab: `fn_8012112C`. `[source-level?]`
- **Destructors registered by a static initializer, in an order no setting reproduces** -> see the C++ entry; still unsolved for one unit -> mlab: `unit_801088C0`. `[source-level?]`
