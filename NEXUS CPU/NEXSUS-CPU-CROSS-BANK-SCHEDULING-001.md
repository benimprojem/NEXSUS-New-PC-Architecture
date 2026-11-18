# NEXSUS CPU — Cross-Bank Pairing and Graph-Coloring Scheduler Plan

**Document ID:** NEXSUS-CPU-CROSS-BANK-SCHEDULING-001  
**Date:** 2026-11-18  
**Status:** Design proposal / OPEN — not yet an ISA or physical-port commitment  
**Scope:** Compiler scheduling across RA, DA, FA and MA register banks; paired and multi-operation issue groups; register allocation and dependency analysis.

## 1. Purpose

NEXSUS has separate architectural register banks and separate App RAM / Data RAM paths. The compiler should exploit that separation by finding independent operations that can progress together, rather than treating each instruction as an isolated operation.

The goal is a flexible compiler and scheduler model that can form 2-operation, 4-operation or wider groups when dependencies and actual execution resources permit.

This document records a design direction. It does **not** add execution units, increase issue width, freeze register-file port counts, or guarantee that every proposed group completes in one cycle.

## 2. Authoritative architectural baseline

The current architecture decision register is authoritative for register counts and execution resources.

| Register bank | Entries | Entry width | Role |
|---|---:|---:|---|
| RA0–RA31 | 32 | 64 bit | Integer, scalar, address |
| FA0–FA31 | 32 | 64 bit | Floating point |
| DA0–DA31 | 32 | 64 bit | Data staging / transfer |
| MA0–MA31 | 32 | 256 bit | Vector / matrix operands |

Additional established rules:
- RB, RC and RD are narrower views of the same RA physical entries, not extra banks.
- FP128 uses an even-indexed pair of FA entries.
- ME512 uses an even-indexed pair of MA entries.
- App RAM and Data RAM are separate memory systems with independent controllers and paths; they may progress concurrently.
- Data RAM is not an instruction-fetch source.

Current per-core execution-resource baseline:

| Resource | Units / lanes | State |
|---|---:|---|
| Integer execution lanes | 8 | FIXED |
| FP64 execution lanes | 6 | FIXED |
| Dedicated FMA units | 4 | FIXED |
| Vector execution units | 2 | FIXED |
| ME512 execution unit | 1 | FIXED |

The above are execution resources, not register-file port counts. Physical register read/write ports, cross-bank connectivity, bypass paths and writeback arbitration remain OPEN and must be verified separately.

## 3. Cross-bank 16+16 logical pairing

The proposed 16+16 split is a **logical compiler organization**, not a physical partition, bank lock or restriction on legal register operands.

For RA and DA, the compiler may treat corresponding indices as logical cross-bank pairs:

| Logical region | Pair indices | Example pair |
|---|---|---|
| Region A | 0–15 | RA1 + DA1 |
| Region B | 16–31 | RA16 + DA16 |

The same index-pairing convention may be explored for other compatible banks (for example FA with DA, or MA with DA), subject to operand width, operation semantics and physical connectivity.

The pairing is a scheduling hint / allocation convention. It does not mean RA1 and DA1 become one physical register, nor does it mean that a register can only communicate with its paired index. Cross-index and cross-bank operations remain legal when supported by the ISA and hardware.

### 3.1 Four destination example

A single parallel operation group may contain two App-RAM-sourced moves to RA and two Data-RAM-sourced moves to DA:

```asm
; Illustrative group notation only — final syntax/encoding is OPEN
mov RA1,  [app_a] : DA1,  [data_a] :
    RA16, [app_b] : DA16, [data_b]
```

The group contains four architectural register writes:
- App RAM → RA1
- Data RAM → DA1
- App RAM → RA16
- Data RAM → DA16

That is **2 RA destinations + 2 DA destinations = 4 destination registers**. It is not four RA writes or four DA writes.

This group can complete in one cycle only if the effective App RAM and Data RAM service capacities, request queues, destination write ports and issue/commit rules can accept all four transfers. Otherwise the group may be split, partially progress under a defined independent-operation model, or be delayed. The exact rule is OPEN.

## 4. Parallel operation groups

The compiler may form groups of different sizes based on available resources and dependencies.

- A 2-operation group is the initial validation target.
- A 4-operation group is the next target, including the two-RA/two-DA example.
- Wider groups are allowed only when the issue mechanism, execution units, register ports and memory paths can support them.

