# NEXSUS CPU — Memory Protection Domains
**Document ID:** NEXSUS-CPU-MEMORY-PROTECTION-DOMAINS-001  
**Status:** Architecture specification — policy baseline  
**Scope:** App RAM, Data RAM, task isolation, privileged memory, and Fabric-mediated access

## 1. Design principles

1. App RAM and Data RAM remain physically separate memory systems with independent parallel-read capability and paths/controllers.
2. App RAM contains executable command streams. Data RAM contains mutable program data, task state, and protected OS context storage.
3. Every access is checked against privilege, ownership, domain, and operation permissions.
4. A task cannot access another task's private memory by default.
5. Sharing is explicit and mediated; a shared cache level or physical proximity does not itself grant access.
6. This specification defines protection policy, not a particular virtual-memory/MMU/TLB implementation. Address translation and permission-cache hardware remain open implementation topics.

## 2. Privilege model

The existing levels remain:
- PL0 — User task.
- PL1 — Supervisor/OS.
- PL2 — Machine/firmware.

Privilege alone is not a universal memory grant. PL1 and PL2 software must still obey ownership, region purpose, and explicit sharing rules. Hardware exception entry and other CPU-internal mechanisms retain their separately defined authority.

## 3. App RAM policy

### 3.1 Contents and access
- App RAM stores application instruction/command streams consumed by P0 and the fetch path.
- PL0 may fetch/execute only App RAM ranges mapped or assigned to its task.
- Normal PL0 data reads and writes to executable App RAM are denied. Code is not a general-purpose data buffer.
- PL0 cannot modify executable command pages while they are executable.
- OS/loader code may populate or update an image before it is published for execution. The image must be made valid and stable before P0 is allowed to fetch it.
- A task cannot execute another task's private App RAM image unless an explicit shared executable-image grant permits read/execute access.
- Data RAM is never an instruction-fetch source under this baseline.

### 3.2 Write/execute separation
The default policy is that a range is not simultaneously writable and executable for PL0. Code publication is a controlled lifecycle: privileged loader writes the image, validates it, publishes it as executable/read-only, then allows task execution. Any future self-modifying or dynamic-code facility requires a separately specified privileged transition; it is not implicit.

## 4. Data RAM policy

### 4.1 Private task data
- Each task receives a private Data RAM address range or equivalent protected allocation.
- PL0 may read/write only its own private allocations and explicitly granted shared ranges.
- A task cannot read, overwrite, infer ownership of, or free another task's private allocation.
- Bounds and access rights apply to the complete requested access width, including vector/matrix and atomic operations.
- Invalid, out-of-range, stale, or revoked references are rejected before any part of the access commits.

### 4.2 Protected OS region
- Exception frames and full task-context backing remain in protected Data RAM.
- The per-core KESP/KELIMIT-bounded privileged exception stack region is inaccessible to PL0.
- SPM3–SPM6 spill/context backing and other scheduler-owned records are protected OS data, not user allocations.
- PL1 may access these regions only through the relevant exception, scheduler, or context-management paths.
- PL2 firmware may perform controlled maintenance/recovery, but privilege does not make protected user or OS allocations interchangeable.
- User-provided pointers are never trusted as destinations for privileged context frames.

### 4.3 Default permissions
| Region | PL0 | PL1 | PL2 | Default purpose |
|---|---|---|---|---|
| Task-private Data RAM | Own range: read/write; no execute | OS-managed access | Controlled maintenance | Task data |
| Explicit shared Data RAM | Only granted operations/ranges | Manage grants | Controlled maintenance | Inter-task/node exchange |
| OS/context Data RAM | Denied | Authorized OS paths | Controlled maintenance | Exception and task context |
| Unallocated/free Data RAM | Denied | Allocator only | Controlled maintenance | OS allocation pool |

Data RAM is non-executable by default. PL0 instruction fetch from Data RAM is denied.

## 5. Explicit sharing and zone memory

1. Sharing requires an explicit grant established by the owner or an authorized OS service.
2. A grant identifies the object/range, permitted operation (read, write, or both), authorized task/agent, and validity/lifetime.
3. Existing L2/L3/L4 zone concepts may carry shared payloads, but zone membership alone does not authorize access.
4. Shared payload access uses the existing zone handle/address model; no implicit copying of large payloads is required.
5. Revocation prevents new accesses after the defined synchronization point. In-flight operations must complete or be cancelled according to the grant's lifetime protocol before storage is reclaimed.
6. A task must not derive authority by guessing or modifying a raw address. Handles/references are validated against ownership and generation.
7. Release/acquire and the established memory-consistency protocol are still required for publication and consumption. A permission grant does not itself provide memory ordering.

## 6. CPU access and operation checks

Protection applies to all CPU memory operations, including:
- LOAD/STORE and their extended/update forms;
- atomic operations;
- vector/matrix accesses and all supported widths;
- instruction fetch from App RAM;
- CPU-controlled memory-domain XFER operations.

The full byte range and requested operation must be authorized before an operation commits. A denied or misaligned access must not partially update memory or architectural destination state. Existing precise-exception rules apply.

## 7. System Fabric, nodes, and peripherals

