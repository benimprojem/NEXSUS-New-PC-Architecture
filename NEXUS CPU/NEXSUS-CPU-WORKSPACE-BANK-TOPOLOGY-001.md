# NEXSUS CPU — Workspace Bank Topology and Port Budget

**Document ID:** NEXSUS-CPU-WORKSPACE-BANK-TOPOLOGY-001  
**Status:** Microarchitecture proposal — logical access budget fixed; physical bank topology not yet frozen  
**Date:** 2026-11-24

## 1. Scope and fixed constraints

This document evaluates the physical access structure for the two core-local workspaces:

- **OS Space (OSSpace):** 8 KiB, OS-owned, PL1/PL2 access.
- **Work Space (WS):** 8 KiB, general-purpose application workspace, PL0 access during an authorized application execution epoch. WS is not task-ID-owned and is not automatically part of task context.

The following decisions are already fixed:

1. CPU-originated WLOAD/WSTORE accesses to WS and OSSpace participate in the same core-wide Resource Access Controller (RAC) budget as RA/FA/DA/MA.
2. The total budget is **32 logical 64-bit reads + 32 logical 64-bit writes per cycle** across all six endpoint groups. It is not 32R/32W per bank or per workspace.
3. A 128/256/512-bit WLOAD/WSTORE consumes 2/4/8 logical 64-bit slots on both its source and destination sides.
4. The complete source and destination footprints are reserved atomically. If either the RAC budget or required physical bank resources are unavailable, the instruction waits without partial access.
5. XFER.WS.MEM/START use the separate transfer engine and do not consume RAC logical slots. They still consume physical workspace read bandwidth.
6. Data RAM, App RAM, DMA, Fabric, peripherals, and other cores cannot write either workspace directly. Workspace export is one-way to Data RAM; restore is CPU-mediated.

The logical access budget does not itself determine the physical SRAM bank count, port macros, latency, or bank-conflict behavior.

## 2. Access accounting

RAC counts 64-bit lane accesses:

| Operation | Workspace endpoint | DA endpoint | RAC reservation |
|---|---|---|---|
| WLOAD.W8/W16/W32/W64 | 1 read | 1 write | 1R + 1W |
| WLOAD.W128 | 2 reads | 2 writes | 2R + 2W |
| WLOAD.W256 | 4 reads | 4 writes | 4R + 4W |
| WLOAD.W512 | 8 reads | 8 writes | 8R + 8W |
| WSTORE.W8/W16/W32/W64 | 1 write | 1 read | 1R + 1W |
| WSTORE.W128 | 2 writes | 2 reads | 2R + 2W |
| WSTORE.W256 | 4 writes | 4 reads | 4R + 4W |
| WSTORE.W512 | 8 writes | 8 reads | 8R + 8W |

The table expresses the combined read/write slot demand, not a promise that the physical SRAM and DA/register banks can always service every admitted operation in one cycle. Bank conflicts, bypass, writeback and other register demand can still defer issue.

## 3. Physical topology candidates

The aggregate logical workspace capacity is 16 KiB. Candidate organizations are:

| Candidate | Physical organization | Per-bank porting | Advantages | Costs / risks |
|---|---|---|---|---|
| A | 8 banks × 2 KiB | 4R + 4W | Lowest bank count; 32 accesses can be distributed across eight banks | Expensive multiported SRAM; high per-bank muxing and collision complexity |
| B | 16 banks × 1 KiB | 2R + 2W | Balanced bank count and port count | True dual-read/dual-write implementation still costly |
| **C — recommended** | **32 banks × 512 B** | **1R + 1W** | Matches the 32R/32W ceiling with simple per-bank ports; 64-bit interleave naturally spreads wide accesses | More bank decoders and crossbar/arbitration endpoints; same-bank requests still conflict |
| D | Two independent 8 KiB arrays, each 32 banks × 256 B | 1R + 1W per bank | Strongest physical isolation between WS and OSSpace; no cross-workspace bank contention | 64 physical banks per core; more area, clock/power and control overhead than the shared 16 KiB array |

### 3.1 Recommended candidate C — shared 16 KiB, 32-bank array

Use one core-local 16 KiB physical SRAM array divided into 32 banks. The two logical 8 KiB workspaces remain separate protected address regions; sharing the physical array does **not** create a software-visible alias or relax access permissions.

- Total capacity: 16 KiB.
- Bank count: 32.
- Bank capacity: 512 bytes = 64 × 64-bit words.
- Per-bank service: at most one 64-bit read and one 64-bit write per cycle.
- Aggregate physical ceiling: up to 32 × 64-bit reads and 32 × 64-bit writes per cycle, subject to bank conflicts and RAC availability.
- Aggregate theoretical payload ceiling: 256 B/cycle read plus 256 B/cycle write. This is an array-side upper bound, not a guaranteed WLOAD/WSTORE or XFER throughput.

### 3.2 Bank mapping proposal

Use 64-bit words as the interleave unit.

Let:

- `offset` be the byte offset within the selected workspace (0–8191).
- `word = floor(offset / 8)`.
- `region_id = 0` for OSSpace and `1` for WS.

Proposed mapping:

```text
bank = (word + 16 * region_id) mod 32
row  = 32 * region_id + floor(word / 32)
```

This maps each 8 KiB logical workspace evenly across all 32 banks. It also skews the two regions by 16 banks, so identical offsets in OSSpace and WS do not automatically collide in the same bank.

