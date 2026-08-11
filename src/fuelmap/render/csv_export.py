"""CSV serialisation of the extracted aerodromes."""

from __future__ import annotations

import csv
from pathlib import Path

from ..model import Aerodrome

#: Separator inside the ``fuels`` column; a comma would collide with the CSV.
FUEL_SEPARATOR = "|"

#: ``availability`` holds one ``FUEL=level`` entry per fuel, e.g.
#: ``100LL=self_service|UL91=restricted``.
AVAILABILITY_SEPARATOR = "="

FULL_COLUMNS = (
    "icao",
    "name",
    "fuels",
    "availability",
    "lat",
    "lon",
    "fuel_section",
    "error",
)

#: The published subset never carries an extraction error, so the column goes.
SUBSET_COLUMNS = tuple(c for c in FULL_COLUMNS if c != "error")


def _to_row(aerodrome: Aerodrome) -> dict[str, str]:
    return {
        "icao": aerodrome.icao,
        "name": aerodrome.name,
        "fuels": FUEL_SEPARATOR.join(sorted(aerodrome.fuels)),
        "availability": FUEL_SEPARATOR.join(
            f"{fuel}{AVAILABILITY_SEPARATOR}{level}"
            for fuel, level in aerodrome.availability
        ),
        "lat": "" if aerodrome.latitude is None else f"{aerodrome.latitude:.6f}",
        "lon": "" if aerodrome.longitude is None else f"{aerodrome.longitude:.6f}",
        "fuel_section": aerodrome.fuel_section,
        "error": aerodrome.error,
    }


def _parse_availability(value: str) -> tuple[tuple[str, str], ...]:
    pairs = []
    for entry in value.split(FUEL_SEPARATOR):
        fuel, separator, level = entry.partition(AVAILABILITY_SEPARATOR)
        if separator:
            pairs.append((fuel, level))
    return tuple(sorted(pairs))


def _from_row(row: dict[str, str]) -> Aerodrome:
    latitude = row.get("lat") or ""
    longitude = row.get("lon") or ""
    return Aerodrome(
        icao=row["icao"],
        name=row["name"],
        fuels=frozenset(f for f in row["fuels"].split(FUEL_SEPARATOR) if f),
        availability=_parse_availability(row.get("availability", "")),
        latitude=float(latitude) if latitude else None,
        longitude=float(longitude) if longitude else None,
        fuel_section=row.get("fuel_section", ""),
        error=row.get("error", ""),
    )


def write_csv(
    path: Path,
    aerodromes: list[Aerodrome],
    columns: tuple[str, ...] = FULL_COLUMNS,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(columns), extrasaction="ignore")
        writer.writeheader()
        writer.writerows(_to_row(a) for a in aerodromes)


def read_csv(path: Path) -> list[Aerodrome]:
    """Load aerodromes back from CSV, so outputs can be rebuilt without PDFs."""
    with path.open(encoding="utf-8", newline="") as handle:
        return [_from_row(row) for row in csv.DictReader(handle)]
