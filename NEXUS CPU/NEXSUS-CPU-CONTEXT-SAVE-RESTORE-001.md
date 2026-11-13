# NEXSUS CPU Register Save/Restore and Context Frame
**Document ID:** NEXSUS-CPU-CONTEXT-SAVE-RESTORE-001  
**Status:** Architecture baseline proposal

## 1. Design rules
This specification reuses the existing NEXSUS register banks and memory system. It adds no memory class or register bank.
- ECS holds hardware exception/return metadata.
- SPM7 is the depth-selected temporary workspace during exception entry.
- Data RAM holds persistent privileged handler save frames and full task contexts when they must survive scheduling.
- Existing RA/FA/DA/MA banks remain unchanged.
- SPM0–SPM6 retain their existing execution-workspace roles by default. The OS may explicitly allocate currently available SPM3–SPM6 capacity as task-context residency slots; this is an ownership/allocation decision, not a permanent hardware reservation. Exception handling does not reserve them.
- P0 is instruction prefetch storage and is not part of a software context save.

## 2. Register bank sizes
| Bank | Registers | Width each | Full bank size |
|---|---:|---:|---:|
| RA | 64 | 64-bit | 512 B |
| FA | 64 | 64-bit | 512 B |
| DA | 64 | 64-bit | 512 B |
| MA | 64 | 256-bit | 2,048 B |
| **Total** | **256** | — | **3,584 B** |

MA is the dominant save cost; saving it on every interrupt without need is prohibited by the baseline ABI.

## 3. Interrupt handler preservation contract
The interrupt ABI defines a 64-bit save mask for each bank. Bit N indicates whether register N must be preserved by this handler invocation:
- RA_MASK[63:0]
- FA_MASK[63:0]
- DA_MASK[63:0]
- MA_MASK[63:0]

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
- RA0–RA63, FA0–FA63, DA0–DA63, MA0–MA63.
- Required FP status/control and other task-visible execution state.
- PC and STATUS/privilege through controlled scheduler context-switch path.
- Memory-domain permissions, ownership/handle state and relevant address-space configuration.
- SPM0–SPM6 allocation/ownership metadata and contents for every bank whose contents are live across the switch. When OS-managed context slots are allocated from SPM1–SPM6, the task's saved register context may remain resident there.
- SPM7 is reserved for active exception entry and is not task-owned.
- P0 is refillable instruction prefetch state, not architectural task state.

Full four-bank register payload is 3,584 bytes before metadata. Scheduler may optimize using bank ownership/dirty state but must restore exact architectural values before resuming a task.

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
- Emission of four per-bank 64-bit save masks.
- Native-width save/restore of selected registers.
- 32-byte frame alignment and bounds checks.
- Nested-handler prologue/epilogue generation.
- Full-context save/restore for scheduler code.

If the compiler cannot prove a register untouched, it must preserve it. Correctness takes priority over frame-size optimization.

## 11. Baseline decisions
**Selected:** SPM7 for temporary exception workspace; privileged Data RAM for persistent software frames; four 64-bit bank masks; selective per-register save/restore; full 3,584-byte register payload for complete task context; P0 excluded; SPM0–SPM6 preserved only when live.

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

The full architectural RA/FA/DA/MA payload is 3,584 bytes. A selective interrupt frame is smaller according to its masks, plus a 64-byte header and alignment. SPM7 remains 8 KiB total, partitioned into eight 1 KiB depth slices for temporary entry state; it is not the storage capacity for all nested full-register frames. Persistent frames use the protected Data RAM region. If the Data RAM frame stack reaches KELIMIT, the CPU enters the defined double-fault path; it must never silently truncate a save frame.


## 14. SPM-resident task-context slots

The scheduler may use available SPM1–SPM6 capacity to keep several complete task register contexts resident on the same core. This reuses the existing SPM memory and existing register-transfer instructions; it adds no new memory type, register bank, cache level or ISA opcode.

