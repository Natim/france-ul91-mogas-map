"""Map data for the static GitHub Pages site.

Only the data is generated. ``docs/index.html`` is a hand-maintained static
page that fetches this file at load time, so the map UI can be edited without
re-running the extraction over the PDFs.

One marker is emitted per *fuel family* rather than per aerodrome: the handful
of fields selling both UL91 and mogas get two markers, so each family can be
filtered independently.
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from ..model import (
    AVAILABILITY_LABELS,
    FAMILY_LABELS,
    Aerodrome,
    format_fuels,
)

#: Bumped when the JSON shape changes, so the page can refuse stale data.
#: 2 — markers are per fuel family and carry an availability level.
#: 3 — markers carry ``note``, set when the level is curated rather than read.
#: 4 — markers carry ``source``, set when the field is absent from the AIP.
SCHEMA_VERSION = 4


def _marker(aerodrome: Aerodrome, family: str) -> dict:
    family_fuels = aerodrome.family_fuels(family)
    return {
        "icao": aerodrome.icao,
        "name": aerodrome.name,
        "lat": aerodrome.latitude,
        "lon": aerodrome.longitude,
        "family": family,
        "familyLabel": FAMILY_LABELS[family],
        "fuels": sorted(family_fuels),
        "fuelsLabel": format_fuels(family_fuels),
        "availability": aerodrome.family_availability(family),
        "availabilityLabel": AVAILABILITY_LABELS[
            aerodrome.family_availability(family)
        ],
        # Everything on the field, so a pilot sees the whole picture, and the
        # raw wording so they can check the availability we inferred.
        "allFuelsLabel": format_fuels(aerodrome.fuels),
        "section": aerodrome.fuel_section,
        # Non-empty when the level was curated: the chart below will not
        # corroborate it, and the popup says so.
        "note": aerodrome.availability_note,
        # Non-empty when the field has no VAC chart at all.
        "source": aerodrome.curated_source,
    }


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
    # A field with no unleaded fuel has no family and would vanish silently;
    # that means it was never filtered out upstream.
    unmappable = [a.icao for a in mappable if not a.families()]
    if unmappable:
        raise ValueError(f"aerodromes without unleaded fuel: {unmappable}")

    markers = [_marker(a, family) for a in mappable for family in a.families()]
    return {
        "schema": SCHEMA_VERSION,
        "airac": airac,
        "generated": (today or date.today()).isoformat(),
        "aerodromeCount": len(mappable),
        "markers": markers,
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
    return payload["aerodromeCount"]