Physical organization check:

- 32 banks × 64 rows × 8 bytes = 16,384 bytes.
- OSSpace occupies rows 0–31 across all banks.
- WS occupies rows 32–63 across all banks.
- Each logical workspace contributes 32 rows × 8 bytes = 256 bytes per bank.

The mapping is a proposal for modeling and review, not a frozen physical address encoding.

## 4. Width mapping and bank footprint

The workspace data path is 64-bit lane-based, matching DA entry width.

| Access width | 64-bit lanes | Consecutive banks touched |
|---:|---:|---:|
| 8/16/32 bit | 1 | 1, with byte/halfword/word enables |
| 64 bit | 1 | 1 |
| 128 bit | 2 | 2 |
| 256 bit | 4 | 4 |
| 512 bit | 8 | 8 |

Natural alignment remains mandatory. A naturally aligned 128/256/512-bit access touches 2/4/8 distinct consecutive banks under the proposed 8-byte interleave. All lane banks are reserved together; no partial wide access is allowed.

A 512-bit WLOAD and a 512-bit WSTORE may use the same eight banks in one cycle if their read and write addresses are independently serviceable and no same-address read/write hazard exists. The per-bank 1R+1W structure permits one read and one write concurrently; it does not permit two reads or two writes to the same bank in one cycle.

## 5. Bank conflicts, hazards, and arbitration

1. Each bank may service at most one read and one write per cycle.
2. Two reads targeting the same bank conflict; two writes targeting the same bank conflict.
3. A read and a write to different rows in the same bank may proceed together.
4. A same-address read/write collision must be resolved by explicit forwarding or serialization. The design must not rely on an unspecified SRAM read-during-write mode.
5. Same-destination multiwrite remains prohibited.
6. RAC first reserves the complete logical 32R/32W footprint. The workspace bank arbiter then reserves every physical bank in the access footprint. If either reservation fails, the instruction remains queued and no partial state changes.
7. Arbitration must be age-aware and starvation-resistant. No fixed bank or execution class receives a permanently reserved portion of the shared RAC budget.

## 6. XFER interaction

XFER.WS.MEM/START bypass RAC logical access slots and DA staging, but the transfer engine reads the same physical workspace array.

- XFER reads compete with WLOAD reads for each bank's read service.
- A WSTORE to bytes inside the active XFER source range is blocked until the transfer releases its source reservation.
- WSTORE to unrelated offsets may continue if its target bank's write port is available and RAC slots are available.
- WLOAD may read the source range while XFER is reading it, but both requests compete for the affected bank's read port.
- XFER arbitration must make forward progress without starving CPU WLOAD; CPU traffic must not indefinitely starve an accepted export.
- The workspace array's 256 B/cycle read ceiling is not the XFER throughput guarantee. The transfer engine, Fabric path, and Data RAM destination may be narrower.

## 7. Protection and lifecycle invariants

- The workspace selector is not an authorization token.
- OSSpace remains PL1/PL2-only; PL0 access is a protection fault.
- WS is accessible to PL0 only during an authorized application execution epoch. WS is not task-ID-owned.
- Before WS is granted to a different protection domain, the OS revokes the previous access epoch and clears/reinitializes WS unless an explicitly authorized continuation preserves the same data domain.
- External agents cannot write either workspace. XFER is a read-only source path.
- A bank conflict is a retry/stall condition; a permission, bounds, alignment, or access-epoch violation is a precise architectural fault.

## 8. Required validation before freezing the physical topology

| Test | Required result |
|---|---|
| 32 independent 64-bit reads to distinct banks | Up to 32 bank reads can be serviced if RAC slots are available |
| 32 independent 64-bit writes to distinct banks | Up to 32 bank writes can be serviced if RAC slots are available |
| More than one read to the same bank | Conflict is detected; no partial issue |
| More than one write to the same bank | Conflict is detected; no partial write |
| One read + one write to one bank, different rows | Both may proceed |
| Same-address read/write | Forwarding or serialization gives deterministic behavior |
| Four 512-bit accesses in one direction | 32 lane banks are reserved atomically; all-or-none issue |
| Mixed WS and OSSpace accesses at identical offsets | Proposed bank skew maps them to different bank groups |
| WLOAD and WSTORE mixed with RA/FA/DA/MA operations | Shared 32R/32W budget is never exceeded |
| XFER and WLOAD on same bank | Read-port arbitration is fair and forward-progressing |
| XFER source reservation plus WSTORE | Writes into reserved bytes are blocked; unrelated writes may proceed |
| Protection-domain change | Old WS data cannot be observed by the next domain |
| External Data RAM/App RAM/DMA/Fabric write attempt | Rejected; no workspace byte changes |

## 9. Open decisions

- Accept or reject the recommended shared 32-bank topology versus two physically independent workspace arrays.
- Confirm whether the per-bank 1R+1W macro is the preferred physical SRAM primitive.
- Exact SRAM latency, pipeline stages, ECC/parity, byte-write implementation, and power gating.
- Final bank conflict queue depth and arbitration age policy.
- XFER versus WLOAD read-port priority and service guarantees.
- Whether a privileged clear/reinitialize operation uses a dedicated hardware clear path or ordinary bank writes.

Until these items are validated, the **32R/32W logical RAC budget is fixed**, while the physical workspace topology remains a proposal.
