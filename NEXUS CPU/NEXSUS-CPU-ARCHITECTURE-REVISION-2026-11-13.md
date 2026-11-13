# NEXSUS CPU Architecture Revision — 2026-11-13

**Status:** Selected architecture direction; encoding and performance validation still open  
**Scope:** Restore 64-entry register banks and adopt P0/P1 command double buffering.

## 1. Register-bank restoration

The earlier 32-entry reduction is reverted. Every architectural bank has 64 entries:

| Bank | Entries | Entry width | Bank bytes |
|---|---:|---:|---:|
| RA | 64 | 64-bit | 512 B |
| FA | 64 | 64-bit | 512 B |
| DA | 64 | 64-bit | 512 B |
| MA | 64 | 256-bit | 2,048 B |
| **Total** | **256 registers** | — | **3,584 B (3.5 KiB)** |

- RA0–RA63, FA0–FA63, DA0–DA63, MA0–MA63.
- RA views RB/RC/RD remain 32/16/8-bit slices of the same 64-bit RA entry.
- Register selectors require 6 bits (0–63).
- FA128 pairs use even starts through FA62:FA63; ME512 pairs use even MA starts through MA62:MA63.
- Interrupt save masks become 64 bits per bank.
- Full architectural register payload is 3,584 bytes; with the existing 64-byte frame header, 3,648 bytes.
- A 4-KiB resident context slot fits this payload and header. SPM3–SPM6 (32 KiB) hold two 4-KiB slots per bank: **8 resident complete contexts/core**. Other task contexts remain in protected Data RAM.

### Encoding consequence

The 64-bit instruction envelope (OP8 + FMT4 + payload52) remains the current top-level proposal. However, format diagrams drafted for 5-bit register selectors are not frozen: selector fields must be widened to 6 bits and every format's operand positions, reserved bits and immediate/displacement budgets must be audited. Do not emit or treat old 32-register encodings as a finalized binary ABI.

## 2. P0/P1 command double buffer

Selected command-prefetch organization:

| Buffer | Capacity | Role |
|---|---:|---|
| P0 | 8 KiB | Active command block / execution supply |
| P1 | 8 KiB | Inactive buffer; prefetch next command block |
| **Total** | **16 KiB** | Ping-pong command storage |

Each buffer contains 1,024 64-bit command words. The intended sequence:

1. Load the first 8-KiB command block into P0.
2. While execution consumes P0, load the next 8-KiB block into P1.
3. At the block boundary, switch active/inactive roles.
4. Prefetch the next block into the now-inactive P0.
5. Repeat continuously; the command path is refillable and is not task architectural state.

### Refill assumption used by the first simulator model

- App RAM refill interface: 512 bits/cycle (64 bytes/cycle).
- 8 KiB block transfer: 128 cycles, excluding any separately modeled setup/queue delay.
- One refill engine/core.
- Prefetch of the next block overlaps execution from the active buffer.
- If the next block is not ready at the boundary, execution waits; no ideal zero-stall assumption.
- These are explicit model assumptions, not validated physical timing. App RAM banking, command queue depth, branch redirects, refill arbitration and actual sustainable bandwidth remain open.

The P0/P1 model supersedes the earlier single 8-KiB P0 / 8-cycle-line-refill baseline. Previously published ablation and cross-architecture numbers are historical for that old model and must be regenerated before they are used to compare the revised architecture.

## 3. Next validation

1. Re-run identical AMD Zen 5, Intel Lion Cove P, Intel Skymont E and NEXSUS workloads with the updated P0/P1 path.
2. Sweep P0/P1 block refill time (64/96/128/160 cycles) and total buffer capacity (4/8/16/32 KiB).
3. Rebuild all ISA format diagrams with 6-bit selectors and check payload constraints.
4. Update register-pressure, context-save, interrupt and compiler/assembler models for 64-entry banks.
5. Treat model output as architecture exploration, not measured silicon performance.
