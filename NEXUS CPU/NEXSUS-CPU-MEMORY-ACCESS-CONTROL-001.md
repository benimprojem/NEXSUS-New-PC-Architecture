# NEXSUS CPU — Memory Access Control Flow
**Document ID:** NEXSUS-CPU-MEMORY-ACCESS-CONTROL-001  
**Status:** Architecture specification — control-flow baseline  
**Scope:** Validation and commit rules for App RAM fetch, L1–L4 LOAD/STORE/ATOM, and memory-domain XFER

## 1. Existing architecture reused

This specification does not introduce a new memory type, standalone protection unit, register bank, CSR, or ISA opcode.

It builds on existing definitions:
- CPU ISA LOAD/STORE, indexed and update forms, ATOM, and L1–L4 domain selection.
- The existing 64-bit effective-address calculation and natural-alignment rules.
- The existing precise fault classes: ADDRESS_OVERFLOW_FAULT, ALIGNMENT_FAULT, MEMORY_BOUNDS_FAULT, MEMORY_PERMISSION_FAULT, and MEMORY_ACCESS_FAULT.
- The existing DA staging path for LOAD/STORE.
- The AGU proposal and internal MAR/MDR/transaction-queue state described in NEXSUS-CPU-SRA-001.md.
- Separate App RAM → P0 instruction-fetch path and Data RAM/L1–L4 data-access paths.
- Existing System Fabric request validation and address routing for non-CPU agents.

Protection is a required behavior of the existing access paths. Its exact gate placement and circuit implementation remain microarchitectural choices.

## 2. Two independent CPU access paths

### 2.1 Instruction-fetch path

App RAM is the instruction source. The path is:

App RAM → instruction-fetch path → P0 → fetch/decode.

Before instruction bytes enter P0, the fetch path must validate that the complete fetched range belongs to an executable App RAM region assigned or explicitly granted to the current task.

Rules:
1. PL0 instruction fetch is allowed only from the task's executable App RAM image/ranges.
2. Data RAM/L1–L4 is not an instruction-fetch source.
3. User App RAM code is not writable by PL0 while executable.
4. A P0 refill/read must not cross an executable-region boundary into an unauthorized range. Prefetch beyond the current authorized range is suppressed until a separately authorized range is selected.
5. A failed fetch raises the existing instruction-fetch protection/access fault and must not publish unauthorized bytes into P0.
6. On task switch, P0 state is invalidated/refilled for the incoming task as already required by the context/scheduler specifications.

P0 remains a refillable command buffer, not architectural task state and not a protection mechanism.

### 2.2 Data-access path

The existing LOAD/STORE/ATOM path uses the selected L1–L4 domain and DA staging where specified. Its functional flow is:

Decode → effective-address generation → access-range validation → ownership/permission validation → domain request → memory-domain controller → result/commit.

This is a logical ordering contract. Independent validation checks may execute in parallel internally, but no memory side effect or architectural destination update may commit until all required checks succeed.

## 3. Required validation inputs

Every CPU-originated data access is validated using the existing architectural context and request fields:

- current privilege level (PL0/PL1/PL2);
- current task identity/generation and its active memory ownership/grants;
- operation class: read, write, execute, atomic-read, atomic-write, or read-modify-write;
- selected L1/L2/L3/L4 domain;
- effective byte address and complete access length;
- region/domain bounds and validity;
- alignment and access width;
- whether the target is private, shared, OS/context-owned, or unallocated.

The active task identity and permission state are scheduler-controlled execution context. This document does not assign them a new architectural register or CSR.

## 4. LOAD/STORE validation sequence

For every LOAD/STORE, including MEMX, MEMUPD, and MEMXUPD:

