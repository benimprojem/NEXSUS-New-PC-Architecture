# NEXSUS CPU — Workspace Access Protection
**Document ID:** NEXSUS-CPU-SPM-ACCESS-PROTECTION-001  
**Status:** Architecture specification — policy baseline  
**Scope:** Software privilege, ownership, and access boundaries for EB, OSSpace, WS, CP0–CP3 and XW

## 1. Design principle

Workspace access is governed by privilege, role, and access epoch. A higher privilege level does not automatically grant unrestricted access to every workspace. PL0 application code may use the core-local WS during an authorized application execution epoch; OSSpace and exception workspaces remain protected.

The workspace role map and capacities are unchanged:
- EB: 4 KiB dual-bank CPU instruction workspace (2 × 2 KiB).
- OSSpace: 8 KiB OS workspace and OS-defined syscall/I/O exchange area.
- WS: 8 KiB general-purpose application workspace; not task-ID-owned.
- CP0–CP3: 8 KiB each, OS-managed task-context pool.
- XW: 8 KiB exception workspace, divided into eight 1 KiB depth-selected slices.

## 2. Access policy

| workspace | PL0 User | PL1 Supervisor | PL2 Machine | Access rule |
|---|---|---|---|---|
| EB | Denied | Denied | Denied | CPU hardware only; no software-visible read, write, or address access at any privilege level |
| OSSpace | Denied | Allowed | Allowed | OS-owned; syscall and I/O exchange data is mediated by the OS |
| WS | Allowed during authorized application execution | Allowed for controlled management/initialization/persistence | Allowed for controlled management | Per-core application workspace; access epoch is controlled by the OS, not a task ID |
| CP0–CP3 | Denied | OS context-manager only | Controlled maintenance/debug only | No ordinary task or general-purpose user access |
| XW | Denied | Denied by default; exceptional diagnostic read-only access only when explicitly authorized | Denied to ordinary software; hardware exception machinery owns it | Exception-only; software writes are never permitted |

PL2 is not an unrestricted bypass. No software privilege level can read or write EB. XW is hardware-owned: ordinary OS and machine software do not access it. If a specific diagnostic/recovery operation genuinely requires inspection, a separately authorized path may expose only read-only data; it must never permit software writes or interfere with a live exception.

## 3. OSSpace — OS workspace

OSSpace is directly byte-addressable by authorized PL1/PL2 code through WLOAD.OSSpace/WSTORE.OSSpace; PL0 remains denied. The workspace access mechanism does not weaken the syscall mediation boundary.

1. OSSpace is reserved for OS execution and OS-defined syscall/I/O exchange.
2. PL0 cannot address OSSpace directly, even while making a syscall.
3. On a syscall transition, the OS may read validated arguments from the agreed exchange interface and write results/status for return to the caller.
4. The syscall ABI defines offsets and data formats; hardware does not assign fixed meanings to OSSpace offsets.
5. Large or long-lived payloads remain in validated Data RAM buffers or handles; OSSpace is bounded staging/workspace, not a general user buffer.
6. OS access to OSSpace is permitted in PL1 and PL2.

## 3.1 OSSpace/WS direct addressing and data movement

OSSpace and WS are each 8 KiB, core-local, byte-addressable workspaces. Their offset range is 0–8191. They are not register banks, but CPU-originated WLOAD/WSTORE operations participate in the same core-wide RAC budget as RA/FA/DA/MA: 32 logical 64-bit reads and 32 logical 64-bit writes per cycle in total. Wide WLOAD/WSTORE operations reserve their complete workspace and DA footprints atomically. XFER.WS.MEM/START use the separate transfer engine and do not consume these logical slots.

- Both workspaces support byte offsets and direct offset or RA-base-plus-byte-displacement addressing.
- WLOAD reads from the selected workspace into DA staging registers; WSTORE writes DA staging registers to the selected workspace. Supported widths are 8/16/32/64/128/256/512 bits, subject to natural alignment, DA range, and the 8 KiB workspace boundary.
- Register-bank save/restore uses the already-defined explicit transfer instructions: MOV.DA.RA / MOV.RA.DA, MOV.DA.FA / MOV.FA.DA, and MOV.DA.MA / MOV.MA.DA, with WSTORE/WLOAD as the workspace edge. No implicit register-bank alias is created.
- XFER.WS.MEM and XFER.WS.START transfer a selected byte range only from OSSpace/WS to an L1–L4 Data RAM domain. The transfer engine exports the workspace contents directly and does not consume DA staging entries or RAC register-access slots. Data RAM, App RAM, DMA, Fabric, peripherals, and other cores cannot use this path to write a workspace.
- During a workspace→Data RAM transfer, the source range is read-reserved. Workspace is never a transfer destination. Data RAM target ranges follow the existing transfer reservation and unpublished-destination rules.
- The full 8 KiB workspace may be transferred as one block. Partial transfers are permitted only when the complete source and destination ranges fit their respective bounds.
- Every CPU workspace access validates privilege, active application-access epoch, range, alignment, and mapping before acceptance. Export validates workspace read authority and Data RAM destination grant. Validation faults cause no partial architectural update or write. Runtime multi-beat transfer failure may leave physical destination bytes changed, but the destination range remains logically invalid/unpublished until fully overwritten successfully.
- The instruction mnemonics, opcodes, and WSMEM fields are assigned in NEXSUS-CPU-INSTRUCTION-ENCODING-001.md. Physical bank/port implementation remains open.

## 3.2 OS/application exchange window (paired shadow ranges)

