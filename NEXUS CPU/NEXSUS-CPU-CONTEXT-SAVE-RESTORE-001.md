# NEXSUS CPU — Register Save/Restore and Context Frame

**Document ID:** NEXSUS-CPU-CONTEXT-SAVE-RESTORE-001  
**Status:** Architecture specification — canonical workspace/register baseline  
**Scope:** Interrupt preservation, task context save/restore, workspace preservation, and cross-core migration

## 1. Design rules

- The architectural register banks are RA0–RA31, FA0–FA31, DA0–DA31, and MA0–MA31.
- Exception Context Stack (ECS) stores protected hardware exception/return metadata.
- Exception Workspace (XW) is an 8 KiB hardware-owned resource divided into eight 1 KiB depth slices. Software cannot use XW as ordinary scratch or persistent storage.
- Kernel Exception Stack (KESP) and persistent interrupt/task context frames reside in protected Data RAM.
- Operating-System Workspace (OW) is 8 KiB and remains OS-owned.
- Task Workspace (TW) is 8 KiB and belongs to the currently executing task on that core. TW is directly byte-addressable and is not required to be a LIFO stack.
- Context Pool (CP0–CP3) is four protected 8 KiB banks. The OS context manager may use them as resident task-context storage; PL0 cannot access them.
- Execution Buffer (EB) is instruction-fetch-only and is never part of a software data/context save.
- App RAM instruction fetch and Data RAM data/context traffic remain separate paths.

## 2. Register-bank sizes and save masks

| Bank | Registers | Width each | Full bank size |
|---|---:|---:|---:|
| RA | 32 | 64-bit | 256 B |
| FA | 32 | 64-bit | 256 B |
| DA | 32 | 64-bit | 256 B |
| MA | 32 | 256-bit | 1,024 B |
| **Total** | **128 physical registers** | — | **1,792 B** |

Interrupt ABI masks are 32-bit:
- RA_MASK[31:0]
- FA_MASK[31:0]
- DA_MASK[31:0]
- MA_MASK[31:0]

Bit N indicates whether register N must be preserved. A set bit means the interrupted value must be restored before IRET. A clear bit means the handler and its complete call path must not modify that register. If static analysis cannot prove a register untouched, the compiler must preserve it.

FP status/control state and other task-visible execution state are saved separately when the handler or task can modify them.

## 3. Interrupt handler preservation contract

- RA: save only touched integer/address registers.
- FA: save touched FP registers and relevant FP status/control state.
- DA: save touched staging registers, including every DA selector used as a save/restore temporary.
- MA: save touched 256-bit registers or pairs; blanket saves are unnecessary unless all are live/modified.
- An interrupt handler calling a normal function must satisfy the interrupt ABI across the complete call graph.
- A register declared preserved cannot be used as hidden prologue scratch.

## 4. Software interrupt-frame layout

Persistent frames are stored in a privileged, bounded Data RAM region addressed by KESP/KELIMIT. Frame alignment is 32 bytes. Only registers selected by save masks occupy payload slots.

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

Each mask uses its low 32 bits; upper bits must be zero. Payload follows in ascending bank order RA, FA, DA, MA and ascending register index. RA/FA/DA entries are 8 bytes each; MA entries are 32 bytes each. Frame size is rounded up to 32 bytes.

EPC/CAUSE/IRQ claim state is not duplicated in the header; protected control metadata remains in ECS.

### 4.2 Integrity

- FRAME_MAGIC_VERSION identifies format/version.
- FRAME_SIZE must be within KELIMIT bounds and 32-byte aligned.
- PREVIOUS_FRAME_PTR must identify the prior valid frame or configured empty-frame sentinel.
- Masks and payload extents must be consistent with the 32-register banks and native register widths.
- Invalid metadata causes controlled fatal/double-fault handling; IRET never trusts arbitrary frame pointers.
- Optional checksum is platform policy, not required for the initial baseline.

## 5. Exception-entry sequence