1. **Decode validation:** Confirm opcode, format, width, domain selector, register selectors, and mode are legal.
2. **Address generation:** Calculate the effective address using the existing base/index/scale/displacement rules. Detect 64-bit overflow/underflow.
3. **Range construction:** Determine the complete byte interval [EA, EA + W/8 - 1]; detect end-address overflow.
4. **Alignment validation:** Enforce the existing natural alignment rule for W.
5. **Domain and region resolution:** Resolve the selected L1–L4 domain and determine whether the complete interval belongs to a valid region in that domain.
6. **Privilege and ownership validation:** Confirm that the current task/privilege is authorized for the complete interval and operation. A domain being reachable by a core does not by itself grant the current task access.
7. **Permission validation:** Check read permission for LOAD and write permission for STORE. Execute permission is not substituted for data-read permission.
8. **Request issue:** Only after validation succeeds may the request enter the selected domain's existing controller/arbitration path.
9. **Architectural commit:** LOAD updates its DA destination group only after the full access succeeds. STORE may commit only after the full requested range has passed bounds and permission validation.

The checks may be pipelined or parallelized, but the externally visible behavior must match this sequence's all-checks-before-commit contract.

## 5. Atomic operations

ATOM uses the same effective-address, domain, bounds, alignment, ownership, and permission framework as LOAD/STORE, with operation-specific rights:

- ATOM.LOAD requires read permission.
- ATOM.STORE requires write permission.
- CAS, SWAP, and FETCH read-modify-write operations require both read and write permission for the complete atomic location.
- Atomic width/alignment and serialization rules remain those of the ISA/Encoding specification.
- A denied atomic operation must not modify memory or its destination DA register.
- Permission validation does not replace atomic serialization, NDC ordering, or release/acquire synchronization.

## 6. Memory-domain XFER

Existing XFER.MEM / XFER.START / XFER.WAIT operations use the same protection domains; they do not bypass LOAD/STORE protection.

For XFER.MEM or XFER.START with a nonzero length:
1. Snapshot the source address, destination address, and byte length from their selected RA registers before writing any destination register. Therefore, the token destination RA may alias DRA, SRA, or LRA.
2. Interpret LRA as an unsigned 64-bit byte count. The architectural instruction has no fixed small transfer-size ceiling; the implementation may divide a large request into bounded internal beats.
3. Validate the complete source range for read access and the complete destination range for write access.
4. Validate source and destination domain membership, 64-bit range arithmetic, bounds, and any required transfer alignment. Range-end calculation must detect overflow before the first payload beat.
5. Validate task ownership and any explicit shared/Fabric grant for both ranges.
6. Do not begin payload movement until both endpoints pass validation and the destination range is reserved for this transfer.
7. The source range must remain stable and readable until completion. The destination range is exclusively owned by the transfer and must not be read, modified, reclaimed, or published while the transfer is in flight. A grant/allocation cannot be revoked or reclaimed until completion or defined cancellation.

**Length and range limit:** The ISA does not impose an arbitrary 4 KiB/64 KiB/etc. maximum. The effective limit is the largest valid range in the selected domain, subject to unsigned 64-bit length and checked address arithmetic. For nonzero length, the last byte address must be representable in the 64-bit address space; overflow raises ADDRESS_OVERFLOW_FAULT. A transfer may be internally segmented into smaller beats without changing its architectural single-operation semantics. Zero length is handled by the special case below and does not form or validate a memory range.

**Acceptance and fault point:** XFER.START performs all validation and reserves the destination before acceptance. If validation or reservation fails, it raises the corresponding synchronous fault, creates no token, starts no payload movement, and leaves TRA unchanged. XFER.MEM reports both validation faults and runtime transfer faults at the XFER.MEM instruction itself. On successful completion, the destination becomes eligible for normal use. If a transfer faults after one or more internal beats, physical destination bytes may have been written; hardware is not required to roll them back. The entire destination range nevertheless remains logically invalid/unpublished. Software must discard that destination allocation or overwrite the complete range successfully before publishing it. No consumer may treat a partial result as valid data.

**Completion visibility and ordering:** A successful synchronous XFER.MEM makes the complete destination range usable under the destination domain's normal NDC rules before the instruction retires. For XFER.START, acceptance does not publish the destination. Only a successful terminal XFER.WAIT establishes the issuing core's acquire-completion boundary; subsequent destination-domain LOADs by that core must observe the completed transfer data. A failed WAIT establishes no such boundary. Other cores require a separate release/acquire publication in the destination domain after successful completion. FENCE does not wait for an active MEMXFER and cannot substitute for WAIT. If another core produced the source data, the initiating core must first observe the producer's publication through synchronization in the source domain; MEMXFER itself does not create that producer/consumer synchronization.

