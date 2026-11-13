# NEXSUS CPU — Full-System Simulator Architecture

**Document ID:** NEXSUS-CPU-SIMULATOR-ARCHITECTURE-001  
**Status:** Simulator design proposal; timing and baseline profiles are configurable, not hardware claims  
**Scope:** Functional and cycle-level behavioral simulation of NEXSUS CPU, plus a fair conventional-CPU comparison framework

## 1. Goal

Build a reproducible simulator that executes the same algorithmic workloads on:
1. a configurable conventional/reference CPU model; and
2. the NEXSUS CPU model.

The simulator reports correctness, execution cycles, throughput, latency, memory traffic, bank conflicts, stalls, energy estimates (only when a defensible energy model is supplied), and system overheads such as task switches and interrupts.

The simulator is not an RTL simulator, transistor-level MOSRAM model, or proof of achievable silicon frequency. It is a configurable architectural/microarchitectural behavioral model. Later it may be calibrated against RTL, FPGA, SPICE/TCAD or measured hardware.

## 2. Fair-comparison rule

Both CPUs must execute the same workload with:
- identical input data and initial state;
- identical algorithm and output requirements;
- identical numeric precision and correctness tolerance;
- equivalent memory-capacity and data-residency constraints;
- equivalent task count, synchronization requirements and completion conditions;
- disclosed, configurable hardware assumptions.

Do not compare a fully optimized NEXSUS workload against an intentionally scalar or artificially constrained reference CPU.

The reference CPU is a **parameterized conventional CPU profile**, not a claim to reproduce a named commercial processor. It must support selectable scalar and SIMD/vector capabilities, issue width, out-of-order window, execution latencies, cache/memory hierarchy, branch prediction and memory ports. A specific commercial CPU profile may be added later only when public or measured parameters are available.

Where a workload uses NEXSUS ME512, the reference profile must be allowed to use its configured SIMD/vector path (for example 256-bit or 512-bit vectors where selected). Where NEXSUS benefits from multiple independent execution units, the reference profile must likewise expose its configured execution resources. Report both the default profile and sensitivity sweeps.

## 3. Two simulation layers

### 3.1 Functional architectural layer

This layer answers: **Does the program produce the correct result?**

It models:
- NEXSUS architectural registers RA/FA/DA/MA and their views/pairs;
- ISA instruction semantics and precise faults;
- P0 command-buffer/refill behavior at the architectural boundary;
- SPM0–SPM7 roles, ownership and access permissions;
- App RAM and Data RAM address spaces;
- L1–L4 domain permissions, ownership and visibility;
- task architectural state and context save/restore;
- synchronous exceptions, asynchronous IRQs and event delivery;
- memory operations, ATOM, FENCE and MEMXFER semantics.

The reference CPU has its own architectural register/ISA adapter, but consumes the same architecture-neutral workload representation.

Functional execution must be deterministic for a fixed workload and configuration. The functional layer is the correctness oracle for the timing layer.

### 3.2 Cycle-level behavioral layer

This layer answers: **How many modeled cycles and resources does execution require?**

It models, as configurable resources:
- fetch, decode, dispatch and issue;
- P0 refill and App RAM bank groups;
- register-bank read/write ports and dependency/forwarding rules;
- ALU, FPU and ME512 pipelines;
- AGU and memory request queues;
- L1–L4 domains and physical bank groups;
- per-bank queues, local arbitration, port direction and turnaround;
- wide-access parent/child tracking and all-or-none multi-bank admission;
- SPM access bandwidth/latency;
- task switch, context save/restore and SPM residency;
- IRQ pending/acceptance, exception entry/exit and handler execution;
- Fabric/MEMXFER traffic and transfer completion.

A modeled cycle is a simulation time quantum, not a promise that a future chip clock runs at a particular GHz.

## 4. Workload representation: one algorithm, two CPU backends

