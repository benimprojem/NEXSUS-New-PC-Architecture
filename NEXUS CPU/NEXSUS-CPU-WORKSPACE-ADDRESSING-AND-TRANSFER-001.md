# NEXSUS CPU — Workspace Addressing and Transfer

**Document ID:** NEXSUS-CPU-WORKSPACE-ADDRESSING-AND-TRANSFER-001  
**Status:** ISA/architecture proposal — semantic baseline; numeric encoding open  
**Scope:** Direct byte addressing, DA-staged register save/restore, and OW/TW↔Data RAM block movement

## 1. Design intent

Operating-System Workspace (OW) and Task Workspace (TW) are directly addressable local working files, not hardware stacks. Software may use them as stack-like frames, fixed-offset records, arrays, temporary structures, or any combination. No mandatory LIFO discipline is imposed.

Both workspaces have an 8 KiB capacity per core. OW remains OS-owned; TW belongs to the currently executing task on that core. Addressability does not change those permission and ownership boundaries.

## 2. Address space

| Property | OW | TW |
|---|---:|---:|
| Capacity | 8 KiB | 8 KiB |
| Address unit | Byte | Byte |
| Valid offset | 0–8191 | 0–8191 |
| Scope | Core-local | Core-local |
| PL0 | Denied | Current owner only |
| PL1/PL2 | Allowed | Controlled management/save/restore |

Workspace offsets are relative to the selected workspace and are not Data RAM physical addresses. The architectural forms are:

```asm
WLOAD.TW.W64  DA0, [0x120]
WSTORE.TW.W64 [0x120], DA0

WLOAD.TW.W64  DA1, [RA4 + 0x120]
WSTORE.OW.W64 [RA5 + 0x40], DA2
```

The immediate form denotes an absolute workspace-relative byte offset. The RA form denotes a base register containing a workspace-relative offset plus a signed byte displacement. The complete effective range must remain inside 0–8191; wrapping is forbidden.

## 3. WLOAD / WSTORE

WLOAD and WSTORE are the scalar/vector-width access path between a workspace and the DA staging bank.

| Instruction | Direction | Operand bank |
|---|---|---|
| WLOAD.OW / WLOAD.TW | Workspace → DA | DA destination |
| WSTORE.OW / WSTORE.TW | DA → workspace | DA source |

Supported widths: 8, 16, 32, 64, 128, 256, and 512 bits.

Rules:
1. Access is naturally aligned to W/8 bytes.
2. The full byte range must fit in the selected 8 KiB workspace.
3. 128/256/512-bit accesses use 2/4/8 consecutive DA registers; the DA range must not exceed DA31.
4. Little-endian byte order is identical to Data RAM LOAD/STORE.
5. A narrow WLOAD zeroes unused high bits in the destination DA register. WSTORE changes only the selected W bits.
6. All permission, ownership, bounds, alignment, and DA-selector checks occur before architectural commit.
7. A faulting WLOAD leaves every DA destination unchanged. A validation-faulting WSTORE changes no workspace byte.
8. WLOAD/WSTORE are synchronous architectural accesses. Their internal latency and bank/port implementation are microarchitectural.

Numeric opcodes and field layouts are assigned in NEXSUS-CPU-INSTRUCTION-ENCODING-001.md: WLOAD=0x89, WSTORE=0x8A, XFER.WS.MEM=0x8B, XFER.WS.START=0x8C; WSMEM uses FMT=1110 and workspace block transfers extend the existing MEMXFER payload.

## 4. Register-bank save and restore

Existing explicit register-transfer instructions are reused; there is no hidden direct workspace↔register alias.

**Save sequence**
1. Preserve original DA values first if the ABI requires them.
2. Move the selected register value into DA using MOV.DA.RA, MOV.DA.FA, or MOV.DA.MA.
3. Use WSTORE.OW/WSTORE.TW to write the DA payload at the chosen workspace offset.

**Restore sequence**
1. WLOAD.OW/WLOAD.TW reads the payload into DA.
2. MOV.RA.DA, MOV.FA.DA, or MOV.MA.DA restores the selected register bank.

