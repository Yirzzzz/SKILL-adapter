import os
import tempfile
from pathlib import Path


def pytest_configure() -> None:
    base = Path(__file__).resolve().parents[1] / ".tmp_test"
    base.mkdir(parents=True, exist_ok=True)
    os.environ["TMP"] = str(base)
    os.environ["TEMP"] = str(base)
    tempfile.tempdir = str(base)