Grouping is not the same as creating a new monolithic instruction. The preferred microarchitectural model is a group of independently tracked micro-operations that may issue or complete independently where the architecture allows it.

A group must not impose unnecessary head-of-line blocking: if one independent operation is waiting for a memory response or unavailable unit, another operation may proceed when the issue/retirement model and precise-state rules permit it.

## 5. Graph algorithms: use separate graphs for separate problems

“Graph coloring” is relevant, but it must not be treated as the entire parallel scheduler.

### 5.1 Register-allocation interference graph

The compiler builds a liveness/interference graph:
- each node represents a live value / virtual register;
- an edge connects two values that must be simultaneously live and therefore cannot occupy the same physical register;
- graph coloring assigns physical register numbers (colors) while respecting bank, width, alignment and reserved-register constraints.

Bank identity is a register class constraint. A value requiring an RA register cannot be colored into DA merely because the index is free. FP128 and ME512 pair alignment/adjacency constraints must also be respected.

### 5.2 Instruction dependency DAG

A separate dependency directed acyclic graph represents operation ordering:
- RAW: producer must precede consumer;
- WAR: earlier read must occur before a later overwrite where required;
- WAW: writes to the same architectural destination must preserve the defined order;
- memory dependencies: aliasing, ordering, atomicity and protection rules;
- control dependencies: branches, exceptions and side effects.

The scheduler may move or group operations only when it proves the transformation preserves architectural behavior.

### 5.3 Resource-conflict / compatibility graph

A further compatibility model determines whether ready operations can share an issue group:
- execution-unit class and remaining capacity;
- source-bank read demand;
- destination-bank write demand;
- App RAM and Data RAM path demand;
- memory queue / bank constraints;
- operand width and alignment;
- bypass and forwarding availability.

Graph coloring may be used for resource-slot assignment or conflict-free grouping, but a resource-aware list scheduler / matching algorithm may be more appropriate for cycle-by-cycle issue. The algorithm choice remains OPEN pending simulator experiments.

## 6. Compiler pipeline proposal

1. **Instruction classification:** identify operation class, source/destination banks, widths, memory domain and side effects.
2. **Liveness and register allocation:** construct the interference graph; allocate bank-constrained physical registers; apply logical 16+16 pairing as a heuristic, not a correctness rule.
3. **Dependency analysis:** build the instruction DAG with RAW/WAR/WAW, memory and control dependencies.
4. **Ready-set formation:** identify operations whose predecessors are satisfied.
5. **Resource matching:** match ready operations to existing INT, FP64, FMA, VEC and ME512 resources and to available bank/path capacity.
6. **Group formation:** form 2/4/wider groups only when compatible; prioritize independent cross-bank opportunities.
7. **Scheduling and emission:** emit legal issue groups or ordinary instructions according to the eventual ISA encoding.
8. **Fallback:** if a safe profitable group cannot be formed, preserve ordinary instruction sequence. Optimization must never be required for correctness.

The compiler may also use profile information and cost estimates, but correctness must not depend on profile data.

## 7. Operation families to evaluate

| Operation family | Candidate parallelism | Main constraints |
|---|---|---|
| MOV / register transfer | Multiple independent destinations; cross-bank pairs | Read/write ports, source paths, overlap |
| LOAD | Independent loads, including App/Data path overlap where legal | Address dependencies, aliasing, queue capacity |
| STORE | Independent stores | Memory ordering, aliasing, bank admission, atomicity |
| ADD / SUB / logic / shift | Independent scalar operations | INT lane capacity, register ports |
| MUL / DIV | Independent arithmetic | Unit class, latency and throughput |
| FP operations | Independent FP operations | FP64 lane capacity, operand width |
| FMA | Independent fused operations | Four dedicated FMA units; dependency latency |
| VEC | Independent vector operations | Two VEC units, MA bandwidth and width |
| ME512 / matrix | Independent matrix operations | Single ME512 unit and paired MA operands |

No instruction family is promised a fixed parallel count by this table. Actual grouping depends on resource availability and the finalized issue model.

## 8. Memory-path and partial-progress rules

App RAM and Data RAM are independent paths and controllers. They must not be collapsed into a shared queue or shared bandwidth budget.

However:
- instruction fetch from App RAM does not itself write an architectural RA register;
- an explicit App-RAM data/constant transfer to RA is a distinct operation and must be defined by ISA semantics;
- a Data-RAM load to DA is a distinct operation;
- simultaneous register writes require real write-port capability and conflict rules;
- a same-destination conflict must be serialized, rejected during grouping, or resolved by an explicitly specified architectural rule;
- different destinations do not by themselves prove that two writes can physically commit in one cycle.

