# NEXSUS CPU — Final Cross-Architecture Comparison (2026-11-14)

## Scope

This report records the final comparison run at commit `63ce89beddb2c139dd31d1e65976ae16330a2c4f`.

- Eight configured cores for each model.
- Same normalized logical workload: **22,382 operations per architecture**.
- Reference profiles: AMD Ryzen 9 9950X3D2 (4.3 GHz), Intel Xeon 698X (2.0 GHz), Apple M6 12-core ARM SoC (heterogeneous approximation, modeled at 3.0 GHz), and NEXSUS (3.0 GHz).
- Lower cycle count is better within the simulator.
- These are **simulator estimates**, not measurements of retail CPUs or NEXSUS silicon.

## Final normalized 8-core results

Values are simulated cycles. Each row runs the same logical operation count on all four profiles.

| Workload | AMD 9950X3D2 | Intel Xeon 698X | Apple M6 | NEXSUS |
|---|---:|---:|---:|---:|
| Scalar control | 154 | 154 | 154 | 170 |
| Pointer graph | 8,673 | 10,833 | 7,233 | 8,689 |
| Numeric tile | 428 | 388 | 303 | 342 |
| Streaming | 1,323 | 566 | 644 | **552** |
| Parallel tasks | 336 | 361 | 265 | 312 |
| INT throughput | 49 | 44 | 44 | 57 |
| INT128 throughput | 41 | 39 | 39 | 65 |
| FP64 throughput | 51 | 52 | 51 | 62 |
| FMA throughput | 51 | 52 | 51 | 67 |
| FMA dependency chain | 801 | 1,057 | 801 | 817 |
| FP + FMA mixed | 51 | 52 | 51 | 67 |
| Vector throughput | 51 | 51 | 56 | 66 |
| ME512 matrix | 738 | 462 | **412** | 420 |
| Atomic contention | 250 | 214 | 175 | 200 |
| IRQ / exception stress | 62 | 64 | 58 | 68 |
| Branch stress | 118 | 140 | 120 | **83** |
| Task Workspace hot set | 9,697 | 11,425 | 8,289 | **2,097** |
| Task Workspace capacity sweep | 32,545 | 39,457 | 26,913 | **16,945** |
| Code Slot sequential | 97 | 87 | 87 | **81** |
| Code Slot branch | 289 | 289 | 289 | **208** |
| Code Slot working set | 161 | 129 | 129 | **113** |
| Code Slot starvation | 289 | 279 | 279 | **225** |

### What the comparison says

**NEXSUS is already strong in the areas its architecture is designed to improve:**

- Streaming: 552 cycles, narrowly ahead of Intel's 566.
- Task Workspace hot set: 2,097 cycles, versus 8,289–11,425 on the reference profiles.
- Task Workspace capacity sweep: 16,945 cycles, versus 26,913–39,457.
- Code Slot tests: NEXSUS leads all four cycle-count comparisons.
- Branch stress: 83 cycles, clearly the lowest modeled cycle count.

**General execution throughput is not caught up yet:**

- INT, INT128, FP64, FMA and vector throughput remain slower in cycle counts than the best reference result.
- Numeric tile and parallel tasks are behind Apple M6.
- ME512 matrix is close to Apple M6 (420 vs 412 cycles), but does not lead.
- Pointer-graph and dependent FMA tests remain latency-sensitive; the wider issue topology does not remove dependency-chain latency.

The configured clocks differ, so raw cycles are not elapsed time. A simple frequency-adjusted estimate (cycles / configured GHz) still shows the clearest NEXSUS advantage in streaming and Task Workspace. It does not turn the general-purpose arithmetic results into a win. This conversion is only a profile-level estimate, not a measured wall-clock benchmark.

## Data RAM MSHR capacity decision

Two eight-core workloads were swept with capacities of 1, 2, 4, 8, 16, 32, 64 and 128 entries **per core**.

### Independent cold LOAD saturation

1,024 cold LOADs total (128 per core):

| MSHR / core | Cycles | Full core-cycles | Blocked retries |
|---:|---:|---:|---:|
| 1 | 15,369 | 121,920 | 7,795,200 |
| 2 | 7,692 | 60,490 | 3,864,290 |
| 4 | 3,854 | 29,781 | 1,899,544 |
| 8 | 1,936 | 14,308 | 910,560 |
| 16 | 984 | 6,692 | 423,360 |
| 32 | 520 | 2,980 | 184,704 |
| 64 | 312 | 1,316 | 69,888 |
| 128 | 256 | 0 | 0 |

### Mixed compute + LOAD

Per core: 128 cold LOADs interleaved with 384 independent INT operations (4,096 operations total):

| MSHR / core | Cycles | Max outstanding | Full core-cycles |
|---:|---:|---:|---:|
| 1 | 15,376 | 1 | 121,948 |
| 2 | 7,696 | 2 | 60,500 |
| 4 | 3,858 | 4 | 29,788 |
| 8 | 1,942 | 8 | 14,442 |
| 16 | 991 | 16 | 6,799 |
| 32 | **531** | 32 | 0 |
| 64 | 531 | 32 | 0 |
| 128 | 531 | 32 | 0 |

**Decision: use 32 Data RAM MSHR entries per core as the current baseline.**

The mixed workload reaches its maximum outstanding count at 32 and gains nothing from 64 or 128. The all-LOAD saturation test does benefit from 64/128, but it represents a deliberately extreme memory-level-parallelism case. Keep 64 as a future high-throughput option if real workloads justify its area and power; do not spend the extra resources on 128 as the default.

This MSHR pool is **per core**. The shared Data RAM bank/bus controller remains separate from it. App RAM has its own independent controller and request path.

## Confirmed execution topology

The tested NEXSUS configuration remains:

- INT: 8 lanes
- FP64: 6 lanes
- Dedicated FMA: 4 lanes (within the FP execution resources)
- VEC: 2 lanes
- ME512: 1 unit

The FMA sweep also confirmed that more FMA issue capacity improves independent FMA throughput, but does not shorten a dependent FMA chain. That is a latency/dependency limit, not simply a lane-count shortage.

## Validation status

CI run [43623509695](https://github.com/benimprojem/NEXSUS-New-PC-Architecture/actions/runs/43623509695) completed successfully at the commit above.

Passed stages include:

- Simulator compilation and regression suite (79 tests).
- Comparison smoke test and combined cross-architecture + CodeFlow suite.
- Task Workspace / Code Slots ablation.
- Normalized eight-core comparison with equal operation counts.
- INT/FP execution topology and resource-count sweeps.
- FP64 / FMA resource sweep.
- Data RAM MSHR cold-load and mixed compute/LOAD sweeps.
- Branch predictor, Code Slot capacity and instruction-fetch latency sensitivity sweeps.

## Model limitations

The simulator is a comparative architecture model, not RTL or a cycle-accurate implementation of the commercial processors. Reference CPU cache behavior is approximated; the Apple profile is a heterogeneous-CPU approximation; cache coherence and several OS/runtime effects are not modeled. Therefore these results identify architectural strengths, bottlenecks and next experiments. They do not establish that NEXSUS is faster than the named commercial CPUs in real applications.

## Current conclusion

The memory split, independent App RAM and Data RAM controllers, execution topology, Task Workspace and Code Slot/CodeFlow mechanisms are now covered by integrated regression and comparative tests. The clearest architectural gains are in code/data locality and streaming behavior. General-purpose arithmetic throughput, pointer-heavy latency and dependency chains remain the main gaps.

**Next phase should be RTL-oriented modeling and workload realism, not another arbitrary increase in execution lanes or MSHR capacity.**
