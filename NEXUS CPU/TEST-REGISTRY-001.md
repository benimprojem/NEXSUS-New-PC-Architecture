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
| NEX-T001 | Architecture configuration contract | Simulator profile explicitly declares fixed per-core resources, cache sizes/groups, App RAM and Data RAM path capacities, and 8×64-bit bank-group baseline | VALID |
| NEX-T002 | Independent App RAM and Data RAM paths | Both paths operate concurrently; each core has 64 B/cycle on each path; 8-core aggregate capacity is 512 B/cycle per memory system; no shared 64 B/cycle bottleneck | VALID |
| NEX-T003 | Instruction path stage rates | App RAM→C0 16 B/cycle/core; C0→CS 20 B/cycle/core; CS→EB 20 B/cycle/core; EB consume 16 B/cycle/core; queueing and overlap are explicit | VALID |
| NEX-T004 | Data RAM bank and wide-access behavior | Per-core bandwidth contract, bank-group behavior, distinct-bank concurrency, same-bank conflicts, 128/256/512-bit accesses, stripe crossings and all-or-none admission | VALID |
| NEX-T005 | Cache topology and sharing | 8×L1, 4×L2, 2×L3, 1×L4 per eight-core block; cross-L3-group L4 access; no false private-L1 replication for shared sets | VALID |
| NEX-T006 | Execution resource issue and latency | INT=8, FP64=6, FMA=4, VEC=2, ME512=1 per core; independent issue throughput and dependency latency measured separately | VALID |
| NEX-T007 | Register-bank connectivity | RA/FA/DA/MA bank widths/counts, simultaneous reads, writeback conflicts, forwarding, pair accesses and ME512 result paths | VALID |
| NEX-T008 | Single-core controlled workloads | Scalar, integer, FP64, FMA, vector, ME512, branch, pointer and instruction-stream tests with operation-count invariants | VALID |
| NEX-T009 | 1/2/4/8-core scaling | Same logical work per experiment, independent per-core paths, active-core accounting, scaling and fairness | VALID |
| NEX-T010 | Mixed full-architecture workloads | Execution + registers + caches + App RAM + Data RAM under concurrent load; isolated and mixed runs | VALID |
| NEX-T011 | Cross-architecture comparison | Identical logical work; native and 8-core controlled mode; only core count, CPU clock and CPU-to-memory bandwidth normalized | VALID |\n| NEX-T012 | System Fabric 2× clock and time-interleaved scheduling | Two Fabric ticks per CPU cycle; destination queues progress without false shared-bus serialization; link bandwidth is not multiplied merely by clock ratio; fairness and backpressure are explicit | DEFERRED — final integrated-system phase |
| NEX-T013 | Instruction pipeline overlap | Continuous CodeFlow page delivery, EB ping-pong safety, registered stage rates and non-starving steady-state feed | VALID |
| NEX-T014 | Memory path contract | App RAM/Data RAM independence, per-core Data RAM service and cache-fill topology invariants | VALID |
| NEX-T015 | Dynamic RAC admission and distributed writeback | Shared 80R/64W logical pool, atomic reservations, age-prioritized work-conserving selection, physical bank conflicts, same-destination write rejection and parallel writes to distinct banks | VALID |
| NEX-T016 | Cycle-level RAC and 16-wide issue integration | Proves 16 backend issues/cycle when front-end/RAC permit it; mixed 16-op issue window exceeds 80R demand, so simulator caps reads at 80, reports RAC stalls, preserves all operations and stays within 64W | VALID |
| NEX-T017 | Cycle-level physical register-bank ports | Explicit RA/FA/DA/MA operand identities enforce configurable per-bank read/write ports; different banks proceed in parallel, same-bank port conflicts retry, same-cycle duplicate destinations serialize, and missing identity is rejected when physical-port mode is enabled | VALID |
| NEX-T018 | Physical register sub-bank mapping | Configurable bank count per RA/FA/DA/MA class; register index maps deterministically by index modulo bank count; per-sub-bank read/write limits, collisions, parallelism and MA512 paired-entry accesses are tested without freezing a default topology | IMPLEMENTED |

### 3.1 NEX-T001 implementation record

