# NEXSUS CPU — SPM Access Protection
**Document ID:** NEXSUS-CPU-SPM-ACCESS-PROTECTION-001  
**Status:** Architecture specification — policy baseline  
**Scope:** Software privilege, ownership, and access boundaries for SPM0–SPM7

## 1. Design principle

SPM access is governed by both privilege and ownership. A higher privilege level does not automatically grant unrestricted access to every SPM bank. The active task receives only its assigned user workspace; OS and exception workspaces remain protected.

The SPM role map and capacities are unchanged:
- SPM0: 2 KiB CPU execution workspace.
- SPM1: 8 KiB OS workspace and OS-defined syscall/I/O exchange area.
- SPM2: 8 KiB active user-task workspace.
- SPM3–SPM6: 8 KiB each, OS-managed task-context pool.
- SPM7: 8 KiB exception workspace, divided into eight 1 KiB depth-selected slices.

## 2. Access policy

| SPM | PL0 User | PL1 Supervisor | PL2 Machine | Access rule |
|---|---|---|---|---|
| SPM0 | Denied | Denied | Denied | CPU hardware only; no software-visible read, write, or address access at any privilege level |
| SPM1 | Denied | Allowed | Allowed | OS-owned; syscall and I/O exchange data is mediated by the OS |
| SPM2 | Allowed to current task only | Allowed for controlled save/restore and management | Allowed for controlled management | Ownership follows the currently executing task on that core |
| SPM3–SPM6 | Denied | OS context-manager only | Controlled maintenance/debug only | No ordinary task or general-purpose user access |
| SPM7 | Denied | Denied by default; exceptional diagnostic read-only access only when explicitly authorized | Denied to ordinary software; hardware exception machinery owns it | Exception-only; software writes are never permitted |

PL2 is not an unrestricted bypass. No software privilege level can read or write SPM0. SPM7 is hardware-owned: ordinary OS and machine software do not access it. If a specific diagnostic/recovery operation genuinely requires inspection, a separately authorized path may expose only read-only data; it must never permit software writes or interfere with a live exception.

## 3. SPM1 — OS workspace

1. SPM1 is reserved for OS execution and OS-defined syscall/I/O exchange.
2. PL0 cannot address SPM1 directly, even while making a syscall.
3. On a syscall transition, the OS may read validated arguments from the agreed exchange interface and write results/status for return to the caller.
4. The syscall ABI defines offsets and data formats; hardware does not assign fixed meanings to SPM1 offsets.
5. Large or long-lived payloads remain in validated Data RAM buffers or handles; SPM1 is bounded staging/workspace, not a general user buffer.
6. OS access to SPM1 is permitted in PL1 and PL2.

## 4. SPM2 — active user workspace

1. SPM2 is the only SPM bank directly accessible to PL0.
2. Access is limited to the task currently executing on that core. A task cannot address another task's SPM2 image.
3. During a task switch, if the outgoing task's SPM2 contents are live, the OS saves the 8 KiB image to that task's protected Data RAM context backing before assigning SPM2 to another task.
4. The incoming task's saved image is restored before PL0 execution resumes.
5. If the task/runtime explicitly releases SPM2 or proves its contents dead, the OS may omit the save.
6. Cross-core migration uses an explicit save to Data RAM and restore into the destination core's local SPM2. No implicit cross-core SPM coherence is assumed.

## 5. SPM3–SPM6 — protected task-context pool

1. These banks contain OS-managed resident register-context slots; they are not user scratch memory.
2. PL0 access is always denied.
3. PL1 access is restricted to scheduler/context-manager paths that allocate, validate, save, restore, or evict a slot.
4. Ordinary application code and unrelated OS subsystems must not read or modify these slots.
5. Slot ownership is validated using the existing task ID and generation metadata. A slot is not exposed until its complete context write is valid.
6. Eviction follows the task-context rules: persist the full context to protected Data RAM and verify it before reusing the slot.

## 6. SPM7 — exception-hardware-only workspace

1. SPM7 is reserved exclusively for exception/IRQ entry and handler prologue/epilogue work performed by the CPU's exception machinery.
2. Hardware selects the 1 KiB slice corresponding to the active ECS depth before the first handler instruction.
3. No PL0, PL1, or PL2 software has normal direct read or write access to SPM7. The OS and exception handlers must not use SPM7 as their own workspace.
4. If a specific diagnostic or recovery procedure genuinely needs to inspect SPM7 contents, the architecture may provide an explicitly authorized read-only inspection path. This is exceptional, not a general OS permission; it must not expose write access, permit slice selection that bypasses hardware ownership, or disturb a live exception.
5. SPM7 contents are temporary. Persistent exception frames remain in protected Data RAM; IRET releases the slice and its contents become unspecified.

## 7. SPM0 — CPU-exclusive execution workspace

SPM0 belongs exclusively to the CPU's internal execution machinery. No software at PL0, PL1, or PL2 may address, read, or write it. This is an absolute boundary, not merely a privilege restriction. Only CPU hardware may perform SPM0 operations.

## 8. Fault behavior and enforcement requirements

- An access violating privilege, task ownership, bank role, or active SPM7 slice boundaries raises a precise protection exception.
- The fault reports the SPM bank and access operation through the existing exception cause/information path; BADADDR/EXCINFO validity follows the CSR exception rules.
- A protection fault must not partially modify the denied bank.
- Permission and ownership checks apply to CPU-originated SPM accesses and any future agent path that can address SPM.
- No Node, peripheral, DMA, or Fabric agent receives implicit SPM access. Any future such access requires an explicit, separately specified grant.
- Task switch must establish incoming SPM2 ownership and the relevant protected-context access state before returning to PL0.
- The exact enforcement circuitry and encoding of SPM protection controls remain implementation work; this policy does not assume a particular MMU, TLB, or new instruction.

## 9. Invariants

1. PL0 directly accesses SPM2 only, and only while it owns the running task on that core.
2. SPM1 is OS-owned and never directly user-accessible.
3. SPM3–SPM6 are protected context storage, not general-purpose scratch.
4. SPM7 is exception-hardware-only and depth-bounded; software access is denied except for a separately authorized read-only diagnostic inspection path.
5. SPM0 is CPU-exclusive; all software read/write/address access is denied at every privilege level.
6. Higher privilege does not silently erase ownership or lifetime rules.
7. Existing SPM capacities, register banks, transfer instructions, and task-context format are unchanged.

## 10. Related specifications

- NEXSUS-CPU-CONTEXT-SAVE-RESTORE-001.md
- NEXSUS-CPU-TASK-SCHEDULING-SPM-RESIDENCY-001.md
- NEXSUS-CPU-EXCEPTION-FRAME-001.md
- NEXSUS-CPU-CSR-001.md
