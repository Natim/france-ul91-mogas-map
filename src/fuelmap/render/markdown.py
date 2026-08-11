"""Human-readable Markdown listing of the unleaded aerodromes."""

from __future__ import annotations

from collections import Counter
from datetime import date

from ..model import (
    AVAILABILITY_LABELS,
    AVAILABILITY_ORDER,
    FUEL_DISPLAY_ORDER,
    FUEL_LABELS,
    Aerodrome,
    best_availability,
    format_fuels,
)

GENERATED_BY = "`fuelmap extract`"

#: Flags a row whose access condition does not come from the chart.
OVERRIDE_MARK = "†"

#: Flags a row for a field that has no VAC chart at all.
OFF_AIP_MARK = "‡"


def count_fuels(aerodromes: list[Aerodrome]) -> Counter[str]:
    counts: Counter[str] = Counter()
    for aerodrome in aerodromes:
        counts.update(aerodrome.fuels)
    return counts


def overall_availability(aerodrome: Aerodrome) -> str:
    """Best availability across the unleaded fuels of an aerodrome."""
    return best_availability(
        {aerodrome.family_availability(f) for f in aerodrome.families()}
    )


def count_availability(aerodromes: list[Aerodrome]) -> Counter[str]:
    return Counter(overall_availability(a) for a in aerodromes)


def render_markdown(
    aerodromes: list[Aerodrome],
    airac: str,
    today: date | None = None,
) -> str:
    """Build the contents of ``AERODROMES.md``."""
    counts = count_fuels(aerodromes)
    updated = (today or date.today()).isoformat()

    off_aip = [a for a in aerodromes if a.is_off_aip]
    # Fields that qualify only through a fuel we added, typically a road
    # station next door: their own chart publishes no unleaded at all.
    nearby = [a for a in aerodromes if not a.is_off_aip and not a.sells_unleaded_itself]
    published = len(aerodromes) - len(off_aip) - len(nearby)

    summary = (
        f"**{published} aérodromes** publient une pompe d'essence sans plomb "
        "(UL91, SP95/SP98, Super Plus ou UL AERO SUPER+) dans leur carte VAC "
        "officielle."
    )
    extras = []
    if nearby:
        extras.append(
            f"{len(nearby)} dont le sans plomb vient d'une source voisine "
            f"({OVERRIDE_MARK})"
        )
    if off_aip:
        absent = "absent" if len(off_aip) == 1 else "absents"
        extras.append(f"{len(off_aip)} {absent} de l'AIP ({OFF_AIP_MARK})")
    if extras:
        total = len(nearby) + len(off_aip)
        verb, plural = ("ajoutent", "s") if total > 1 else ("ajoute", "")
        summary += (
            f" S'y {verb} **{total} terrain{plural} renseigné{plural} à "
            f"la main** : " + ", ".join(extras) + "."
        )

    lines = [
        "# Aérodromes français — UL91 / Mogas",
        "",
        summary,
        "",
        f"- **Cycle AIRAC** : {airac}",
        f"- **Date d'extraction** : {updated}",
        "- **Source** : eAIP du SIA, Atlas-VAC",
        "",
        "## Répartition par carburant",
        "",
        "| Carburant | Nb terrains |",
        "|-----------|-------------|",
    ]
    lines.extend(
        f"| {FUEL_LABELS[fuel]} | {counts[fuel]} |"
        for fuel in FUEL_DISPLAY_ORDER
        if counts.get(fuel)
    )

    availability = count_availability(aerodromes)
    lines += [
        "",
        "> Malgré son préfixe, `UL AERO SUPER+` n'est **pas** du `UL91` : c'est "
        "un SP98 sans éthanol de qualité aviation distribué par TotalEnergies, "
        "réservé aux moteurs ROTAX 912/914 homologués pour le SP98 EN 228. Il "
        "est donc rangé avec `Super Plus` / `SP95` / `SP98`. Le `UL91`, lui, est "
        "une essence aviation à la norme ASTM D7547.",
        "",
        "## Conditions d'accès",
        "",
        "| Accès | Nb terrains |",
        "|-------|-------------|",
    ]
    lines.extend(
        f"| {AVAILABILITY_LABELS[level]} | {availability[level]} |"
        for level in AVAILABILITY_ORDER
        if availability.get(level)
    )
    lines += [
        "",
        "> Déduit automatiquement du texte de la section « 10 - AVT », sauf "
        f"mention {OVERRIDE_MARK}. `Automate / H24` signifie qu'une pompe en "
        "libre-service est annoncée ; les autres terrains demandent un PPR, un "
        "appel, ou ne servent que pendant certaines plages. **En cas de doute, "
        "la carte VAC fait foi.**",
        "",
        "## Liste complète",
        "",
        "| Code | Nom | Carburants | Accès |",
        "|------|-----|-----------|-------|",
    ]
    ordered = sorted(aerodromes, key=lambda a: a.icao)
    lines.extend(
        f"| {a.icao}{' ' + OFF_AIP_MARK if a.is_off_aip else ''} "
        f"| {a.name} | {format_fuels(a.fuels)} "
        f"| {AVAILABILITY_LABELS[overall_availability(a)]}"
        f"{' ' + OVERRIDE_MARK if a.availability_note and not a.is_off_aip else ''} |"
        for a in ordered
    )

    overridden = [a for a in ordered if a.availability_note and not a.is_off_aip]
    if overridden:
        lines += [
            "",
            f"{OVERRIDE_MARK} Condition d'accès **non publiée par la VAC**, "
            "renseignée manuellement :",
            "",
        ]
        lines.extend(
            f"- **{a.icao}** {a.name} — {a.availability_note}" for a in overridden
        )

    if off_aip:
        lines += [
            "",
            f"{OFF_AIP_MARK} Terrain **absent de l'AIP**, donc absent des CSV et "
            "invérifiable sur une carte VAC. Position, carburant et conditions "
            "sont renseignés à la main :",
            "",
        ]
        lines.extend(
            f"- **{a.icao}** {a.name} — {a.availability_note} "
            f"_(source : {a.curated_source})_"
            for a in off_aip
        )

    lines += [
        "",
        f"_Fichier auto-généré par {GENERATED_BY}. Ne pas éditer à la main._",
        "",
    ]
    return "\n".join(lines)
