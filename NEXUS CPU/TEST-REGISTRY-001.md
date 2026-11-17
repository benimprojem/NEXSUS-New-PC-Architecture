# NEXSUS CPU — Test Registry 001

**Document ID:** NEXSUS-CPU-TEST-REGISTRY-001  
**Created:** 2026-11-17  
**Purpose:** Permanent index of historical and new architecture tests. No test file or result is deleted when a test is superseded.

## 1. Rules

1. Every new test receives a permanent ID: `NEX-T001`, `NEX-T002`, and so on. IDs are never reused.
2. Historical tests receive `LEGACY-L001`, `LEGACY-L002`, etc. Their source files and artifacts remain untouched.
3. A test is **VALID** only when its assumptions match the active Architecture Decision Register, its expected invariants are explicit, its operation counts are verified, and the test passes on a recorded commit.
4. **PASS** means the test passed on the recorded revision; it does not imply that the simulator is physically validated.
5. **INVALIDATED** means its assumptions conflict with a later approved decision or a defect was found. Keep its file, result, and reason.
6. **SUPERSEDED** means a newer test replaces it. Keep the old test and link the replacement.
7. Never compare performance results from different test IDs, workload revisions, architecture revisions, or simulator revisions as if they were the same experiment.
8. Every benchmark record must include: test ID, architecture-register revision, simulator commit, workload ID/revision, core count, per-core and aggregate bandwidth assumptions, clock/latency assumptions, feature flags, operation count, result artifact, and CI run.
9. Record both absolute cycles/time and normalized ratios. Lower time/cycles is better; higher throughput/IPC/speedup/efficiency is better.
10. Never rank architectures by adding unrelated kernel times. Compare like-for-like workloads separately.
11. Preserve all old test scripts, reports, workflow artifacts, and commits. Do not rename or delete them as part of this rebuild.

## 2. Status vocabulary

| Status | Meaning |
|---|---|
| PLANNED | Test is specified but not implemented |
| IMPLEMENTED | Test code exists but has not passed validation |
| VALID | Passed with assumptions aligned to the current decision register |
| FAILED | Ran with valid assumptions but failed an assertion |
| INVALIDATED | Test assumptions/model are inconsistent with an approved architecture decision |
| HISTORICAL | Retained for traceability; validity not yet re-established |
| SUPERSEDED | Replaced by a newer test; historical record retained |

## 3. New test series

These tests are designed from the architecture contract upward. Implement them in order; do not begin comparative performance ranking until the foundational tests are VALID.

| ID | Test scope | Required proof | Initial status |
|---|---|---|---|
| NEX-T001 | Architecture configuration contract | Simulator profile explicitly declares fixed per-core resources, cache sizes/groups, App RAM and Data RAM path capacities, and 8×64-bit bank-group baseline | IMPLEMENTED |
| NEX-T002 | Independent App RAM and Data RAM paths | Both paths operate concurrently; each core has 64 B/cycle on each path; 8-core aggregate capacity is 512 B/cycle per memory system; no shared 64 B/cycle bottleneck | IMPLEMENTED |
| NEX-T003 | Instruction path stage rates | App RAM→C0 16 B/cycle/core; C0→CS 20 B/cycle/core; CS→EB 20 B/cycle/core; EB consume 16 B/cycle/core; queueing and overlap are explicit | PLANNED |
| NEX-T004 | Data RAM bank and wide-access behavior | Per-core bandwidth contract, bank-group behavior, distinct-bank concurrency, same-bank conflicts, 128/256/512-bit accesses, stripe crossings and all-or-none admission | PLANNED |
| NEX-T005 | Cache topology and sharing | 8×L1, 4×L2, 2×L3, 1×L4 per eight-core block; cross-L3-group L4 access; no false private-L1 replication for shared sets | PLANNED |
| NEX-T006 | Execution resource issue and latency | INT=8, FP64=6, FMA=4, VEC=2, ME512=1 per core; independent issue throughput and dependency latency measured separately | PLANNED |
| NEX-T007 | Register-bank connectivity | RA/FA/DA/MA bank widths/counts, simultaneous reads, writeback conflicts, forwarding, pair accesses and ME512 result paths | PLANNED |
| NEX-T008 | Single-core controlled workloads | Scalar, integer, FP64, FMA, vector, ME512, branch, pointer and instruction-stream tests with operation-count invariants | PLANNED |
| NEX-T009 | 1/2/4/8-core scaling | Same logical work per experiment, independent per-core paths, active-core accounting, scaling and fairness | PLANNED |
| NEX-T010 | Mixed full-architecture workloads | Execution + registers + caches + App RAM + Data RAM under concurrent load; isolated and mixed runs | PLANNED |
| NEX-T011 | Cross-architecture comparison | Only after T001–T010 foundations are valid; identical logical work and documented, defensible peer assumptions | PLANNED |\n| NEX-T012 | System Fabric 2× clock and time-interleaved scheduling | Two Fabric ticks per CPU cycle; destination queues progress without false shared-bus serialization; link bandwidth is not multiplied merely by clock ratio; fairness and backpressure are explicit | PLANNED |

