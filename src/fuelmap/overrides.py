"""Everything the eAIP does not tell us, in one auditable place.

Two mechanisms, for two different gaps:

``OVERRIDES``
    Corrections to a field the AIP *does* describe. Section 10 of a VAC is free
    text, and some charts publish a bare fuel list with no access wording, so
    the heuristic can only answer "unknown" even where the pump is a known
    automat. An entry maps a fuel to its access level; a fuel the chart omits
    is added, which is how a road service station next door becomes visible.
``ADDITIONS``
    Whole records for fields the AIP does not describe at all, typically
    private ULM strips with no VAC chart.

Both are applied to the Markdown listing and the map, never to the CSVs: those
stay a faithful record of the charts, so anything here is undone by deleting
its entry and rebuilding, and no curated value is ever baked into the
extraction output. Consequently the listing carries more fields than
``aerodromes-unleaded.csv``, and every curated element is flagged to the reader.

Nothing here has an upstream to refresh it, so entries should be re-checked at
each AIRAC cycle and kept few.
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
    """Fuel to access level. A fuel the chart omits is added to the field.

    ``AVAILABILITY_UNKNOWN`` is meaningful here: it adds the fuel without
    claiming hours we have not checked.
    """

    reason: str = ""
    """Shown next to the marker, so the reader knows it is not from the chart."""


#: Keyed by ICAO code. Fuels left out of an entry keep whatever the chart
#: supports, so 100LL and Jet A1 are untouched unless named explicitly.
OVERRIDES: dict[str, Override] = {
    "LFRS": Override(
        availability={UL91: AVAILABILITY_SELF_SERVICE},
        reason="Automate accessible H24. La VAC ne donne aucune condition.",
    ),
    "LFCF": Override(
        availability={SUPER_PLUS: AVAILABILITY_SELF_SERVICE},
        reason=(
            "Pas de sans plomb sur le terrain : SP98 H24 à la station-service "
            "voisine, à emporter en bidon."
        ),
    ),
    "LFCY": Override(
        availability={SUPER_PLUS: AVAILABILITY_SELF_SERVICE},
        reason=(
            "Pas de sans plomb sur le terrain : SP98 H24 à la station-service "
            "voisine, à emporter en bidon."
        ),
    ),
    "LFHY": Override(
        availability={SUPER_PLUS: AVAILABILITY_RESTRICTED},
        reason=(
            "SP98 non publié à la VAC : disponible auprès du club ULM, "
            "sur demande."
        ),
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


@dataclass(frozen=True)
class CuratedAerodrome:
    """A field the AIP does not describe at all, entered by hand.

    Mostly private ULM strips: they carry no VAC chart, so the code, position,
    fuel and conditions all come from ``source`` rather than from the eAIP.
    Landing at one needs the operator's prior agreement, which is why ``note``
    is mandatory and shown on the map.
    """

    code: str
    name: str
    latitude: float
    longitude: float
    availability: dict[str, str]
    source: str
    """Human-readable provenance, shown to the reader."""

    note: str
    """Conditions and caveats, including the prior-agreement requirement."""

    details: str = ""
    """Free text reproduced from the source sheet, shown like a VAC excerpt."""

    def to_aerodrome(self) -> Aerodrome:
        return Aerodrome(
            icao=self.code,
            name=self.name,
            fuels=frozenset(self.availability),
            latitude=self.latitude,
            longitude=self.longitude,
            fuel_section=self.details,
            availability=tuple(sorted(self.availability.items())),
            availability_note=self.note,
            curated_source=self.source,
        )


#: Fields absent from the eAIP. Kept deliberately short: this is hand-maintained
#: data with no upstream to refresh it, so each entry earns its place by being
#: a fuel source a pilot would otherwise never find.
ADDITIONS: tuple[CuratedAerodrome, ...] = (
    CuratedAerodrome(
        code="LF4724",
        name="MONTPEZAT D'AGENAIS",
        # N 44 21 51 / E 000 29 29, reproduced in `details` for checking.
        latitude=44.364167,
        longitude=0.491389,
        availability={UL91: AVAILABILITY_RESTRICTED},
        source="Fiche BASULM LF4724 (FFPLUM), mise à jour du 24/10/2024",
        note=(
            "Aérodrome privé ouvert aux ULM : accord préalable du gestionnaire "
            "obligatoire (Philippe Boucherat, +33 5 53 95 08 81). Terrain absent "
            "de l'AIP, données non vérifiables sur une carte VAC."
        ),
        details=(
            "BASULM LF4724 — Montpezat d'Agenais. LAT : N 44 21 51 - "
            "LONG : E 000 29 29 - ALT : 120 ft. Radio : 123.50. "
            "Carburants : Avgas UL 91. Pistes : 15-33 herbe 800x40, "
            "10-28 herbe 250x40, préférentielle 33. TDP à l'Est à 500 ft. "
            "Activité écolage importante. Gestionnaire : Philippe Boucherat, "
            "+33 5 53 95 08 81, info@ulmstex.com, http://www.ulmstex.com"
        ),
    ),
)


def curated_aerodromes() -> list[Aerodrome]:
    """The off-AIP fields, as :class:`~fuelmap.model.Aerodrome` records."""
    return [addition.to_aerodrome() for addition in ADDITIONS]


def apply(aerodrome: Aerodrome) -> Aerodrome:
    """Return ``aerodrome`` with its curated fuels and levels, if it has any."""
    override = OVERRIDES.get(aerodrome.icao)
    if override is None:
        return aerodrome

    availability = dict(aerodrome.availability) | override.availability
    # Keep any earlier marking: after the first pass the fuel is present, so
    # recomputing the difference alone would forget that we added it.
    added = (frozenset(override.availability) - aerodrome.fuels) | frozenset(
        aerodrome.curated_fuels
    )
    return replace(
        aerodrome,
        fuels=aerodrome.fuels | frozenset(override.availability),
        availability=tuple(sorted(availability.items())),
        availability_note=override.reason,
        curated_fuels=tuple(sorted(added)),
    )


def apply_all(aerodromes: list[Aerodrome]) -> list[Aerodrome]:
    """Correct the AIP records, then add the fields the AIP omits entirely."""
    corrected = [apply(a) for a in aerodromes] + curated_aerodromes()
    return sorted(corrected, key=lambda a: a.icao)
