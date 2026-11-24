# NEXSUS CPU — Memory Path and Expanded Naming Reference

**Document ID:** NEXSUS-CPU-MEMORY-PATH-AND-NAMING-001  
**Status:** Canonical naming reference — follows CodeFlow & Workspace Naming Decision 001  
**Date:** 2026-11-16

## 1. Mandatory naming rule

Use the **new canonical names** in all new documents, diagrams, simulator output, and explanations. Never use a short symbol alone when introducing a resource: write its expanded name and symbol together, then explain its role.

Examples:
- **Code Cache (C0)** — first-level application-code staging/cache.
- **Code Slots (CS0–CS7)** — eight executable-code page slots.
- **Execution Buffer (EB)** — two-bank execution-code workspace.
- **CodeFlow Manager (CFM)** — manager for code-page lifecycle and transfer orchestration.
- **Code Stream Transfer (CST)** — transfer from a Code Slot into the inactive Execution Buffer bank.

The former names PX, P0–P7, Ping-Pong, SPM0, and L0I are **legacy names**. They may appear in a compatibility note or when reading older documents, but must not be used as the current architecture vocabulary.

## 2. Canonical application-instruction path

```text
Application RAM (App RAM)
    → Code Cache (C0)
    → Code Slots (CS0–CS7)
    → Code Stream Transfer (CST)
    → Execution Buffer (EB)
         ├── Bank A (2 KiB)
         └── Bank B (2 KiB)
    → Active Execution Page (the selected 2 KiB EB bank)
    → Instruction Fetch / Decode / Execute
```

| Order | Expanded name | Canonical symbol | Defined role |
|---:|---|---|---|
| 1 | Application RAM | App RAM | Backing source for application instruction bytes; separate from Data RAM with its own controller and path |
| 2 | Code Cache | C0 | First code staging/cache layer after App RAM; current documented capacity is 64 KiB |
| 3 | Code Slots | CS0–CS7 | Eight equal, dynamically allocated executable-code slots; each 2 KiB, 16 KiB total per core |
| 4 | Code Stream Transfer | CST | Validated transfer from a selected Code Slot into the inactive Execution Buffer bank |
| 5 | Execution Buffer | EB | CPU-visible instruction workspace; 4 KiB total, split into two independently managed 2 KiB banks |
| 6 | Active Execution Page | Active EB bank | Descriptive name for the one 2 KiB EB bank currently supplying the instruction-fetch stream; not another memory layer |

**Important:** the old term “Ping-Pong” describes the two-bank operating method of the Execution Buffer (EB). It is not a separate resource or stage. “Execution Page” means the currently active 2 KiB bank inside EB, not a separate 2 KiB buffer placed after EB.

## 3. CodeFlow Manager responsibilities

**CodeFlow Manager (CFM)** manages the lifecycle of Code Slots and coordinates Code Stream Transfers. CFM is a controller/manager, not a data-storage stage.

It coordinates:
- Code Cache (C0) availability and source-page readiness;
- allocation, ownership, generation, and validity of Code Slots (CS0–CS7);
- transfer selection and validation for Code Stream Transfer (CST);
- inactive-bank refill and safe bank switching in Execution Buffer (EB);
- task-aware ordering and safe release/reuse of code slots.

A Code Slot is not permanently tied to a task or execution position. All eight slots are equal pool resources. The task's logical code-page mapping and program counter identify the next code; the physical slot number is not a task-visible code address.

## 4. Fixed capacities and safety rules

| Resource | Capacity / organization | Rule |
|---|---:|---|
| Code Cache (C0) | 64 KiB | Task-aware code staging; may fill progressively |
| Code Slots (CS0–CS7) | 8 × 2 KiB = 16 KiB/core | Executable code only; dynamic equal-slot pool |
| Execution Buffer (EB) | 2 × 2 KiB = 4 KiB | Two independent banks; one may be active while the other is refilled |
| Active Execution Page | 2 KiB | One selected EB bank; descriptive active role, not extra capacity |

- Code Slots contain executable code, not task data or register-context images.
- A Code Slot becomes usable only after content, owner, generation, permissions, mapping, and valid-byte range are committed.
- CST may refill only the inactive EB bank.
- At a legal instruction boundary, the active-bank selector may switch only when the destination bank is fully READY and its task identity, generation, logical-page mapping, permissions, and valid-byte range are valid.
- The consumed bank becomes eligible for a subsequent CST refill only after instruction-fetch references have drained.
- Code-page residency and register-context residency are independent.

## 5. Other workspace and memory domains

These are separate logical resource domains. The table does **not** claim that every domain is a separate physical RAM chip or independent controller.