For a multi-operation group, define whether each micro-operation can complete independently or whether the group has an all-or-none architectural commit. This must preserve precise exceptions and memory ordering. Do not assume atomic group commit merely because operations share a group.

## 9. Illustrative examples

### 9.1 Two-path dual move

```asm
; Illustrative syntax; not yet frozen
mov RA1, [app_a] : DA1, [data_a]
```

### 9.2 Four register writes (two RA + two DA)

```asm
; Illustrative group
mov RA1,  [app_a] : DA1,  [data_a] :
    RA16, [app_b] : DA16, [data_b]
```

### 9.3 Mixed execution resources

```asm
; Illustrative independent operations
add RA2,  RA3,  RA4
fma FA2,  FA3,  FA4, FA5
vadd MA2, MA3, MA4
```

The three operations may be scheduled together only if dependencies, register ports, issue capacity and the existing execution resources permit it.

## 10. Required validation matrix

| Test | Expected result |
|---|---|
| RA1 + DA1 logical pair | Pairing metadata does not merge physical registers |
| RA16 + DA16 logical pair | Second logical region works independently |
| Two App RAM → RA plus two Data RAM → DA moves | Correctly accounts for 2 RA + 2 DA writes |
| Same destination written twice | Conflict detected; no silent overwrite |
| RAW dependency inside candidate group | Consumer is not issued before producer value is available |
| WAR / WAW conflict | Required ordering preserved |
| App RAM delayed, Data RAM ready | Independent Data operation may progress if group semantics allow |
| Data RAM delayed, App RAM ready | Independent App operation may progress if group semantics allow |
| FP128 allocation | Even-indexed FA pair constraints preserved |
| ME512 allocation | Even-indexed MA pair constraints preserved |
| RA sub-width aliases | RB/RC/RD alias conflicts correctly tracked against RA |
| INT + FMA + VEC independent operations | Correct resource matching; no invented execution capacity |
| Memory alias / atomic operations | Ordering and atomicity preserved |
| Exception in one group member | Precise exception and architectural state preserved |
| No profitable pairing | Compiler emits correct ordinary instructions |

## 11. Open decisions — do not infer or freeze yet

1. Exact architectural and assembly syntax for multi-operation groups.
2. Whether group members issue independently or share an issue packet.
3. Whether a group may partially complete and how precise exceptions are represented.
4. Physical read/write port counts for RA, DA, FA and MA.
5. Cross-bank bypass / forwarding paths and latency.
6. Whether two App RAM sourced data transfers can be accepted concurrently by the same core connection, and under what bandwidth/queue constraints.
7. Exact 16+16 pairing policy: default heuristic, ABI convention, compiler allocation hint, or optional programmer-visible grouping.
8. Graph-coloring variant and whether resource scheduling uses coloring, bipartite matching, list scheduling, or a hybrid.
9. Cost model for deciding when grouping is beneficial versus added encoding/coordination cost.

## 12. Implementation roadmap

| Phase | Work | Completion evidence |
|---|---|---|
| CBP-1 | Canonical register-bank model and pair metadata | Unit tests for bank/index/width constraints |
| CBP-2 | Liveness and interference graph | Correct graph and register allocation tests |
| CBP-3 | Dependency DAG | RAW/WAR/WAW and memory-order regression tests |
| CBP-4 | Resource compatibility model | Capacity and conflict tests for existing units |
| CBP-5 | Two-operation cross-bank groups | Simulator tests for RA+DA |
| CBP-6 | Four-write group model | 2 RA + 2 DA acceptance/backpressure tests |
| CBP-7 | FA/FMA/VEC/MA integration | Mixed-unit scheduling tests |
| CBP-8 | Compiler emission and fallback | Differential correctness tests |
| CBP-9 | Performance study | Baseline vs grouped instruction/cycle/queue metrics |

## 13. Decision summary

**Selected direction:** flexible cross-bank scheduling, using logical 16+16 pairing as a compiler heuristic and supporting 2-, 4- or wider operation groups when proven legal and supported by existing resources.

**Not selected / not yet frozen:** fixed physical register partitions, mandatory pairing, new execution units, extra register-file ports, fixed issue width, final multi-operation syntax, or guaranteed same-cycle completion.

The first prototype should validate the two-path RA+DA case, then the four-destination case (two RA and two DA). Only after that should the model expand to FA/FMA/VEC/MA.
