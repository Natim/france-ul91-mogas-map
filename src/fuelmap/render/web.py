"""Map data for the static GitHub Pages site.

Only the data is generated. ``docs/index.html`` is a hand-maintained static
page that fetches this file at load time, so the map UI can be edited without
re-running the extraction over the PDFs.
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from ..model import Aerodrome, format_fuels

#: Bumped when the JSON shape changes, so the page can refuse stale data.
SCHEMA_VERSION = 1


def build_payload(
    aerodromes: list[Aerodrome],
    airac: str,
    today: date | None = None,
) -> dict:
    """Build the JSON document consumed by ``docs/index.html``.

    Aerodromes without coordinates are dropped: they cannot be plotted, and
    they remain listed in the CSV and Markdown outputs.
    """
    mappable = sorted(
        (a for a in aerodromes if a.has_position), key=lambda a: a.icao
    )
    return {
        "schema": SCHEMA_VERSION,
        "airac": airac,
        "generated": (today or date.today()).isoformat(),
        "aerodromes": [
            {
                "icao": a.icao,
                "name": a.name,
                "fuels": sorted(a.fuels),
                "fuelsLabel": format_fuels(a.fuels),
                "category": a.category,
                "lat": a.latitude,
                "lon": a.longitude,
            }
            for a in mappable
        ],
    }


def write_map_data(
    path: Path,
    aerodromes: list[Aerodrome],
    airac: str,
    today: date | None = None,
) -> int:
    """Write the map JSON and return the number of plotted aerodromes."""
    payload = build_payload(aerodromes, airac, today)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return len(payload["aerodromes"])
