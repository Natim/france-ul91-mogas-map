"""Curated corrections to what the VAC charts say about fuel.

Section 10 of a VAC is free text, and some fields publish a bare fuel list with
no access wording whatsoever, so the heuristic can only answer "unknown" even
where the pump is a well-known automat. A few fields also have a fuel source
that the AIP will never mention, such as a road service station next door.

An entry maps a fuel to its access level. Fuels absent from the chart are
*added* to the field, which is a deliberate departure from the official source
and the reason every entry carries a ``reason`` shown to the reader.

These are applied to the Markdown listing and the map, never to the CSVs: those
stay a faithful record of the charts, so an override is undone by deleting its
entry and rebuilding. Each one should be re-checked at each AIRAC cycle.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace

from .model import (
    AVAILABILITY_RESTRICTED,
    AVAILABILITY_SELF_SERVICE,
    SUPER_PLUS,
    UL91,
    Aerodrome,
)


@dataclass(frozen=True)
class Override:
    """Curated fuels and access conditions for one aerodrome."""

    availability: dict[str, str] = field(default_factory=dict)
    """Fuel to access level. A fuel the chart omits is added to the field."""

    reason: str = ""
    """Shown next to the marker, so the reader knows it is not from the chart."""


#: Keyed by ICAO code. Fuels left out of an entry keep whatever the chart
#: supports, so 100LL and Jet A1 are untouched unless named explicitly.
OVERRIDES: dict[str, Override] = {
    "LFRS": Override(
        availability={UL91: AVAILABILITY_SELF_SERVICE},
        reason="Automate accessible H24. La VAC ne donne aucune condition.",
    ),
    "LFOF": Override(
        availability={
            UL91: AVAILABILITY_RESTRICTED,
            # Not an apron pump: the road station facing the aerodrome. Recorded
            # as field fuel so it shows under the SP98 filter, with the reason
            # spelling out where it actually is.
            SUPER_PLUS: AVAILABILITY_SELF_SERVICE,
        },
        reason=(
            "Pompe UL91 en HX. SP98 H24 à la station Total en face, "
            "nécessite un bidon."
        ),
    ),
}


def apply(aerodrome: Aerodrome) -> Aerodrome:
    """Return ``aerodrome`` with its curated fuels and levels, if it has any."""
    override = OVERRIDES.get(aerodrome.icao)
    if override is None:
        return aerodrome

    availability = dict(aerodrome.availability) | override.availability
    return replace(
        aerodrome,
        fuels=aerodrome.fuels | frozenset(override.availability),
        availability=tuple(sorted(availability.items())),
        availability_note=override.reason,
    )


def apply_all(aerodromes: list[Aerodrome]) -> list[Aerodrome]:
    return [apply(a) for a in aerodromes]
