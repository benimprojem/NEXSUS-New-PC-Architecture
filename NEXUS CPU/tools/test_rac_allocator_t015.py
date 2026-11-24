import unittest

from rac_allocator import RACAllocator, RACRequest


class DynamicRACAllocatorT015(unittest.TestCase):
    def test_shared_pool_dynamically_serves_multiple_register_domains(self):
        rac = RACAllocator()
        requests = [
            RACRequest("ra", reads=tuple(("RA", i, 1) for i in range(24)),
                       writes=tuple(("RA", i, 1) for i in range(12)),
                       queue_class="ARITH"),
            RACRequest("fa", reads=tuple(("FA", i, 1) for i in range(24)),
                       writes=tuple(("FA", 0 + i, 1) for i in range(8)),
                       queue_class="FP"),
            RACRequest("ma", reads=tuple(("MA", i, 4) for i in range(8)),
                       writes=tuple(("MA", 8 + i, 4) for i in range(2)),
                       queue_class="ME512"),
        ]
        result = rac.allocate_cycle(requests)
        self.assertEqual(set(result["accepted"]), {"ra", "fa", "ma"})
        self.assertEqual(result["read_slots_granted"], 80)
        self.assertEqual(result["write_slots_granted"], 28)

    def test_instruction_reservation_is_atomic_when_read_budget_is_exceeded(self):
        rac = RACAllocator(read_budget=80, write_budget=64)
        too_wide = RACRequest(
            "too-wide", reads=tuple(("MA", i, 4) for i in range(21)),
            writes=(("MA", 30, 4),),
        )
        small = RACRequest("small", reads=(("RA", 0, 1),), writes=(("RA", 1, 1),))
        result = rac.allocate_cycle([too_wide, small])
        self.assertEqual(result["accepted"], ["small"])
        self.assertIn("exceeds RAC read budget", result["rejected"]["too-wide"])
        self.assertEqual(result["read_slots_granted"], 1)
        self.assertEqual(result["write_slots_granted"], 1)

    def test_same_destination_multiwrite_is_rejected_without_blocking_other_banks(self):
        rac = RACAllocator()
        requests = [
            RACRequest("ra-writer", writes=(("RA", 3, 1),), age=10),
            RACRequest("fa-writer", writes=(("RA", 3, 1),), age=5),
            RACRequest("ma-writer", writes=(("MA", 3, 4),), age=1),
        ]
        result = rac.allocate_cycle(requests)
        self.assertEqual(result["accepted"], ["ra-writer", "ma-writer"])
        self.assertEqual(result["rejected"]["fa-writer"], "same-destination write conflict")
        self.assertEqual(result["write_slots_granted"], 5)

    def test_multiple_physical_banks_accept_parallel_writes(self):
        rac = RACAllocator()
        requests = [
            RACRequest("ra", writes=(("RA", 0, 1),)),
            RACRequest("fa", writes=(("FA", 0, 1),)),
            RACRequest("da", writes=(("DA", 0, 1),)),
            RACRequest("ma", writes=(("MA", 0, 4),)),
        ]
        result = rac.allocate_cycle(
            requests,
            physical_write_ports={"RA": 1, "FA": 1, "DA": 1, "MA": 1},
        )
        self.assertEqual(set(result["accepted"]), {"ra", "fa", "da", "ma"})
        self.assertEqual(result["write_slots_granted"], 7)
        self.assertEqual(result["physical_writes"], {"RA": 1, "FA": 1, "DA": 1, "MA": 1})

    def test_physical_bank_conflict_does_not_waste_other_bank_capacity(self):
        rac = RACAllocator()
        requests = [
            RACRequest("old-ra", reads=(("RA", 0, 1),), age=10),
            RACRequest("blocked-ra", reads=(("RA", 1, 1),), age=9),
            RACRequest("ready-fa", reads=(("FA", 0, 1),), age=1),
        ]
        result = rac.allocate_cycle(
            requests, physical_read_ports={"RA": 1, "FA": 1}
        )
        self.assertEqual(result["accepted"], ["old-ra", "ready-fa"])
        self.assertEqual(result["rejected"]["blocked-ra"], "RA physical read-port conflict")
        retry = rac.allocate_cycle(
            [requests[1]], physical_read_ports={"RA": 1}
        )
        self.assertEqual(retry["accepted"], ["blocked-ra"])

    def test_logical_write_budget_is_independent_of_physical_bank_ports(self):
        rac = RACAllocator(read_budget=80, write_budget=4)
        requests = [
            RACRequest("four", writes=tuple(("RA", i, 1) for i in range(4))),
            RACRequest("one-more", writes=(("FA", 0, 1),)),
        ]
        result = rac.allocate_cycle(
            requests, physical_write_ports={"RA": 4, "FA": 1}
        )
        self.assertEqual(result["accepted"], ["four"])
        self.assertEqual(result["rejected"]["one-more"], "RAC write budget exhausted")
        self.assertEqual(result["write_slots_granted"], 4)


if __name__ == "__main__":
    unittest.main(verbosity=2)