**Token capacity and backpressure:** Each accepted XFER.START owns one core-local token record until a successful or failed terminal WAIT consumes it. The number of token records is finite and implementation-defined; it is reported through the platform/OS capability information, not through a new ISA register or CSR. If no token record is available, START raises MEMORY_ACCESS_FAULT with EXCINFO subtype TRANSFER_RESOURCE_UNAVAILABLE. This is a retryable resource condition: no transfer is accepted, no payload moves, and TRA remains unchanged. START must not wait indefinitely for a token slot, because doing so could prevent the same instruction stream from issuing the WAIT needed to free one. A zero-length START also requires a token record until WAIT consumes it.

**Zero-length special case:** If the selected length is zero, XFER.MEM is a successful no-op and XFER.START creates an already-completed token, subject to token-record availability. No memory range, mapping, ownership, or permission checks are performed because no byte is accessed. Instruction format, domain selectors, and RA selectors must still be valid. No payload movement occurs.

**WAIT/token behavior:**
- Successful XFER.WAIT consumes the token and clears its TRA register to zero. Reusing a consumed token is an illegal-token fault.
- An asynchronous runtime transfer failure is reported synchronously by XFER.WAIT. The failed token is retired by hardware, but the faulting WAIT does not commit its TRA write under precise-exception rules; the old token bits remain in the RA and are stale. The exception handler may clear or overwrite that RA using normal RA operations.
- A token is local to the initiating core and does not grant new access rights. Its 64-bit RA representation is opaque to software and must distinguish a token slot's current generation from stale copies; recycling a slot must never make an old token value valid for a later transfer during the core's active lifetime.
- A token record remains allocated after the transfer reaches either success or failure, until WAIT consumes it. Completion frees transfer-engine execution resources, not the token record.

## 7. Domain reachability is not task permission

The existing area/zone and L1–L4 model defines where data resides and which cores can physically/logically reach a domain:
- L1 is private to its owning core.
- L2/L3/L4 are shared by their defined core groups.

This reachability does not grant every task on an eligible core unrestricted access. Task-private allocations and shared zone objects retain their own ownership and permissions. A zone handle is valid only for the task/agent and operations covered by its explicit grant.

## 8. Fabric and non-CPU requesters

CPU LOAD/STORE protection and Fabric-agent authorization are related but distinct entry paths.

- CPU-originated requests are checked against the active CPU task/privilege context before issue.
- Node, peripheral, DMA, and other Fabric-originated requests are checked against their task descriptor and explicit access grant at the Fabric authorization/target ingress path.
- The System Fabric Address Manager's physical/logical address routing role does not, by itself, constitute an authorization grant.
- A requester identity, task ID/generation, domain, range, direction, and grant lifetime must remain associated with an accepted transfer until completion.
- No external requester receives access to App RAM, Data RAM, SPM, or task-private allocations merely by presenting an address.

## 9. Fault and commit guarantees

The existing ISA fault classes remain authoritative:
- ADDRESS_OVERFLOW_FAULT — effective/range address arithmetic exceeds the 64-bit address space.
- ALIGNMENT_FAULT — access violates natural alignment.
- MEMORY_BOUNDS_FAULT — the complete range exceeds its valid domain/region bounds.
- MEMORY_PERMISSION_FAULT — the requester lacks the required operation permission.
- MEMORY_ACCESS_FAULT — no valid access target/mapping is available.

For validation faults:
- LOAD destination DA registers remain unchanged.
- STORE writes no byte.
- ATOM does not modify memory or its destination.
- MEMUPD/MEMXUPD base-register updates do not commit.
- No unauthorized bytes are fetched into P0.
- The fault is reported synchronously to the initiating CPU for CPU-originated operations, using the existing exception/CSR path.

If multiple validation conditions fail simultaneously, the implementation must report one deterministic architecturally defined fault. The exact cross-fault precedence is left open for the exception/ISA integration pass; it must not vary nondeterministically between implementations.

## 10. Parallelism and arbitration