### 3.1 NEX-T001 implementation record

- Test file: `NEXUS CPU/tools/test_architecture_contract_t001.py`
- Profile source: `NEXUS CPU/tools/cpu_comparison_sim.py` → `PROFILES[\"nexus_balanced_128\"]`
- Profile fields added: per-core App/Data RAM bandwidth, 8-bank group counts, 64-bit bank slice, 512-bit group width, shared-Fabric declaration, and explicit cache sharing group sizes.
- Implementation commit: `3cf7a7262adcece9f1bb4f7d3d9ffcf3ce6616b6`
- Simulator profile commit: `217971918c7c06f18c49de6e05891b181b39fca0`
- Execution status: not yet run in CI; therefore **IMPLEMENTED**, not VALID.
- Scope limitation: configuration declarations only. Runtime Data RAM service and Fabric arbitration remain for NEX-T002/NEX-T004.

### 3.2 NEX-T002 implementation record

- Test file: `NEXUS CPU/tools/test_fabric_memory_paths_t002.py`
- Runtime change: NEXSUS Data RAM misses now use `DataRamController`, with a separate 64 B/cycle/core Fabric-facing bandwidth timeline. Other CPU profiles retain the legacy shared-memory comparison model.
- App RAM remains on its separate `AppRamController` timeline.
- Data RAM controller commit: `b85e5113761f66eeaa94aa9a48efcdc752a65d20`
- Profile dataclass compatibility commit: `d2faac5049b99b56c464011a55c97f6954f837ba`
- Test commit: `1a957cb7cc2a4b5e24b55453d38f48d111317df3`
- CI workflow commit: `ffcff089969594180a03c60da709d636a936945c`
- Execution status: queued for CI; therefore **IMPLEMENTED**, not VALID.
- Scope: validates core-facing link capacity and App/Data path independence. It deliberately does not claim that one 8×64-bit physical bank group can satisfy all eight cores simultaneously. Total bank-group count/placement, physical port replication, and multi-client Fabric arbitration/QoS remain open for NEX-T004 and follow-up tests.

### 3.3 NEX-T012 architecture definition\n\n- Architectural decision: System Fabric clock = 2× CPU core clock.\n- Scheduling model: two Fabric scheduling ticks are available per CPU cycle; requests may be time-interleaved across destination queues.\n- The model must distinguish scheduler opportunity from physical link bandwidth and destination service capacity.\n- Required tests: two-tick cadence; alternating destinations; same-destination queue contention; independent destination progress; backpressure; fairness under sustained mixed traffic; no implicit 2× link-bandwidth multiplier.\n- Execution status: **PLANNED**. Exact lane width, queue depth, multi-client arbitration, and destination service curves remain open.\n\n## 4. Historical test files — retained, not yet re-certified

The following files existed before this registry. They are not deleted, renamed, or silently treated as valid. Their historical outputs remain useful for regression analysis, but each must be mapped to a new test ID and re-run where relevant.

| Legacy ID | Existing file | Historical scope | Current status |
|---|---|---|---|
| LEGACY-L001 | `NEXUS CPU/tools/test_cpu_comparison_sim.py` | Core simulator regression tests | HISTORICAL |
| LEGACY-L002 | `NEXUS CPU/tools/test_core_scaling_comparison.py` | 1/2/4/8-core scaling comparison | HISTORICAL |
| LEGACY-L003 | `NEXUS CPU/tools/test_app_ram_contention_sweep.py` | App RAM contention | HISTORICAL |
| LEGACY-L004 | `NEXUS CPU/tools/test_app_ram_multicore_fairness_sweep.py` | App RAM multi-core fairness | HISTORICAL |
| LEGACY-L005 | `NEXUS CPU/tools/test_branch_latency_sweep.py` | Branch latency sensitivity | HISTORICAL |
| LEGACY-L006 | `NEXUS CPU/tools/test_l0i_px_pipeline_sim.py` | Legacy instruction pipeline model | HISTORICAL |
| LEGACY-L007 | `NEXUS CPU/tools/test_nexus_naming_standard.py` | Naming convention | HISTORICAL |
| LEGACY-L008 | `NEXUS CPU/tools/test_p0p1_branch_redirect_sim.py` | Legacy P0/P1 branch redirect | HISTORICAL |
| LEGACY-L009 | `NEXUS CPU/tools/test_p0p1_command_buffer_sim.py` | Legacy command-buffer model | HISTORICAL |
| LEGACY-L010 | `NEXUS CPU/tools/test_p0p1_l0i_px_bottleneck_sweep.py` | Legacy frontend bottleneck sweep | HISTORICAL |
| LEGACY-L011 | `NEXUS CPU/tools/test_p0p1_l0i_px_integrated_sim.py` | Legacy integrated frontend model | HISTORICAL |
| LEGACY-L012 | `NEXUS CPU/tools/test_p0p1_l0i_px_integrated_sweep.py` | Legacy integrated frontend sweep | HISTORICAL |
| LEGACY-L013 | `NEXUS CPU/tools/test_p0p1_l0i_px_middle_sweep.py` | Legacy middle-stage sweep | HISTORICAL |
| LEGACY-L014 | `NEXUS CPU/tools/test_p0p1_l0i_px_refined_sweep.py` | Legacy refined frontend sweep | HISTORICAL |
| LEGACY-L015 | `NEXUS CPU/tools/test_p0p1_l0i_px_workload_sweep.py` | Legacy frontend workload sweep | HISTORICAL |
| LEGACY-L016 | `NEXUS CPU/tools/test_p0p1_refill_sweep.py` | Legacy refill sensitivity | HISTORICAL |
| LEGACY-L017 | `NEXUS CPU/tools/test_target_prefetch_overlap_sweep.py` | Target/prefetch overlap | HISTORICAL |
| LEGACY-L018 | `NEXUS CPU/tools/test_wrong_path_cleanup_sweep.py` | Wrong-path cleanup | HISTORICAL |

