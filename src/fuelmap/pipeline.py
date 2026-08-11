"""Run the extraction across a whole eAIP VAC directory."""

from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

from . import vac
from .model import Aerodrome
from .parsing import icao_from_filename, parse_vac_text

DEFAULT_WORKERS = 8
PROGRESS_EVERY = 50


def extract_one(pdf_path: Path) -> Aerodrome | None:
    """Parse a single VAC chart, or ``None`` if it is not an aerodrome chart."""
    icao = icao_from_filename(pdf_path.name)
    if icao is None:
        return None
    return parse_vac_text(icao, vac.pdf_to_text(pdf_path))


def extract_all(
    vac_dir: Path,
    workers: int = DEFAULT_WORKERS,
    progress: bool = True,
) -> list[Aerodrome]:
    """Parse every VAC chart under ``vac_dir``, sorted by ICAO code."""
    charts = vac.find_vac_charts(vac_dir)
    if not charts:
        raise FileNotFoundError(
            f"aucun fichier {vac.VAC_GLOB} dans {vac_dir}"
        )
    if progress:
        print(f"{len(charts)} cartes VAC à analyser…")

    aerodromes: list[Aerodrome] = []
    with ProcessPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(extract_one, chart) for chart in charts]
        for done, future in enumerate(as_completed(futures), start=1):
            aerodrome = future.result()
            if aerodrome is not None:
                aerodromes.append(aerodrome)
            if progress and done % PROGRESS_EVERY == 0:
                print(f"  …{done}/{len(charts)}")

    aerodromes.sort(key=lambda a: a.icao)
    return aerodromes


def unleaded_only(aerodromes: list[Aerodrome]) -> list[Aerodrome]:
    """Keep the aerodromes publishing a fuel an unleaded engine can burn."""
    return [a for a in aerodromes if a.has_unleaded]