Protection must not serialize unrelated valid accesses unnecessarily:
- Independent requests to independent banks/domains may proceed in parallel after their own validation succeeds.
- Requests contending for the same bank/address/resource are handled by the existing domain controller/arbitration and atomic-serialization rules.
- App RAM instruction fetch and Data RAM data access remain independent paths.
- Permission checks may be pipelined or replicated near the request sources/target ingress. The architecture specifies the result, not a mandatory centralized checker.
- A failed request must not block unrelated requests unless they share a required resource or ordering dependency.


## 10.1 Çakışan erişimler ve MEMXFER aralık rezervasyonu

Domain controller, her isteğin tam byte aralığını ve erişim yönünü dikkate alır. LOAD/LOAD çakışmaları birlikte ilerleyebilir; STORE içeren çakışan normal erişimler ilgili domain coherence order içinde sıralanır. Kontrolsüz normal LOAD/STORE yarışları data race'tir; donanım sıralaması yazılım için belirli bir kazanan değer garantisi oluşturmaz. Normal erişim ile aynı aralığa ATOM erişiminin karıştırılması da synchronization gerektirir; normal STORE atomic handoff değildir.

MEMXFER için mevcut domain controller/Fabric transaction metadata'sı üzerinde aralık rezervasyonu uygulanır; yeni register bankı, CSR, opcode veya global kilit eklenmez:

1. XFER.MEM/XFER.START kabulünden önce, aynı aralıkta devam eden çakışan işlemler varsa istek bekletilmez; MEMORY_ACCESS_FAULT ve EXCINFO=TRANSFER_RANGE_BUSY ile reddedilir.
2. Kabul edilen transferin kaynak aralığı read-reserved'dır. Kaynakla örtüşen normal LOAD serbesttir; STORE ve ATOM reddedilir.
3. Hedef aralık write-reserved/unpublished'dır. Hedefle örtüşen LOAD, STORE ve ATOM reddedilir.
4. Tek bir transferin kaynak ve hedef aralıkları aynı domain'de örtüşemez; bu durum TRANSFER_RANGE_OVERLAP ile kabul öncesinde reddedilir. Farklı transferler arasında kaynak-kaynak örtüşmesi serbesttir. Bir transferin hedefi diğer aktif transferin kaynak veya hedef aralığıyla kesişirse sonraki transfer TRANSFER_RANGE_BUSY ile reddedilir; START token oluşturmaz, TRA değişmez ve payload hareketi başlamaz.
5. Başarılı XFER.MEM completion'ında rezervasyon kaldırılır. XFER.START için başarılı transferin hedef rezervasyonu, başarılı WAIT'e kadar korunur. Runtime failure kesinleştiğinde transfer artık yazma yapmayacağından rezervasyon kaldırılır; başarısız hedef yine invalid/unpublished kalır. Token kaydı WAIT tarafından tüketilene kadar ayrı olarak tutulur. Kısmi fiziksel yazmalar rollback garantisi taşımaz.
6. Rezervasyon byte-range ve domain kapsamındadır. Uygulama cache-line/bank/beat seviyesinde daha geniş iç arbitration yapabilir; mimari olarak ilgisiz aralıklara busy fault veremez.

Normal LOAD/STORE aynı aralıkta XFER rezervasyonuyla çakışırsa fail-fast fault kullanılır; bekleme yapılmaz. Bu, aynı task'ın hedefi okumadan önce WAIT çalıştırmasını ve kaynak verisini transfer sürerken değiştirmemesini zorunlu kılar; WAIT'e ulaşmayı engelleyen deadlock riskini önler. Farklı aralık ve domain'lerdeki istekler paralel kalır.

## 10.2 Bellek arbitration, QoS ve starvation koruması

Arbitration, erişim izni doğrulandıktan sonra ve hedef domain/bank seviyesinde yapılır. L1–L4 için tek bir global FIFO/kilit kullanılmaz. Bağımsız bankalar ve domain'ler kendi isteklerini paralel ilerletebilir.

CPU ve Fabric istekleri şu servis sınıflarıyla ele alınır:

