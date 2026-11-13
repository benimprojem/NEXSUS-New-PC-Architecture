# NEXSUS CPU Memory Bank Topology Specification

**Document ID:** NEXSUS-CPU-MEMORY-BANK-TOPOLOGY-001  
**Status:** Architecture baseline proposal; physical implementation parameters remain open  
**Scope:** App RAM and Data RAM bank grouping, data-lane width, interleaving, concurrency and throughput model

---

## 1. Purpose

This document defines a CPU-facing physical bank organization that connects the existing NEXSUS CPU data widths and MOSRAM 64-bit sense-block model to a scalable memory topology.

The document distinguishes the following concepts:

- **Memory domain (L1–L4):** logical access, sharing, ownership and visibility scope.
- **Controller:** accepts and schedules requests for a memory resource.
- **Bank group:** a set of physical banks that can operate independently and expose an aggregate data path.
- **Physical bank:** independently serviceable memory array/sense/write resource.
- **Bank slice:** the local data width delivered by one bank for one access beat.
- **Port:** the physical/logical path through which a bank accepts reads or writes.
- **Fabric lane:** interconnect capacity between system nodes; it is not a RAM bank or a bank slice.

A domain may map to multiple bank groups. A bank group is not a new L1–L4 domain and does not change NDC visibility or ownership rules.

## 2. Existing CPU and MOSRAM constraints

The topology must support the existing CPU contracts:

- App RAM is the instruction source and feeds P0 through an independent fetch path.
- Data RAM is physically separate and serves data LOAD/STORE, task payload and protected context-frame accesses.
- App RAM and Data RAM have independent controllers/access paths and may operate concurrently.
- P0 uses 64-bit command words and has a peak fetch interface target of 512 bits (eight words) per fetch beat; this is not a promise of eight retired instructions per cycle.
- CPU LOAD/STORE supports 8/16/32/64/128/256/512-bit widths. Wide loads/stores may be split into internal beats without changing their single architectural instruction semantics.
- MA registers are 256-bit; ME512 is a 512-bit execution datapath and may use an MA pair.
- MOSRAM's physical study models a 64-bit parallel sense block and explores 4×64 and 8×64 aggregate structures. Those are physical read-block targets, not proof that a bank must equal one 64-bit block.

The selected baseline therefore aligns one 8-bank group with a 512-bit aggregate data path.

## 3. Recommended baseline: 8 banks × 64 bits

**Recommended CPU-facing baseline: one bank group contains eight independently serviceable physical banks, each exposing a 64-bit local data slice.**

| Parameter | Baseline |
|---|---:|
| Banks per group | 8 |
| Local bank read slice | 64 bit (8 byte) |
| Aggregate group width | 512 bit (64 byte) |
| Interleave granule | 8 byte |
| Bytes represented by one complete 8-bank stripe | 64 byte |
| Independent full-width 512-bit aligned transfer | One 64-byte stripe across all 8 banks |
| Smaller aligned transfer | Uses the corresponding 1/2/4 bank slices |
| Additional capacity | Add bank groups; do not widen the local 64-bit slice by default |

This is the best starting balance for the current CPU because the aggregate group width matches the 512-bit maximum CPU data operation and P0 fetch interface target. It also keeps the physical read slice aligned with the existing MOSRAM 64-bit sense-block study.

The eight-bank count is a **per-group baseline**, not a claim that the entire App RAM or Data RAM contains only eight physical banks. Larger capacities and more concurrent request streams may use multiple groups/controllers.

## 4. Why eight banks rather than four or sixteen?

| Candidate | Aggregate width at 64-bit/bank | Main advantage | Main limitation | Assessment |
|---|---:|---|---|---|
| 4 banks | 256 bit | Lower area, routing and control cost | A 512-bit access needs multiple group beats or multiple groups | Valid compact implementation, but under-matches the current 512-bit path |
| **8 banks** | **512 bit** | Matches 512-bit CPU/P0 data path; supports 1/2/4/8-bank aligned transfers | Requires eight active sense/write slices and careful routing | **Recommended baseline** |
| 16 banks | 1024 bit | More independent requests or two 512-bit aggregates if paths are duplicated | Higher area, power, routing and controller complexity; CPU issue demand not yet frozen | Defer until AGU/port throughput measurements justify it |

A 16-bank organization is not rejected. It is a future scaling option, especially where a controller serves multiple CPU cores or where two independent 512-bit groups are proven useful. It should not be selected merely because more banks appear faster on paper.

## 5. Address interleaving

### 5.1 Base striping

The base mapping distributes each consecutive 8-byte word to a different bank:

