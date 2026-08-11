"""Fuel taxonomy and the aerodrome record produced by the extractor.

The terminology is easy to get wrong, so it is pinned down here:

* ``UL91`` is an unleaded *aviation* gasoline (ASTM D7547). TotalEnergies
  sells it as ``UL AERO SUPER+``, which is why both spellings appear in VAC
  charts and are treated as the same product.
* ``SUPER PLUS`` / ``SP95`` / ``SP98`` is automotive gasoline, i.e. mogas,
  dispensed at aerodromes for engines certified to burn it. French VAC charts
  never use the word "MOGAS", but it is matched defensively.
* ``100LL`` is the leaded avgas that this project exists to help pilots avoid,
  and ``JET A1`` is turbine fuel. Both are recorded for context only.
"""

from __future__ import annotations

from dataclasses import dataclass

UL91 = "UL91"
UL_AERO = "UL_AERO"
SUPER_PLUS = "SUPER_PLUS"
MOGAS = "MOGAS"
AVGAS_100LL = "100LL"
JET_A1 = "JET_A1"

#: Unleaded aviation gasoline: the same physical product under two names.
UNLEADED_AVGAS = frozenset({UL91, UL_AERO})

#: Automotive gasoline sold airside.
MOGAS_FUELS = frozenset({SUPER_PLUS, MOGAS})

#: Everything an unleaded-certified piston engine can burn. Membership in this
#: set is what puts an aerodrome in the published subset.
UNLEADED_FUELS = UNLEADED_AVGAS | MOGAS_FUELS

#: Display order for tables and legends, coarsest interest first.
FUEL_DISPLAY_ORDER = (UL91, UL_AERO, SUPER_PLUS, MOGAS, AVGAS_100LL, JET_A1)

FUEL_LABELS = {
    UL91: "UL91",
    UL_AERO: "UL AERO SUPER+",
    SUPER_PLUS: "Super Plus",
    MOGAS: "MOGAS",
    AVGAS_100LL: "100LL",
    JET_A1: "Jet A1",
}

# Map marker categories. Every aerodrome carrying an unleaded fuel falls into
# exactly one of these, which is what lets the legend stay exhaustive.
CATEGORY_UL91 = "ul91"
CATEGORY_MOGAS = "mogas"
CATEGORY_BOTH = "both"

CATEGORY_LABELS = {
    CATEGORY_UL91: "UL91 / UL AERO SUPER+",
    CATEGORY_MOGAS: "Mogas (Super Plus / SP95-98)",
    CATEGORY_BOTH: "UL91 + Mogas",
}


def map_category(fuels: frozenset[str] | set[str]) -> str:
    """Classify an aerodrome for the map legend.

    Raises ``ValueError`` for aerodromes with no unleaded fuel at all, which
    would otherwise be drawn in a colour the legend cannot explain.
    """
    has_avgas = bool(fuels & UNLEADED_AVGAS)
    has_mogas = bool(fuels & MOGAS_FUELS)
    if has_avgas and has_mogas:
        return CATEGORY_BOTH
    if has_avgas:
        return CATEGORY_UL91
    if has_mogas:
        return CATEGORY_MOGAS
    raise ValueError(f"no unleaded fuel among {sorted(fuels)}")


def format_fuels(fuels: frozenset[str] | set[str] | tuple[str, ...]) -> str:
    """Render fuel keys as a human-readable list in display order."""
    known = [FUEL_LABELS[f] for f in FUEL_DISPLAY_ORDER if f in fuels]
    unknown = sorted(set(fuels) - set(FUEL_DISPLAY_ORDER))
    return ", ".join(known + unknown)


@dataclass(frozen=True)
class Aerodrome:
    """One French aerodrome as read from its VAC chart."""

    icao: str
    name: str
    fuels: frozenset[str]
    latitude: float | None
    longitude: float | None
    fuel_section: str
    """Raw text of VAC section "10 - AVT", trimmed. Empty when not found."""

    error: str = ""
    """Non-empty when the chart could not be read at all."""

    @property
    def has_unleaded(self) -> bool:
        return bool(self.fuels & UNLEADED_FUELS)

    @property
    def has_position(self) -> bool:
        return self.latitude is not None and self.longitude is not None

    @property
    def category(self) -> str:
        return map_category(self.fuels)