| Expanded name | Canonical symbol | Capacity / placement | Purpose |
|---|---|---|---|
| Operating-System Workspace | OW | 8 KiB workspace | Privileged OS/kernel scratch and control data; not a task context |
| Task Workspace | TW | 8 KiB workspace | Current task/user-local scratch data |
| Context Pool | CP0–CP3 | Four 8 KiB banks; 16 × 2 KiB context slots/core | Saved architectural register/context images; protected residency, with spill to protected Data RAM when required |
| Exception Workspace | XW | 8 KiB; eight 1 KiB slices | Exception/interrupt entry scratch and handler workspace |
| Kernel Exception Stack | KESP | Protected Data RAM | Privileged exception software stack |
| Exception Context Stack | ECS | Per-core protected hardware records; minimum eight entries | Live exception context records; not diagnostic history |
| Emergency Double-Fault Record | EDFR | Separate per-core protected record | Emergency state for double-fault handling |
| Task Area | Task Area | Logical OS-managed area; physical subdivision open | Task state, scheduling metadata, and lifecycle records |
| Error Log Area | Error Log Area | Placement and capacity not frozen | Persistent diagnostic/error history |
| General Data Memory | Data RAM | Separate memory system/controller/path from App RAM | Mutable program data, task data, shared data, and protected OS backing |

## 5.1 OW/TW workspace addressing and persistence

OW and TW are directly byte-addressable, core-local 8 KiB working files. TW is general-purpose task-local storage and is not required to follow LIFO stack order. OW remains OS-owned.

- WLOAD (0x89) and WSTORE (0x8A), using WSMEM format, move 8/16/32/64/128/256/512-bit values between OW/TW and DA staging.
- Workspace offsets are byte addresses 0–8191. Addressing supports absolute workspace offset and RA base + signed byte displacement. Natural alignment and complete-range bounds checks apply.
- Register banks are saved/restored explicitly through MOV.DA.RA / MOV.RA.DA, MOV.DA.FA / MOV.FA.DA, and MOV.DA.MA / MOV.MA.DA. DA staging clobbers remain visible to the ABI.
- XFER.WS.MEM (0x8B) copies a selected OW/TW range only to an L1–L4 Data RAM domain. XFER.WS.START (0x8C) starts the asynchronous export; XFER.WAIT (0x88) consumes the token. The reverse direction is forbidden.
- A full 8 KiB workspace may be exported as one block. This path uses the transfer engine and Data RAM controller, not DA staging or RAC register-access slots. Restore is CPU-mediated through Data RAM LOAD→DA→WSTORE; App RAM is never a workspace data source.
- OW/TW permissions and source/destination reservation rules are defined in Workspace Addressing and Transfer and Workspace Access Protection.

## 6. Exception-storage separation — preserve existing decisions

- Exception Context Stack (ECS) holds protected per-core hardware exception-context records; minimum eight entries.
- Exception Workspace (XW) is 8 KiB split into eight 1 KiB slices.
- Kernel Exception Stack (KESP) is in protected Data RAM.
- Emergency Double-Fault Record (EDFR) remains a separate per-core protected record.
- Error Log Area stores diagnostic history. It must not be conflated with ECS, XW, KESP, or EDFR.

## 7. Legacy-name compatibility crosswalk

The following are old names and must not be used as current names in new diagrams or prose:

| Legacy name | Current canonical name | Note |
|---|---|---|
| L0I / Level-0 Instruction Cache (L0) | Code Cache (C0) | First application-code staging/cache layer |
| PX Manager | CodeFlow Manager (CFM) | Manager/controller, not a storage stage |
| PX pages P0–P7 | Code Slots CS0–CS7 | Eight equal 2 KiB executable-code slots |
| PX → SPM0 transfer | Code Stream Transfer (CST) | Transfer into the inactive EB bank |
| Ping-Pong buffer / SPM0 | Execution Buffer (EB) | Same 4 KiB dual-bank execution workspace |
| SPM1 | Operating-System Workspace (OW) | 8 KiB |
| SPM2 | Task Workspace (TW) | 8 KiB |
| SPM3–SPM6 | Context Pool (CP0–CP3) | Four 8 KiB banks |
| SPM7 | Exception Workspace (XW) | 8 KiB, eight 1 KiB slices |

Do not mix legacy and canonical names in the same current-state diagram. When a legacy term is necessary to explain an older document, mark it explicitly as **legacy**.

## 8. Remaining physical-map decisions

The canonical names and logical roles above are fixed by this reference. The following implementation details remain open and must not be guessed:

1. Physical address placement and address visibility for OW, TW, Task Area, and Error Log Area.
2. Whether each workspace is implemented as a dedicated SRAM, a partition, or a protected region of a shared physical memory.
3. Exact physical placement and access path for ECS and EDFR, preserving their existing CPU-local protected semantics.
4. Capacity and retention policy for the Error Log Area.
5. Detailed arbitration and timing for C0 → CS and CST → EB, beyond explicitly recorded simulator operating points.

App RAM and Data RAM remain independent memory systems with separate controllers and paths. No new memory type, cache level, register bank, or execution stage is introduced by this naming reference.

## 9. Related naming decision

This document follows **NEXSUS-CPU-CODEFLOW-NAMING-001.md**, which is the canonical source for CodeFlow and workspace terminology. If an older document conflicts with this naming reference, use the canonical names and roles here, then update the older document through an explicit compatibility/migration edit.
