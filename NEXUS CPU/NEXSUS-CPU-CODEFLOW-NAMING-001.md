# NEXSUS CPU — CodeFlow & Workspace Naming Standard (Decision 001)

Status: canonical terminology; legacy identifiers remain accepted in historical/source contexts.

## Naming rule
**A single instance has no numeric suffix.** Add an index only when multiple independently addressable instances exist. Examples: `Execution Buffer` (one), `Code Cache` (one), `Code Slot CS0–CS7` (eight), `Context Pool CP0–CP3` (four banks).

## Code path

| Legacy identifier | Canonical name | Symbol | Responsibility |
|---|---|---|---|
| PX Manager | CodeFlow Manager | CFM | OS-facing task/page orchestration and safe page lifecycle |
| PX P0–P7 | Code Slots | CS0–CS7 | Eight equal, dynamic 2 KiB executable-page slots |
| L0I | Code Cache | C0 | 64 KiB task-aware App RAM staging/cache |
| SPM0 | Execution Buffer | EB | CPU-visible code workspace; 2 × 2 KiB ping-pong banks |
| PX → SPM0 | Code Stream Transfer | CST | Transfer into inactive execution bank |
| PX_NEXT | Code-Flow Continue | CF_NEXT | Manager-only continuation metadata |
| PX_END | Code-Flow End | CF_END | Manager-only stream-end metadata |

## Former SPM workspaces — separate purposes, separate names

| Legacy address/name | Canonical name | Symbol | Capacity | Purpose |
|---|---|---|---:|---|
| SPM1 | OS Workspace | OW | 8 KiB | OS/kernel working data and control |
| SPM2 | Task Workspace | TW | 8 KiB | Current user/task-local working data |
| SPM3–SPM6 | Context Pool | CP0–CP3 | 4 × 8 KiB | Protected task context images; pool entries, not task IDs |
| SPM7 | Exception Workspace | XW | 8 KiB | Exception/interrupt entry scratch and handler workspace |

These are not one generic memory class: they have different ownership, privilege, lifetime, and save/restore rules. The old SPMx labels remain compatibility aliases for existing docs, source, and historical simulation records; new architecture text must use the canonical names.

## Canonical code path

```
App RAM -> Code Cache C0 (legacy L0I, 64 KiB)
        -> Code Slots CS0–CS7 (legacy PX, 8 × 2 KiB)
        -> Execution Buffer EB (legacy SPM0, 2 × 2 KiB banks)
```

App RAM baseline remains one 64-bit read lane. C0 fills are task/page-aware and may use non-contiguous source addresses. App RAM→C0, C0→CS, and CS→EB are independent queues and may overlap subject to validity, ownership, and backpressure.

## Compatibility and usage
- Legacy PX/P0–P7/L0I/SPM0–SPM7 identifiers are **not deleted or silently reinterpreted**.
- In new prose, introduce the canonical name first and legacy identifier parenthetically once.
- Do not append `0` to a singleton. Index only genuinely repeated units.
- CS0 is not a permanently active slot; all Code Slots are equal.
- C0 is staging/cache, not directly executable. EB is the CPU-visible code buffer, not a register/context image.
- CP0–CP3 are pool positions; a task's identity is independent of its context residency.

## Naming rationale
CodeFlow describes the page lifecycle; Code Slot describes physical residency; Code Cache describes staging/reuse; Execution Buffer is the final code workspace. OS Workspace, Task Workspace, Context Pool, and Exception Workspace explicitly distinguish the former SPM regions by role.
