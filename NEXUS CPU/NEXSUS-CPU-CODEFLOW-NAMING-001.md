# NEXSUS CPU Code-Path Terminology — Naming Decision 001

Status: proposed canonical vocabulary (implementation identifiers remain backward-compatible)

## Canonical names

| Legacy identifier | Canonical architectural name | Short symbol | Responsibility |
|---|---|---|---|
| PX Manager | CodeFlow Manager | CFM | OS-facing task/page orchestration and hardware-safe page lifecycle |
| PX P0–P7 | Code Slots | CS0–CS7 | Eight equal, dynamically allocated 2 KiB executable-page slots |
| L0I | Code Cache | C0 | 64 KiB task-aware App RAM staging/cache; incremental fills |
| SPM0 | Execution Buffer | EB0 | 4 KiB CPU code workspace, two 2 KiB ping-pong banks |
| PX → SPM0 transfer | Code Stream | CST | Page movement into the inactive execution bank |
| PX_NEXT | Code-Flow Continue | CF_NEXT | Manager metadata indicating continuation |
| PX_END | Code-Flow End | CF_END | Manager metadata marking end of code stream |

## Compatibility rule

The existing names PX, P0–P7, L0I, SPM0, PX_NEXT and PX_END remain valid in source, simulation output and historical records. The canonical names above are descriptive aliases, not a breaking rename. In new prose, use canonical name first and legacy symbol in parentheses on first occurrence, e.g. **Code Cache (C0; legacy L0I)**.

Do not call CS0 the active slot by default: every Code Slot is equal; any mapped slot may be referenced by fetch. Code Cache (C0) is staging, not directly executable. Execution Buffer (EB0) is the active code workspace and does not hold register images.

## Pipeline

```text
App RAM -> Code Cache C0 (L0I, 64 KiB)
        -> Code Slots CS0–CS7 (PX, 8 x 2 KiB)
        -> Execution Buffer EB0 (SPM0, 2 x 2 KiB)
```

App RAM baseline is one 64-bit read lane. Code Cache fills are task/page-aware and may use non-contiguous source addresses. The three transfer queues remain independent and may overlap subject to validity, ownership and backpressure.

## Naming rationale

- **CodeFlow** describes task-aware code page lifecycle, rather than an opaque “PX”.
- **Code Slot** describes a physical page residency slot without implying task identity or priority.
- **Code Cache** conveys incremental reuse/staging.
- **Execution Buffer** identifies the final CPU-visible code workspace, distinguishing it from register/context storage.
- **Code Stream** names the transfer/continuation concept without treating metadata as instruction bytes.