1. CPU detects a synchronous exception or accepts an eligible IRQ at a safe instruction boundary.
2. Hardware pushes minimal control metadata into ECS.
3. Hardware selects the XW 1 KiB slice corresponding to active ECS depth.
4. On privilege transition, hardware switches to configured privileged KESP before the first handler instruction.
5. Exception hardware uses XW for bounded entry temporaries; software does not address XW.
6. Handler prologue allocates and validates a Data RAM frame, writes its header, and saves selected register payloads.
7. Before enabling nested maskable IRQs, the handler must have saved every register it has modified so far.
8. Handler body executes under the interrupt ABI.
9. Before return, handler restores selected registers, validates/releases the software frame, and performs source-specific IRQ acknowledgement/IRQEOI as required.
10. IRET validates and pops the ECS record, restores control state, and resumes execution.

XW is temporary hardware state. Persistent interrupt frames always reside in protected Data RAM.

## 6. Nested interrupts

- Each ECS depth selects its own 1 KiB XW slice.
- Each nested handler receives a distinct software frame on the privileged Data RAM exception stack.
- Outer frames remain allocated until their handlers return.
- Nested frames link through PREVIOUS_FRAME_PTR and release strictly LIFO.
- Before re-enabling nested IRQs, the handler must finish its frame header and save every register it has modified.
- Nested handlers preserve outer handler live state under the same interrupt ABI.
- Eight ECS levels are the minimum. KESP bounds must cover worst-case nesting, save masks, and call depth.

## 7. Full task context

A task context preserves all architectural state the task owns and may later observe.

Baseline full context includes:
- RA0–RA31, FA0–FA31, DA0–DA31, and MA0–MA31 (1,792-byte register payload).
- Required FP status/control and other task-visible execution state.
- PC and STATUS/privilege through the controlled scheduler context-switch path.
- Memory-domain permissions, ownership/handle state, and relevant address-space configuration.
- The task's TW ownership and, when live, the complete 8 KiB TW image.
- Task-local runtime/ABI metadata required for safe resumption.

OW is not task-owned and is not swapped with the task. EB is refillable instruction-fetch state, not architectural task data. XW is exception-hardware state and is not task-owned. CP0–CP3 may hold protected resident register-context images under OS control.

## 8. OW/TW workspace save and restore

TW is a general-purpose task-local working file. A program may use it as stack-like frames, fixed-offset records, arrays, tables, or temporary data. It is not implicitly cleared or treated as a LIFO stack.

- WLOAD.TW and WSTORE.TW provide byte-offset access to the current task's TW through DA staging.
- WLOAD.OW and WSTORE.OW are available only to authorized PL1/PL2 OS code.
- Register-bank save/restore uses explicit MOV.DA.RA / MOV.RA.DA, MOV.DA.FA / MOV.FA.DA, and MOV.DA.MA / MOV.MA.DA operations with WSTORE/WLOAD. MOV and WLOAD/WSTORE DA operands consume the shared RAC 32R+32W register-access budget; wide DA groups reserve all touched entries atomically.
- DA staging clobbers must be included in the save plan. If DA values are live, preserve them before using DA as staging and restore them last.
- XFER.WS.MEM copies a selected OW/TW byte range directly to or from an L1–L4 Data RAM domain. A full 8 KiB TW image can be persisted or restored in one transfer.
- XFER.WS.START uses the existing asynchronous token model; XFER.WAIT is the completion boundary.
- A workspace transfer does not implicitly transfer task ownership or grant access to another task/core.

## 9. CP0–CP3 resident context pool

CP0–CP3 are four protected 8 KiB banks. Each bank may be divided into four 2 KiB context slots, giving sixteen resident slots per core.

A complete register payload is 1,792 bytes. The remaining space in a 2 KiB slot holds slot metadata, validity/generation state, and aligned context fields. The exact slot header layout is OS ABI data and must not be confused with the interrupt-frame header.

- PL0 cannot access CP0–CP3.
- PL1 scheduler/context-manager paths allocate, validate, save, restore, and evict slots.
- A slot is not visible as valid until the complete context image and metadata are committed.
- Slot identity includes task ID and generation; stale slot references cannot name a newly allocated task context.
- If no resident slot is available, or a task migrates, its context is persisted in protected Data RAM.

## 10. Task-switch sequence