1. Nodes, peripherals, and other Fabric agents receive no implicit access to CPU App RAM, Data RAM, SPM, or task-private allocations.
2. A task request supplies a descriptor/reference; it does not grant access merely by naming an address.
3. Before payload movement, the Fabric/OS authorization path validates the descriptor, task identity/generation, target agent, memory domain, range, operation, length, and grant lifetime.
4. Payload movement is limited to the authorized range and direction. A read grant does not permit writes; a write grant does not permit reads unless separately granted.
5. Completion notifications and IRQ metadata carry status/reference information, not payload authority. An IRQ does not bypass protection or imply memory visibility.
6. Revoked, stale, malformed, or out-of-bounds descriptors are rejected and reported through the established task/Fabric error path.
7. No node-to-node or node-to-memory bypass is assumed. Any direct Fabric path must enforce the same grant and lifetime rules.


## 7.1 Eşzamanlı erişim ve aktif transfer sahipliği

- Bir memory grant veya allocation, yalnızca izin verilen byte aralığı ve işlem yönü için yetki verir; eşzamanlı erişim tutarlılığı NDC ve domain-controller arbitration kurallarına tabidir.
- Kabul edilmiş MEMXFER işlemi boyunca kaynak aralığı read-reserved, hedef aralık write-reserved/unpublished kabul edilir. Kaynak üzerinde okuma izni devam eder; çakışan yazma/ATOM işlemleri reddedilir. Hedefe yönelik her türlü normal LOAD/STORE/ATOM erişimi transfer tamamlanana kadar reddedilir.
- Bu rezervasyon, grant'in iptal edilmesi veya allocation'ın serbest bırakılmasıyla ortadan kaldırılamaz. Revocation/reclaim, ilgili transfer başarıyla veya hatayla terminal duruma ulaşana ve rezervasyon kaldırılana kadar ertelenir.
- Başka bir transferin hedefi aktif transferin kaynak/hedef aralığıyla çakışamaz. Kaynak-kaynak örtüşmesi read-only olduğundan serbesttir. Çakışma yalnızca aynı domain içindeki kesişen byte aralıklarında değerlendirilir.
- Rezervasyon, tüm domain'i veya çekirdeği kilitlemez; ilgisiz aralıklar, farklı domain'ler ve izinli kaynak okumaları paralel kalır.
## 8. Task switch and migration

Before returning to PL0 for an incoming task, the scheduler must ensure:
1. The incoming task's private App RAM image and entry PC are valid.
2. Its Data RAM ranges and shared grants are installed/validated.
3. Its protected OS context is not exposed through user mappings.
4. Its SPM2 ownership and restored workspace are valid under the SPM access policy.
5. P0 is invalidated/refilled from the incoming task's App RAM stream as required.
6. Any per-core permission or translation state is switched or validated before user execution.

Cross-core migration transfers ownership explicitly. Task memory remains in its authorized Data RAM domain or is moved through a supported, authorized transfer. No implicit cross-core cache or SPM coherence is assumed by this document.

## 9. Protection faults

- Privilege, ownership, range, operation, stale-handle, and execute-permission violations raise precise protection exceptions.
- Existing CAUSE/BADADDR/EXCINFO mechanisms report the fault class and relevant access metadata where valid.
- The faulting operation has no partial memory write or destination-register commit.
- A failed instruction fetch from App RAM is reported as an instruction-fetch protection fault.
- Protection faults during privileged OS activity follow the existing exception/double-fault policy; they must not silently fall back to user permissions.
- Exact numeric cause/subcode assignments and hardware permission-check structures remain to be specified in the exception/implementation phase.

## 10. Invariants

1. App RAM and Data RAM remain physically distinct.
2. App RAM is the instruction source; Data RAM is the data/context source.
3. PL0 cannot access another task's private memory.
4. Data RAM is non-executable by default.
5. Executable App RAM is not writable by PL0.
6. OS exception/context storage is inaccessible to PL0.
7. Shared memory requires an explicit, scoped, revocable grant.
8. Fabric agents obey the same ownership and grant boundaries; notification is not authorization.
9. Memory permission does not replace release/acquire synchronization.
10. No new RAM type, cache level, register bank, or ISA opcode is introduced.

## 11. Open implementation decisions

The following are deliberately not frozen here:
- physical versus virtual address presentation to software;
- whether address translation is implemented and, if so, its hardware structure;
- permission-table representation and caching;
- allocation granularity and guard-region layout;
- exact grant/handle binary format and generation width;
- cache maintenance requirements on grant, revocation, and migration;
- exact protection-fault numeric codes;
- controlled dynamic-code publication, if ever required.

These decisions must preserve the policies and invariants above.

## 12. Related specifications

- NEXSUS-CPU-SPM-ACCESS-PROTECTION-001.md
- NEXSUS-CPU-CONTEXT-SAVE-RESTORE-001.md
- NEXSUS-CPU-TASK-SCHEDULING-SPM-RESIDENCY-001.md
- NEXSUS-CPU-CSR-001.md
- NEXSUS-SYSTEM-NODE-COMMUNICATION-001.md


## 14. Memory access-control flow reference

The operational validation sequence for instruction fetch, LOAD/STORE, ATOM, and memory-domain XFER is specified in `NEXSUS-CPU-MEMORY-ACCESS-CONTROL-001.md`. This policy document defines who may access each region; the access-control-flow document defines when and how the existing request path must validate that authority before issue and commit.