- Test file: `NEXUS CPU/tools/test_architecture_contract_t001.py`
- Profile source: `NEXUS CPU/tools/cpu_comparison_sim.py` → `PROFILES[\"nexus_balanced_128\"]`
- Profile fields added: per-core App/Data RAM bandwidth, 8-bank group counts, 64-bit bank slice, 512-bit group width, shared-Fabric declaration, and explicit cache sharing group sizes.
- Implementation commit: `3cf7a7262adcece9f1bb4f7d3d9ffcf3ce6616b6`
- Simulator profile commit: `217971918c7c06f18c49de6e05891b181b39fca0`
- Validation: **VALID** on CI run `44118299885` (commit `cc7d6fbc6f19644590ea87aaf8e0de9cc13eeb55`); the numbered architecture-contract test step and full workflow passed.
- Scope limitation: configuration declarations only. Runtime Data RAM service and Fabric arbitration remain for NEX-T002/NEX-T004.

### 3.2 NEX-T002 implementation record

- Test file: `NEXUS CPU/tools/test_fabric_memory_paths_t002.py`
- Runtime change: NEXSUS Data RAM misses now use `DataRamController`, with a separate 64 B/cycle/core Fabric-facing bandwidth timeline. Other CPU profiles retain the legacy shared-memory comparison model.
- App RAM remains on its separate `AppRamController` timeline.
- Data RAM controller commit: `b85e5113761f66eeaa94aa9a48efcdc752a65d20`
- Profile dataclass compatibility commit: `d2faac5049b99b56c464011a55c97f6954f837ba`
- Test commit: `1a957cb7cc2a4b5e24b55453d38f48d111317df3`
- CI workflow commit: `ffcff089969594180a03c60da709d636a936945c`
- Validation: **VALID** on CI run `44118299885` (commit `cc7d6fbc6f19644590ea87aaf8e0de9cc13eeb55`); both independent-path tests and the full workflow passed.
- Scope: validates core-facing link capacity and App/Data path independence. It deliberately does not claim that one 8×64-bit physical bank group can satisfy all eight cores simultaneously. Total bank-group count/placement, physical port replication, and multi-client Fabric arbitration/QoS remain open for NEX-T004 and follow-up tests.

### 3.7 NEX-T007 MA/RAC footprint extension