1. Stop dispatch to the outgoing task and reach the architectural context-switch boundary.
2. Preserve outgoing architectural register state in an assigned CP slot or protected Data RAM frame.
3. If the outgoing TW image is live, use XFER.WS.MEM or XFER.WS.START/XFER.WAIT to persist its complete 8 KiB image to the task's protected Data RAM backing.
4. Validate the incoming task's identity, generation, memory permissions, shared grants, context image, and TW backing.
5. Restore incoming register state from CP or Data RAM.
6. Restore the incoming task's TW image into the local TW using the reverse workspace transfer.
7. Establish the incoming task as the TW owner and activate its memory permission state.
8. Refill instruction code through the App RAM → C0 → CS0–CS7 → CST → EB path.
9. Resume PL0 only after register state, TW contents, and ownership/permission state are valid.

If the outgoing task has explicitly released TW or the compiler/runtime proves its contents dead, the scheduler may omit the TW image save. It must not infer that TW is disposable merely because the task is descheduled.

## 11. Cross-core migration

TW is core-local; its physical contents do not follow a task automatically.

- Before migration, persist the live TW image to protected Data RAM.
- Transfer the task's register/context image and permission/ownership metadata through protected Data RAM/Fabric paths.
- On the destination core, restore the register context and TW image before returning to PL0.
- The destination core establishes a new local TW ownership generation. Old-core workspace addresses do not authorize access to the destination TW.
- CP residency is core-local; a task migrating to another core cannot retain a physical CP slot from the source core.

## 12. Save/restore ordering when DA is the staging bank

DA is the staging bank for memory LOAD/STORE and explicit bank transfers. The handler must not overwrite interrupted DA values before preserving them.

**Save order**
1. Save every DA register selected by DA_MASK to the Data RAM frame while original DA values are intact.
2. Save selected RA registers: MOV.DA.RA to DA staging, then STORE to Data RAM.
3. Save selected FA registers: MOV.DA.FA to DA staging, then STORE to Data RAM.
4. Save selected MA registers/groups: MOV.DA.MA to DA staging, then STORE the 256/512-bit group to Data RAM.

**Restore order**
1. Restore MA payloads: LOAD to DA staging, then MOV.MA.DA.
2. Restore FA payloads: LOAD to DA staging, then MOV.FA.DA.
3. Restore RA payloads: LOAD to DA staging, then MOV.RA.DA.
4. Restore DA payloads last, so no later staging operation overwrites restored DA values.

This ordering applies to protected Data RAM save frames. OW/TW save sequences use the same DA-clobber rule with WSTORE/WLOAD at the workspace edge.

## 13. Frame capacity and overflow

The complete architectural register payload is 1,792 bytes. A selective interrupt frame is smaller according to its masks, plus the 64-byte header and alignment. KESP/KELIMIT must cover worst-case nesting and call depth.

If the Data RAM frame stack reaches KELIMIT, the CPU enters the defined double-fault path. It must never silently truncate a save frame or overwrite another ECS depth's XW slice.

## 14. ABI and compiler requirements

Compiler/assembler support:
- Interrupt-handler attribute and a distinct interrupt ABI.
- Static or conservative transitive register-clobber analysis.
- Emission of four 32-bit per-bank save masks.
- Native-width save/restore of selected registers.
- 32-byte frame alignment and bounds checks.
- Nested-handler prologue/epilogue generation.
- Full-context save/restore for scheduler code.
- DA staging clobber tracking for every register-bank transfer.
- TW liveness tracking so the scheduler can omit a TW save only when contents are proven dead or explicitly released.

If the compiler cannot prove a register untouched, it must preserve it. Correctness takes priority over frame-size optimization.

## 15. Baseline decisions and open items

**Selected**
- 32 registers per bank: RA/FA/DA 32×64-bit; MA 32×256-bit.
- Full register payload: 1,792 bytes.
- Four 32-bit interrupt save masks.
- XW hardware-only for depth-selected exception entry.
- KESP and persistent exception/task frames in protected Data RAM.
- OW and TW each 8 KiB, directly byte-addressable.
- WLOAD/WSTORE for DA-staged workspace access.
- XFER.WS.MEM / XFER.WS.START for workspace↔Data RAM block transfer.
- CP0–CP3 as OS-protected resident context pool.

**Open**
- Exact KESP/KELIMIT CSR semantics and stack direction.
- Exact interrupt-frame flag inventory and optional checksum.
- CP slot header/metadata layout.
- Workspace bank count, ports, arbitration, and latency.
- Scheduler policy for eager versus liveness-based TW persistence.
- Precise exception/fault behavior for interrupted asynchronous workspace transfers.
