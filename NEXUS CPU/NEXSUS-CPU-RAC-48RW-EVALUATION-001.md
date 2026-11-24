# NEXSUS CPU — RAC 80R/64W Baseline and Workspace Bank Split

**Document ID:** NEXSUS-CPU-RAC-48RW-EVALUATION-001  
**Status:** BASELINE selected — physical implementation and workload validation remain open  
**Date:** 2026-11-24

## 1. Decisions and proposals

- **Workspace physical separation: selected direction.** OS and WS are separate 8 KiB SRAM arrays. Each array has 16 banks × 512 B. They share no physical banks or ports.
- **RAC logical capacity: BASELINE = 80R/64W per cycle.** This is the selected starting point; tests may justify later adjustment.
- **Global backend issue width: BASELINE = 16 instructions/cycle.** Current front-end/dispatch remains 8; compare 8/12/24/32 as backend sensitivity points and evaluate delivery width separately; see the issue-width study.
- **Physical register organization: domain-separated RA/FA/DA/MA banks with a shared dynamic RAC allocator.** Use banked/replicated arrays, operand collectors/broadcast where proven, bypass and distributed writeback rather than one monolithic multiported SRAM.
- RAC values count logical 64-bit lane accesses per cycle, not physical SRAM ports.
- One shared dynamic allocator serves RA/FA/DA/MA and CPU-originated WLOAD/WSTORE workspace accesses. No fixed per-class partition is reserved.

## 2. Separate workspace arrays

Each workspace is its own 8 KiB array:

| Workspace | Capacity | Banks | Bank size | Per-bank service | Aggregate array ceiling |
|---|---:|---:|---:|---:|---:|
| OS | 8 KiB | 16 | 512 B | 1R + 1W / cycle | 16R + 16W / cycle |
| WS | 8 KiB | 16 | 512 B | 1R + 1W / cycle | 16R + 16W / cycle |

Each bank contains 64 × 64-bit words. The proposed mapping is independently applied within each array:

```text
word = floor(offset / 8)
bank = word mod 16
row  = floor(word / 16)
```

This gives each workspace 16 banks × 64 rows × 8 bytes = 8192 bytes. A naturally aligned 128/256/512-bit access uses 2/4/8 consecutive banks. Each bank supports one 64-bit read and one 64-bit write per cycle. Same-bank multiple reads or multiple writes conflict; one read plus one write can proceed if the SRAM macro supports 1R+1W and the address hazard is resolved.

The two arrays can operate simultaneously. For example, a WLOAD from WS and a WSTORE to OS do not contend for the same physical bank. They still consume the shared RAC logical slots and DA register slots.

Per-workspace bandwidth ceiling is 16 × 8 = 128 bytes/cycle read and 128 bytes/cycle write. Combined array-side ceiling is 256 B/cycle read plus 256 B/cycle write across both arrays. This is not a guaranteed sustained rate; RAC, issue width, DA ports, bank conflicts and transfer arbitration may lower it.

XFER.WS.MEM/START reads only the selected source workspace through its array read ports. It does not consume RAC logical slots or DA slots, but competes with WLOAD reads in that workspace. The other workspace's banks remain independent.

## 3. Historical 48R/48W comparison point

The currently documented peak operand demand, before MA and workspace-transfer traffic, is:

| Resource group | Read demand | Write demand | Derivation |
|---|---:|---:|---|
| RA: 8 Arithmetic + 8 Logic + 8 Compare | 48 | 24 | 24 units × (2R + 1W) |
| FA: 6 FP64 + 4 FMA | 24 | 10 | 6 × (2R+1W) + 4 × (3R+1W) |
| DA: 8 LOAD + 4 STORE | 4 | 8 | 4 STORE source reads + 8 LOAD result writes |
| **Subtotal** | **76** | **42** | Excludes MA, WLOAD/WSTORE, XFER and any extra operand/update traffic |

This is a theoretical all-units-active operand demand, not a claim that all these instructions can issue together. Global issue width baseline is 16 instructions/cycle; compare 8/12/24/32 independently from RAC capacity. The known scalar/FP/FMA read envelopes are 36R/52R/68R at widths 16/24/32, before VEC/ME512 and workspace operations. Each 256-bit MA entry consumes four 64-bit RAC slots, so normalized MA opcode demand is added on top of these scalar/FP/FMA envelopes. See `NEXSUS-CPU-ISSUE-WIDTH-RAC-DEMAND-001.md`.

Consequences:

- 32R/32W cannot sustain even the documented RA+FA peak operand demand.
- 48R/48W materially improves concurrency but still cannot serve the 76-read all-unit subtotal in one cycle.
- 48W exceeds the 42-write subtotal by six slots before MA and workspace stores; 48W may be adequate under realistic issue limits, but must be measured.
- The read side is more likely to be the limiting dimension than the write side.
- Choosing 48R/48W must not be described as enough for every execution unit to issue at full physical count simultaneously.

