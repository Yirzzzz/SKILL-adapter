from pathlib import Path
from uuid import uuid4


def make_case_dir() -> Path:
    base = Path(__file__).resolve().parents[1] / ".tmp_test_cases"
    base.mkdir(parents=True, exist_ok=True)
    case_dir = base / uuid4().hex
    case_dir.mkdir(parents=True, exist_ok=False)
    return case_dir
