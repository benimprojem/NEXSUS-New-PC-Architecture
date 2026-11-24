# NEXSUS CPU — Workspace Access Protection
**Document ID:** NEXSUS-CPU-SPM-ACCESS-PROTECTION-001  
**Status:** Architecture specification — policy baseline  
**Scope:** Software privilege, ownership, and access boundaries for EB, OW, TW, CP0–CP3 and XW

## 1. Design principle

Workspace access is governed by both privilege and ownership. A higher privilege level does not automatically grant unrestricted access to every workspace. The active task receives only its assigned user workspace; OS and exception workspaces remain protected.

The workspace role map and capacities are unchanged:
- EB: 4 KiB dual-bank CPU instruction workspace (2 × 2 KiB).
- OW: 8 KiB OS workspace and OS-defined syscall/I/O exchange area.
- TW: 8 KiB active user-task workspace.
- CP0–CP3: 8 KiB each, OS-managed task-context pool.
- XW: 8 KiB exception workspace, divided into eight 1 KiB depth-selected slices.

## 2. Access policy

| workspace | PL0 User | PL1 Supervisor | PL2 Machine | Access rule |
|---|---|---|---|---|
| EB | Denied | Denied | Denied | CPU hardware only; no software-visible read, write, or address access at any privilege level |
| OW | Denied | Allowed | Allowed | OS-owned; syscall and I/O exchange data is mediated by the OS |
| TW | Allowed to current task only | Allowed for controlled save/restore and management | Allowed for controlled management | Ownership follows the currently executing task on that core |
| CP0–CP3 | Denied | OS context-manager only | Controlled maintenance/debug only | No ordinary task or general-purpose user access |
| XW | Denied | Denied by default; exceptional diagnostic read-only access only when explicitly authorized | Denied to ordinary software; hardware exception machinery owns it | Exception-only; software writes are never permitted |

PL2 is not an unrestricted bypass. No software privilege level can read or write EB. XW is hardware-owned: ordinary OS and machine software do not access it. If a specific diagnostic/recovery operation genuinely requires inspection, a separately authorized path may expose only read-only data; it must never permit software writes or interfere with a live exception.

## 3. OW — OS workspace

OW is directly byte-addressable by authorized PL1/PL2 code through WLOAD.OW/WSTORE.OW; PL0 remains denied. The workspace access mechanism does not weaken the syscall mediation boundary.

1. OW is reserved for OS execution and OS-defined syscall/I/O exchange.
2. PL0 cannot address OW directly, even while making a syscall.
3. On a syscall transition, the OS may read validated arguments from the agreed exchange interface and write results/status for return to the caller.
4. The syscall ABI defines offsets and data formats; hardware does not assign fixed meanings to OW offsets.
5. Large or long-lived payloads remain in validated Data RAM buffers or handles; OW is bounded staging/workspace, not a general user buffer.
6. OS access to OW is permitted in PL1 and PL2.

## 3.1 OW/TW direct addressing and data movement

OW and TW are each 8 KiB, core-local, byte-addressable workspaces. Their offset range is 0–8191. They are not register banks and do not consume the shared RAC 32R+32W register-access budget.

- Both workspaces support byte offsets and direct offset or RA-base-plus-byte-displacement addressing.
- WLOAD reads from the selected workspace into DA staging registers; WSTORE writes DA staging registers to the selected workspace. Supported widths are 8/16/32/64/128/256/512 bits, subject to natural alignment, DA range, and the 8 KiB workspace boundary.
- Register-bank save/restore uses the already-defined explicit transfer instructions: MOV.DA.RA / MOV.RA.DA, MOV.DA.FA / MOV.FA.DA, and MOV.DA.MA / MOV.MA.DA, with WSTORE/WLOAD as the workspace edge. No implicit register-bank alias is created.
- XFER.WS.MEM and XFER.WS.START transfer a selected byte range only from OW/TW to an L1–L4 Data RAM domain. The transfer engine exports the workspace contents directly and does not consume DA staging entries or RAC register-access slots. Data RAM, App RAM, DMA, Fabric, peripherals, and other cores cannot use this path to write a workspace.
- During a workspace→Data RAM transfer, the source range is read-reserved. Workspace is never a transfer destination. Data RAM target ranges follow the existing transfer reservation and unpublished-destination rules.
- The full 8 KiB workspace may be transferred as one block. Partial transfers are permitted only when the complete source and destination ranges fit their respective bounds.
- Every CPU workspace access validates privilege, active task ownership, range, alignment, and mapping before acceptance. Export validates workspace read authority and Data RAM destination grant. Validation faults cause no partial architectural update or write. Runtime multi-beat transfer failure may leave physical destination bytes changed, but the destination range remains logically invalid/unpublished until fully overwritten successfully.
- The instruction mnemonics and architectural behavior are specified in ISA §5.6. Numeric opcode allocation and exact WS-MEM encoding remain open; no existing opcode assignment is changed by this policy section.

