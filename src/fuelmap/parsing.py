"""Pure text parsing of VAC chart content.

Everything here takes the plain text produced by ``pdftotext -layout`` and
returns data. No file or process access, so it is all directly testable
against the fixtures in ``tests/fixtures``.
"""

from __future__ import annotations

import re

from . import model

ICAO_FILENAME_RE = re.compile(r"AD-2\.(LF[A-Z0-9]{2,3})\.pdf$", re.IGNORECASE)

# The fuel section opens with "10 - AVT" or "10. AVT" and runs until section
# 11 (RFFS) or 12. A leading "←" marks an amended paragraph in SIA charts.
FUEL_SECTION_RE = re.compile(
    r"(?:^|\n)\s*(?:←\s*)?10\s*[-.]\s*AVT.*?(?=\n\s*(?:←\s*)?1[12]\s*[-.])",
    re.IGNORECASE | re.DOTALL,
)

# Spelling variants observed across the French VAC set.
FUEL_PATTERNS: dict[str, re.Pattern[str]] = {
    model.UL91: re.compile(r"\bUL\s*91\b", re.IGNORECASE),
    model.UL_AERO: re.compile(r"\bUL\s*AERO\b", re.IGNORECASE),
    model.SUPER_PLUS: re.compile(
        r"\bSUPER\s*\+|\bSUPER\s*PLUS\b|\bSP\s*95\b|\bSP\s*98\b", re.IGNORECASE
    ),
    model.MOGAS: re.compile(r"\bMOGAS\b", re.IGNORECASE),
    model.AVGAS_100LL: re.compile(r"\b100\s*LL\b", re.IGNORECASE),
    model.JET_A1: re.compile(r"\bJET\s*A[-\s]?1\b", re.IGNORECASE),
}

# TotalEnergies sells UL91 as "UL AERO SUPER+", sometimes shortened to
# "AERO SUPER+". The trailing "SUPER+" is part of that brand name and must not
# be read as mogas, so these mentions are masked out before the other patterns
# run. Without this, aerodromes carrying only UL91 (Lyon-Bron, Avignon,
# Perpignan…) are wrongly advertised as selling SP95/SP98.
UL_AERO_BRAND_RE = re.compile(r"\b(?:UL\s+)?AERO\s*SUPER\s*\+", re.IGNORECASE)

LATITUDE_RE = re.compile(
    r"LAT\s*:\s*(\d{1,3})\s+(\d{1,2})\s+(\d{1,2})\s*([NS])", re.IGNORECASE
)
LONGITUDE_RE = re.compile(
    r"LONG\s*:\s*(\d{1,3})\s+(\d{1,2})\s+(\d{1,2})\s*([EW])", re.IGNORECASE
)

AIRAC_DIR_RE = re.compile(r"AIRAC-(\d{4}-\d{2}-\d{2})")

# Boilerplate that sits alongside the aerodrome name in the chart header.
NAME_BLOCKLIST = frozenset(
    {
        "AD",
        "AERODROME",
        "APPROCHE A VUE",
        "ATTERRISSAGE",
        "ATTERRISSAGE A VUE",
        "OUVERT A LA CAP",
        "PUBLIC AIR TRAFFIC",
        "RESTREINT",
        "USAGE PARTICULIER",
        "USAGE PRIVE",
        "USAGE RESTREINT",
        "VISUAL APPROACH",
    }
)
NAME_PREFIX_BLOCKLIST = ("AD ", "AD2", "FIS", "ATIS", "TWR", "APP")
NAME_LINE_RE = re.compile(r"^[A-ZÀÂÄÉÈÊËÎÏÔÖÙÛÜŸÇ’'\u2019\u2018 \-/.]{5,60}$")

#: Poppler leaves a few Windows-1252 bytes untranslated in SIA charts.
_MOJIBAKE_REPLACEMENTS = {
    "\x91": "'",
    "\x92": "'",
    "\x93": '"',
    "\x94": '"',
    "\x96": "-",
    "\x97": "-",
    "\u2018": "'",
    "\u2019": "'",
}

