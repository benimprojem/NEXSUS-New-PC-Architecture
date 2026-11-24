# NEXSUS CPU — Functional Workspace Naming

**Document ID:** NEXSUS-CPU-WORKSPACE-NAMING-001  
**Status:** Canonical workspace naming reference  
**Date:** 2026-11-24

## 1. Naming rule

Use the expanded canonical name and symbol on first mention. The current user/application workspace is **Work Space (WS)**. The privileged operating-system workspace is **OS Space (OSSpace)**. Do not use the superseded TW or OW labels in current specifications, assembly examples, simulator output, or diagrams.

## 2. Canonical workspace map

| Legacy label | Expanded canonical name | Canonical symbol | Capacity / organization | Primary purpose |
|---|---|---|---:|---|
| SPM0 | Execution Buffer | EB | 4 KiB; 2 × 2 KiB banks | CPU-only instruction-fetch buffer; CodeFlow Manager fills the inactive bank |
| SPM1 | OS Space | OSSpace | 8 KiB | Privileged OS/kernel scratch, control data, and mediated OS/application exchange |
| SPM2 | Work Space | WS | 8 KiB | General-purpose application working area; not task-owned and not a mandatory stack |
| SPM3–SPM6 | Context Pool | CP0–CP3 | 4 × 8 KiB banks; 16 × 2 KiB slots/core | Saved/restored architectural register-context images |
| SPM7 | Exception Workspace | XW | 8 KiB; 8 × 1 KiB slices | Exception/interrupt entry scratch and handler workspace |

## 3. Workspace ownership and separation

- **Execution Buffer (EB)** stores executable instruction bytes only. It is not a register-context slot and is not software-addressable.
- **OS Space (OSSpace)** is privileged OS/kernel working storage. PL1/PL2 access is permitted; PL0 access is denied.
- **Work Space (WS)** is a core-local, general-purpose application working area. It is available to PL0 application execution and to authorized privileged management paths. It is not owned by a task ID and is not automatically saved/restored as task context.
- **Context Pool (CP0–CP3)** stores saved architectural context images. A context may spill to protected Data RAM when no resident slot is available.
- **Exception Workspace (XW)** is reserved for exception/interrupt entry and handler scratch. It is not a persistent error log.
- Workspace names describe function and ownership. They do not imply that every workspace is a separate physical SRAM chip or controller. Implementation may use dedicated arrays, partitions, or protected regions while preserving capacity, isolation, and timing contracts.
- **Code Slots (CS0–CS7)** and **Context Pool (CP0–CP3)** are different resource classes. Never conflate executable-code residency with register-context residency.

## 4. Legacy-name crosswalk

| Legacy label | Canonical name | Migration note |
|---|---|---|
| SPM0 | Execution Buffer (EB) | Dual-bank 4 KiB instruction workspace |
| SPM1 | OS Space (OSSpace) | 8 KiB |
| SPM2 | Work Space (WS) | 8 KiB |
| SPM3–SPM6 | Context Pool (CP0–CP3) | Four 8 KiB banks |
| SPM7 | Exception Workspace (XW) | 8 KiB; eight 1 KiB slices |

SPM0–SPM7 may appear only when explaining or migrating older documents, source, or simulator records. No superseded workspace symbol is a valid current alias.

## 5. Data-path and workspace overview

```text
Application RAM (App RAM)
    → Code Cache (C0)
    → Code Slots (CS0–CS7)
    → Code Stream Transfer (CST)
    → Execution Buffer (EB: two 2 KiB banks)
    → Active Execution Page (selected EB bank)

OS services ---------------------------> OS Space (OSSpace)
Application working data --------------> Work Space (WS)
Context save/restore <-----------------> Context Pool (CP0–CP3)
Exception/interrupt handling ----------> Exception Workspace (XW)
```

The two EB banks may operate in ping-pong fashion. “Ping-pong” describes the bank-switching method; it is not a separate workspace or additional pipeline stage.

## 6. Related specifications

- **NEXSUS-CPU-CODEFLOW-NAMING-001.md** — canonical Code Cache, Code Slots, CodeFlow Manager, Code Stream Transfer, and Execution Buffer terminology.
- **NEXSUS-CPU-MEMORY-PATH-AND-NAMING-001.md** — complete instruction path, memory domains, expanded naming, and legacy crosswalk.
- **NEXSUS-CPU-WORKSPACE-ADDRESSING-AND-TRANSFER-001.md** — WS/OSSpace addressing, access accounting, and one-way export.
- **NEXSUS-CPU-EXCEPTION-FRAME-001.md** — exception frame and protected exception storage.
