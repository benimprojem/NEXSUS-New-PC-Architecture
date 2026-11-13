# NEXSUS CPU Register Save/Restore and Context Frame
**Document ID:** NEXSUS-CPU-CONTEXT-SAVE-RESTORE-001  
**Status:** Architecture baseline proposal

## 1. Design rules
This specification reuses the existing NEXSUS register banks and memory system. It adds no memory class or register bank.
- ECS holds hardware exception/return metadata.
- SPM7 is the depth-selected temporary workspace during exception entry.
- Data RAM holds persistent privileged handler save frames and full task contexts when they must survive scheduling.
- Existing RA/FA/DA/MA banks remain unchanged.
- SPM0–SPM6 retain their existing execution-workspace roles by default. The OS may explicitly allocate currently available SPM1–SPM6 capacity as task-context residency slots; this is an ownership/allocation decision, not a permanent hardware reservation. Exception handling does not reserve them.
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

A set bit means the interrupted value must be restored before IRET. A clear bit means the handler and its save/restore prologue are guaranteed not to alter that register. Masks are generated from handler code, the complete call graph, and the prologue's own staging-register clobbers, or supplied by handwritten assembly. If analysis is unavailable or unknown code can be called, the conservative mask includes every register the call path may modify.

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
- SPM0–SPM6 allocation/ownership metadata and contents for every bank whose contents are live across the switch. When OS-managed context slots are allocated from SPM1–SPM6, the task's saved register context may remain resident there.
- SPM7 is reserved for active exception entry and is not task-owned.
- P0 is refillable instruction prefetch state, not architectural task state.

Full four-bank register payload is 1,792 bytes before metadata. Scheduler may optimize using bank ownership/dirty state but must restore exact architectural values before resuming a task.

## 8. SPM ownership and migration
SPM banks are directly addressed local resources, not automatically coherent cache levels.
- A task using an SPM bank has explicit owner/lifetime in its execution context.
- A same-core task switch preserves live SPM0–SPM6 contents or transfers ownership only after the old owner no longer depends on them. SPM1–SPM6 may additionally host explicitly allocated, fixed-size task-context slots; a slot remains owned by its task until released or evicted.
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


## 12. Existing instruction paths for save/restore

The save/restore ABI reuses already specified ISA operations; it does not require new opcodes or a new transfer engine.

- SPM.RD / SPM.WR can transfer supported widths directly between SPM and RA/FA/DA/MA register banks. SPM7 is used for the per-depth temporary workspace and initial prologue scratch.
- MOV.DA.RA and MOV.RA.DA provide the existing 64-bit RA↔DA staging path.
- MOV.DA.FA and MOV.FA.DA provide the existing FA↔DA path.
- MOV.DA.MA and MOV.MA.DA provide the existing 256/512-bit MA↔DA group path.
- Existing LOAD/STORE operations move DA staging groups to/from the protected Data RAM save-frame region.

### 12.1 Safe bank ordering when DA is the transfer staging bank

Because DA is the staging bank for memory LOAD/STORE and explicit bank transfers, the handler must not overwrite interrupted DA values before preserving them.

**Save order:**
1. Save every DA register selected by DA_MASK to the Data RAM frame first, using STORE while the original DA values are intact. DA_MASK must also include every DA selector that the prologue will use as a staging temporary for RA/FA/MA transfers, even if the handler body itself never references that DA register.
2. Save selected RA registers: MOV.DA.RA to staging DA, then STORE to the frame.
3. Save selected FA registers: MOV.DA.FA to staging DA, then STORE to the frame.
4. Save selected MA registers/groups: MOV.DA.MA to staging DA, then STORE the 256/512-bit DA group to the frame.

**Restore order:**
1. Restore MA payloads: LOAD to DA staging, then MOV.MA.DA.
2. Restore FA payloads: LOAD to DA staging, then MOV.FA.DA.
3. Restore RA payloads: LOAD to DA staging, then MOV.RA.DA.
4. Restore DA payloads last, so no subsequent staging operation can overwrite the restored DA values.

SPM7 supplies the temporary prologue workspace and can preserve the initial scratch values while KESP/frame setup is performed. SPM7 is not used as an excuse to introduce a parallel register bank. The per-depth 1 KiB slice is bounded; if a prologue needs more temporary data, it must use the normal protected Data RAM frame rather than overwrite another depth's slice.

This ordering is mandatory for correctness. The compiler may optimize transfers only when it proves the same preservation and ordering invariants. It must account for the DA staging clobber set in DA_MASK; otherwise the interrupted program's DA state could be corrupted.

## 13. Save-frame size and SPM7 capacity

The full architectural RA/FA/DA/MA payload is 1,792 bytes. A selective interrupt frame is smaller according to its masks, plus a 64-byte header and alignment. SPM7 remains 8 KiB total, partitioned into eight 1 KiB depth slices for temporary entry state; it is not the storage capacity for all nested full-register frames. Persistent frames use the protected Data RAM region. If the Data RAM frame stack reaches KELIMIT, the CPU enters the defined double-fault path; it must never silently truncate a save frame.


## 14. SPM-resident task-context slots