Do not hand-write two different optimized algorithms. Define a common workload representation (initially a small architecture-neutral operation graph / trace format) containing:
- integer, floating-point and vector arithmetic;
- loads, stores and address dependencies;
- branches and loop structure;
- task creation, synchronization and data exchange;
- memory working sets and access patterns;
- optional IRQ/event injection points.

The same workload graph is translated by two backend adapters:
- Reference CPU adapter;
- NEXSUS CPU adapter.

Each adapter may choose legal implementation instructions, but must preserve the workload's observable semantics. Record generated operation counts and transformations so vectorization or fusion is visible rather than hidden.

A later phase may add native compilers and run the same source language through two code-generation backends. The first simulator milestone must not depend on a completed compiler.

## 5. Reference CPU profile

The initial reference model is configurable and intentionally generic. It should provide at least:
- scalar integer and floating-point execution;
- selectable SIMD width and number of vector pipelines;
- configurable decode/issue/retire width;
- configurable in-order or out-of-order scheduling;
- configurable reorder/issue window and dependency handling;
- branch predictor and misprediction penalty;
- register-file and load/store port limits;
- configurable L1/L2/L3 or unified cache/memory latency/bandwidth;
- memory bank/port contention;
- task/interrupt overhead.

The first comparison must publish a complete reference parameter table. Unknown values must be labeled assumptions and swept over a range. Do not label this profile “Intel”, “AMD” or a particular generation.

## 6. NEXSUS CPU model inputs

The NEXSUS backend must read architecture parameters from versioned configuration, not hard-code speculative values in the simulator.

The initial architectural resource map includes:
- RA0–RA31, FA0–FA31, DA0–DA31 and MA0–MA31;
- 2 ALUs, at least 2 FPUs and one ME512 per core as the current baseline proposal;
- P0 64-bit command records and 512-bit peak refill interface target;
- SPM0 2 KiB; SPM1–SPM7 8 KiB each with their defined roles and permissions;
- separate App RAM and Data RAM paths;
- L1 private 128 KiB/core, L2 shared per 2 cores 1 MiB, L3 shared per 4 cores 8 MiB, L4 shared per 8+ cores 64 MiB as current proposed capacities;
- 8 banks × 64-bit per bank group as a recommended topology baseline, not physical freeze;
- local bank queues and all-or-none multi-bank admission;
- existing task context residency and IRQ/exception architecture.

Where latency, port counts, queue depth, clock ratio, pipeline width or service weights are not finalized, keep them configurable and mark them as assumptions.

## 7. Workload suite

The benchmark suite must contain different bottleneck classes. Initial workloads:

| ID | Workload | Primary behavior measured |
|---|---|---|
| W01 | Scalar integer loop | ALU issue, dependencies, branch and fetch |
| W02 | Floating-point vector loop | FPU throughput and SIMD/vector mapping |
| W03 | 256/512-bit vector transform | ME512 utilization versus reference SIMD |
| W04 | Matrix multiply / tiled matrix kernel | compute throughput, data reuse and memory traffic |
| W05 | Sequential memory scan/copy | bank bandwidth and read/write turnaround |
| W06 | Strided and random memory access | bank conflicts, queueing and latency |
| W07 | Mixed compute + memory | overlap of execution and memory paths |
| W08 | Producer/consumer across cores | synchronization, shared domains and visibility |
| W09 | Task-switch stress | SPM context residency and Data RAM save/restore |
| W10 | IRQ/exception stress | interrupt latency, frame save/restore and handler overhead |
| W11 | MEMXFER bulk movement | chunking, reservations, arbitration and completion |
| W12 | Mixed multi-task system load | scheduler, QoS, fairness and aggregate throughput |

Every workload has a scalar correctness oracle and fixed input seeds. Report warm-up and cold-start cases separately where relevant.

## 8. Metrics and reporting

