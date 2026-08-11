from pathlib import Path

import pytest

FIXTURE_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def vac_text():
    """Return the ``pdftotext`` output stored for a given ICAO code."""

    def _load(icao: str) -> str:
        return (FIXTURE_DIR / f"AD-2.{icao}.txt").read_text(encoding="utf-8")

    return _load
