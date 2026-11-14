# NEXSUS CPU — Functional Workspace Naming

**Document ID:** NEXSUS-CPU-WORKSPACE-NAMING-001  
**Status:** Naming baseline  
**Rule:** Purpose-based names are canonical. Legacy SPM labels are compatibility aliases only.

## Canonical memory/workspace map

| Legacy label | Canonical name | Capacity / organization | Primary purpose |
|---|---|---:|---|
| SPM0 | **EB — Execution Buffer** | 4 KiB; 2 × 2 KiB ping-pong banks | Active instruction stream; CFM fills inactive bank and swaps |
| SPM1 | **OW — OS Workpad** | 8 KiB | OS-local scratch/workspace; not a task context |
| SPM2 | **TW — Task Workpad** | 8 KiB | Task/user-local scratch workspace |
| SPM3–SPM6 | **CTP — Context Pool** | 4 × 8 KiB banks; 16 × 2 KiB slots/core | Saved/restored architectural context frames |
| SPM7 | **XW — Exception Workpad** | 8 KiB; 8 × 1 KiB slices | Exception/interrupt entry, temporary frame and recovery workspace |

## Naming rules

- Use **EB, OW, TW, CTP, XW** in new architecture documents, diagrams, simulator output and implementation names.
- Do not append a zero to a singleton resource: **EB**, not EB0. Banked resources may use indices when addressing a particular bank/slice (e.g. CTP bank 0).
- SPM0…SPM7 may appear only in a migration note, compatibility mapping or historical citation. SPM is no longer a canonical resource class.
- Names describe function and ownership, not a claim that these are all CPU physical SRAMs. Implementation may realize them as dedicated arrays, partitions or protected regions, provided capacity, isolation and timing contracts are preserved.
- **EB is code staging, not a context slot. CTP is context storage, not executable code.** Their ownership, valid bits and scheduling are independent.

## Data-path overview

```text
App RAM -> C0 Code Cache -> CS0..CS7 -> EB (ping-pong execution banks)
OS services ---------------------------> OW
Task/user scratch ---------------------> TW
Context save/restore <----------------> CTP
Exception/interrupt handling ----------> XW
```

## Migration checklist

1. Replace canonical SPM0 references with EB.
2. Replace SPM1 with OW; SPM2 with TW.
3. Replace the four context banks SPM3–SPM6 with CTP (bank/slice indices remain explicit).
4. Replace SPM7 with XW.
5. Keep a legacy alias table where older documents or tooling need compatibility.
6. Never conflate CS Code Slots with CTP Context Pool.
