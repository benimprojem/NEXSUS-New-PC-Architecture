# NEXSUS CPU — Workspace Addressing and Transfer

**Document ID:** NEXSUS-CPU-WORKSPACE-ADDRESSING-AND-TRANSFER-001  
**Status:** ISA/architecture baseline — WSMEM and workspace MEMXFER opcode/field assignments recorded; microarchitecture implementation open  
**Scope:** Direct byte addressing, DA-staged register save/restore, and one-way OSSpace/WS→Data RAM block export

## 1. Design intent

OS Space (OSSpace) and Work Space (WS) are directly addressable, core-local working files, not hardware stacks. Software may use them as stack-like frames, fixed-offset records, arrays, tables, temporary structures, or any combination. No mandatory LIFO discipline is imposed.

Both workspaces have an 8 KiB capacity per core. OSSpace is OS-owned. WS is a general-purpose application workspace and is not owned by a task ID or treated as task-context state. The OS controls access epochs and must prevent data from one protection domain from leaking into the next when WS is reassigned.

## 2. Address space

| Property | OSSpace | WS |
|---|---:|---:|
| Capacity | 8 KiB | 8 KiB |
| Address unit | Byte | Byte |
| Valid offset | 0–8191 | 0–8191 |
| Scope | Core-local | Core-local |
| PL0 | Denied | Allowed during application execution |
| PL1/PL2 | Allowed | Controlled management, initialization, save/restore |

Workspace offsets are relative to the selected workspace and are not Data RAM physical addresses. The architectural forms are:

```asm
WLOAD.WS.W64  DA0, [0x120]
WSTORE.WS.W64 [0x120], DA0

WLOAD.WS.W64  DA1, [RA4 + 0x120]
WSTORE.OSSpace.W64 [RA5 + 0x40], DA2
```

The immediate form denotes an absolute workspace-relative byte offset. The RA form denotes a base register containing a workspace-relative offset plus a signed byte displacement. The complete effective range must remain inside 0–8191; wrapping is forbidden.

## 3. WLOAD / WSTORE and shared access budget

WLOAD and WSTORE are the scalar/vector-width access path between a workspace and the DA staging bank. Workspace endpoints participate in the same core-wide access budget as the RA/FA/DA/MA register banks; they do not receive an independent extra 32R/32W pool.

The Resource Access Controller (RAC) provides **32 logical 64-bit read slots and 32 logical 64-bit write slots per cycle in total**, dynamically shared across RA, FA, DA, MA, WS, and OSSpace. It is a global budget, not 32R/32W per bank or per workspace.

- WLOAD.W8/W16/W32/W64 consumes one workspace read slot and one DA write slot. WLOAD.W128/W256/W512 consumes 2/4/8 workspace read slots and 2/4/8 DA write slots.
- WSTORE.W8/W16/W32/W64 consumes one DA read slot and one workspace write slot. WSTORE.W128/W256/W512 consumes 2/4/8 DA read slots and 2/4/8 workspace write slots.
- Wide operations reserve their complete source and destination footprints atomically. If either side lacks the required slots, the instruction waits without partial access or partial commit.
- All other register operations compete for the same 32R+32W budget. Unused slots are dynamically available to any ready instruction class.
- These are logical access slots, not a promise of 32 arbitrary physical SRAM addresses being conflict-free. Physical banking, port replication, bank conflicts, and arbitration remain separate microarchitectural constraints.
- XFER.WS.MEM / XFER.WS.START use the independent transfer engine and do not consume RAC register/workspace slots; they do consume physical workspace read bandwidth and reserve their source range for the transfer lifetime.

| Instruction | Direction | Operand bank |
|---|---|---|
| WLOAD.OSSpace / WLOAD.WS | Workspace → DA | DA destination |
| WSTORE.OSSpace / WSTORE.WS | DA → workspace | DA source |

Supported widths: 8, 16, 32, 64, 128, 256, and 512 bits.

Rules:
1. Access is naturally aligned to W/8 bytes.
2. The full byte range must fit in the selected 8 KiB workspace.
3. 128/256/512-bit accesses use 2/4/8 consecutive DA registers; the DA range must not exceed DA31.
4. Little-endian byte order is identical to Data RAM LOAD/STORE.
5. A narrow WLOAD zeroes unused high bits in the destination DA register. WSTORE changes only the selected W bits.
6. All permission, ownership, bounds, alignment, and DA-selector checks occur before architectural commit.
7. A faulting WLOAD leaves every DA destination unchanged. A validation-faulting WSTORE changes no workspace byte.
8. WLOAD/WSTORE are synchronous architectural accesses. Their internal latency and workspace bank/port implementation are microarchitectural.
9. WLOAD/WSTORE reserve both their workspace and DA footprints through the shared RAC. Wide accesses reserve every touched 64-bit lane atomically. If the shared 32R+32W budget is unavailable, the instruction waits without a partial register or workspace operation.

Numeric opcodes and field layouts are assigned in NEXSUS-CPU-INSTRUCTION-ENCODING-001.md: WLOAD=0x89, WSTORE=0x8A, XFER.WS.MEM=0x8B, XFER.WS.START=0x8C; WSMEM uses FMT=1110 and workspace block transfers extend the existing MEMXFER payload.

## 4. Register-bank save and restore

Existing explicit register-transfer instructions are reused; there is no hidden direct workspace↔register alias.