```
byte address:  0..7    8..15   16..23  24..31  32..39  40..47  48..55  56..63
bank:            0       1       2       3       4       5       6       7
```

Thus:

- 64-bit aligned access uses one bank slice.
- 128-bit aligned access uses two bank slices.
- 256-bit aligned access uses four bank slices.
- 512-bit access aligned to a 64-byte stripe uses all eight bank slices.

For a naturally aligned 512-bit access, all eight bank slices can contribute to the same aggregate transfer. Smaller widths use only the required slices. The ISA's existing alignment and fault rules remain authoritative; an access that crosses the stripe boundary may be split or scheduled over additional beats as the implementation requires.

### 5.2 Bank selector candidate

The simplest selector is the three-bit word index:

```
bank = (address >> 3) & 0b111
```

This is a useful baseline for sequential striping, but a pure low-bit selector can send every 64-byte-stride access to the same bank. The preferred simulator candidate is therefore a folded selector:

```
bank = A[5:3] XOR A[8:6] XOR A[11:9]
```

Here A is the translated physical/domain-relative byte address used by the target controller. This preserves distribution across the eight banks within each 64-byte stripe while allowing higher address bits to rotate the bank assignment between stripes.

The folded selector is a **candidate mapping, not a frozen ISA-visible rule**. Simulator results must compare at least:
1. low-bit sequential striping;
2. folded/XOR striping;
3. selected stride patterns (8, 16, 32, 64, 128 and 4 KiB bytes);
4. random and multi-stream accesses.

The final selector may be chosen independently for App RAM and Data RAM if their physical organizations differ. Software-visible addresses and NDC semantics must not depend on the selected physical bank hash.

### 5.3 Deterministic mapping comparison

The first architectural mapping model treats each independent 64-bit LOAD as one request to the bank selected by its byte address. For a batch of eight requests, it reports:

- **unique banks:** number of banks receiving at least one request;
- **per-bank count:** number of requests assigned to each bank;
- **minimum service rounds:** maximum per-bank request count, assuming one 64-bit request beat per bank per round and no other bottleneck.

This is a bank-conflict lower-bound model. It does not model cycle timing, queue depth, read/write turnaround, wide-operation grouping, ECC, refresh, Fabric delay or physical MOSRAM behavior.

The reproducible script is [tools/bank_mapping_model.py](tools/bank_mapping_model.py). It runs deterministic self-tests before printing the comparison table. With eight requests and base address zero, the current model produces:

| Byte stride | Low-bit unique banks | Low-bit min rounds | Folded unique banks | Folded min rounds |
|---:|---:|---:|---:|---:|
| 8 | 8 | 1 | 8 | 1 |
| 16 | 4 | 2 | 8 | 1 |
| 32 | 2 | 4 | 8 | 1 |
| 64 | 1 | 8 | 8 | 1 |
| 128 | 1 | 8 | 8 | 1 |
| 4096 | 1 | 8 | 1 | 8 |

Interpretation:

1. Sequential 8-byte words already distribute perfectly under both selectors.
2. The folded selector improves the tested 16/32/64/128-byte strides by mixing higher address bits into the bank index.
3. The folded selector does **not** solve every alias pattern. In particular, the tested 4-KiB stride still maps all eight requests to one bank because the current XOR uses only A[11:3].
4. A more complex hash is not automatically better. Any candidate must be evaluated against realistic address traces, page/region boundaries, multi-stream offsets and App RAM versus Data RAM access patterns.
5. The table is specific to eight 64-bit requests at base address zero. Changing the base address, request count or address distribution can change the result.

The next mapping evaluation must include multiple base offsets and simultaneous streams, then compare conflict histograms rather than selecting a hash from a few favorable strides. The current folded selector remains a simulator candidate only.

### 5.4 Width, alignment, multi-stream and random-trace model

The mapping script now models each architectural request as a byte range. It converts that range into the set/count of intersected 64-bit bank words, then aggregates bank demand for a simultaneous batch.

This keeps two different cases separate:

- **One wide request:** a 512-bit request uses eight 64-bit slices when it is aligned to the 64-byte stripe. It is one architectural request, not eight independent CPU instructions.
- **Many independent requests:** eight 64-bit requests can be serviced in one idealized round only if they map to eight banks with available ports/resources. Repeated bank assignments create local contention.

The model sweeps 8/16/32/64/128/256/512-bit request widths at byte offsets 0 and 1. Offset 1 is a physical mapping stress case only; it does not declare byte-misaligned wide accesses legal. Existing ISA natural-alignment and precise-fault rules remain authoritative. A byte-misaligned 512-bit range intersects nine 64-bit words, which can demand one bank twice under the simple low-bit selector. An implementation may reject such an access before bank issue if the ISA alignment rule requires it.

