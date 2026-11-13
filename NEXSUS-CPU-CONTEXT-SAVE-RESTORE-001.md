# NEXSUS CPU Register Save/Restore and Context Frame
**Document ID:** NEXSUS-CPU-CONTEXT-SAVE-RESTORE-001  
**Status:** Architecture baseline proposal

## 1. Design rules
This specification reuses the existing NEXSUS register banks and memory system. It adds no memory class or register bank.
- ECS holds hardware exception/return metadata.
- SPM7 is the depth-selected temporary workspace during exception entry.
- Data RAM holds persistent privileged handler save frames and full task contexts when they must survive scheduling.
- Existing RA/FA/DA/MA banks remain unchanged.
- SPM0–SPM6 retain their existing execution-workspace roles; exception handling does not silently reserve them.
- P0 is instruction prefetch storage and is not part of a software context save.

## 2. Register bank sizes
| Bank | Registers | Width each | Full bank size |
|---|---:|---:|---:|
| RA | 32 | 64-bit | 256 B |
| FA | 32 | 64-bit | 256 B |
| DA | 32 | 64-bit | 256 B |
| MA | 32 | 256-bit | 1,024 B |
| **Total** | **128** | — | **1,792 B** |

MA is the dominant save cost; saving it on every interrupt without need is prohibited by the baseline ABI.

## 3. Interrupt handler preservation contract
The interrupt ABI defines a 32-bit save mask for each bank. Bit N indicates whether register N must be preserved by this handler invocation:
- RA_MASK[31:0]
- FA_MASK[31:0]
- DA_MASK[31:0]
- MA_MASK[31:0]

A set bit means the interrupted value must be restored before IRET. A clear bit means the handler is guaranteed not to alter that register. Masks are generated from handler code and its complete call graph, or supplied by handwritten assembly. If analysis is unavailable or unknown code can be called, the conservative mask includes every register the call path may modify.

### 3.1 Bank policy
- RA: save touched integer registers only.
- FA: save touched FP registers only; preserve FP status/control state if handler FP operations can change it.
- DA: save touched staging registers only.
- MA: save touched 256-bit registers only; blanket MA saves are unnecessary unless all are live/modified.
- A handler calling a normal function must satisfy the interrupt ABI across the complete call graph.
- A handler may not use a register declared preserved as hidden scratch.

## 4. Software save-frame layout
Frames are stored in a privileged, bounded Data RAM region addressed by KESP/KELIMIT. Frame alignment is 32 bytes. Only selected registers occupy payload slots.

### 4.1 Header (fixed 64 bytes)
| Offset | Size | Field |
|---:|---:|---|
| 0x00 | 8 | FRAME_MAGIC_VERSION |
| 0x08 | 8 | FRAME_SIZE |
| 0x10 | 8 | PREVIOUS_FRAME_PTR |
| 0x18 | 8 | SAVE_MASK_RA |
| 0x20 | 8 | SAVE_MASK_FA |
| 0x28 | 8 | SAVE_MASK_DA |
| 0x30 | 8 | SAVE_MASK_MA |
| 0x38 | 8 | FLAGS / BANK_STATE_VALID |

Each mask uses its low 32 bits; upper bits must be zero. Payload follows in ascending bank order RA, FA, DA, MA, and ascending register index. Each register retains native width. MA payloads are 32-byte aligned. Frame size is rounded up to 32 bytes.

The header does not duplicate EPC/CAUSE/IRQ claim state; those remain in ECS.

### 4.2 Integrity
- FRAME_MAGIC_VERSION identifies format/version.
- FRAME_SIZE must be within KELIMIT bounds and 32-byte aligned.
- PREVIOUS_FRAME_PTR must point to the prior valid frame or configured empty-frame sentinel.
- Masks and payload extents must be consistent.
- Invalid metadata causes controlled fatal/double-fault handling; IRET never trusts arbitrary frame pointers.
- Optional checksum is platform policy, not required for initial ISA baseline.

