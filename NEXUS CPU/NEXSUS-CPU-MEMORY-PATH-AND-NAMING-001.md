# NEXSUS CPU — Memory Path and Expanded Naming Reference

**Document ID:** NEXSUS-CPU-MEMORY-PATH-AND-NAMING-001  
**Status:** Working architecture reference — naming crosswalk; unresolved aliases are explicitly marked  
**Date:** 2026-11-16

## 1. Mandatory naming rule

Never introduce or use a short symbol by itself in explanatory prose. On first use, write the expanded name followed by the symbol, then state its role. Tables and diagrams must retain the expanded name beside the symbol.

Example: **Level-0 Instruction Cache (L0)** — first-level staging for executable application code.

Do not silently rename, merge, or reinterpret an existing resource. Historical symbols remain searchable, but must be labelled as legacy or alternate terminology where appropriate.

## 2. Canonical logical application-instruction path

The agreed logical order is:

```text
Application RAM (App RAM)
    → Level-0 Instruction Cache (L0)
    → Page eXecution pool (PX): P0–P7
    → Dual-bank Ping-Pong preparation
    → Execution Page (active bank)
    → Instruction Fetch / Decode / Execute
```

| Order | Expanded name | Symbol / label | Defined role |
|---:|---|---|---|
| 1 | Application RAM | App RAM | Backing source for application instruction bytes; separate from Data RAM and served by its own controller/path |
| 2 | Level-0 Instruction Cache | L0 | First code staging/cache layer between App RAM and the page pool; current capacity recorded elsewhere as 64 KiB |
| 3 | Page eXecution pool | PX, pages P0–P7 | Eight equal, dynamically allocated executable-code slots; each 2 KiB, 16 KiB total per core |
| 4 | Dual-bank Ping-Pong preparation | Ping-Pong A/B | Two-bank handoff mechanism; one bank can supply the current execution page while the other is prepared |
| 5 | Execution Page | Active execution bank | The 2 KiB bank currently supplying the instruction-fetch stream to the CPU |

**Important size distinction:** the existing PX manager specification defines the ping-pong execution workspace as 4 KiB total, made of two 2 KiB banks. Therefore, “Execution Page” means one 2 KiB active bank; “Ping-Pong workspace” means both banks together (4 KiB). These are not two additional storage layers.

## 3. PX page-pool rules

- P0–P7 are eight equal physical slots; no slot is permanently the active slot.
- Each slot is 2 KiB; aggregate capacity is 16 KiB per core.
- Slots contain executable code, not task data or register-context images.
- The task's logical code-page mapping and PC identify the next instruction; physical slot number is not a task-visible code address.
- A slot becomes usable only after its content, owner, generation, permissions, mapping, and valid-byte range are committed.
- Code-page residency and register-context residency are independent.

## 4. Ping-Pong and Execution Page terminology

The PX manager specification already defines the downstream execution workspace as two independently managed 2 KiB banks:

| Expanded name | Label | Capacity | Meaning |
|---|---|---:|---|
| Ping-Pong bank A | Bank A | 2 KiB | One execution-workspace bank |
| Ping-Pong bank B | Bank B | 2 KiB | The other execution-workspace bank |
| Execution Page | Active bank A or B | 2 KiB | The bank currently selected for instruction fetch |
| Dual-bank execution workspace | Existing SPM0 / alternate name EB | 4 KiB total | Both banks plus bank-selection/refill behavior |

At a legal instruction boundary, the selector may switch to the other bank only when that bank is fully READY and its task identity, generation, logical page, permissions, and valid-byte range are valid. The consumed bank may then be refilled. A bank must never be overwritten while fetch still references it.

## 5. Other memory/workspace areas — kept separate from the code path

These are separate logical domains. This table does **not** claim that each is a separate physical RAM chip or independent controller.