## 3.2 OS/task exchange window (paired shadow ranges)

An OS/task exchange window may be reserved as a bounded pair of ranges: one in OW and one in TW. They are not a shared physical alias and are never writable by an external memory agent. On syscall entry, the CPU/OS copies the task's designated TW request range into OW using controlled WLOAD.TW→DA→WSTORE.OW operations. Before returning to PL0, the OS prepares a response in OW and the CPU/OS copies it into the designated TW response range using WLOAD.OW→DA→WSTORE.TW. The copy is performed by privileged CPU instructions under the context-management permission path, not by DMA or XFER.WS.MEM. The exact size, offsets, alignment, and ABI schema are OS policy and remain configurable; the initial architecture does not reserve a fixed number of bytes.

This gives the application a predictable request/response shadow area while OW remains OS-private and TW remains task-owned. Outside the controlled handoff, PL0 cannot access OW and OS subsystems cannot arbitrarily mutate the task's TW.

## 4. TW — active user workspace

TW is directly byte-addressable by its current PL0 owner through WLOAD.TW/WSTORE.TW. It is general-purpose task-local storage, not a mandatory LIFO stack; software may organize it as stack-like frames, fixed-offset records, tables, or scratch buffers.

1. TW is the only workspace directly accessible to PL0.
2. Access is limited to the task currently executing on that core. A task cannot address another task's TW image.
3. During a task switch, if the outgoing task's TW contents are live, the OS saves the 8 KiB image to that task's protected Data RAM context backing before assigning TW to another task.
4. The incoming task's saved image is restored before PL0 execution resumes.
5. If the task/runtime explicitly releases TW or proves its contents dead, the OS may omit the save.
6. Cross-core migration uses an explicit save to Data RAM and restore into the destination core's local TW. No implicit cross-core workspace coherence is assumed.

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

- An access violating privilege, task ownership, bank role, or active XW slice boundaries raises a precise protection exception.
- The fault reports the workspace and access operation through the existing exception cause/information path; BADADDR/EXCINFO validity follows the CSR exception rules.
- A protection fault must not partially modify the denied bank.
- Permission and ownership checks apply to CPU-originated Workspace accesses and any future agent path that can address workspace.
- No Node, peripheral, DMA, Data RAM controller, App RAM controller, or Fabric agent receives workspace write access. The one-way workspace export engine may read OW/TW but cannot write them. Any future exception to this invariant requires a separate architecture decision and explicit capability.
- Task switch must establish incoming TW ownership and the relevant protected-context access state before returning to PL0.
- The exact enforcement circuitry and encoding of workspace protection controls remain implementation work; this policy does not assume a particular MMU, TLB, or new instruction.

## 9. Invariants

1. PL0 directly accesses TW only, and only while it owns the running task on that core.
2. OW is OS-owned and never directly user-accessible.
3. CP0–CP3 are protected context storage, not general-purpose scratch.
4. XW is exception-hardware-only and depth-bounded; software access is denied except for a separately authorized read-only diagnostic inspection path.
5. EB is CPU-exclusive; all software read/write/address access is denied at every privilege level.
6. Higher privilege does not silently erase ownership or lifetime rules.
7. Existing workspace capacities, register banks, transfer instructions, and task-context format are unchanged.

## 10. Related specifications

- NEXSUS-CPU-WORKSPACE-ADDRESSING-AND-TRANSFER-001.md

- NEXSUS-CPU-CONTEXT-SAVE-RESTORE-001.md
- NEXSUS-CPU-TASK-SCHEDULING-SPM-RESIDENCY-001.md
- NEXSUS-CPU-EXCEPTION-FRAME-001.md
- NEXSUS-CPU-CSR-001.md
