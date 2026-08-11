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

    lines = [
        "# Aérodromes français — UL91 / Mogas",
        "",
        f"**{len(aerodromes)} aérodromes** publient une pompe d'essence sans "
        "plomb (UL91, UL AERO SUPER+, Super Plus ou MOGAS) dans leur carte VAC "
        "officielle.",
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
        "> `UL91` et `UL AERO SUPER+` désignent le même carburant : "
        "`UL AERO SUPER+` est la dénomination commerciale TotalEnergies du UL91. "
        "C'est une essence *aviation* sans plomb, à ne pas confondre avec le "
        "mogas (`Super Plus` / `SP95` / `SP98`), qui est de l'essence routière.",
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
        "> Déduit automatiquement du texte de la section « 10 - AVT ». "
        "`Automate / H24` signifie qu'une pompe en libre-service est annoncée ; "
        "les autres terrains demandent un PPR, un appel, ou ne servent que "
        "pendant certaines plages. **En cas de doute, la carte VAC fait foi.**",
        "",
        "## Liste complète",
        "",
        "| OACI | Nom | Carburants | Accès |",
        "|------|-----|-----------|-------|",
    ]
    lines.extend(
        f"| {a.icao} | {a.name} | {format_fuels(a.fuels)} "
        f"| {AVAILABILITY_LABELS[overall_availability(a)]} |"
        for a in sorted(aerodromes, key=lambda a: a.icao)
    )
    lines += [
        "",
        f"_Fichier auto-généré par {GENERATED_BY}. Ne pas éditer à la main._",
        "",
    ]
    return "\n".join(lines)
