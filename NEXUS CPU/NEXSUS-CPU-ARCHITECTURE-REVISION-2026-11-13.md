# NEXSUS CPU Architecture Revision — 2026-11-13

**Status:** Selected architecture direction; simulator validation in progress  
**Scope:** Restore original NEXSUS memory bandwidth and P0/P1 command double buffering.

## 1. Memory bandwidth correction (the intended 64 → 32 reversal)

The parameter temporarily normalized for vendor comparison was **aggregate DRAM data bandwidth**, not register count:

| Profile | Aggregate DRAM bandwidth in simulator |
|---|---:|
| AMD Zen 5 reference | 32 B/cycle |
| Intel Lion Cove P reference | 32 B/cycle |
| Intel Skymont E reference | 32 B/cycle |
| **NEXSUS 128 architecture** | **64 B/cycle (restored)** |

NEXSUS had originally been modeled at 64 bytes/cycle. It was reduced to 32 B/cycle solely to make an equal-bandwidth comparison. That fairness normalization is now undone: vendor reference profiles remain at 32 B/cycle and NEXSUS returns to its architectural 64 B/cycle. The new comparison intentionally includes NEXSUS's wider memory path. Earlier equalized numbers are historical and must be rerun.

This is **Data-RAM/DRAM aggregate bandwidth**. It is distinct from:
- physical bank slice: 64-bit per bank;
- aggregate 8-bank data group: 512-bit (64 bytes) per full beat;
- App-RAM P0/P1 instruction refill path: separate 512-bit interface candidate.

## 2. Register architecture — unchanged (32 entries)

The previous edit that changed register banks to 64 entries was a mistake and has been reverted. Selected banks remain:

| Bank | Entries | Entry width | Bank bytes |
|---|---:|---:|---:|
| RA | 32 | 64-bit | 256 B |
| FA | 32 | 64-bit | 256 B |
| DA | 32 | 64-bit | 256 B |
| MA | 32 | 256-bit | 1,024 B |
| **Total** | **128 registers** | — | **1,792 B (1.75 KiB)** |

- RA0–RA31, FA0–FA31, DA0–DA31, MA0–MA31.
- Register selectors remain 5 bits.
- FA128 pairs use even starts through FA30:FA31; ME512 pairs use even MA starts through MA30:MA31.
- Full architectural register payload is 1,792 bytes; with the 64-byte frame header, 1,856 bytes.
- A 2-KiB resident context slot fits. SPM3–SPM6 (32 KiB) hold four 2-KiB slots per bank: **16 resident complete contexts/core**. Other task contexts remain in protected Data RAM.

## 3. P0/P1 command double buffer

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
4. Prefetch the next block into the now-inactive buffer.
5. Repeat continuously.

### Refill assumption
- App RAM refill interface: 512 bits/cycle (64 bytes/cycle).
- 8 KiB block transfer: 128 cycles, excluding separately modeled setup/queue delay.
- One refill engine/core; next-block prefetch overlaps active-buffer execution.
- If the next block is not ready at the boundary, execution waits.
- This is a model assumption, not validated physical timing. App RAM bank behavior, command queues, branch redirects, arbitration and sustainable bandwidth remain open.

The P0/P1 model supersedes the earlier single 8-KiB P0 baseline. Previous ablation/comparison figures are historical until rerun.

## 4. Next validation
1. Rerun AMD Zen 5, Intel P, Intel E and NEXSUS with restored 64 B/cycle NEXSUS DRAM bandwidth and P0/P1.
2. Sweep P0/P1 refill delay and capacity.
3. Audit all 5-bit register selector format diagrams (register width has not changed).
4. Validate task-context and exception behavior against the unchanged 32-entry banks.
5. Treat model output as architecture exploration, not measured silicon performance.