It also runs:
- eight simultaneous 64-bit requests across the configured stride set;
- a deterministic random-address sweep (default seed 20261113, 1,000 batches, eight streams);
- a separate App RAM 512-bit P0 refill and Data RAM scalar/vector batch.

App RAM and Data RAM results are reported independently. Their service rounds are not added together because the architecture defines separate physical paths/controllers. This model does not assert that every bank supports a simultaneous read and write, nor does it model cross-bank request assembly latency.

Run the model from the repository root:

```sh
python "NEXUS CPU/tools/bank_mapping_model.py"
```

Useful parameter overrides:

```sh
python "NEXUS CPU/tools/bank_mapping_model.py" --base 0x1000 --requests 8
python "NEXUS CPU/tools/bank_mapping_model.py" --random-samples 5000 --random-streams 4 --seed 42
python "NEXUS CPU/tools/bank_mapping_model.py" --widths 64,128,256,512 --strides 8,64,4096
```

The reported minimum rounds are an ideal bank-demand lower bound, not cycle-accurate latency. Real service depends on port topology, queueing, arbitration/QoS, address translation, ECC, refresh, Fabric transport and physical timing.

## 6. App RAM code-fetch path

App RAM serves application instructions and is physically/logically independent from Data RAM. The current baseline code path is:

```text
App RAM -> L0I (64 KiB) -> PX P0–P7 (8 x 2 KiB) -> SPM0 (4 KiB; 2 x 2 KiB)
```

- The App RAM -> L0I connection is one 64-bit (8-byte) read lane. One transfer beat carries one 64-bit instruction word.
- The initial design uses one read lane only. Four independent 64-bit lanes (256-bit aggregate) are a future expansion and require additional ports/routing/arbitration.
- L0I is filled progressively in task-aware chunks. It does not wait for a complete 64 KiB refill.
- The OS selects task/logical-page requests and priorities. Consecutive logical pages may reside at non-contiguous App RAM addresses.
- L0I -> PX transfers selected logical 2 KiB pages according to OS requests, not a sequential physical-address scan.
- PX -> SPM0 uses the dual 2 KiB banks; PX fills the inactive bank while CPU consumes the active bank.
- The 8-bank × 64-bit Data RAM throughput table in Section 8 does not describe or widen this single-lane App-code path.

App RAM and Data RAM access remain physically independent and may make progress concurrently. App RAM writes/maintenance for loader and controlled code updates use a separately specified maintenance path.

## 7. Data RAM bank group

Data RAM must support both scalar and wide data traffic:

- 64-bit scalar accesses can use one bank slice.
- 128-bit accesses can use two bank slices.
- 256-bit accesses can use four bank slices.
- 512-bit accesses can use all eight bank slices.
- MEMXFER reads and writes use the same existing domain/controller/Fabric resources and may be internally segmented into bounded beats.

The eight-bank organization supports a single 512-bit aggregate access and can also serve multiple independent narrower accesses when they map to different banks and do not violate ordering, ownership or reservation rules.

A bank is not assumed to accept a read and a write in the same cycle. If the physical implementation has a shared or single-direction port, the bank controller applies the already-defined bounded read/write turnaround and aging policy. Separate read/write paths may be implemented only if physical design validates the area, timing and power cost.

## 8. Throughput model

The following values are theoretical Data RAM interface ceilings, not guaranteed sustained application bandwidth. They assume every 64-bit Data RAM bank slice can complete one 64-bit beat per memory cycle and the aggregate Data RAM path can carry all eight slices. These figures do not apply to the single 64-bit App RAM -> L0I code-fetch lane.

| Active bank slices | Aggregate width | Bytes/cycle | At 10 GHz | At 20 GHz |
|---:|---:|---:|---:|---:|
| 1 | 64 bit | 8 B | 80 GB/s | 160 GB/s |
| 2 | 128 bit | 16 B | 160 GB/s | 320 GB/s |
| 4 | 256 bit | 32 B | 320 GB/s | 640 GB/s |
| 8 | 512 bit | 64 B | 640 GB/s | 1.28 TB/s |

App RAM and Data RAM have separate physical paths. Their activity can overlap; the table applies independently to each qualifying bank group and must not be interpreted as one shared combined bus.

Actual sustained bandwidth will be lower where sense time, write time, bank conflicts, controller scheduling, Fabric transport, ECC, refresh/retention management, power or thermal limits reduce the usable service rate. The MOSRAM 10–20 GHz and 50–100 ps values remain physical research targets pending SPICE/TCAD and prototype validation.

