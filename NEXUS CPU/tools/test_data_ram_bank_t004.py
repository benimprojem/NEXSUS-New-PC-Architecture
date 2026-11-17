"""NEX-T004: Data RAM bank mapping, concurrency and wide-access contract."""
from data_ram_bank_model import DataRamBankGroup


def test_width_to_bank_slices():
    expected = {8: 1, 16: 2, 32: 4, 64: 8}
    for width, count in expected.items():
        group = DataRamBankGroup("low")
        row = group.reserve(0, f"w{width}", 0, width)
        assert row["bank_count_touched"] == count, (width, row)
        assert len(row["bank_beats"]) == count


def test_distinct_banks_overlap_and_same_bank_serializes():
    group = DataRamBankGroup("low")
    rows = group.reserve_batch(0, [
        {"id": "bank0", "address": 0, "width": 8},
        {"id": "bank1", "address": 8, "width": 8},
        {"id": "bank0_again", "address": 0, "width": 8},
    ])
    assert rows[0]["service_complete_cycle"] == 1
    assert rows[1]["service_complete_cycle"] == 1
    assert rows[2]["service_complete_cycle"] == 2
    assert group.bank_next_cycle[0] == 2
    assert group.bank_next_cycle[1] == 1


def test_misaligned_wide_access_crossing_is_rejected_atomically():
    group = DataRamBankGroup("low")
    before = list(group.bank_next_cycle)
    try:
        group.reserve(0, "crossing-128", 56, 16)
    except ValueError as error:
        assert "naturally aligned" in str(error)
    else:
        raise AssertionError("misaligned stripe-crossing access was accepted")
    assert group.bank_next_cycle == before
    assert group.events == []


def test_folded_mapping_spreads_64_byte_stride_stream():
    group = DataRamBankGroup("folded")
    rows = [group.reserve(0, f"r{i}", i * 64, 8) for i in range(8)]
    assert len({row["unique_banks"][0] for row in rows}) == 8


def test_all_or_none_validation_has_no_partial_reservation():
    group = DataRamBankGroup("low")
    before = list(group.bank_next_cycle)
    try:
        group.reserve(0, "bad-wide", 8, 16)  # not naturally aligned
    except ValueError:
        pass
    else:
        raise AssertionError("misaligned wide access was accepted")
    assert group.bank_next_cycle == before
    assert group.events == []


if __name__ == "__main__":
    test_width_to_bank_slices()
    test_distinct_banks_overlap_and_same_bank_serializes()
    test_misaligned_wide_access_crossing_is_rejected_atomically()
    test_folded_mapping_spreads_64_byte_stride_stream()
    test_all_or_none_validation_has_no_partial_reservation()
    print("PASS NEX-T004: width mapping, independent banks, local conflicts, stripe crossing and atomic admission.")
    print("SCOPE: one 8-bank group; group count/placement and Fabric arbitration are not modeled.")