At minimum report:
- output correctness and fault behavior;
- total simulated cycles and modeled time;
- instructions/operations issued, completed and retired;
- IPC and per-unit utilization;
- dependency, issue, queue-full, bank-conflict and port-turnaround stall cycles;
- App RAM fetch stalls and P0 refill efficiency;
- Data RAM and L1–L4 bytes read/written;
- per-bank service and conflict histograms;
- wide-access assembly/commit delay;
- task-switch and context save/restore cycles;
- IRQ arrival-to-handler and handler-to-return latency;
- MEMXFER accepted/completed latency and throughput;
- fairness/starvation metrics under mixed traffic.

Report per-workload results and aggregate results. Do not collapse all workloads into one score without showing the component metrics.

Energy and power are optional until calibrated per operation, memory access, interconnect transfer and idle state. An uncalibrated energy number must never be presented as measured power.

## 9. Validation strategy

Validation proceeds in stages:

1. **Unit tests:** each instruction, register view, bank mapping, queue, arbitration class, fault and state transition.
2. **Functional conformance:** reference calculations verify every workload result.
3. **Deterministic trace tests:** same inputs/configuration produce identical event traces.
4. **Cycle-model invariants:** no lost/duplicated request, no partial architectural wide-LOAD commit, no illegal permission bypass, no starvation under declared fairness assumptions.
5. **Differential tests:** both CPU backends produce identical observable outputs.
6. **Sensitivity sweeps:** vary uncertain pipeline, memory, queue, vector and branch parameters.
7. **Calibration:** compare model outputs with RTL/FPGA/physical measurements when those exist.

A failed test must identify workload, cycle/event, operation, address/domain where applicable, expected state and observed state.

## 10. Simulator implementation plan

Build the simulator incrementally:

- **Phase A — Shared workload IR and deterministic runner:** workload definitions, input generation, correctness oracle, event log and result schema.
- **Phase B — Functional reference CPU:** scalar execution and memory semantics.
- **Phase C — Functional NEXSUS CPU:** ISA/register/SPM/memory/fault behavior.
- **Phase D — Timing engine:** discrete-event or cycle-stepped resource scheduler; start with explicit cycle steps for deterministic arbitration.
- **Phase E — NEXSUS microarchitecture:** P0, execution units, SPM, bank controller, App/Data RAM, L1–L4.
- **Phase F — System behavior:** tasks, context residency, IRQ/exception and MEMXFER/Fabric.
- **Phase G — Reference timing model:** conventional pipeline, SIMD, cache/memory, branch and task/IRQ behavior.
- **Phase H — Comparative benchmark runner:** paired runs, parameter sweeps, CSV/JSON outputs and plots.
- **Phase I — Calibration and refinement:** replace assumptions with measured/validated values.

Do not attempt to implement all blocks in one monolithic script. Use independent modules with explicit interfaces and a common event/metrics schema.

## 11. Proposed repository layout

```
NEXUS CPU/
  simulator/
    README.md
    configs/
      nexsus_baseline.json
      reference_baseline.json
    core/
      event.py
      workload_ir.py
      runner.py
      metrics.py
      memory.py
      scheduler.py
    models/
      reference/
      nexsus/
    workloads/
    tests/
    reports/
  tools/
    bank_mapping_model.py
```

The final directory and filenames must use ASCII-safe names; the conceptual placeholders above are not a frozen package API. Configuration files must clearly distinguish architectural facts, accepted proposals and tunable assumptions.

## 12. Comparison integrity rules

- Same workload, inputs, precision, output checks and task semantics.
- Both models get legal scalar and vector optimization opportunities.
- No assumed NEXSUS memory latency or clock frequency without a stated scenario.
- Publish low/base/high sensitivity cases for unresolved parameters.
- Separate single-core, multi-core, compute-bound, memory-bound and system-overhead results.
- Show raw metrics and configuration alongside any speedup ratio.
- A speedup is meaningful only when correctness passes and the compared resource assumptions are disclosed.

## 13. Immediate next step

Before implementing the timing engine, freeze the first simulator configuration schema and a small shared workload IR. Then implement W01 scalar integer loop end-to-end on both functional backends. This creates the first verified comparison path before adding vector, memory and system complexity.