### 14.1 Slot sizing and resident-context target

With 64 registers in each bank, the full register payload is **3,584 bytes**:
- RA: 64 × 8 = 512 bytes
- FA: 64 × 8 = 512 bytes
- DA: 64 × 8 = 512 bytes
- MA: 64 × 32 = 2,048 bytes

A resident context slot is **4 KiB**, aligned to 4 KiB. A 64-byte frame header plus 3,584-byte register payload totals 3,648 bytes and fits with alignment reserve.

SPM3–SPM6 provide four 8-KiB banks. Each bank holds two 4-KiB slots:
- 4 banks × 2 slots = **8 resident full-context slots/core**.
- These are fast resident contexts, not total task count or simultaneous execution count.
- Further task contexts remain in protected Data RAM.

### 14.2 Allocation policy

- SPM3–SPM6 remain OS-managed context-residency pools; each 4-KiB slot has task ID, generation, valid state and ownership metadata.
- A slot becomes valid only after its complete context is saved and published with release ordering; restore requires acquire ordering.
- SPM1/SPM2 keep their OS/user workspace roles and are not counted in the eight-slot context pool.
- SPM0 remains CPU-exclusive; SPM7 remains exception-entry-only.
- If a task has no resident slot, its full context stays in protected Data RAM.

### 14.3 Eight-context ready set

A core may keep up to eight full register contexts resident across SPM3–SPM6. One task owns the execution pipeline at a time; the other contexts are saved and ready. The OS may choose residency based on scheduling priority and reuse. Eviction is an explicit OS decision and must never overwrite a live context.

### 14.4 Task-switch operation

1. Stop outgoing architectural retirement at the defined switch boundary.
2. Save the outgoing 3,584-byte register payload plus frame metadata into a resident 4-KiB slot when available; otherwise use protected Data RAM.
3. Resolve and restore the incoming task's register state from its resident slot or Data RAM.
4. Restore control, address-space and memory-domain state under privilege checks.
5. Refill the incoming task's P0/P1 command buffers in parallel where the App RAM and context paths permit.
6. Do not resume until architectural state and the required instruction block are valid.
7. Publish the handoff with release/acquire ordering.

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

**Selected:** OS-managed 4 KiB task-context slots in SPM3–SPM6; eight simultaneous resident full-register contexts/core (32 KiB pool); Data RAM backing for nonresident/evicted contexts; P0 refill for the incoming task overlapped with context restoration when possible.

**Unchanged:** SPM0 execution workspace; SPM7 exception workspace; P0 refillable command prefetch; full task context remains 1,792 bytes of register payload plus metadata; SPM is directly addressed local memory, not a coherent cache.

**Open:** exact context-slot metadata layout; SPM allocator interface; whether the scheduler dedicates a configurable SPM quota per core; P0 task/code identity tagging details.

## 14. Fixed SPM role partition and resident task-context pool

The baseline per-core SPM allocation is now explicitly partitioned by role. Each SPM bank is 8 KiB.

| Bank | Capacity | Owner / role |
|---|---:|---|
| SPM0 | 2 KiB | CPU execution workspace; existing role |
| SPM1 | 8 KiB | OS-only workspace and OS-defined syscall/I/O exchange area |
| SPM2 | 8 KiB | User/programmer-addressable workspace |
| SPM3 | 8 KiB | OS-managed resident task-context pool |
| SPM4 | 8 KiB | OS-managed resident task-context pool |
| SPM5 | 8 KiB | OS-managed resident task-context pool |
| SPM6 | 8 KiB | OS-managed resident task-context pool |
| SPM7 | 8 KiB | Exception-entry workspace; eight 1 KiB depth slices |

### 14.1 SPM1 — OS workspace and syscall exchange

SPM1 is reserved to the OS. It provides temporary OS working storage and a fast exchange area for syscall arguments, results, and bounded I/O staging such as print/input operations.