#: How much of the fuel section to keep in the CSV, in characters.
FUEL_SECTION_EXCERPT_LENGTH = 300

#: The aerodrome name and coordinates both live in the chart header.
HEADER_LINES = 20
NAME_LINES = 12


def fix_mojibake(text: str) -> str:
    """Repair the Windows-1252 leftovers that ``pdftotext`` does not decode."""
    for source, replacement in _MOJIBAKE_REPLACEMENTS.items():
        if source in text:
            text = text.replace(source, replacement)
    return text


def icao_from_filename(filename: str) -> str | None:
    """Read the ICAO code out of a VAC filename such as ``AD-2.LFOU.pdf``."""
    match = ICAO_FILENAME_RE.search(filename)
    return match.group(1).upper() if match else None


def extract_fuel_section(text: str) -> str:
    """Isolate VAC section "10 - AVT", or return an empty string if absent."""
    match = FUEL_SECTION_RE.search(text)
    return match.group(0) if match else ""


def detect_fuels(text: str) -> frozenset[str]:
    """Return the fuel keys mentioned anywhere in ``text``."""
    fuels = set()
    if UL_AERO_BRAND_RE.search(text):
        fuels.add(model.UL_AERO)
    masked = UL_AERO_BRAND_RE.sub(" ", text)
    fuels.update(
        fuel for fuel, pattern in FUEL_PATTERNS.items() if pattern.search(masked)
    )
    return frozenset(fuels)


def dms_to_decimal(degrees: str, minutes: str, seconds: str, hemisphere: str) -> float:
    """Convert sexagesimal coordinates to signed decimal degrees."""
    value = int(degrees) + int(minutes) / 60 + int(seconds) / 3600
    if hemisphere.upper() in ("S", "W"):
        value = -value
    return round(value, 6)


def extract_position(text: str) -> tuple[float | None, float | None]:
    """Read latitude/longitude from the VAC header, as decimal degrees."""
    header = "\n".join(text.splitlines()[:HEADER_LINES])
    latitude = LATITUDE_RE.search(header)
    longitude = LONGITUDE_RE.search(header)
    if not (latitude and longitude):
        return None, None
    return dms_to_decimal(*latitude.groups()), dms_to_decimal(*longitude.groups())


def extract_aerodrome_name(text: str) -> str:
    """Find the aerodrome name in the VAC header.

    The name sits in the first few lines in capitals, usually right-aligned and
    therefore separated from neighbouring text by a run of spaces. Standard
    headings such as "APPROCHE A VUE" occupy the same region and are skipped.
    """
    for line in text.splitlines()[:NAME_LINES]:
        for chunk in re.split(r"\s{3,}", line.strip()):
            chunk = chunk.strip()
            if not chunk:
                continue
            if chunk.upper() in NAME_BLOCKLIST:
                continue
            if chunk.upper().startswith(NAME_PREFIX_BLOCKLIST):
                continue
            if NAME_LINE_RE.match(chunk):
                return chunk
    return ""


def summarize_fuel_section(section: str) -> str:
    """Collapse whitespace and truncate the fuel section for CSV storage."""
    return re.sub(r"\s+", " ", section).strip()[:FUEL_SECTION_EXCERPT_LENGTH]


def parse_vac_text(icao: str, text: str) -> model.Aerodrome:
    """Build an :class:`~fuelmap.model.Aerodrome` from one chart's text."""
    if not text.strip():
        return model.Aerodrome(
            icao=icao,
            name="",
            fuels=frozenset(),
            latitude=None,
            longitude=None,
            fuel_section="",
            error="no_text",
        )

    # Fall back to the whole document when the section markers are missing, so
    # that unusually formatted charts still contribute fuel data.
    section = extract_fuel_section(text)
    latitude, longitude = extract_position(text)
    return model.Aerodrome(
        icao=icao,
        name=extract_aerodrome_name(text),
        fuels=detect_fuels(section or text),
        latitude=latitude,
        longitude=longitude,
        fuel_section=summarize_fuel_section(section),
    )
