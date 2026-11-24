"""Dynamic logical RAC admission model for one NEXSUS core.

The 80R/64W limits count logical 64-bit lanes. Physical register-bank port
limits are optional, separately supplied implementation constraints.
"""
from dataclasses import dataclass, field


@dataclass(frozen=True)
class RACRequest:
    request_id: str
    reads: tuple = ()
    writes: tuple = ()
    queue_class: str = "UNSPECIFIED"
    age: int = 0


@dataclass
class RACAllocator:
    read_budget: int = 80
    write_budget: int = 64
    waiting_age: dict = field(default_factory=dict)

    def __post_init__(self):
        if self.read_budget < 0 or self.write_budget < 0:
            raise ValueError("RAC budgets must be non-negative")

    @staticmethod
    def _validate_accesses(request, accesses, kind):
        normalized = []
        for access in accesses:
            if not isinstance(access, (tuple, list)) or len(access) != 3:
                raise ValueError(
                    f"{request.request_id}: {kind} access must be (bank, index, slots)"
                )
            bank, index, slots = access
            if not isinstance(bank, str) or not bank:
                raise ValueError(f"{request.request_id}: invalid bank name")
            if not isinstance(index, int) or index < 0:
                raise ValueError(f"{request.request_id}: invalid {bank} index")
            if not isinstance(slots, int) or slots < 1:
                raise ValueError(f"{request.request_id}: invalid {bank} slot width")
            normalized.append((bank, index, slots))
        return normalized

    def allocate_cycle(self, requests, *, physical_read_ports=None,
                       physical_write_ports=None):
        """Grant complete instruction footprints in age-prioritized, work-
        conserving order. Blocked instructions reserve nothing.

        A physical port map is keyed by bank name (RA/FA/DA/MA/WS/OS) and
        counts register/workspace entries, while logical RAC budgets count
        64-bit slots. If a physical map is supplied, an omitted bank has zero
        available ports for that direction.
        """
        requests = list(requests)
        ids = [r.request_id for r in requests]
        if len(ids) != len(set(ids)):
            raise ValueError("RAC request IDs must be unique within a cycle")
        if any(not isinstance(r, RACRequest) for r in requests):
            raise TypeError("allocate_cycle expects RACRequest instances")

        indexed = list(enumerate(requests))
        indexed.sort(
            key=lambda item: (
                -self.waiting_age.get(item[1].request_id, 0),
                -item[1].age,
                item[0],
            )
        )

        read_used = write_used = 0
        physical_reads = {}
        physical_writes = {}
        destinations = set()
        accepted = []
        rejected = {}

        for _position, request in indexed:
            reads = self._validate_accesses(request, request.reads, "read")
            writes = self._validate_accesses(request, request.writes, "write")
            request_read_slots = sum(slots for _bank, _index, slots in reads)
            request_write_slots = sum(slots for _bank, _index, slots in writes)

            if request_read_slots > self.read_budget:
                rejected[request.request_id] = "single instruction exceeds RAC read budget"
                self.waiting_age.pop(request.request_id, None)
                continue
            if request_write_slots > self.write_budget:
                rejected[request.request_id] = "single instruction exceeds RAC write budget"
                self.waiting_age.pop(request.request_id, None)
                continue

            request_destinations = [(bank, index) for bank, index, _slots in writes]
            if len(request_destinations) != len(set(request_destinations)):
                rejected[request.request_id] = "duplicate destination inside instruction"
                self.waiting_age.pop(request.request_id, None)
                continue
            if any(destination in destinations for destination in request_destinations):
                rejected[request.request_id] = "same-destination write conflict"
                self.waiting_age[request.request_id] = (
                    self.waiting_age.get(request.request_id, 0) + 1
                )
                continue

            if read_used + request_read_slots > self.read_budget:
                rejected[request.request_id] = "RAC read budget exhausted"
                self.waiting_age[request.request_id] = (
                    self.waiting_age.get(request.request_id, 0) + 1
                )
                continue
            if write_used + request_write_slots > self.write_budget:
                rejected[request.request_id] = "RAC write budget exhausted"
                self.waiting_age[request.request_id] = (
                    self.waiting_age.get(request.request_id, 0) + 1
                )
                continue

            read_counts = {}
            write_counts = {}
            for bank, _index, _slots in reads:
                read_counts[bank] = read_counts.get(bank, 0) + 1
            for bank, _index, _slots in writes:
                write_counts[bank] = write_counts.get(bank, 0) + 1

            physical_conflict = None
            if physical_read_ports is not None:
                for bank, count in read_counts.items():
                    capacity = physical_read_ports.get(bank, 0)
                    if physical_reads.get(bank, 0) + count > capacity:
                        physical_conflict = f"{bank} physical read-port conflict"
                        break
            if physical_conflict is None and physical_write_ports is not None:
                for bank, count in write_counts.items():
                    capacity = physical_write_ports.get(bank, 0)
                    if physical_writes.get(bank, 0) + count > capacity:
                        physical_conflict = f"{bank} physical write-port conflict"
                        break
            if physical_conflict:
                rejected[request.request_id] = physical_conflict
                self.waiting_age[request.request_id] = (
                    self.waiting_age.get(request.request_id, 0) + 1
                )
                continue

            accepted.append(request.request_id)
            read_used += request_read_slots
            write_used += request_write_slots
            destinations.update(request_destinations)
            for bank, count in read_counts.items():
                physical_reads[bank] = physical_reads.get(bank, 0) + count
            for bank, count in write_counts.items():
                physical_writes[bank] = physical_writes.get(bank, 0) + count
            self.waiting_age.pop(request.request_id, None)

        return {
            "accepted": accepted,
            "rejected": rejected,
            "read_slots_granted": read_used,
            "write_slots_granted": write_used,
            "physical_reads": physical_reads,
            "physical_writes": physical_writes,
        }