- Extended test file: `NEXUS CPU/tools/test_register_bank_t007.py`
- New coverage: 80R/64W logical per-core RAC baseline; conversion of each 256-bit MA entry to four 64-bit logical slots; 512-bit pair conversion; vector, VMACC, VSUM, VDOT, MMUL, MMAC, MTRANS and MREDUCE operand-footprint formulas; supported tile-shape limits.
- Supporting model: `NEXUS CPU/tools/register_bank_model.py`
- Supporting model commits: `b6535a14bcdda9f0dc8e38c1e48b4816049f0e11`, `242995d61ddcfba7fac76dea857f7da74b5a54d5`
- Test commits: `6527b55c7e51416a4b394bac27a4a822667210c9`, `fe10201d9f262d2555a1ec310d31027c03ce3c00`
- Validation: **VALID** for the MA footprint/accounting extension on CI run [45440385306](https://github.com/benimprojem/NEXSUS-New-PC-Architecture/actions/runs/45440385306), commit `fe10201d9f262d2555a1ec310d31027c03ce3c00`. The numbered contract and regression-test steps passed; a later unrelated FMA-latency workflow assertion failed because it expected an outdated JSON field name.
- Scope limitation: validates total MA tile footprints and the provisional one-512-bit-slice-per-operand-per-cycle RAC arithmetic. Dynamic RAC arbitration and physical RF banking/replication are covered separately by NEX-T015 and still require cycle-level integration/timing validation.

### 3.8 NEX-T015 dynamic RAC allocator

- Allocator: `NEXUS CPU/tools/rac_allocator.py`
- Test file: `NEXUS CPU/tools/test_rac_allocator_t015.py`
- Contract: one shared per-core 80R/64W logical 64-bit slot pool across RA/FA/DA/MA and CPU-originated workspace requests; physical bank ports remain independent, explicit implementation parameters.
- Required behavior: complete instruction footprints are granted atomically; different banks may write in parallel; same-destination multiwrite is rejected; a physical bank conflict must not waste available capacity in another bank; age-prioritized waiting requests are retried.
- Implementation commits: `9296508920d7cc2fdbb0d2f597742630b5040936`, `9c1c425533ed0b9ff216e952b7cf2e867de4cc79`, `c54e58bfdbcaa183376c628f98dff2b9b8507f3f`
- Validation: **VALID** on CI run [45441039124](https://github.com/benimprojem/NEXSUS-New-PC-Architecture/actions/runs/45441039124), commit `c54e58bfdbcaa183376c628f98dff2b9b8507f3f`; numbered contract tests and full regression-test step passed. The remaining full-workflow sweeps are separate validation stages.
- Scope limitation: this is the logical admission/arbitration model; it does not yet model SRAM macro timing, replica placement, bypass-network delay, or integrated cycle-level execution.

### 3.9 NEX-T016 cycle-level RAC integration

- Simulator: `NEXUS CPU/tools/cpu_comparison_sim.py`
- Regression test: `NEXUS CPU/tools/test_cpu_comparison_sim.py` → `RACCycleIntegrationTests`
- NEXSUS profile: issue=16, RAC=80R/64W per core per cycle; reference profiles leave RAC limits disabled.
- Default per-op slot accounting covers scalar INT/ARITH/LOGIC/CMP/FP, FMA, vector widths, LOAD/STORE/ATOM and workspace operations. Unusual ME512 opcodes can provide explicit read/write slot overrides; default MMAC uses a 512-bit per-operand slice.
- Required proof: the mixed 16-op test requests 86R/37W in its first issue window; at most 80R/64W are admitted in one cycle, blocked instructions retry, and all operations eventually complete. The test raises front-end/dispatch to 16 to isolate backend issue/RAC behavior; the selected integrated profile remains front-end=8/dispatch=8, so this test does not claim sustained 16 IPC.
- Implementation commit: `f73305e0682c6416fff52222f73ef89f37ded4c2`
- Test commits: `97103182204f3f3c648965359b6026f9bc92ca31`, `2de57083fa5f37b688d70e384e76869ae13e0a3c`
- Issue-peak instrumentation commit: `1aa13f142da8a9e75dbf71bd66db5344c3bd9ae9`
- Validation status: **IMPLEMENTED — the new explicit 16-issue peak assertion is awaiting CI**. The earlier aggregate RAC cap test passed the regression suite on CI run `45442320176`; the expanded T016 scope must be revalidated.
- Scope limitation: aggregate logical slot budgeting is integrated. Physical bank-port conflicts, exact register destination identity and distributed writeback timing remain modeled by NEX-T015 or follow-up integrated-cycle tests.

### 3.10 NEX-T017 cycle-level physical register-bank ports

- Simulator: `NEXUS CPU/tools/cpu_comparison_sim.py`
- Regression tests: `NEXUS CPU/tools/test_cpu_comparison_sim.py` → `RACCycleIntegrationTests`
- Explicit `(class, register_index, 64-bit_slot_width)` metadata is required when physical-port mode is enabled.
- Legacy per-register-class physical port maps remain available; no default physical port counts are frozen.
- Validation: **VALID** on CI run [45470623199](https://github.com/benimprojem/NEXSUS-New-PC-Architecture/actions/runs/45470623199); all workflow steps passed.
- Scope limitation: this version models one physical bank group per register class. NEX-T018 adds sub-bank mapping; actual SRAM macro topology, replication, bypass and writeback timing remain open.

### 3.11 NEX-T018 physical register sub-bank mapping

- Simulator parameters: `rac_physical_bank_counts`, `rac_physical_read_ports_per_bank`, and `rac_physical_write_ports_per_bank`.
- Mapping: `physical_subbank = register_index % bank_count`, independently within RA/FA/DA/MA. One operand entry consumes one physical port; its 64-bit logical slot width is separately charged to the 80R/64W RAC.
- Legacy NEX-T017 class-level port maps remain supported for compatibility.
- Tests cover distinct-sub-bank parallelism, same-sub-bank conflict/retry with progress in another class, missing class mapping rejection, and 512-bit MA paired entries using two physical entries/eight logical slots.
- No bank count or per-bank port count is selected as the architecture default. This configurable mapping is not a claim about final SRAM macro implementation.
- Status: **IMPLEMENTED — awaiting CI**.

### 3.10 NEX-T017 cycle-level physical register-bank ports

- Simulator: `NEXUS CPU/tools/cpu_comparison_sim.py`
- Regression tests: `NEXUS CPU/tools/test_cpu_comparison_sim.py` → `RACCycleIntegrationTests`
- New operation metadata: explicit `rac_read_accesses` and `rac_write_accesses`, each containing `(bank, register_index, 64-bit_slot_width)`.
- Physical port maps are optional profile parameters, separate from the shared logical 80R/64W budgets. No default physical port counts are frozen.
- Tests cover four-bank parallel read/write, same-bank read-port collision with retry and cross-bank progress, duplicate same-cycle destination serialization, and mandatory explicit register identity when physical-port mode is enabled.
- Implementation commit: `3301d67b9166e3701db87bc8f67eabac930200a1`
- Test commit: `c48818df61ce165e661f82a1919567f68f2a8db6`
- Validation status: **IMPLEMENTED — awaiting CI**.
- Scope limitation: physical ports are configurable model constraints; actual SRAM macro port topology, replication, bypass and writeback timing are not selected.

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
- NEX-T001 through NEX-T011 are VALID;
- all compared workloads pass operation-count and dependency checks;
- per-core and aggregate bandwidth accounting is explicit in every report;
- no test uses a shared aggregate 64 B/cycle Data RAM bus for the eight-core NEXSUS block;
- frontend stage rates match the current decision register;
- the exact commit and CI run are recorded.

## 8. Change log

- 2026-11-17: Initial registry created. Existing test files and reports are retained as historical records. New architecture-contract tests NEX-T001 through NEX-T011 are planned.
- 2026-11-17: Initial T011 CI run 44133980360 passed technically, but its controlled-mode assumptions were rejected after architecture-owner clarification: it incorrectly normalized NEXSUS DataRAM down to 32 B/cycle aggregate and forced common memory latency. That comparison result is INVALIDATED; T011 is being corrected. The 37-kernel logical operation-count invariant remains useful.


### 3.3 NEX-T003 implementation record

- Test file: `NEXUS CPU/tools/test_instruction_path_rates_t003.py`
- Simulator change: `CommandFetchModel` defaults and NEXSUS profile construction now use C0→CS = 20 B/cycle/core and CS→EB = 20 B/cycle/core, matching the Architecture Decision Register.
- Test verifies the separate 64-B/cycle AppRAM link, the 16-B/cycle AppRAM→C0 and EB stage rates, and both 20-B/cycle middle stages using a 2-KiB page service-time calculation.
- Implementation commits: simulator `70a1cfd02a75519348b4528cef05b7b3712af9b2`; test `19c9b9fb78783d3c67fddc7edc254ad2bee99f78`.
- Validation status: **VALID** on CI run `44094128217` (commit `843e92d30ed6bdab7f7ec3c6659941a04a1c2ddc`); all 37 workflow steps completed successfully.
- Scope limitation: this validates the registered stage-rate contract and the stated 2-KiB service-time calculation. Multi-page queue overlap and detailed EB drain timing are explicitly not claimed as validated by this rate-contract test.


### 3.4 NEX-T003 validation record

- CI run: [44094128217](https://github.com/benimprojem/NEXSUS-New-PC-Architecture/actions/runs/44094128217)
- Validated commit: `843e92d30ed6bdab7f7ec3c6659941a04a1c2ddc`
- Result: all workflow steps passed, including numbered architecture contract tests, regressions, comparison smoke test, and existing design-space sweeps.
- T003 is marked **VALID** only for its explicit stage-rate contract and calculation scope; it does not certify detailed multi-page frontend overlap.
- NEX-T012 is intentionally deferred until the final integrated-system phase, per the current testing sequence. CPU tests proceed with System Fabric assumed operational.


### 3.5 NEX-T004 implementation record

- Model: `NEXUS CPU/tools/data_ram_bank_model.py` — isolated one-group bank scheduler using the approved 8 × 64-bit bank baseline and 8-byte interleave.
- Test: `NEXUS CPU/tools/test_data_ram_bank_t004.py`.
- Covered: 64/128/256/512-bit width-to-slice mapping; distinct-bank concurrent service; same-bank local serialization; naturally aligned wide access crossing a 64-byte stripe; folded-selector 64-byte-stride distribution; validation-before-commit for all-or-none wide admission.
- Model service assumption: one 64-bit bank beat per cycle, configurable as a model parameter; this is not a silicon measurement or a new architecture decision.
- Scope boundary: one bank group only. Total physical group count/placement, physical ports, queue depth, cross-client arbitration/QoS and System Fabric internals are not inferred or tested here. System Fabric is assumed operational during this CPU test phase.
- Implementation commits: model `3b1aa2e1bd080dc1a57d8d1a8171eb02006d3ec2`; tests `b3e5f57d04a82c567086f044e1bcac3c0d77a503`.
- Validation: **VALID** on CI run `44096831765` (commit `d2f097319a2f43411aa3003de84af3f6b2475079`); all 37 workflow steps passed, including T001–T004, regression tests and the existing comparison/benchmark smoke stages.


### 3.6 NEX-T004 validation record

- CI run: [44096831765](https://github.com/benimprojem/NEXSUS-New-PC-Architecture/actions/runs/44096831765)
- Validated commit: `d2f097319a2f43411aa3003de84af3f6b2475079`
- Result: all workflow steps passed. The numbered architecture contract step, full regression suite, comparison smoke test, and all existing benchmark/sweep steps completed successfully.
- T004 is **VALID** for the isolated 8-bank group behavior covered by its test. This does not establish total physical group count/placement or Fabric arbitration behavior.


### 3.7 NEX-T005 implementation record

- Test file: `NEXUS CPU/tools/test_cache_topology_t005.py`.
- Existing model under test: `build_cache_hierarchies()` and `CacheHierarchy` in `NEXUS CPU/tools/cpu_comparison_sim.py`; no cache topology or architecture capacity values were changed.
- Covered: eight distinct private L1s; four pair-shared L2s; two four-core-shared L3s; one eight-core-shared L4; registered per-instance capacities (1/2/4/8/64 MiB); cross-L3-group lookup through shared L4; private L1 isolation.
- Scope limitation: this validates object topology, capacity and lookup visibility. It does not claim a cache-coherence protocol, replacement policy beyond the existing LRU model, port count, bandwidth, transfer latency, or System Fabric behavior.
- Test commit: `47f36e88b6038133e58ab500811df568a0ad7738`.
- Validation: **VALID** on CI run `44099666476` (workflow commit `28508c5b6a753ec5f902880025b6a941a70389ef`); all workflow steps passed, including numbered architecture contract tests, regression tests, comparison smoke test, and existing sweeps.
- Scope limitation: validates cache instance topology, configured capacities, shared-L4 lookup visibility and private-L1 isolation only; cache timing, ports, bandwidth, coherence and Fabric are not validated.


### 3.8 NEX-T005 validation record

- CI run: [44099666476](https://github.com/benimprojem/NEXSUS-New-PC-Architecture/actions/runs/44099666476)
- Validated workflow commit: `28508c5b6a753ec5f902880025b6a941a70389ef`
- Result: all workflow steps passed.
- T005 is **VALID** within the scope stated in section 3.7.


### 3.9 NEX-T006 implementation record

- Test file: `NEXUS CPU/tools/test_execution_resources_t006.py`.
- CI integration: added to the numbered architecture-contract test step in `.github/workflows/nexus-cpu-simulator.yml`.
- Covered: per-core INT8 / FP64-6 / FMA4 / VEC2 / ME512-1 resource counts; FMA as a subset of FP64 lanes; vector opcode routing to VEC; separate independent-issue and dependency-chain workloads for VEC and ME512; 128-bit INT pair reservation.
- Workload invariants: VEC independent stream 256 ops and dependency chain 64 ops; ME512 independent stream and dependency chain 128 ops each. Tests assert all operations retire and dependency chains take longer than independent issue streams.
- Test commit: `744fe1264248eb219746c3a4b3545c84680415c5`.
- CI integration commit: `cc7d6fbc6f19644590ea87aaf8e0de9cc13eeb55`.
- Validation: **VALID** on CI run `44118299885` (commit `cc7d6fbc6f19644590ea87aaf8e0de9cc13eeb55`); all 75 workflow steps completed successfully, including the numbered T001–T006 contract tests, full regression, VEC/ME512 isolation, comparison suites, scaling tests and benchmark artifact generation.
- Scope limitation: issue/latency behavior is validated under the execution-only backend isolation. Register-file port contention, register-bank connectivity and forwarding remain NEX-T007; System Fabric internals remain deferred to NEX-T012.


### 3.10 NEX-T001 / T002 / T006 validation consolidation

- CI run: [44118299885](https://github.com/benimprojem/NEXSUS-New-PC-Architecture/actions/runs/44118299885)
- Validated commit: `cc7d6fbc6f19644590ea87aaf8e0de9cc13eeb55`
- Result: all 75 workflow steps passed. The numbered contract step explicitly executed T001, T002, T003, T004, T005 and T006; the full regression and downstream comparison/sweep steps also passed.
- T001 and T002 are now **VALID** within their recorded configuration-contract and independent core-facing memory-path scopes. This does not close physical bank-group placement, port replication, or Fabric arbitration/QoS questions.
- T006 is now **VALID** within its execution-resource routing, independent issue, dependency-latency and 128-bit INT pair-reservation scope. Register-file connectivity and forwarding remain NEX-T007.


### 3.11 NEX-T007 implementation record

- Model: `NEXUS CPU/tools/register_bank_model.py` — logical RA/FA/DA/MA bank organization, RA low-width aliases, even-indexed paired access, explicit cycle access checks and optional forwarding.
- Test: `NEXUS CPU/tools/test_register_bank_t007.py`.
- Covered: 32×64-bit RA/FA/DA banks; 32×256-bit MA bank; 1,792-byte architectural payload; RB/RC/RD aliases; FP128 even FA pair; ME512 even MA pair; simultaneous cross-bank reads/writes; configurable read/write-port conflict checks; explicit read-first versus forwarding behavior; no partial write commit on port-budget rejection.
- Important boundary: physical port counts, bank replication, cross-unit physical wiring, forwarding timing and writeback arbitration policy remain OPEN. The test uses explicit port budgets as test parameters and does not select a hardware port count.
- Model commit: `8955257c77dfb0e96ea57fc039f5e0b01a36895d`.
- Test commit: `4f0a6bcc664049116a4b6d973a186c5456b305c1`.
- CI integration commit: `44120384150` run head; validation commit `44120384150`.
- Validation: **VALID** on CI run `44120384150`; all 75 workflow steps passed, including T001–T007, full regression, comparison/sweep suite, scaling tests and benchmark artifact generation.


### 3.12 NEX-T007 validation record

- CI run: [44120384150](https://github.com/benimprojem/NEXSUS-New-PC-Architecture/actions/runs/44120384150)
- Result: all 75 workflow steps completed successfully.
- T007 is **VALID** within the logical register-bank organization, pair access, explicitly parameterized port-conflict and optional forwarding semantics recorded in section 3.11. Physical port count and implementation timing remain OPEN.


### 3.13 NEX-T008 implementation record

- Test: `NEXUS CPU/tools/test_single_core_workloads_t008.py`.
- Workload suite: existing deterministic `build_composite_workload(scale=1)` traces, run one workload at a time with `core_count=1`.
- Covered categories: scalar/control flow, integer ALU, FP64, FMA, 512-bit vector, ME512, branch stress, dependent pointer graph and sequential instruction-stream/CS starvation.
- Invariants: each workload exists and is non-empty; exactly one core is configured and active; retired operation count equals source trace length; cycle and issue-span counts are positive. Instruction-stream case additionally requires CodeFlow refills, useful bytes and wait cycles to be observed.
- Features: Task Workspace disabled; Code Slots/CodeFlow enabled for the instruction-delivery test path. This is a controlled single-core CPU test, not a Fabric integration test.
- CI integration: compile and numbered test steps added to `.github/workflows/nexus-cpu-simulator.yml`.
- Validation: **VALID** on CI run [44124177964](https://github.com/benimprojem/NEXSUS-New-PC-Architecture/actions/runs/44124177964), head commit `d72ff68b428284d5020d106e1cb482abe587e019`; all 75 workflow steps passed, including compile, numbered contract tests, regressions, comparison smoke test and existing sweep/artifact stages.\n- Scope limitation: validates controlled single-core workload execution and operation-count/cycle invariants only. It does not establish multicore scaling, fairness or full mixed-resource contention; those remain T009/T010.
\n\n### 3.14 NEX-T008 validation record\n\n- CI run: [44124177964](https://github.com/benimprojem/NEXSUS-New-PC-Architecture/actions/runs/44124177964)\n- Validated commit: `d72ff68b428284d5020d106e1cb482abe587e019`\n- Result: simulator job completed successfully; all 75 workflow steps passed.\n- T008 is **VALID** within the single-core controlled workload and operation-count scope in section 3.13.\n

### 3.15 NEX-T009 implementation record

- Test: `NEXUS CPU/tools/test_core_scaling_t009.py`.
- Core counts: 1, 2, 4 and 8, using the same deterministic workload revision and exact operation count at every count.
- Covered: independent integer work distribution across all configured cores; streaming DataRAM accounting by core; separate CodeFlow/AppRAM accounting; per-core 64 B/cycle capacity and aggregate 64×active-core capacity on both memory paths.
- Fairness/accounting invariant: streaming DataRAM bytes must be attributed to every active core, and the sum of per-core bytes must equal controller transferred bytes. This test does not select physical bank-group count, placement, ports or Fabric arbitration policy.
- AppRAM and DataRAM remain separate controllers and are checked independently. No shared aggregate 64 B/cycle bus is introduced.
- CI integration: compile and numbered architecture-contract steps added to `.github/workflows/nexus-cpu-simulator.yml`.
- Validation: **VALID** on CI run [44127684525](https://github.com/benimprojem/NEXSUS-New-PC-Architecture/actions/runs/44127684525), head commit `a2e917ce894e57efbf497a7b4f91c8678db8f0fb`; all 75 workflow steps passed, including numbered tests, regressions, comparisons and benchmark artifact generation.\n- Scope limitation: validates simulator accounting and workload scaling across 1/2/4/8 cores. It does not validate physical silicon behavior, final System Fabric 2× clock/time-interleaving, or unspecified physical bank placement/arbitration details.


### 3.16 NEX-T009 validation record

- CI run: [44127684525](https://github.com/benimprojem/NEXSUS-New-PC-Architecture/actions/runs/44127684525)
- Validated commit: `a2e917ce894e57efbf497a7b4f91c8678db8f0fb`
- Result: simulator job completed successfully; all 75 workflow steps passed.
- T009 is **VALID** within the 1/2/4/8-core workload scaling and per-core AppRAM/DataRAM accounting scope in section 3.15.


### 3.17 NEX-T010 implementation record

- Test: `NEXUS CPU/tools/test_mixed_resource_stress_t010.py`.
- One combined eight-core operation stream includes numeric tile loads/stores, streaming DataRAM traffic, FP64+FMA, 512-bit vector work, ME512 matrix operations, mixed VEC/ME512 memory overlap, atomic contention, IRQ/context work and CodeFlow instruction-stream stress.
- The test preserves each component's dependency graph while remapping operation sequence IDs into one stream. The simulator executes this combined stream once; all assertions inspect the same run.
- Required checks: exact operation retirement; eight active cores; both independent memory controllers make progress in the same run; AppRAM and DataRAM each retain 64 B/cycle/core and 512 B/cycle aggregate at eight cores; per-core transferred-byte accounting sums exactly to each controller's total; CodeFlow refills and data DRAM accesses occur; execution-unit blocking is observable.
- This validates simulator-level simultaneous mixed-resource pressure only. It does not establish physical silicon behavior, physical bank-group placement/port count, finalized Fabric arbitration/QoS, or the deferred 2× clock/time-interleaving integration.
- CI integration: compile and numbered architecture-contract steps added to `.github/workflows/nexus-cpu-simulator.yml`.
- Status: **VALID** on CI run [44130763148](https://github.com/benimprojem/NEXSUS-New-PC-Architecture/actions/runs/44130763148), validated commit `3bf482f81f09e105eadabbbeabd543b8e0a47d58`; the complete simulator workflow finished with `success`, including numbered tests, regressions, comparison smoke test, design-space sweeps, scaling comparisons and full benchmark-table generation/artifact upload.
- Scope limitation: confirms the mixed workload's simulator assertions and the workflow's generated benchmark artifacts. It does not validate physical silicon, System Fabric internals, physical bank-group placement/ports or Fabric arbitration/QoS. System Fabric is assumed operational for the CPU test phase; no Fabric integration test is being run now.
- No architecture resource counts, clock values or bandwidth values were changed.


### 3.18 NEX-T011 implementation record

- Test: `NEXUS CPU/tools/test_cross_architecture_comparison_t011.py`.
- Comparison generator: `NEXUS CPU/tools/generate_full_architecture_benchmark.py`.
- Required comparison policy: identical logical workload; controlled mode uses eight cores, 3.0 GHz CPU clock and 64 B/cycle/core CPU-to-data-memory bandwidth (512 B/cycle aggregate).
- Only those three comparison dimensions are normalized. Memory latency, cache topology/capacity, execution resources, instruction delivery and all other architecture-specific properties remain as each architecture defines them.
- NEXSUS DataRAM remains at its native 64 B/cycle/core and 512 B/cycle aggregate. Reference profiles use a 512 B/cycle aggregate data-memory interface in the controlled mode. No 32 B/cycle override is permitted.
- The initial T011 implementation and artifact from CI run [44133980360](https://github.com/benimprojem/NEXSUS-New-PC-Architecture/actions/runs/44133980360) are **INVALIDATED for controlled comparative conclusions** because they forced 32 B/cycle aggregate bandwidth and 120-cycle latency. Its full CI success is retained as a historical software pass, not an architecture-valid comparison.
- Corrected T011 test verifies eight-core/3.0-GHz normalization, 512 B/cycle aggregate CPU-memory interface for all profiles, native NEXSUS per-core accounting, equal operation counts, and no forced common memory latency.
- CI integration remains in the numbered architecture test stage after T010.
- Artifact audit on CI run [44140530099](https://github.com/benimprojem/NEXSUS-New-PC-Architecture/actions/runs/44140530099) confirmed all 37 kernels have identical logical operation counts and the controlled mode uses 8 cores, 3.0 GHz and 512 B/cycle aggregate for all four profiles. It also exposed a reporting-only defect: the NEXSUS native profile's top-level aggregate DataRAM field was 64 even though its per-core controller capacity was 64 B/cycle/core and eight-core aggregate capacity was 512 B/cycle.
- Reporting correction: simulator commit `c887b86d5a64873b6270196c797ebac8b0ed853d` sets NEXSUS aggregate DataRAM metadata to 512 B/cycle and exposes the 64 B/cycle/core value separately; T011 assertions added in commit `a10f9a582802c1e812935cd7c33d42fc0c291b8c`. This changes metadata only; the per-core DataRamController behavior and all architecture resource settings remain unchanged.
- The first metadata-correction CI run [44143714199](https://github.com/benimprojem/NEXSUS-New-PC-Architecture/actions/runs/44143714199) passed the numbered architecture-contract tests but exposed six stale assertions in the legacy regression suite that still treated 64 B/cycle as NEXSUS aggregate bandwidth. Those assertions were updated to the approved 64 B/cycle/core and 512 B/cycle eight-core contract in commit `316507e427b745b5672558a1db4450236f8aeb7a`; no architecture values were reduced.
- Final validation: **VALID** on CI run [44143949931](https://github.com/benimprojem/NEXSUS-New-PC-Architecture/actions/runs/44143949931), validated commit `316507e427b745b5672558a1db4450236f8aeb7a`; all workflow steps passed, including compile, numbered architecture tests, full regression, comparison smoke test, design-space sweeps, 1/2/4/8-core scaling and benchmark artifact generation/upload.
- Final artifact: `nexus-cpu-comparison-results` (artifact ID `14357670191`). Audit of `full-architecture-results.json/.md` confirms 37 kernels with identical logical operation counts across all four profiles. In controlled mode all profiles use 8 cores, 3.0 GHz and 512 B/cycle aggregate; NEXSUS separately reports 64 B/cycle/core. Native NEXSUS metadata also reports 64 B/cycle/core and 512 B/cycle aggregate.
- Controlled-mode diagnostic totals (sum across 37 separate kernels; not a single-program score): AMD 56,561 cycles / 18.854 µs / IPC 0.431; Intel 68,732 / 22.911 µs / 0.355; Apple 51,080 / 17.027 µs / 0.477; NEXSUS 39,112 / 13.037 µs / 0.623.
- The controlled comparison normalizes only core count, CPU clock and CPU-to-data-memory bandwidth. Architecture-specific cache, memory latency, execution resources and instruction delivery remain distinct. Results are simulator estimates, not physical silicon measurements.
- T011 status: **VALID** within the simulator comparison and artifact-audit scope above. T012 System Fabric integration remains deferred; Fabric was assumed operational and no Fabric integration test was run.
- T012 System Fabric integration remains deferred; Fabric is assumed operational for this CPU comparison phase.