| Sınıf | İstek türü |
|---|---|
| URGENT | CPU exception/IRQ handler ve context-frame için donanımca işaretlenen erişimler |
| CPU-DEMAND | Normal CPU LOAD/STORE/ATOM |
| LATENCY-SENSITIVE | Gecikme hedefi tanımlanmış yetkili Fabric/Node erişimleri |
| BULK | MEMXFER ve büyük DMA/Fabric payload beat/chunk işlemleri |
| BACKGROUND | Ertelenebilir bakım ve arka plan istekleri |

- URGENT servisinin bütçesi sınırlıdır; diğer sınıflar için de servis kapasitesi korunur. URGENT işaretini yalnızca CPU hardware aktif exception/IRQ durumuna göre üretebilir; PL0 bunu kendisi yükseltemez.
- Kalan kapasite ağırlıklı adil arbitration ile dağıtılır. Bekleme süresi arttıkça aging etkin önceliği yükseltir; aktif bir sınıf süresiz aç bırakılamaz.
- Uzun transferler sınırlı beat/chunk quantum'larıyla yürütülür. MEMXFER quantum sınırında duraklatılabilir; kaynak/hedef range reservation ve token yaşam döngüsü transfer tamamlanana kadar korunur.
- Bir XFER'ın duraklatılması, source range'in sabit kalması veya destination range'in unpublished kalması kurallarını değiştirmez. WAIT yalnızca gerçek terminal completion/failure sonucunu bekler.
- ATOM işlemleri bankaya erişim için sınırsız öncelik almaz; ancak kabul edildiklerinde kendi atomic serialization/indivisibility kurallarına uyar.
- Banka/port çakışması yalnızca ilgili kaynağı bekletir. Ayrı bankalar, bağımsız domain'ler ve aynı bankada paralel erişime uygun bağımsız portlar çalışmayı sürdürür.
- IRQ/exception'ın kendisi bellek sıralaması veya senkronizasyon sağlamaz. URGENT yalnızca handler'ın gerekli bellek erişimlerine latency önceliği verir.

Kesin quantum, ağırlık, URGENT bütçesi ve cycle bazlı latency sınırları mikro-mimari parametrelerdir; bunlar bellek clock'u, bank/port sayısı ve Fabric yükü ölçüldükten sonra belirlenir. Mimari olarak starvation koruması ve sınırlı burst zorunludur.
## 11. Task switch and permission-state transition

Before PL0 resumes for a new task, the scheduler must establish:
1. the incoming task identity/generation as the active execution context;
2. the task's App RAM executable ranges;
3. its private Data RAM ranges and explicit shared grants;
4. the correct L1–L4 domain reachability and ownership state;
5. the incoming SPM2 ownership/workspace;
6. P0 invalidation/refill for the incoming App RAM stream.

The previous task's permission state must no longer authorize accesses after the handoff. Any in-flight memory/Fabric transfer must retain its validated ownership/lifetime until completion or cancellation; it cannot silently become owned by the incoming task.

## 12. Implementation boundary

No standalone Memory Protection Unit, new AGU register, new CSR, new opcode, or new memory level is mandated here. The implementation may place validation logic in the existing AGU/load-store issue path, domain controllers, and Fabric target ingress as appropriate.

The following remain open implementation details:
- exact physical placement and pipelining of validation logic;
- permission metadata representation and lookup latency;
- whether mapping/translation exists and how it is cached;
- precise fault precedence when multiple checks fail together;
- physical rollback/atomicity for a runtime hardware failure after a multi-beat request has begun;
- cache/permission metadata invalidation mechanics on grant revocation and task migration.

## 13. Related specifications

- NEXSUS-CPU-ISA-001.md — LOAD/STORE, ATOM, FENCE, NDC.
- NEXSUS-CPU-INSTRUCTION-ENCODING-001.md — memory formats and fault/commit rules.
- NEXSUS-CPU-SRA-001.md — AGU, MAR/MDR, transaction state.
- NEXSUS-CPU-MEMORY-PROTECTION-DOMAINS-001.md — ownership and access policy.
- NEXSUS-CPU-TASK-SCHEDULING-SPM-RESIDENCY-001.md — task identity and handoff.
- NEXSUS-SYSTEM-NODE-COMMUNICATION-001.md — Fabric task descriptors and payload requests.
- NEXSUS System Fabric.md — Address Manager, bank parallelism, and Fabric arbitration.