The compiler/ABI must track DA staging clobbers. If DA values are live across the save/restore sequence, those DA entries must be preserved before they are used as staging. MA 256-bit values and 512-bit pairs follow the existing DA group and selector-alignment rules.

This design lets OW/TW hold register snapshots, spill records, call frames, task-local structures, and temporary datasets without forcing a LIFO stack abstraction.

## 5. OW/TW ↔ Data RAM block transfer

`XFER.WS.MEM` copies a selected byte range directly between OW or TW and an L1–L4 Data RAM domain. `XFER.WS.START` starts the same transfer asynchronously; the existing `XFER.WAIT` consumes its completion token.

- Source and destination are explicit: workspace selector, workspace offset, Data RAM domain, Data RAM byte address, length, and direction.
- Length is an unsigned byte count. A complete 8 KiB workspace can be moved in one operation; partial ranges are also permitted.
- This path uses the transfer engine/Fabric path, not DA staging. It does not consume RAC register-read or register-write slots.
- It does consume transfer-engine bandwidth and the relevant Data RAM bank/controller bandwidth. Independent banks/domains may continue in parallel under existing arbitration rules.
- The source workspace range is read-reserved for the transfer lifetime. A destination workspace range is write-reserved and inaccessible to CPU reads/writes until completion.
- Data RAM destination ranges use the existing XFER range-reservation and unpublished-destination rules. A destination becomes usable only after successful completion.
- Validation is completed before acceptance. A validation fault starts no payload movement. A runtime multi-beat failure may leave physical destination bytes changed, but the destination range remains logically invalid/unpublished and must be fully overwritten before use.
- Asynchronous transfer tokens retain the existing per-core generation/stale-token rules. XFER.WAIT is the terminal completion boundary.

Assembly form uses the workspace offset in the RA selector and the Data RAM byte address in the other RA selector:

```asm
; RA19 = 0, RA20 = Data RAM destination address, RA21 = 8192
XFER.WS.MEM   TW[RA19], [L4:RA20], RA21

; Reverse direction: Data RAM source → TW
XFER.WS.MEM   [L4:RA20], TW[RA19], RA21

; Asynchronous full-workspace save; RA22 receives the token
XFER.WS.START TW[RA19], [L4:RA20], RA21, RA22
XFER.WAIT     RA22
```

For the reverse asynchronous direction, the workspace is the destination endpoint and is write-reserved until WAIT completes. The transfer engine does not implicitly change task ownership or grant cross-core access. The Data RAM destination still requires the active task/OS permission and domain grant.

## 6. Permission and fault model

The workspace selector is not an authorization token.

- OW: PL1/PL2 only; PL0 always receives a protection fault.
- TW: PL0 only for the currently executing task that owns the local TW; PL1/PL2 may access it only through controlled scheduler/context-management paths.
- A task cannot address another task's TW image.
- EB, CP0–CP3, and XW are not exposed through these instructions.
- Permission, owner/generation, range, alignment, and mapping validation precedes commit.
- Violations use the existing precise protection, alignment, bounds, address-overflow, or memory-access fault path. No denied write may partially commit.

## 7. Open implementation items

- Decoder implementation and validation tests for WLOAD/WSTORE and XFER.WS.*.
- Microarchitectural implementation of the assigned WSMEM and MEMXFER workspace fields.
- Whether indexed workspace addressing is needed in the first encoding revision; base+displacement and absolute offset are the baseline forms.
- Workspace bank count, multi-read/write ports, arbitration, and transfer bandwidth.
- Whether a full-workspace transfer receives a dedicated fast path or is serviced as a normal bounded block transfer.

## 8. Related specifications

- NEXSUS-CPU-ISA-001.md
- NEXSUS-CPU-SPM-ACCESS-PROTECTION-001.md
- NEXSUS-CPU-CONTEXT-SAVE-RESTORE-001.md
- NEXSUS-CPU-MEMORY-ACCESS-CONTROL-001.md
- NEXSUS-CPU-INSTRUCTION-ENCODING-001.md