- The hardware does not hard-code syscall meanings or fixed sub-addresses.
- The OS defines the ABI layout, offsets, ownership, valid lengths, and lifetime of each exchange region.
- User code must enter through the defined syscall interface; it must not directly overwrite OS-owned SPM1 state.
- Large or long-lived payloads remain in the appropriate App/Data RAM domain and are referenced by address/handle. SPM1 is not a general payload buffer for arbitrary large transfers.
- OS code must define whether each exchange field is input, output, in/out, and whether it is valid only for the duration of the syscall.

### 14.2 SPM3 — user/programmer workspace

SPM2 is directly addressable by user programs as a fast local working area. It is not a hardware-managed stack and imposes no push/pop or LIFO behavior. Programs may use it for explicitly addressed scratch data, temporary values, and runtime-defined workspace.

SPM2 has one physical 8 KiB capacity per core. Its contents are owned by the currently scheduled execution context when that context is allowed to use it. On a task switch, the OS must preserve live task-owned SPM2 contents in that task's Data RAM context backing (or retain the task/core residency without reassigning SPM3). The next task's SPM2 image is restored before it resumes if that image is live. A program that does not require SPM3 contents to survive a yield may declare/release that workspace through the OS ABI. No implicit cross-core migration of SPM3 contents occurs.

### 14.3 SPM2 and SPM4–SPM6 — resident task register-context slots

Four banks are dedicated to the OS-managed fast task-context pool: SPM3, SPM4, SPM5, and SPM6. Their combined capacity is 32 KiB.

A full RA/FA/DA/MA payload is 1,792 bytes. The existing 64-byte save-frame header brings the base frame to 3,648 bytes, which fits in a 4 KiB slot with 32-byte alignment. Therefore each 8 KiB bank contains two 4 KiB slots:

- 4 banks × 2 slots = **8 resident task-context slots per core**.
- Each 4-KiB slot holds one full register-bank image and its save-frame header.
- Task control metadata (PC, STATUS, FP control/status, address-space and memory-domain descriptors, SPM ownership metadata, and scheduling state) remains in the task control block in protected Data RAM; the slot does not duplicate ECS state.
- A slot is assigned to exactly one task at a time. The OS tracks valid/invalid state, task identity, generation, and ownership. It must complete the save before publishing a slot as valid and complete restore before resuming the task.
- If more than 8 tasks are runnable/retained on a core, the excess contexts remain in protected Data RAM and can be loaded into a slot when scheduled. **8 is the resident fast-slot maximum, not the system-wide task-count limit.**
- If the implementation changes slot header size or adds context payload fields, the 4 KiB fit must be revalidated; it must not silently overlap adjacent slots.

The OS may choose any slot ordering and eviction policy, but it must preserve explicit ownership and cannot overwrite a live context. Task-context slots are OS-owned storage; they are not simultaneously available as arbitrary application scratch space.

### 14.4 Task switch overlap with P0 refill

When the scheduler selects a different task, the context and instruction paths may proceed independently:

1. Save the outgoing task's architectural register context into its assigned SPM slot when a slot is available; otherwise save it to protected Data RAM.
2. Resolve the incoming task's slot and restore RA/FA/DA/MA state. If its context is not resident, load it from protected Data RAM into a free slot or directly restore through the established transfer path.
3. In parallel, initiate/refill P0 from the incoming task's App RAM instruction stream using the task's saved PC and address-space mapping.
4. Do not dispatch the incoming task until both its required architectural state and the first required instruction(s) are ready and all address-space/permission state is installed.
5. P0 contents are discarded/replaced as needed; P0 is not copied into the task's 2 KiB context slot and is not part of the saved architectural context.

This overlap is an implementation opportunity, not a guarantee that context restore and P0 refill always finish in the same cycle. The scheduler must handle either path completing first.

### 14.5 Capacity summary

