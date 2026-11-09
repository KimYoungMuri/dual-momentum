from pathlib import Path

HW5_ROOT = Path(__file__).resolve().parents[2]
DATA_RAW = HW5_ROOT / "data" / "raw"
DATA_PROC = HW5_ROOT / "data" / "processed"
OUT = HW5_ROOT / "outputs"
TAB = OUT / "tables"
FIG = OUT / "figures"
REPORT = HW5_ROOT / "report"


def ensure_dirs() -> None:
    for d in (DATA_RAW, DATA_PROC, OUT, TAB, FIG, REPORT):
        d.mkdir(parents=True, exist_ok=True)
