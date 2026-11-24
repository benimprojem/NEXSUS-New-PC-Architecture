"""Logical architectural register-bank model for NEX-T007.

This model validates the fixed architectural organization only. Physical port counts,
replication, arbitration and forwarding timing remain configurable/open assumptions.
"""
from dataclasses import dataclass, field

BANK_LAYOUT = {
    "RA": (32, 64),
    "FA": (32, 64),
    "DA": (32, 64),
    "MA": (32, 256),
}
RA_VIEWS = {"RB": 32, "RC": 16, "RD": 8}


class RegisterAccessError(ValueError):
    pass


@dataclass
class RegisterFile:
    values: dict = field(default_factory=lambda: {
        name: [0] * count for name, (count, _width) in BANK_LAYOUT.items()
    })

    def _check(self, bank, index):
        if bank not in BANK_LAYOUT:
            raise RegisterAccessError(f"unknown bank: {bank}")
        count, _ = BANK_LAYOUT[bank]
        if not isinstance(index, int) or not 0 <= index < count:
            raise RegisterAccessError(f"{bank} index out of range: {index}")

    def read(self, bank, index):
        self._check(bank, index)
        return self.values[bank][index]

    def write(self, bank, index, value):
        self._check(bank, index)
        _count, width = BANK_LAYOUT[bank]
        if not isinstance(value, int) or value < 0 or value >= (1 << width):
            raise RegisterAccessError(f"value does not fit {bank}{index} ({width} bits)")
        self.values[bank][index] = value

    def read_ra_view(self, view, index):
        if view not in RA_VIEWS:
            raise RegisterAccessError(f"unknown RA view: {view}")
        value = self.read("RA", index)
        return value & ((1 << RA_VIEWS[view]) - 1)

    def write_ra_view(self, view, index, value):
        if view not in RA_VIEWS:
            raise RegisterAccessError(f"unknown RA view: {view}")
        bits = RA_VIEWS[view]
        if not isinstance(value, int) or value < 0 or value >= (1 << bits):
            raise RegisterAccessError(f"value does not fit {view} ({bits} bits)")
        old = self.read("RA", index)
        mask = (1 << bits) - 1
        self.write("RA", index, (old & ~mask) | value)

    def read_pair(self, bank, even_index):
        self._check(bank, even_index)
        count, width = BANK_LAYOUT[bank]
        if even_index % 2 or even_index + 1 >= count:
            raise RegisterAccessError(f"{bank} pair must start at a valid even index")
        low = self.read(bank, even_index)
        high = self.read(bank, even_index + 1)
        return low | (high << width)

    def write_pair(self, bank, even_index, value):
        self._check(bank, even_index)
        count, width = BANK_LAYOUT[bank]
        if even_index % 2 or even_index + 1 >= count:
            raise RegisterAccessError(f"{bank} pair must start at a valid even index")
        if not isinstance(value, int) or value < 0 or value >= (1 << (2 * width)):
            raise RegisterAccessError(f"value does not fit {bank} pair ({2 * width} bits)")
        mask = (1 << width) - 1
        self.write(bank, even_index, value & mask)
        self.write(bank, even_index + 1, value >> width)

    def access_cycle(self, reads, writes, *, read_ports, write_ports, forwarding=False):
        """Execute a logical cycle using caller-supplied port budgets.

        Port budgets are mandatory test parameters, not architecture defaults.
        Reads are read-first unless explicit same-cycle forwarding is enabled.
        """
        if not isinstance(read_ports, dict) or not isinstance(write_ports, dict):
            raise RegisterAccessError("explicit per-bank port budgets are required")
        read_counts, write_counts = {}, {}
        for bank, index in reads:
            self._check(bank, index)
            read_counts[bank] = read_counts.get(bank, 0) + 1
        for bank, index, _value in writes:
            self._check(bank, index)
            write_counts[bank] = write_counts.get(bank, 0) + 1
        for bank, count in read_counts.items():
            if bank not in read_ports or count > read_ports[bank]:
                raise RegisterAccessError(f"{bank} read-port conflict: {count}")
        for bank, count in write_counts.items():
            if bank not in write_ports or count > write_ports[bank]:
                raise RegisterAccessError(f"{bank} write-port conflict: {count}")
        pending = {(bank, index): value for bank, index, value in writes}
        results = []
        for bank, index in reads:
            if forwarding and (bank, index) in pending:
                results.append(pending[(bank, index)])
            else:
                results.append(self.read(bank, index))
        # Commit only after all accesses have passed validation.
        for bank, index, value in writes:
            self.write(bank, index, value)
        return results


# RAC accounting uses 64-bit logical lanes, including wide MA entries.
RAC_READ_BUDGET = 80
RAC_WRITE_BUDGET = 64
MA_ENTRY_BITS = 256
RAC_LANE_BITS = 64


def ma_tile_entries(n, element_width):
    """Return the complete MA-entry count for one supported square tile."""
    supported = {
        2: {8, 16, 32, 64},
        4: {8, 16, 32, 64},
        8: {8, 16, 32},
    }
    if n not in supported or element_width not in supported[n]:
        raise RegisterAccessError(
            f"unsupported MA tile configuration: N={n}, W={element_width}"
        )
    return (n * n * element_width + MA_ENTRY_BITS - 1) // MA_ENTRY_BITS


def ma_reduction_output_entries(n, element_width):
    """Return the MA-entry count for a lossless row/column reduction result."""
    ma_tile_entries(n, element_width)  # validate N/W against the ISA tile table
    accumulator_width = element_width + (n - 1).bit_length()
    return (n * accumulator_width + MA_ENTRY_BITS - 1) // MA_ENTRY_BITS


def ma_opcode_rac_footprint(opcode, *, n=None, element_width=None):
    """Return (logical 64-bit RAC read slots, write slots) for an MA opcode.

    Each 256-bit MA entry costs four logical 64-bit slots. This is operand
    accounting, not a claim about physical SRAM ports or execution latency.
    """
    op = opcode.upper()
    fixed = {
        "VEC_R3": (8, 4),   # two MA sources, one MA destination
        "VMACC": (12, 4),   # A, B, accumulator -> D
        "VSUM": (4, 4),     # one MA source -> one MA destination
        "VDOT": (8, 4),     # A, B -> one MA destination
        "ME512_PAIR": (8, 8),
    }
    if op in fixed:
        return fixed[op]
    if n is None or element_width is None:
        raise RegisterAccessError(f"{op} requires tile N and element width W")
    t = ma_tile_entries(n, element_width)
    if op == "MMUL":
        return 8 * t, 4 * t
    if op == "MMAC":
        return 12 * t, 4 * t
    if op == "MTRANS":
        return 4 * t, 4 * t
    if op == "MREDUCE":
        out = ma_reduction_output_entries(n, element_width)
        return 4 * t, 4 * out
    raise RegisterAccessError(f"unknown MA opcode footprint: {opcode}")