**Save sequence**
1. Preserve original DA values first if the ABI requires them.
2. Move the selected register value into DA using MOV.DA.RA, MOV.DA.FA, or MOV.DA.MA.
3. Use WSTORE.OSSpace/WSTORE.WS to write the DA payload at the chosen workspace offset.

**Restore sequence**
1. WLOAD.OSSpace/WLOAD.WS reads the payload into DA.
2. MOV.RA.DA, MOV.FA.DA, or MOV.MA.DA restores the selected register bank.

The compiler/ABI must track DA staging clobbers. If DA values are live across the save/restore sequence, those DA entries must be preserved before they are used as staging. MA 256-bit values and 512-bit pairs follow the existing DA group and selector-alignment rules.

Example — save one RA register into WS and restore it later:

```asm
MOV.DA.RA     DA0, RA7
WSTORE.WS.W64 [0x000], DA0

; ... RA7 may now be reused ...

WLOAD.WS.W64  DA0, [0x000]
MOV.RA.DA     RA7, DA0
```

This design lets OSSpace/WS hold register snapshots, spill records, call frames, application working structures, and temporary datasets without forcing a LIFO stack abstraction.

## 5. OSSpace/WS → Data RAM block export

`XFER.WS.MEM` copies a selected byte range only from OSSpace or WS into an L1–L4 Data RAM domain. `XFER.WS.START` starts the same one-way export asynchronously; `XFER.WAIT` consumes its completion token. The reverse direction is architecturally forbidden: Data RAM, App RAM, DMA, Fabric, and other cores cannot write OSSpace/WS through this transfer path.

- The source is OSSpace or WS; the destination is an L1–L4 Data RAM domain. Workspace selector, workspace offset, Data RAM byte address, and length are explicit. There is no direction bit.
- Length is an unsigned byte count. A complete 8 KiB workspace can be moved in one operation; partial ranges are also permitted.
- This path uses the transfer engine/Fabric path, not DA staging. It does not consume RAC register-read or register-write slots. By contrast, WLOAD/WSTORE do consume RAC slots for their DA register operands.
- It does consume transfer-engine bandwidth and the relevant Data RAM bank/controller bandwidth. Independent banks/domains may continue in parallel under existing arbitration rules.
- The source workspace range is read-reserved for the transfer lifetime. Workspace is never a destination.
- Data RAM destination ranges use the existing XFER range-reservation and unpublished-destination rules. A destination becomes usable only after successful completion.
- Validation is completed before acceptance. A validation fault starts no payload movement. A runtime multi-beat failure may leave physical destination bytes changed, but the destination range remains logically invalid/unpublished and must be fully overwritten before use.
- Asynchronous transfer tokens retain the existing per-core generation/stale-token rules. XFER.WAIT is the terminal completion boundary.

Assembly form is deliberately source-first and has no reverse form:

```asm
; RA19 = 0, RA20 = Data RAM destination address, RA21 = 8192
XFER.WS.MEM   WS[RA19], [L4:RA20], RA21

; Asynchronous full-workspace save; RA22 receives the token
XFER.WS.START WS[RA19], [L4:RA20], RA21, RA22
XFER.WAIT     RA22
```

Workspace restore is CPU-mediated, not a transfer-engine operation: privileged code LOADs Data RAM into DA staging and then WSTOREs the selected workspace bytes. App RAM is never a data-transfer endpoint; it feeds only the independent CodeFlow instruction-fetch path. Neither path grants another core or DMA agent workspace write authority.

## 6. Permission and fault model

The workspace selector is not an authorization token.

- OSSpace: PL1/PL2 only; PL0 always receives a protection fault.
- WS: PL0 only for the current PL0 application execution context; PL1/PL2 may access it only through controlled scheduler/context-management paths.
- A task cannot address another task's WS image.
- EB, CP0–CP3, and XW are not exposed through these instructions.
- Permission, active application-access epoch, range, alignment, and mapping validation precedes commit.
- Violations use the existing precise protection, alignment, bounds, address-overflow, or memory-access fault path. No denied write may partially commit.

## 7. Open implementation items

- Decoder implementation and validation tests for WLOAD/WSTORE and XFER.WS.*.
- Microarchitectural implementation of the assigned WSMEM and MEMXFER workspace fields.
- Whether indexed workspace addressing is needed in the first encoding revision; base+displacement and absolute offset are the baseline forms.
- Workspace bank count, physical multi-read/write ports, arbitration, bank-conflict policy, and transfer bandwidth; the logical 32R+32W budget is fixed and shared.
- Whether a full-workspace export receives a dedicated fast path or is serviced as a normal bounded block transfer.
- CPU-mediated Data RAM→workspace restore throughput and whether a privileged copy assist is warranted; it must preserve the no-external-writer invariant.
- OS/application exchange-window size and ABI layout. The window is a pair of reserved OSSpace/WS ranges copied by privileged CPU instructions, not a shared alias or DMA destination.

## 8. Related specifications

- NEXSUS-CPU-ISA-001.md
- NEXSUS-CPU-SPM-ACCESS-PROTECTION-001.md
- NEXSUS-CPU-CONTEXT-SAVE-RESTORE-001.md
- NEXSUS-CPU-MEMORY-ACCESS-CONTROL-001.md
- NEXSUS-CPU-INSTRUCTION-ENCODING-001.md
