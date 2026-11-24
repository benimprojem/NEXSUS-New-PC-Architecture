# NEXSUS CPU — Global Issue Width and RAC Demand Study 001

**Document ID:** NEXSUS-CPU-ISSUE-WIDTH-RAC-DEMAND-001  
**Status:** BASELINE selected for implementation/simulation — subject to measured re-evaluation  
**Date:** 2026-11-24

## 1. Purpose and separation of variables

This study evaluates global dispatch/issue width independently from the Resource Access Controller (RAC) logical read/write budget.

- Global issue width is the maximum number of instructions admitted to execution in one cycle across all issue classes.
- RAC capacity is the maximum number of logical 64-bit register/workspace read and write lane accesses granted in one cycle.
- Execution-unit availability, dependency readiness, issue-queue readiness, physical bank/port conflicts, DA staging availability and writeback conflicts can all reduce actual issue below either limit.
- Do not infer issue width from the number of execution units, issue queues, scheduler entries or ROB entries.
- Do not change issue width and RAC capacity in the same experiment sweep.

Candidate global issue widths: **8, 12, 16, 24 and 32 instructions/cycle**. The selected starting baseline is **16 instructions/cycle**. Widths 8 and 12 provide market-aligned lower comparison points; 24 and 32 remain aggressive scaling/stress points. The 16-wide baseline is not immutable: a measured result may justify reopening it.

## 2. Operand footprints currently safe to count

| Instruction class | Read footprint | Write footprint | Accounting |
|---|---:|---:|---|
| Arithmetic ALU | 2 | 1 | RA lanes |
| Logic | 2 | 1 | RA lanes |
| Compare | 2 | 1 | RA lanes |
| FP64 | 2 | 1 | FA lanes |
| FMA | 3 | 1 | FA lanes |
| LOAD | 0 RAC source reads | 1 | DA result write; memory/cache read is not a RAC register read |
| STORE | 1 | 0 | DA source read; memory/cache write is not a RAC register write |
| WLOAD | width-dependent | width-dependent | Workspace source reads + DA destination writes |
| WSTORE | width-dependent | width-dependent | DA source reads + workspace destination writes |
| VEC | 8R standard R3; 12R VMACC; 4R VSUM | 4W per vector result | Each 256-bit MA entry = 4 logical 64-bit RAC slots; see ISA §15 |
| ME512 | 16R/8W for MMUL; 24R/8W for MMAC; 8R/8W for MTRANS/MREDUCE at a full 512-bit slice | Slice-dependent | One 512-bit slice per operand per cycle is provisional; whole tile groups remain reserved but are not read in one cycle; see ISA §15 |
| XFER.WS.MEM/START | 0 RAC | 0 RAC | Independent transfer engine; consumes selected workspace physical read bandwidth |

For WLOAD/WSTORE, a 64/128/256/512-bit operation consumes 1/2/4/8 logical 64-bit lanes on each participating side. XFER is deliberately not counted as RAC demand, but it competes for the selected workspace's physical read banks.

## 3. Known scalar/FP/FMA demand at candidate issue widths

The known read-intensive execution pools contain:
- 24 two-read scalar units: 8 Arithmetic + 8 Logic + 8 Compare.
- 6 two-read FP64 lanes.
- 4 three-read FMA units.

For a conservative upper envelope, fill the issue width with the most read-intensive available known operations first: all four FMA units (3R each), then two-read scalar/FP operations. This assumes the corresponding instructions are ready and their units are available.

| Global issue width | Four FMA reads | Two-read operations | Known read demand upper envelope | One-result-per-instruction write envelope |
|---:|---:|---:|---:|---:|
| 16 | 12 | 12 | **36R** | **16W** |
| 24 | 12 | 20 | **52R** | **24W** |
| 32 | 12 | 28 | **68R** | **32W** |
| 34 | 12 | 30 | **72R** | **34W** |

The 34-instruction row is a reference point covering all 34 known Arithmetic/Logic/Compare/FP64/FMA units at once; it is not a candidate global width.

The write envelope assumes each admitted instruction produces one architectural destination write. It is not a complete physical writeback-port model. Multi-destination instructions, paired/wide writes, vector/matrix operations, WLOAD/WSTORE and same-cycle writeback collisions require explicit opcode-level accounting.

The separate LOAD/STORE pools add up to 8 LOAD and 4 STORE admission resources. LOAD contributes a DA write; STORE contributes a DA read. Their inclusion in a particular issue mix depends on the global width and the available units. They do not increase the scalar/FP/FMA read-envelope table above, because STORE has only one DA source read and LOAD has no RAC register-source read.

## 4. What the candidate RAC budgets imply

