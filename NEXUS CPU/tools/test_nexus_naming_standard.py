#!/usr/bin/env python3
"""Guard canonical NEXSUS workspace naming and singleton suffix policy."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EN = ROOT / "NEXUS CPU" / "NEXSUS-CPU-CODEFLOW-NAMING-001.md"
TR = ROOT / "Türkçe" / "NEXSUS-CPU-CODEFLOW-NAMING-001.md"
en, tr = EN.read_text(encoding="utf-8"), TR.read_text(encoding="utf-8")

required = {
    "Execution Buffer": "EB",
    "OS Workspace": "OW",
    "Task Workspace": "TW",
    "Context Pool": "CP0–CP3",
    "Exception Workspace": "XW",
    "Code Cache": "C0",
    "Code Slots": "CS0–CS7",
}
for name, symbol in required.items():
    assert name in en and symbol in en, (name, symbol, "English naming decision")
    assert name in tr and symbol in tr, (name, symbol, "Turkish naming decision")

assert "single instance has no numeric suffix" in en
assert "Tek örnek varsa sonuna sayı eklenmez" in tr
assert "SPM1 | OS Workspace | OW | 8 KiB" in en
assert "SPM2 | Task Workspace | TW | 8 KiB" in en
assert "SPM3–SPM6 | Context Pool | CP0–CP3" in en
assert "SPM7 | Exception Workspace | XW | 8 KiB" in en
assert "SPM0 | Execution Buffer | EB" in en
print("PASS: canonical singleton and multi-instance workspace names are synchronized (EN/TR).")