An OS/application exchange window may be reserved as a bounded pair of ranges: one in OSSpace and one in WS. They are copies, not a shared physical alias, and are never writable by an external memory agent. On syscall entry, the CPU/OS copies the application's designated WS request range into OSSpace using controlled WLOAD.WS→DA→WSTORE.OSSPACE operations. Before returning to PL0, the OS prepares a response in OSSpace and the CPU/OS copies it into the designated WS response range using WLOAD.OSSPACE→DA→WSTORE.WS. The copy is performed by privileged CPU instructions under the context-management permission path, not by DMA or XFER.WS.MEM. The exact size, offsets, alignment, and ABI schema are OS policy and remain configurable; the initial architecture does not reserve a fixed number of bytes.

This gives the application a predictable request/response shadow area while OSSpace remains OS-private and WS remains a general-purpose application workspace. Outside the controlled handoff, PL0 cannot access OSSpace and OS subsystems cannot arbitrarily mutate WS.

## 4. WS — application workspace

WS is directly byte-addressable by PL0 application code through WLOAD.WS/WSTORE.WS during an authorized application execution epoch. It is general-purpose application working storage, not a mandatory LIFO stack; software may organize it as stack-like frames, fixed-offset records, tables, arrays, or scratch buffers. WS is not owned by a task ID and is not automatically part of task context.

1. WS is the only general-purpose workspace directly accessible to PL0.
2. Access is controlled by the active application-access epoch, not by a task ID or task-indexed workspace image.
3. A task switch does not automatically save or restore WS.
4. Before WS is granted to a different protection domain, the OS revokes the prior access epoch and clears or fully initializes the 8 KiB area, unless an explicitly authorized continuation preserves the same data domain.
5. If an application needs WS contents to survive a protection-domain change or core migration, it explicitly exports the required range to protected Data RAM. Restore is CPU-mediated through Data RAM LOAD→DA→WSTORE.
6. No implicit cross-core workspace coherence or migration is assumed.

## 5. CP0–CP3 — protected task-context pool

1. These banks contain OS-managed resident register-context slots; they are not user scratch memory.
2. PL0 access is always denied.
3. PL1 access is restricted to scheduler/context-manager paths that allocate, validate, save, restore, or evict a slot.
4. Ordinary application code and unrelated OS subsystems must not read or modify these slots.
5. Slot ownership is validated using the existing task ID and generation metadata. A slot is not exposed until its complete context write is valid.
6. Eviction follows the task-context rules: persist the full context to protected Data RAM and verify it before reusing the slot.

## 6. XW — exception-hardware-only workspace

1. XW is reserved exclusively for exception/IRQ entry and handler prologue/epilogue work performed by the CPU's exception machinery.
2. Hardware selects the 1 KiB slice corresponding to the active ECS depth before the first handler instruction.
3. No PL0, PL1, or PL2 software has normal direct read or write access to XW. The OS and exception handlers must not use XW as their own workspace.
4. If a specific diagnostic or recovery procedure genuinely needs to inspect XW contents, the architecture may provide an explicitly authorized read-only inspection path. This is exceptional, not a general OS permission; it must not expose write access, permit slice selection that bypasses hardware ownership, or disturb a live exception.
5. XW contents are temporary. Persistent exception frames remain in protected Data RAM; IRET releases the slice and its contents become unspecified.

## 7. EB — CPU-exclusive execution workspace

EB belongs exclusively to the CPU's internal execution machinery. No software at PL0, PL1, or PL2 may address, read, or write it. This is an absolute boundary, not merely a privilege restriction. Only CPU hardware may perform EB operations.

## 8. Fault behavior and enforcement requirements

- An access violating privilege, application access-epoch violation, bank role, or active XW slice boundaries raises a precise protection exception.
- The fault reports the workspace and access operation through the existing exception cause/information path; BADADDR/EXCINFO validity follows the CSR exception rules.
- A protection fault must not partially modify the denied bank.
- Permission and access-epoch checks apply to CPU-originated workspace accesses and any future agent path that can address workspace.
- No Node, peripheral, DMA, Data RAM controller, App RAM controller, or Fabric agent receives workspace write access. The one-way workspace export engine may read OSSpace/WS but cannot write them. Any future exception to this invariant requires a separate architecture decision and explicit capability.
- Every protection-domain switch must revoke the previous WS access epoch and clear or fully initialize WS before granting it to a different application domain, unless an explicitly authorized continuation preserves the same data domain.
- The exact enforcement circuitry and encoding of workspace protection controls remain implementation work; this policy does not assume a particular MMU, TLB, or new instruction.

## 9. Invariants

1. PL0 directly accesses WS only during an authorized application execution epoch; WS is not task-ID-owned.
2. OSSpace is OS-owned and never directly user-accessible.
3. CP0–CP3 are protected context storage, not general-purpose scratch.
4. XW is exception-hardware-only and depth-bounded; software access is denied except for a separately authorized read-only diagnostic inspection path.
5. EB is CPU-exclusive; all software read/write/address access is denied at every privilege level.
6. Higher privilege does not silently erase ownership or lifetime rules.
7. Existing workspace capacities, register banks, transfer instructions, and task-context format are unchanged.

## 10. Related specifications

- NEXSUS-CPU-WORKSPACE-ADDRESSING-AND-TRANSFER-001.md
- NEXSUS-CPU-WORKSPACE-BANK-TOPOLOGY-001.md

- NEXSUS-CPU-CONTEXT-SAVE-RESTORE-001.md
- NEXSUS-CPU-TASK-SCHEDULING-SPM-RESIDENCY-001.md
- NEXSUS-CPU-EXCEPTION-FRAME-001.md
- NEXSUS-CPU-CSR-001.md