## 4. Candidate budgets

| Candidate | Logical read slots/cycle | Logical write slots/cycle | Assessment |
|---|---:|---:|---|
| Current baseline | 32 | 32 | Clearly restrictive against RA+FA peak |
| Historical intermediate | 48 | 48 | Useful comparison point; below the selected 80R/64W baseline |
| Read-biased candidate | 64 | 48 | Tests whether extra read capacity improves mixed integer/FP throughput |
| Peak-subtotal candidate | 80 | 48 | Covers the 76R subtotal with small headroom, but excludes MA and WLOAD/WSTORE demand |
| **Selected baseline** | **80** | **64** | Starting logical RAC budget; physical topology cost and throughput to be validated |

80R/64W is the selected starting baseline; 80R/48W remains a read-heavy comparison alternative. 32/32, 48/48 and 64/48 remain lower sensitivity points. The selected baseline may be reopened only if measured throughput, area, power or timing justifies a change.

## 5. Dynamic distribution

The RAC must remain work-conserving and dynamically allocate the full pool among ready instructions. It must not reserve fixed slices such as 16R for RA, 8R for FA, etc.

Each issue candidate declares its complete logical footprint:

- RA/FA/DA: each 64-bit register lane read or written counts as one slot.
- MA: each 256-bit MA entry consumes 4 logical 64-bit RAC slots per read/write; a 512-bit pair consumes 8 slots. A matrix tile with T MA entries consumes 4T slots for each full source or destination group.
- WLOAD: workspace read lanes + DA destination write lanes.
- WSTORE: DA source read lanes + workspace write lanes.
- FP128 and other paired register operands count each physical 64-bit FA entry.
- Broadcast/operand reuse may reduce physical array reads only when the implementation proves one read can safely feed all consumers; it must not silently reduce the architectural logical accounting before that policy is defined.

RAC selects instructions atomically. If either the read or write budget is exceeded, or a physical bank/port is unavailable, the entire instruction waits. No partial operand reservation or partial destination update is permitted.

Age-based fairness is required, but a ready high-priority instruction may use idle capacity. No class receives a permanent guaranteed share in the first implementation.

## 6. Required experiments before freezing

1. Sweep RAC budgets: 32/32, 48/48, 64/48, 80/48, 80/64.
2. Sweep global issue width at 8/12/16/24/32 independently; do not change both dimensions in one test. See `NEXSUS-CPU-ISSUE-WIDTH-RAC-DEMAND-001.md`.
3. Run integer-only, FP-only, mixed integer+FP, memory-heavy, vector/matrix, and mixed all-class workloads.
4. Record per-cycle requested versus granted reads/writes, issue stalls by reason, queue age, bank conflicts, DA conflicts, writeback conflicts, throughput and fairness.
5. Add simultaneous WS+OS tests to confirm the two independent arrays do not cross-contend.
6. Add XFER+WLOAD tests on the same workspace and on opposite workspaces.
7. Test worst-case MA pair and 512-bit DA groups; each MA entry counts as four 64-bit RAC slots. Validate every opcode/tile footprint against the 80R/64W baseline.
8. Compare area/power/timing estimates for the selected logical budget and physical register-file banking/replication. A logical 80R/64W budget does not require one monolithic 80-read/64-write SRAM.

## 7. Current conclusion

The physical workspace direction is now **two independent 8 KiB arrays, each 16 banks × 512 B with 1R+1W per bank**.

The selected starting point is **16-wide issue with an 80R/64W logical RAC budget**. Compare issue widths 8/12/24/32 and RAC alternatives 32/32, 48/48, 64/48 and 80/48 in controlled sweeps. The known scalar/FP/FMA read envelope at width 16 is 36R, leaving 44 logical read slots for MA, memory staging and workspace traffic; the one-result write envelope is 16W, leaving 48 write slots before wide/pair writes and WSTORE traffic. Each 256-bit MA entry is four 64-bit slots, but large ME512 tiles are streamed in 512-bit slices rather than charged as a full-tile read in one cycle. This is intentionally a generous initial budget, not proof that every execution unit can issue simultaneously.

The physical organization is domain-separated RA/FA/DA/MA banks behind a shared, dynamically allocated RAC. Multiple banks can write independently in the same cycle, subject to physical bank availability and writeback arbitration. The same architectural destination must not receive conflicting multiwrites in one cycle. Atomic reservations prevent partially issued instructions. MA total footprints and provisional 512-bit per-operand slice demand are now documented and formula-tested. Re-evaluate 16-wide and 80R/64W only after cycle-level RAC throughput, fairness, bank-conflict, area, power and timing results are available.
