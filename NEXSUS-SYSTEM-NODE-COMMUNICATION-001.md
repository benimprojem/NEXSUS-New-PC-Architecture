# NEXSUS Node Communication and Task Notification Model

**Document:** NEXSUS-SYSTEM-NODE-COMMUNICATION-001  
**Status:** Architecture baseline / protocol details pending  
**Scope:** CPU, shared memory, target nodes and System Fabric

## 1. Core principle

The CPU does not directly push payload data into another hardware node. CPU-side work is staged in an agreed memory domain; the CPU publishes a task header/notification containing the task identity and the payload address/descriptor to the target node.

The target node obtains the payload by requesting it through System Fabric. Fabric performs the actual node-to-node or memory-to-node data movement according to routing, permissions, arbitration and transfer rules.

**CPU responsibility:** prepare data, write task descriptor/header, publish it, and notify the target.  
**Target-node responsibility:** receive notification, validate/accept task, request required data through Fabric, execute, and publish completion/status.  
**System Fabric responsibility:** route requests, resolve source/destination endpoints, arbitrate resources, transfer payload, and return transfer/completion responses.

A notification is control metadata, not the payload itself. Sending a task address does not mean payload bytes were copied to the target.

## 2. Logical flow

1. CPU prepares payload in a permitted shared memory domain (for example a suitable L2/L3/L4 zone or another explicitly accessible memory region).
2. CPU writes a task descriptor/header. At minimum it identifies task type, target node, payload address/domain, payload length or descriptor size, and task/sequence identity. Additional flags, dependencies and completion destination may be defined by the task protocol.
3. CPU publishes the descriptor and payload with the required memory-ordering/release semantics.
4. CPU issues a **task notification** to the target node. The notification carries a descriptor address/handle and task identity; it does not carry the payload.
5. Target node receives the notification and requests the descriptor/payload through System Fabric.
6. Fabric routes the request, checks endpoint/domain permissions and resource availability, and performs the data transfer.
7. Target node executes the task and writes completion/status into the agreed completion area or sends a completion notification through the system notification mechanism.
8. CPU or another interested node observes completion using the defined acquire/synchronization protocol before consuming results.

## 3. Separation of planes

- **Payload/data plane:** bulk bytes moved by Fabric between memory and target node, or between permitted nodes.
- **Task/control plane:** task header, address/handle, notification, acceptance, completion, error and cancellation metadata.
- **Synchronization plane:** publish/consume ordering, ownership, lifetime, visibility and completion guarantees.
- These planes may share physical Fabric links, but they are distinct architectural transactions and must not be conflated.

## 4. Required guarantees

- Notification must not make an unpublished or partially prepared descriptor/payload visible as a valid task.
- Target must validate task identity, descriptor bounds, permissions and supported task type before requesting data.
- Fabric must not treat a descriptor address as permission by itself; access control is checked independently.
- Payload transfer is not assumed atomic. Target must not consume incomplete payload.
- Completion means the target's specified work and result publication have reached the task protocol's defined completion point—not merely that a request was accepted.
- Duplicate, stale, reordered or lost notifications must be handled by task identity/sequence and protocol state. Exact retry/idempotency behavior remains to be specified.
- CPU does not bypass Fabric by directly writing target-node private memory.
- A node may request only the payload/regions authorized by its task descriptor and access policy.

## 5. Minimal task descriptor (conceptual, not frozen binary layout)

| Field | Purpose |
|---|---|
| TASK_ID / SEQUENCE | Distinguish tasks and stale/duplicate notifications |
| TARGET_NODE | Intended execution node |
| TASK_TYPE / FLAGS | Operation class and options |
| PAYLOAD_DOMAIN | Memory domain containing payload |
| PAYLOAD_ADDRESS or HANDLE | Payload start/descriptor reference |
| PAYLOAD_LENGTH | Bytes or descriptor-defined extent |
| DEPENDENCY / VERSION | Optional prerequisite or data version |
| COMPLETION_REFERENCE | Where status/result notification is published |

The exact field widths, alignment, descriptor versioning, queue layout and notification encoding are open.

## 6. Notification is not payload transfer

The CPU's task notification may be a small control transaction (for example a Fabric-routed doorbell/message containing descriptor reference and task ID). It must not be modeled as CPU-to-node payload push.

The notification mechanism's physical implementation—dedicated notification wires, Fabric control packets, node mailboxes, queue polling, or a hybrid—is not yet selected. Regardless of implementation, the architectural contract remains: **CPU publishes address/descriptor + task notice; target requests payload; Fabric moves payload.**

## 7. Open design items

- Node addressing and discovery: node ID, node class, endpoint/port addressing.
- Task queues: per-node queue, shared queue, or hybrid; producer/consumer ownership.
- Notification delivery: reliable, ordered, retry, acknowledgment and backpressure.
- Fabric request/response packet fields and routing topology.
- Payload access grants, protection domains and isolation.
- Task acceptance vs task completion states.
- Error codes, cancellation, timeout and recovery.
- IRQ integration: node completion/error raises routed interrupt or event.
- Multi-node dependencies and task chaining.
- Memory consistency rules for descriptor publication and payload visibility.
- Whether nodes can exchange data directly via Fabric without CPU mediation after task authorization.

## 8. Relationship to CPU memory ISA

- CPU LOAD/STORE and ATOM operate on CPU-visible memory domains.
- Register-bank XFER is CPU-local register transfer.
- Lx XFER.MEM/START/WAIT is CPU-controlled memory-domain copy.
- Node task notification is a control-plane operation; it is not a LOAD/STORE, register XFER, or Lx memory copy.
- System Fabric owns node request routing and payload movement.
- A future CPU instruction or privileged interface may publish/notify a task, but its opcode and exact interface must be designed only after the Fabric control protocol is specified.
