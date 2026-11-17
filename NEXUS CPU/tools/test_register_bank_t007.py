import unittest

from register_bank_model import (
    BANK_LAYOUT, RA_VIEWS, RegisterAccessError, RegisterFile,
)


class RegisterBankConnectivityT007(unittest.TestCase):
    def test_architectural_bank_sizes_and_widths(self):
        self.assertEqual(BANK_LAYOUT, {
            "RA": (32, 64), "FA": (32, 64),
            "DA": (32, 64), "MA": (32, 256),
        })
        self.assertEqual(RA_VIEWS, {"RB": 32, "RC": 16, "RD": 8})
        total_bytes = sum(count * width // 8 for count, width in BANK_LAYOUT.values())
        self.assertEqual(total_bytes, 1792)

    def test_all_banks_are_independently_readable_and_writable(self):
        rf = RegisterFile()
        values = {"RA": 0x1234, "FA": 0x2345, "DA": 0x3456, "MA": (1 << 200) + 7}
        for bank, value in values.items():
            rf.write(bank, 7, value)
        for bank, value in values.items():
            self.assertEqual(rf.read(bank, 7), value)

    def test_ra_low_width_views_alias_same_physical_entry(self):
        rf = RegisterFile()
        rf.write("RA", 3, 0x1122334455667788)
        self.assertEqual(rf.read_ra_view("RB", 3), 0x55667788)
        self.assertEqual(rf.read_ra_view("RC", 3), 0x7788)
        self.assertEqual(rf.read_ra_view("RD", 3), 0x88)
        rf.write_ra_view("RD", 3, 0xAA)
        self.assertEqual(rf.read("RA", 3), 0x11223344556677AA)

    def test_fp128_uses_even_fa_pair(self):
        rf = RegisterFile()
        value = (0xFEDCBA9876543210 << 64) | 0x0123456789ABCDEF
        rf.write_pair("FA", 4, value)
        self.assertEqual(rf.read_pair("FA", 4), value)
        with self.assertRaises(RegisterAccessError):
            rf.read_pair("FA", 3)
        with self.assertRaises(RegisterAccessError):
            rf.write_pair("FA", 31, value)

    def test_me512_uses_even_ma_pair_and_round_trips(self):
        rf = RegisterFile()
        value = (1 << 500) | (1 << 256) | 0xA5
        rf.write_pair("MA", 12, value)
        self.assertEqual(rf.read_pair("MA", 12), value)
        with self.assertRaises(RegisterAccessError):
            rf.read_pair("MA", 13)

    def test_simultaneous_cross_bank_reads_and_writes(self):
        rf = RegisterFile()
        rf.write("RA", 0, 10)
        rf.write("FA", 0, 20)
        rf.write("DA", 0, 30)
        rf.write("MA", 0, 40)
        result = rf.access_cycle(
            [("RA", 0), ("FA", 0), ("DA", 0), ("MA", 0)],
            [("RA", 1, 11), ("FA", 1, 21), ("DA", 1, 31), ("MA", 1, 41)],
            read_ports={"RA": 1, "FA": 1, "DA": 1, "MA": 1},
            write_ports={"RA": 1, "FA": 1, "DA": 1, "MA": 1},
        )
        self.assertEqual(result, [10, 20, 30, 40])
        self.assertEqual([rf.read(b, 1) for b in ("RA", "FA", "DA", "MA")],
                         [11, 21, 31, 41])

    def test_port_conflicts_are_parameterized_not_architecture_defaults(self):
        rf = RegisterFile()
        with self.assertRaisesRegex(RegisterAccessError, "RA read-port conflict"):
            rf.access_cycle(
                [("RA", 0), ("RA", 1)], [],
                read_ports={"RA": 1}, write_ports={"RA": 1},
            )
        # A different explicit port budget admits the same logical accesses.
        self.assertEqual(
            rf.access_cycle(
                [("RA", 0), ("RA", 1)], [],
                read_ports={"RA": 2}, write_ports={"RA": 1},
            ),
            [0, 0],
        )

    def test_writeback_conflict_is_reported_without_partial_commit(self):
        rf = RegisterFile()
        with self.assertRaisesRegex(RegisterAccessError, "RA write-port conflict"):
            rf.access_cycle(
                [], [("RA", 0, 1), ("RA", 1, 2)],
                read_ports={"RA": 1}, write_ports={"RA": 1},
            )
        self.assertEqual(rf.read("RA", 0), 0)
        self.assertEqual(rf.read("RA", 1), 0)

    def test_forwarding_is_explicit_and_read_first_is_default(self):
        rf = RegisterFile()
        rf.write("RA", 2, 5)
        read = [("RA", 2)]
        write = [("RA", 2, 9)]
        self.assertEqual(rf.access_cycle(
            read, write, read_ports={"RA": 1}, write_ports={"RA": 1}
        ), [5])
        rf.write("RA", 2, 5)
        self.assertEqual(rf.access_cycle(
            read, write, read_ports={"RA": 1}, write_ports={"RA": 1},
            forwarding=True,
        ), [9])
        self.assertEqual(rf.read("RA", 2), 9)


if __name__ == "__main__":
    unittest.main()