| RAC candidate | Width 16: 36R | Width 24: 52R | Width 32: 68R | Interpretation |
|---|---:|---:|---:|---|
| 32R/32W | Short by 4R | Short by 20R | Short by 36R | Constraining even at width 16 in the read-heavy envelope |
| 48R/48W | Headroom 12R | Short by 4R | Short by 20R | Plausible width-16 candidate; close at width 24 |
| 64R/48W | Headroom 28R | Headroom 12R | Short by 4R | Covers known width-24 envelope, not width 32 |
| 80R/48W | Headroom 44R | Headroom 28R | Headroom 12R | Covers known width-32 envelope before MA/workspace demand |
| 80R/64W | Headroom 44R | Headroom 28R | Headroom 12R | Selected starting RAC baseline; generous read/write headroom before MA/workspace traffic |

“Headroom” here is arithmetic budget minus the table's known read envelope. It is not measured throughput. Actual instructions may share/broadcast operands, but no reduction should be assumed until the operand-delivery design proves it. Conversely, MA and workspace operations can increase demand beyond this table.

## 5. Important interpretation

1. **48R/48W is naturally aligned with a 16-wide experiment**, because the known read-heavy envelope is 36R.
2. At width 24, 48R is already 4 reads below the known upper envelope.
3. At width 32, even 64R is 4 reads short; 80R provides 12 reads of headroom before VEC/ME512 and workspace operations.
4. The 76R/42W figure in the RAC evaluation is the all-unit peak subtotal across RA, FA and DA. It is not a per-issue-width demand and must not be directly compared with a width-16/24/32 row without modeling which instructions are selected in that cycle.
5. A 48W budget exceeds the known one-result-per-instruction write envelope for widths 16, 24 and 32. This does not prove 48W is sufficient after wide/pair writes, WLOAD/WSTORE, VEC/ME512 and writeback collisions are modeled.
6. The physical register-file topology is a separate question. Logical RAC slots do not imply one monolithic 48- or 80-port SRAM.

## 6. Required cycle-level instruction mixes

For each candidate issue width, the simulator should run at least:

- Integer arithmetic/logic/compare only.
- FP64 only and FMA only.
- Mixed scalar + FP64 + FMA, including the read-heavy envelope.
- LOAD-heavy and STORE-heavy.
- Scalar/FP plus memory operations.
- VEC and ME512 once all MA footprints are normalized.
- WLOAD/WSTORE widths 64/128/256/512 with same-workspace and opposite-workspace traffic.
- XFER concurrent with WLOAD on the same workspace and on the other workspace.
- Mixed all-class stress with dependent and independent destination chains.

Record per cycle:
- ready instructions per issue queue;
- selected and actually issued instructions;
- requested/granted RAC reads and writes by RA/FA/DA/MA/WS/OS;
- physical bank conflicts and port conflicts;
- DA staging conflicts;
- writeback collisions and forwarding/bypass use;
- stalls by cause, queue age and fairness;
- IPC, unit utilization and useful work completed.

RAC admission must remain atomic: reserve every source and destination footprint together or issue nothing. Allocation remains work-conserving and dynamically shared; no permanent per-class reservation.

## 7. Experiment sequence

1. Normalize VEC/ME512 and wide/pair operand footprints.
2. Keep the selected baseline at 16-wide and use 8/12/24/32 as comparison points. Hold RAC generous/non-binding while measuring issue-width effects.
3. Hold issue width at 16 and sweep RAC budgets 32/32, 48/48, 64/48, 80/48 and 80/64; include the selected 80R/64W baseline.
4. Run the complete mixed workload matrix and compare throughput, fairness, stall causes and estimated physical cost.
5. Re-evaluate 16-wide and 80R/64W only if measurements show a meaningful throughput, power, area or timing reason to do so.

## 8. Current decision

**Global issue width: BASELINE = 16 instructions/cycle.** Compare 8, 12, 24 and 32; reopen only with measured evidence.

**RAC logical budget: BASELINE = 80R/64W per cycle.** Each slot is one logical 64-bit register/workspace lane access. This is not a requirement for a monolithic 80-read/64-write SRAM. Physical banking, replication, bypass, collectors and distributed writeback implement the logical budget.

**Register organization: domain-separated physical banks (RA, FA, DA, MA) under one shared dynamic RAC allocator.** The allocator is work-conserving and age-fair, with atomic instruction reservations and no permanent class quotas. Multiple independent banks may accept writes in parallel; same-destination multiwrite conflicts are prohibited and resolved before issue/commit.

These are the selected starting architecture/simulator baselines, not silicon-validated limits. VEC/ME512 total tile footprints and per-cycle 512-bit slice assumptions are documented in ISA §15 and formula-tested in NEX-T007; full cycle-level RAC contention, fairness, bank-conflict, power/area/timing validation remains required. Re-evaluate only from measured evidence.