| Purpose | SPM capacity |
|---|---:|
| OS workspace + syscall exchange (SPM1) | 8 KiB |
| User/programmer workspace (SPM2) | 8 KiB |
| Resident task register-context pool (SPM3–SPM6) | 32 KiB |
| Execution workspace (SPM0) | 2 KiB |
| Exception workspace (SPM7) | 8 KiB |
| **Total per core** | **58 KiB** |

This partition replaces the earlier flexible SPM1–SPM6 task-slot allocation proposal. The fixed role partition is the baseline; changing it requires an explicit OS/platform configuration rather than implicit sharing.



## 15. Task-switch sequence and SPM2 user-workspace preservation

The fixed allocation is SPM1=OS, SPM2=user workspace, SPM3–SPM6=resident task-context pool, and SPM7=exception workspace. The scheduler follows this order:

1. Enter the privileged scheduler path using the existing exception/context-switch mechanism. SPM7 remains reserved for exception entry; SPM1 is available for OS scheduler bookkeeping and syscall exchange.
2. Quiesce the outgoing task at a defined architectural boundary and prevent its state from being modified while it is being saved.
3. Save the outgoing RA/FA/DA/MA architectural state to its assigned 4 KiB slot in SPM3–SPM6 if resident capacity is available; otherwise save it to the protected Data RAM context backing. The DA staging ordering rules in Section 12.1 remain mandatory.
4. Preserve the outgoing task's live SPM2 user-workspace contents. The baseline safe path copies the live 8 KiB SPM2 image to that task's protected Data RAM context backing using existing SPM copy/read-write and Data RAM transfer paths. If the OS has a documented proof that the task does not need the contents after yield, it may mark the workspace non-live and omit the copy.
5. Select the incoming task, validate its control block, address-space and memory-domain permissions, and locate its resident context slot or Data RAM backing.
6. Restore the incoming RA/FA/DA/MA state from its SPM3–SPM6 slot or Data RAM backing. Restore its SPM2 user-workspace image before allowing user execution if that image is live.
7. In parallel with steps 3–6 where the implementation's independent paths permit, invalidate/refill P0 from the incoming task's App RAM stream using its saved PC and address-space mapping. P0 is not saved as architectural task state.
8. Install the incoming task's PC/STATUS and required execution-control state. Dispatch only when register state, SPM2 workspace, permissions, and the first required P0 command(s) are ready.
9. Publish the handoff with the required release/acquire ordering. An IRQ or scheduler notification alone does not imply memory visibility.

The OS must never treat SPM2 as an extra task-context slot. SPM2 is user-owned workspace while a task executes; SPM3–SPM6 are the OS-owned resident context pool. On task migration to another core, the outgoing SPM2 image and any live SPM-owned data must be explicitly transferred through supported mechanisms or reconstructed before the task resumes. No implicit SPM coherence or migration is assumed.

## 17. Authoritative SPM role map — supersedes earlier allocation drafts

This section is the final authoritative allocation. If an earlier section in this document describes a different SPM owner, capacity pool, or slot count, Section 17 takes precedence.

| Bank | Capacity | Exclusive baseline role |
|---|---:|---|
| SPM0 | 2 KiB | CPU execution workspace |
| SPM1 | 8 KiB | OS workspace and OS-defined syscall/I/O exchange |
| SPM2 | 8 KiB | User/programmer workspace |
| SPM3 | 8 KiB | OS-managed resident task-context slots |
| SPM4 | 8 KiB | OS-managed resident task-context slots |
| SPM5 | 8 KiB | OS-managed resident task-context slots |
| SPM6 | 8 KiB | OS-managed resident task-context slots |
| SPM7 | 8 KiB | Exception-entry workspace; eight 1 KiB depth slices |
| **Total** | **58 KiB** | Per core |

### 17.1 Resident task-context capacity

Only SPM3–SPM6 are in the resident task-context pool: 4 × 8 KiB = 32 KiB. Each full register context uses a 4 KiB slot, so each bank holds two slots and the per-core resident maximum is **8 task contexts**. This is a resident fast-context limit, not a system-wide task limit. Additional task contexts stay in protected Data RAM.

