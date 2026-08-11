"""Access to the SIA eAIP package on disk: PDF text and AIRAC cycle."""

from __future__ import annotations

import subprocess
from pathlib import Path

from .parsing import AIRAC_DIR_RE, fix_mojibake

VAC_GLOB = "AD-2.LF*.pdf"
PDFTOTEXT_TIMEOUT_SECONDS = 30
UNKNOWN_AIRAC = "unknown"


class PdftotextMissing(RuntimeError):
    """Raised when the Poppler ``pdftotext`` binary is not installed."""


def pdf_to_text(pdf_path: Path) -> str:
    """Extract the text of a VAC chart, preserving its column layout.

    Returns an empty string when the chart cannot be read; a scanned or
    corrupt chart should not abort a run over several hundred files.
    """
    try:
        result = subprocess.run(
            ["pdftotext", "-layout", "-enc", "UTF-8", str(pdf_path), "-"],
            capture_output=True,
            text=True,
            check=True,
            timeout=PDFTOTEXT_TIMEOUT_SECONDS,
        )
    except FileNotFoundError as exc:
        raise PdftotextMissing(
            "pdftotext introuvable : installez le paquet poppler-utils."
        ) from exc
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        print(f"[WARN] pdftotext a échoué sur {pdf_path.name} : {exc}")
        return ""
    return fix_mojibake(result.stdout)


def find_vac_charts(vac_dir: Path) -> list[Path]:
    """List the metropolitan/DOM VAC charts, sorted by ICAO code."""
    return sorted(vac_dir.glob(VAC_GLOB))


def detect_airac(vac_dir: Path) -> str:
    """Find the most recent AIRAC cycle in the eAIP tree above ``vac_dir``.

    An eAIP package bundles several regional sub-trees (FRANCE, PAC-N, PAC-P,
    RUN, CAR-SAM-NAM) that can sit on different cycles, so the newest date wins.
    """
    for ancestor in vac_dir.parents:
        cycles = {
            match.group(1)
            for candidate in ancestor.glob("**/AIRAC-*")
            if (match := AIRAC_DIR_RE.search(candidate.name))
        }
        if cycles:
            return max(cycles)
    return UNKNOWN_AIRAC
