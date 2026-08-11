"""Fuel taxonomy and the aerodrome record produced by the extractor.

The terminology is easy to get wrong, and the trap is that two different
products both read as "unleaded". What decides the grouping here is which
engine approval a pilot needs, not how the name is spelled:

* ``UL91`` is an unleaded *aviation* gasoline to ASTM D7547. It is its own
  product, usable only on engines approved for UL91 avgas.
* ``SUPER PLUS`` / ``SP95`` / ``SP98`` is automotive petrol to EN 228, i.e.
  mogas, dispensed for engines certified to burn it. French VAC charts never
  use the word "MOGAS", but it is matched defensively.
* ``UL AERO SUPER+`` is TotalEnergies' *aviation-grade SP98*: an ethanol-free
  EN 228 petrol, stored and filtered to aviation standards, approved for ROTAX
  912/914 engines certified for SP98. Despite the "UL" it is **not** UL91 —
  TotalEnergies sells the two side by side — so it belongs with the mogas
  family. Grouping it under UL91 would tell a ROTAX pilot to skip a field they
  can use, and send a UL91-only aircraft to a pump it is not approved for.
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

#: Display order for tables and legends, grouped by family.
FUEL_DISPLAY_ORDER = (UL91, UL_AERO, SUPER_PLUS, MOGAS, AVGAS_100LL, JET_A1)

FUEL_LABELS = {
    UL91: "UL91",
    UL_AERO: "UL AERO SUPER+",
    SUPER_PLUS: "Super Plus",
    MOGAS: "MOGAS",
    AVGAS_100LL: "100LL",
    JET_A1: "Jet A1",
}

# The two families a pilot chooses between, by required engine approval. The
# map draws one marker per family, so a field selling both is filterable under
# either.
FAMILY_UL91 = "ul91"
FAMILY_MOGAS = "mogas"

#: The single source of truth for which fuels belong together. Insertion order
#: is the legend order.
FUEL_FAMILIES = {
    FAMILY_UL91: frozenset({UL91}),
    FAMILY_MOGAS: frozenset({SUPER_PLUS, MOGAS, UL_AERO}),
}

FAMILY_LABELS = {
    FAMILY_UL91: "UL91 (AVGAS sans plomb)",
    FAMILY_MOGAS: "SP95 / SP98 (dont UL AERO SUPER+)",
}

#: Everything an unleaded-certified piston engine can burn. Membership is what
#: puts an aerodrome in the published subset.
UNLEADED_FUELS = frozenset().union(*FUEL_FAMILIES.values())

# How obtainable a fuel is. See fuelmap.availability for how this is derived.
AVAILABILITY_SELF_SERVICE = "self_service"
AVAILABILITY_RESTRICTED = "restricted"
AVAILABILITY_UNKNOWN = "unknown"

#: Most permissive first; also the legend order.
AVAILABILITY_ORDER = (
    AVAILABILITY_SELF_SERVICE,
    AVAILABILITY_RESTRICTED,
    AVAILABILITY_UNKNOWN,
)

AVAILABILITY_LABELS = {
    AVAILABILITY_SELF_SERVICE: "Automate / H24",
    AVAILABILITY_RESTRICTED: "HX, PPR, sur demande",
    AVAILABILITY_UNKNOWN: "Non précisé",
}

AVAILABILITY_HINTS = {
    AVAILABILITY_SELF_SERVICE: "Pompe en libre-service, accessible par carte.",
    AVAILABILITY_RESTRICTED: "Horaires limités, PPR, sur demande ou réservé aux basés.",
    AVAILABILITY_UNKNOWN: "La carte VAC ne précise pas les conditions.",
}


def best_availability(levels) -> str:
    """Return the most permissive level in ``levels``."""
    for level in AVAILABILITY_ORDER:
        if level in levels:
            return level
    return AVAILABILITY_UNKNOWN


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

    availability: tuple[tuple[str, str], ...] = ()
    """Sorted ``(fuel, level)`` pairs. A tuple so the record stays hashable."""

    error: str = ""
    """Non-empty when the chart could not be read at all."""

    @property
    def has_unleaded(self) -> bool:
        return bool(self.fuels & UNLEADED_FUELS)

    @property
    def has_position(self) -> bool:
        return self.latitude is not None and self.longitude is not None

    def availability_of(self, fuel: str) -> str:
        return dict(self.availability).get(fuel, AVAILABILITY_UNKNOWN)

    def family_fuels(self, family: str) -> frozenset[str]:
        """The fuels this aerodrome carries within ``family``."""
        return self.fuels & FUEL_FAMILIES[family]

    def families(self) -> list[str]:
        """Which unleaded families are available, in legend order.

        Empty for a field with no unleaded fuel, which therefore contributes
        no markers to the map.
        """
        return [f for f in FUEL_FAMILIES if self.family_fuels(f)]

    def family_availability(self, family: str) -> str:
        """Best availability across the fuels of ``family``.

        A family is as obtainable as its easiest member: a field where SP98 is
        on an automat and UL AERO SUPER+ is on request still counts as
        self-service for a pilot who can burn either.
        """
        return best_availability(
            {self.availability_of(fuel) for fuel in self.family_fuels(family)}
        )