## 5. Historical benchmark/report records

These records must be preserved and treated as historical until their assumptions are audited against the current architecture contract.

| Record | Location | Note |
|---|---|---|
| Architecture decision register | `NEXUS CPU/NEXSUS-CPU-ARCHITECTURE-DECISION-REGISTER-001.md` | Current authority for approved decisions |
| Core scaling report | `NEXUS CPU/reports/CORE_SCALING_COMPARISON_REPORT.md` | Historical comparison; not a new baseline |
| Full architecture benchmark | `NEXUS CPU/NEXSUS-CPU-FULL-ARCHITECTURE-BENCHMARK-001.md` | Audit assumptions before reuse |
| Cross-architecture results | `NEXUS CPU/NEXSUS-CPU-CROSS-ARCHITECTURE-RESULTS-001.md` | Audit assumptions before reuse |
| Simulation results | `NEXUS CPU/NEXSUS-CPU-SIMULATION-RESULTS-001.md` | Historical simulator output |
| SPM/P0 ablation results | `NEXUS CPU/NEXSUS-CPU-SPM-P0-ABLATION-RESULTS-001.md` | Legacy naming/model; preserve |

## 6. Initial audit findings

The following are audit findings, not architecture changes:

- The active architecture decision register now specifies 64 B/cycle/core App RAM and 64 B/cycle/core Data RAM, therefore 512 B/cycle aggregate for each memory system in an eight-core block.
- The existing cross-architecture scaling script uses aggregate shared DRAM budgets of 32 B/cycle or 4 B/cycle/core equivalent. It does not represent the NEXSUS Data RAM contract of 64 B/cycle/core. Its NEXSUS Data RAM performance rows must therefore not be used as valid architecture-comparison evidence.
- The simulator's current `SharedMemoryController` is a shared aggregate controller. It must be replaced or parameterized so each core-facing path can sustain 64 B/cycle while the System Fabric arbitrates access to fabric-attached bank groups; do not mistake the shared physical memory pool for one shared 64 B/cycle CPU bus.
- The current NEXSUS instruction frontend model defaults C0→CS and CS→EB to 8 B/cycle in `CommandFetchModel` construction, despite the architecture register's current simulator operating point of 20 B/cycle. This mismatch must be tested and corrected before frontend performance results are accepted.
- The minimum App RAM and Data RAM bank-group baseline is clarified as 8 banks × 64 bit (512 bit / 64 B per group). This is eight 64-bit banks, not 64 banks. Total group count/placement across the shared System Fabric, bank mapping, physical ports, and multi-client arbitration/QoS remain OPEN.
- App RAM's per-core connection capacity (64 B/cycle) and the App RAM→C0 refill-stage rate (16 B/cycle) are separate serial stages; they must not be collapsed into one number.
- The cache hierarchy instance grouping in the simulator currently matches the registered 8×L1 / 4×L2 / 2×L3 / 1×L4 eight-core topology. Port count, bandwidth, and latency are still open/provisional and must not be inferred from instance count.

## 7. Acceptance gate

No new cross-architecture performance ranking is accepted until:
- NEX-T001 through NEX-T007 are VALID;
- all compared workloads pass operation-count and dependency checks;
- per-core and aggregate bandwidth accounting is explicit in every report;
- no test uses a shared aggregate 64 B/cycle Data RAM bus for the eight-core NEXSUS block;
- frontend stage rates match the current decision register;
- the exact commit and CI run are recorded.

## 8. Change log

- 2026-11-17: Initial registry created. Existing test files and reports are retained as historical records. New architecture-contract tests NEX-T001 through NEX-T011 are planned.