The scheduler may use available SPM1–SPM6 capacity to keep several complete task register contexts resident on the same core. This reuses the existing SPM memory and existing register-transfer instructions; it adds no new memory type, register bank, cache level or ISA opcode.

### 14.1 Slot sizing and five-task target

The four architectural register banks contain 1,792 bytes:
- RA: 256 bytes
- FA: 256 bytes
- DA: 256 bytes
- MA: 1,024 bytes

A full task-context slot is allocated as **2 KiB**, aligned to a 2 KiB boundary. It contains the 1,792-byte register payload, context/control metadata, and alignment reserve. The exact internal metadata layout is an ABI detail to be finalized with the scheduler implementation.

Five resident contexts therefore require **10 KiB**. SPM1–SPM6 provide 48 KiB in total, so five slots fit when that capacity is available. If all six banks were dedicated to this purpose, the theoretical ceiling would be 24 slots of 2 KiB each. This is a capacity calculation, not a promise that all 24 are always available: active workloads may already own SPM space.

### 14.2 Allocation policy

- SPM1–SPM6 remain general directly addressable SPM resources. The OS explicitly reserves free 2 KiB-aligned ranges for context slots; there is no unconditional fixed reservation.
- SPM0 remains the 2 KiB execution workspace and is not included in the five-slot baseline.
- SPM7 remains exclusively reserved for exception-entry temporary slices.
- Each slot has an owner task ID, generation/version, valid-state and size recorded in the scheduler's existing task metadata.
- A slot is valid only after the complete context payload and metadata have been written. Publication uses required release ordering; a consumer uses acquire ordering before restoring it.
- A task with no resident SPM slot keeps its full context in the protected Data RAM task-context area. SPM residency is an optimization, never the only durable copy when the scheduler needs to reclaim the slot.
- Eviction is explicit: write the complete valid context to Data RAM, verify completion, then release the SPM range. Never overwrite a live owner's slot.
- When SPM capacity is occupied by application workspace, the scheduler falls back to Data RAM; it must not silently steal task-owned SPM ranges.

### 14.3 Context switch with resident slots

For a same-core switch from Task A to Task B:

1. Enter the scheduler through the normal exception/context-switch path; preserve the outgoing task's architectural state.
2. If A owns an allocated context slot, write A's latest RA/FA/DA/MA values and required control metadata into that slot. Otherwise, write them to its protected Data RAM context.
3. Locate B's slot by task ID and generation. If valid and resident, restore its context directly from SPM using the existing SPM.RD/SPM.WR and register-bank transfer paths. If it is not resident, restore from Data RAM and optionally allocate a free SPM slot for a later switch.
4. Restore control state and memory-domain ownership under the scheduler's privilege checks.
5. Start/refill P0 for B's saved PC in parallel with the context restore where the implementation permits.
6. Do not dispatch B's first instruction until its architectural state is valid and the required instruction fetch for its resume PC is available.
7. Publish the task handoff with release/acquire ordering; then resume B.

The scheduler must use the existing DA staging-order rules when transferring RA/FA/MA through DA. DA values are preserved before DA is used as staging, and DA is restored last.

### 14.4 Five-task ready set

A core can keep five task contexts resident simultaneously using five 2 KiB slots (10 KiB total). This means five saved contexts can be restored without first reading their register payloads from Data RAM. It does **not** mean five tasks execute simultaneously on one core: one task owns the architectural execution pipeline at a time, while the other four remain saved and ready.

The OS may choose which five tasks receive resident slots based on scheduling priority, wake frequency and expected reuse. Slot replacement is an OS policy decision; no hardware task-cache behavior is implied.

## 15. P0 refill during task dispatch

P0 is per-core command prefetch storage, separate from SPM-resident task contexts.

- When the scheduler selects a task, it obtains that task's resume PC and App RAM code-domain reference.
- P0 refill/prefetch for the selected task may begin while the scheduler restores its RA/FA/DA/MA context from SPM or Data RAM.
- The fetch path uses App RAM → P0 → Fetch/Decode/Dispatch. Context payload transfers use SPM and/or Data RAM; they are independent paths.
- The core must not issue the resumed task's instruction stream until the correct P0 contents are valid for its resume PC and code-domain identity.
- On a task switch, stale P0 entries from the outgoing task must not be interpreted as instructions belonging to the incoming task. P0 refill/validity is associated with the selected task's code identity and resume address; implementation may invalidate or replace entries as required.
- P0 contents are not saved in the task context. A later switch back to a task simply refills P0 from App RAM as needed.

This allows command prefetch and context restoration to overlap without treating P0 as persistent task state or merging the App RAM and Data RAM paths.

## 16. Updated baseline decisions

**Selected:** OS-managed, explicitly allocated 2 KiB task-context slots in available SPM1–SPM6; five simultaneous resident contexts as a practical target (10 KiB); Data RAM backing for nonresident/evicted contexts; P0 refill for the incoming task overlapped with context restoration when possible.

**Unchanged:** SPM0 execution workspace; SPM7 exception workspace; P0 refillable command prefetch; full task context remains 1,792 bytes of register payload plus metadata; SPM is directly addressed local memory, not a coherent cache.

**Open:** exact context-slot metadata layout; SPM allocator interface; whether the scheduler dedicates a configurable SPM quota per core; P0 task/code identity tagging details.
