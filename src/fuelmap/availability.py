"""Work out how hard it is to actually get fuel at an aerodrome.

The VAC charts rarely state opening hours as a clean field. What they say is
closer to "H24 at the card dispenser, otherwise ask the aero club", so a plain
H24/HX flag would be wrong for half of the readers. The question this module
answers is the one a visiting pilot asks: *can I land and refuel on my own, or
do I have to arrange something first?*

Attribution is done clause by clause, because a single section routinely gives
different terms to different fuels — Montceau-les-Mines publishes 100LL on an
H24 dispenser but UL91 only from 0800 to 1500.
"""

from __future__ import annotations

import re

from .model import (
    AVAILABILITY_RESTRICTED,
    AVAILABILITY_SELF_SERVICE,
    AVAILABILITY_UNKNOWN,
)

# A card-operated dispenser you can use without arranging anything first.
SELF_SERVICE_RE = re.compile(
    r"\bH\s*24\b|automat|libre[\s-]?service|self[\s-]?service", re.IGNORECASE
)

# Anything that puts a person, a phone call or a clock between you and the pump.
# A quoted phone number counts: a chart that offers a number and no hours is
# telling you to arrange it with somebody. It never demotes a field that also
# announces a dispenser, since self-service wins within a clause and on merge.
RESTRICTED_RE = re.compile(
    r"\bHX\b|\bHJ\b|\bPPR\b|\bO/R\b"
    r"|sur demande|on request"
    r"|r[ée]serv[ée]|bas[ée]s\b|home[\s-]?based"
    r"|\bRDV\b|rendez-vous|appointment"
    r"|se renseigner|contacter\b|\bcontact\b"
    r"|\bHOR\b|\bSKED\b"
    r"|\bT[ÉE]L\b|\b0\d(?:[ .]?\d{2}){4}\b"
    r"|\d{4}\s*-\s*\d{4}",
    re.IGNORECASE,
)

# "HOR AVT uniquement" / "AVT SKED only": the dispenser exists but only runs
# during published hours, which cancels the self-service reading.
SKED_ONLY_RE = re.compile(
    r"\bHOR\b[^.]{0,30}\buniquement\b|\bSKED\b[^.]{0,15}\bonly\b", re.IGNORECASE
)

# "Tous carburants : CB H24" applies to every pump on the field.
ALL_FUELS_RE = re.compile(r"tous\s+(?:les\s+)?carburants|all\s+fuels", re.IGNORECASE)

CLAUSE_BOUNDARY_RE = re.compile(r"(?<=[.;])\s+")


def _clause_level(clause: str) -> str:
    """Classify a single clause in isolation.

    Self-service wins over a restriction in the same breath, because "H24 by
    card or during club hours" still means you can help yourself. The one
    exception is an explicit statement that the dispenser only runs during
    published hours.
    """
    if SELF_SERVICE_RE.search(clause) and not SKED_ONLY_RE.search(clause):
        return AVAILABILITY_SELF_SERVICE
    if RESTRICTED_RE.search(clause) or SKED_ONLY_RE.search(clause):
        return AVAILABILITY_RESTRICTED
    return AVAILABILITY_UNKNOWN


def _merge(levels: set[str]) -> str:
    """Pick the most permissive level that was observed."""
    if AVAILABILITY_SELF_SERVICE in levels:
        return AVAILABILITY_SELF_SERVICE
    if AVAILABILITY_RESTRICTED in levels:
        return AVAILABILITY_RESTRICTED
    return AVAILABILITY_UNKNOWN


def detect_availability(section: str, fuels: frozenset[str]) -> dict[str, str]:
    """Map each fuel to how obtainable it is, from the raw "10 - AVT" text.

    ``fuels`` is passed in rather than re-detected so that the caller's view of
    which fuels exist stays authoritative.
    """
    # Imported here to avoid a cycle: parsing imports model, not the reverse.
    from .parsing import detect_fuels

    per_fuel: dict[str, set[str]] = {fuel: set() for fuel in fuels}
    unattributed: set[str] = set()

    for clause in CLAUSE_BOUNDARY_RE.split(section):
        level = _clause_level(clause)
        if level == AVAILABILITY_UNKNOWN:
            continue
        named = fuels if ALL_FUELS_RE.search(clause) else detect_fuels(clause) & fuels
        if named:
            for fuel in named:
                per_fuel[fuel].add(level)
        else:
            unattributed.add(level)

    fallback = _merge(unattributed)
    return {
        fuel: _merge(levels) if levels else fallback
        for fuel, levels in per_fuel.items()
    }