## 9. Port and concurrency contract

1. Each bank arbitrates its own accepted requests. There is no global bank lock.
2. Different banks may serve independent requests concurrently.
3. A same-bank conflict is local to the affected bank/port.
4. The baseline does not promise simultaneous READ and WRITE on one bank.
5. App RAM and Data RAM remain independent even when their requests occur in the same cycle.
6. Wide accesses may reserve/use multiple banks as one architectural operation; internal beat scheduling must preserve the existing precise fault and commit semantics.
7. MEMXFER source/target range reservations remain in force across chunk yields. Bank-level parallelism does not permit conflicting STORE/ATOM/LOAD operations to bypass those reservations.
8. ATOM serialization and NDC ordering are defined by the ISA and memory-access-control specifications, not by bank-number order.
9. Queue depth, exact number of concurrent bank commands, turnaround cycles, and controller clock ratios remain implementation parameters until the physical design is characterized.

## 10. Required simulator scenarios

| Test | Expected result |
|---|---|
| Sequential 64-byte aligned read | Uses all eight banks in one group without same-bank collision |
| 64-bit sequential stream | Consecutive 8-byte words rotate across all eight banks |
| 128/256/512-bit aligned load | Uses 2/4/8 bank slices respectively |
| 512-bit aligned store | Uses the full eight-bank group while preserving architectural commit rules |
| 64-byte stride across many streams | Folded selector distributes requests better than the low-bit-only baseline where address bits permit |
| 4 KiB stride | Detects pathological bank aliasing; compare candidate hashes |
| Eight independent 64-bit reads to distinct banks | All may be serviced concurrently when ports/resources are available |
| Eight reads to one bank | Local bank conflict; unrelated banks continue |
| READ and WRITE contend in one bank | Turnaround and aging prevent starvation |
| READ in one bank and WRITE in another | Independent banks may proceed concurrently |
| App RAM fetch plus Data RAM load | Both independent paths make progress concurrently |
| App RAM -> L0I single-lane fetch | Transfers one 64-bit instruction word per beat; no implicit 512-bit code refill |\n| Task-based L0I -> PX transfer | Selects requested 2 KiB logical pages from non-contiguous App RAM code regions |\n| PX -> SPM0 dual-bank refill | Fills inactive 2 KiB bank while active bank supplies instruction words |
| MEMXFER crosses several banks | Bounded chunking and reservation semantics remain correct |
| ECC/error or backpressure in one bank | Affected request is handled locally; independent banks continue where possible |

## 11. Freeze criteria

The eight-bank × 64-bit organization is the recommended architecture baseline for the first NEXSUS CPU memory simulator. It becomes a physical design freeze only after:

- MOSRAM cell and sense-block behavior is validated with realistic SPICE/TCAD parameters;
- 64-bit bank slice read and write timing/energy are measured;
- 8-bank routing, clock distribution, power and thermal limits are evaluated;
- bank-hash tests show acceptable conflict rates for sequential, strided, random and multi-stream workloads;
- CPU AGU count, memory issue throughput and 512-bit access alignment behavior are finalized.

Until then, the bank count and width are a recommended topology, not a claim of proven silicon performance.

## 12. Architecture references\n\n- [Bank Controller Behavior](NEXSUS-CPU-BANK-CONTROLLER-001.md) defines local bank queues, all-or-none multi-bank admission, port scheduling and wide-access completion.

These references are comparative evidence for banked access paths, address-based bank selection, independent load/store resources and the value of bank-conflict testing. They are not direct templates for MOSRAM:

- AMD, *Software Optimization Guide for the AMD Zen 5 Microarchitecture*, Publication 58455, Rev. 1.00 (2024): [AMD documentation portal](https://docs.amd.com/v/u/en-US/58455_1.00). Describes a banked L1 data cache, address-derived bank selection, multiple load pipes and separate store-commit resources.
- Intel, *64 and IA-32 Architectures Optimization Reference Manual*, Order No. 248966: [Intel manual PDF](https://www.intel.com/content/dam/doc/manual/64-ia-32-architectures-optimization-manual.pdf). Documents an eight-bank L1 data-cache organization in the Sandy Bridge/Nehalem examples and explains bank-conflict effects.
 - Reproducible architectural mapping model: [tools/bank_mapping_model.py](tools/bank_mapping_model.py).\n- AMD, *Software Optimization Guide for the AMD Zen 4 Microarchitecture*, Publication 57647: [Guide PDF](https://www.numberworld.org/blogs/2024_8_7_zen5_avx512_teardown/57647_zen4_sog.pdf). Describes address-derived bank selection, bank conflicts and alignment-sensitive wide accesses.