SPM1 and SPM2 are never counted as task-context slots. SPM1 belongs to the OS; SPM2 belongs to the currently executing user task and its live contents must be preserved across a switch when required.

### 17.2 User workspace lifecycle

SPM2 is a single physical 8 KiB user workspace per core. At a task switch, if the outgoing task's SPM2 contents are live, the OS saves them to that task's protected Data RAM context backing before another task receives SPM2. The incoming task's saved SPM2 image is restored before user execution. The OS may omit save/restore only when the task explicitly relinquished the workspace or its ABI proves the contents dead. No implicit per-task duplicate SPM2 bank exists.

### 17.3 OS exchange area

SPM1 is reserved to privileged OS code. The OS defines the syscall exchange ABI and assigns offsets for arguments, return values, status, and bounded staging buffers used by services such as print/input. These are OS-defined conventions, not fixed hardware addresses or hardwired syscall semantics. Large or persistent payloads remain in App RAM/Data RAM and are passed by validated address or handle.

### 17.4 Canonical task-switch order

1. Enter the privileged scheduler path; SPM7 handles exception-entry temporaries and SPM1 handles OS bookkeeping.
2. Quiesce the outgoing task at an architectural boundary.
3. Save the outgoing RA/FA/DA/MA register state into its SPM3–SPM6 resident slot, or protected Data RAM if it has no resident slot. Preserve DA before using DA as a staging bank and restore DA last, as specified in Section 12.1.
4. If outgoing SPM2 contents are live, copy the full 8 KiB image to its protected Data RAM backing before SPM2 is reassigned.
5. Select and validate the incoming task's control block, privilege state, address-space mapping, and memory-domain permissions.
6. Restore incoming RA/FA/DA/MA state from its resident slot or Data RAM backing.
7. Restore incoming SPM2 workspace from protected Data RAM if live.
8. In parallel with steps 3–7 where independent paths permit, invalidate/refill P0 from the incoming task's App RAM instruction stream at its saved PC. P0 is per-core refillable prefetch state and is not saved in the task context.
9. Resume only when architectural state, SPM2 workspace, permissions, and the required first P0 instruction(s) are valid. Publish the handoff with the required release/acquire ordering.

P0 refill and context transfer may overlap, but the scheduler must wait for both dependencies; neither completion order is assumed. SPM contents never migrate between cores implicitly. A migrated task's live SPM2 data must be explicitly transferred through supported mechanisms or reconstructed before it resumes.

## 18. Task scheduler specification reference
Task READY/RUNNING/BLOCKED/SLEEPING transitions, eight-slot residency pressure, SPM2 save/restore lifecycle, wake-up race handling, priority updates, and explicit cross-core migration are specified in `NEXSUS-CPU-TASK-SCHEDULING-SPM-RESIDENCY-001.md`. That document uses the authoritative SPM allocation in Section 17 of this file and does not change the register context format.


## 19. SPM access protection reference

SPM privilege and ownership rules are specified in `NEXSUS-CPU-SPM-ACCESS-PROTECTION-001.md`. PL0 directly accesses only its currently owned SPM2 workspace. SPM1 is OS-owned; SPM3–SPM6 are accessible only to OS context-management paths. SPM7 is owned exclusively by exception hardware: software has no normal access, with only a separately authorized read-only diagnostic inspection path permitted if genuinely required. SPM0 is CPU-exclusive and cannot be addressed, read, or written by software at any privilege level. These rules do not change SPM capacities or the context frame format.


## 20. Memory protection domains reference

App RAM/Data RAM ownership, task-private ranges, protected OS context storage, explicit shared-memory grants, and Fabric-agent authorization are specified in `NEXSUS-CPU-MEMORY-PROTECTION-DOMAINS-001.md`. Context frames remain in privileged Data RAM and are never placed in user-controlled memory. Task permissions must be validated before PL0 resumes.