## 5. Exception-entry sequence
1. CPU detects a synchronous exception or accepts an eligible IRQ at a safe instruction boundary.
2. Hardware pushes minimal control metadata into ECS.
3. Hardware selects the SPM7 slice corresponding to active ECS depth.
4. On privilege transition, hardware switches to configured privileged exception stack pointer KESP before the first handler instruction.
5. Handler prologue uses SPM7 for temporary values while establishing its Data RAM save frame.
6. Prologue writes header and selected RA/FA/DA/MA payloads to the bounded privileged Data RAM region.
7. Only after required interrupted state is safe may the handler enable nested maskable IRQs.
8. Handler body executes; registers outside declared masks must remain unchanged.
9. Before return, handler restricts nesting as required, restores selected registers in reverse payload order, validates/releases software frame.
10. IRQ handler performs source-specific acknowledgement and IRQEOI as required.
11. IRET validates and pops the ECS frame, restores control state and resumes execution.

SPM7 is temporary; persistent save frames live in Data RAM. Its contents are unspecified after the ECS level is released.

## 6. Nested interrupts
Each ECS depth selects its own 1 KiB SPM7 slice. Each nested handler gets a distinct software frame on the privileged Data RAM exception stack.
- Outer frame remains allocated until its handler returns.
- Nested frames link through PREVIOUS_FRAME_PTR and release strictly LIFO.
- KESP uses downward-growing stack; frame alignment is 32 bytes.
- Before re-enabling nested IRQs, the handler must finish its header and save every register it has modified so far.
- Nested handlers preserve outer handler live state under the same interrupt ABI.
- Eight ECS levels are the minimum; Data RAM stack bounds must cover worst-case nesting, save masks and call depth.

## 7. Full task context switch
A task context differs from an interrupt frame. When scheduler switches execution, it preserves all architectural state the task owns and may later observe.

Baseline full context includes:
- RA0–RA31, FA0–FA31, DA0–DA31, MA0–MA31.
- Required FP status/control and other task-visible execution state.
- PC and STATUS/privilege through controlled scheduler context-switch path.
- Memory-domain permissions, ownership/handle state and relevant address-space configuration.
- SPM0–SPM6 allocation/ownership metadata and contents for every bank whose contents are live across the switch.
- SPM7 is reserved for active exception entry and is not task-owned.
- P0 is refillable instruction prefetch state, not architectural task state.

Full four-bank register payload is 1,792 bytes before metadata. Scheduler may optimize using bank ownership/dirty state but must restore exact architectural values before resuming a task.

## 8. SPM ownership and migration
SPM banks are directly addressed local resources, not automatically coherent cache levels.
- A task using an SPM bank has explicit owner/lifetime in its execution context.
- A same-core task switch preserves live SPM0–SPM6 contents or transfers ownership only after the old owner no longer depends on them.
- Migrating a task to another core transfers live SPM contents through existing memory/Fabric mechanisms or rebuilds them; physical SPM contents do not follow automatically.
- SPM7 remains reserved for exception entry on every core.
- No automatic SPM migration is implied by a normal task switch.

## 9. Restore and return invariants
- Restore exactly registers selected by masks; never restore uninitialized payload.
- Restore all selected registers before IRET.
- IRET restores ECS control state only; it does not load RA/FA/DA/MA payloads.
- IRQEOI is separate from software-frame release and IRET.
- A synchronous fault handler may edit saved PC only when CAUSE flags permit skip/emulation/recovery.
- An asynchronous IRQ resumes at the saved next instruction boundary.
- Context switch is scheduler-controlled state replacement, not an ECS pop.

## 10. ABI and compiler requirements
Compiler/assembler support:
- Interrupt-handler attribute and distinct interrupt ABI.
- Static or conservative transitive register-clobber analysis.
- Emission of four per-bank 32-bit save masks.
- Native-width save/restore of selected registers.
- 32-byte frame alignment and bounds checks.
- Nested-handler prologue/epilogue generation.
- Full-context save/restore for scheduler code.

If the compiler cannot prove a register untouched, it must preserve it. Correctness takes priority over frame-size optimization.

## 11. Baseline decisions
**Selected:** SPM7 for temporary exception workspace; privileged Data RAM for persistent software frames; four 32-bit bank masks; selective per-register save/restore; full 1,792-byte register payload for complete task context; P0 excluded; SPM0–SPM6 preserved only when live.

**Not introduced:** new memory type, new register bank, new transfer mechanism, or automatic cache-like SPM migration.

**Open:** exact KESP stack direction/CSR semantics; save-mask representation in compiler metadata; eager versus bank-dirty optimized full task save; FP status/control inventory; SPM ownership descriptor format.