| Expanded name | Existing short symbol | Purpose / ownership | Current placement understanding |
|---|---|---|---|
| Operating-System Workspace | OW (older label: SPM1) | Privileged OS/kernel scratch and control data | Dedicated protected workspace concept; physical implementation detail remains open |
| Task Workspace | TW (older label: SPM2) | Current task's private scratch/work data | Task-owned workspace; protected by task/privilege rules |
| Context Pool | CTP (older labels: SPM3–SPM6) | Saved architectural register/context images | Four 8 KiB banks; protected context residency, with spill to protected Data RAM when needed |
| Exception Workspace | XW (older label: SPM7) | Exception/interrupt temporary workspace | 8 KiB, eight 1 KiB slices; retain existing exception ownership/protection rules |
| Kernel Exception Stack | KESP | Privileged exception software stack | Protected Data RAM |
| Exception Context Stack | ECS | Per-core protected hardware exception-context records; minimum eight entries | CPU-local protected exception mechanism; do not merge with error logs |
| Error Log Area | Error Log | Persistent diagnostic/error records | Placement and capacity not yet frozen; distinct from ECS/XW |
| Task Area | Task Area | Task state, scheduling metadata, lifecycle records | Logical OS-managed domain; exact physical subdivision not yet frozen |
| General Data Memory | Data RAM | Mutable program data, task data, shared data, protected OS backing | Separate memory system/controller/path from App RAM |

## 6. Existing exception decisions — preserve, do not redesign here

- Exception Context Stack (ECS): per-core protected hardware context records, minimum eight entries.
- Exception Workspace (XW; legacy SPM7): 8 KiB split into eight 1 KiB slices.
- Kernel Exception Stack (KESP): privileged software stack in protected Data RAM.
- Emergency double-fault record: separate per-core protected record.
- Error Log Area is diagnostic history, not exception-entry scratch or the live exception context.

## 7. Naming crosswalk and unresolved repository conflict

The repository contains an earlier canonical naming decision that introduced:
- CodeFlow Manager (CFM) as an alternate/new name for the PX Manager;
- Code Slots (CS0–CS7) as alternate names for PX pages P0–P7;
- Code Cache (C0) as an alternate name for L0I;
- Execution Buffer (EB) as an alternate name for SPM0;
- Code Stream Transfer (CST) for the transfer into the inactive execution bank.

Those names are retained here as **documented alternate terminology**, not silently substituted into the agreed path above. The current architecture conversation uses **L0 → PX P0–P7 → Ping-Pong → Execution Page**. A final global rename must be made only after the owner explicitly freezes one naming set. Until then, every new explanatory document must show both the expanded term and the chosen symbol, and must identify CFM/CS/C0/EB as alternate names when they appear.

| Current path term | Existing alternate repository term | Status |
|---|---|---|
| Level-0 Instruction Cache (L0) | Code Cache (C0); older L0I | Alternate terminology; canonical symbol needs final freeze |
| Page eXecution pool (PX), P0–P7 | Code Slots (CS0–CS7) | Alternate terminology; do not mix symbols in one diagram |
| Dual-bank Ping-Pong workspace | Execution Buffer (EB); older SPM0 | Same documented 4 KiB dual-bank resource; naming alias needs final freeze |
| Execution Page (one active 2 KiB bank) | EB active bank | Descriptive sub-resource, not a separate 4 KiB buffer |

## 8. Open items before physical memory-map freeze

1. Freeze whether the canonical code-path symbols remain L0/PX/P0–P7 or change globally to C0/CS0–CS7.
2. Freeze whether the dual-bank resource is named Ping-Pong Execution Workspace, Execution Buffer (EB), or another approved full name.
3. Define physical placement, address visibility, capacity, and access-control boundaries for OW, TW, Task Area, Error Log Area, and other OS-managed regions.
4. Define which records are CPU-local protected structures versus protected Data RAM allocations. Preserve the existing ECS, XW, KESP, and double-fault separation.
5. Keep App RAM and Data RAM as independent memory systems with separate controllers and paths.

Until these items are resolved, diagrams must show the logical data path and separate logical domains without implying an unapproved physical address map.
