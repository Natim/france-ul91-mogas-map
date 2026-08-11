"""Human-readable Markdown listing of the unleaded aerodromes."""

from __future__ import annotations

from collections import Counter
from datetime import date

from ..model import FUEL_DISPLAY_ORDER, FUEL_LABELS, Aerodrome, format_fuels

GENERATED_BY = "`fuelmap extract`"


def count_fuels(aerodromes: list[Aerodrome]) -> Counter[str]:
    counts: Counter[str] = Counter()
    for aerodrome in aerodromes:
        counts.update(aerodrome.fuels)
    return counts


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
    lines += [
        "",
        "> `UL91` et `UL AERO SUPER+` désignent le même carburant : "
        "`UL AERO SUPER+` est la dénomination commerciale TotalEnergies du UL91. "
        "C'est une essence *aviation* sans plomb, à ne pas confondre avec le "
        "mogas (`Super Plus` / `SP95` / `SP98`), qui est de l'essence routière.",
        "",
        "## Liste complète",
        "",
        "| OACI | Nom | Carburants |",
        "|------|-----|-----------|",
    ]
    lines.extend(
        f"| {a.icao} | {a.name} | {format_fuels(a.fuels)} |"
        for a in sorted(aerodromes, key=lambda a: a.icao)
    )
    lines += [
        "",
        f"_Fichier auto-généré par {GENERATED_BY}. Ne pas éditer à la main._",
        "",
    ]
    return "\n".join(lines)
