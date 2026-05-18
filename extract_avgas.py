"""
Extrait depuis les VAC PDFs du SIA (Atlas-VAC) la liste des aérodromes OACI
fournissant un carburant essence (UL91 / Super Plus / UL AERO / MOGAS / SP95).

Stratégie:
  1. Parcourir tous les fichiers AD-2.LF*.pdf
  2. Extraire le texte avec `pdftotext -layout`
  3. Isoler la section "10 - AVT" (Carburant / Fuel) si trouvée, sinon
     fallback sur tout le document
  4. Regex sur les variantes de UL91 / Super Plus / MOGAS / UL AERO
  5. Sortir un CSV trié par OACI

Usage:
    python extract_avgas.py --vac-dir <path> --out avgas.csv
"""

from __future__ import annotations

import argparse
import csv
import re
import subprocess
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

ICAO_RE = re.compile(r"AD-2\.(LF[A-Z0-9]{2,3})\.pdf$", re.IGNORECASE)

# La section avitaillement commence à "10 - AVT" ou "10. AVT" et se termine
# au paragraphe 11 (RFFS) ou 12.
SECTION_RE = re.compile(
    r"(?:^|\n)\s*(?:←\s*)?10\s*[-.]\s*AVT.*?(?=\n\s*(?:←\s*)?1[12]\s*[-.])",
    re.IGNORECASE | re.DOTALL,
)

# Variantes rencontrées dans les VAC françaises.
FUEL_PATTERNS: dict[str, re.Pattern[str]] = {
    "UL91": re.compile(r"\bUL\s*91\b", re.IGNORECASE),
    "UL_AERO": re.compile(r"\bUL\s*AERO\b", re.IGNORECASE),
    "SUPER_PLUS": re.compile(
        r"\bSUPER\s*\+|\bSUPER\s*PLUS\b|\bSP\s*95\b|\bSP\s*98\b", re.IGNORECASE
    ),
    "MOGAS": re.compile(r"\bMOGAS\b", re.IGNORECASE),
    "100LL": re.compile(r"\b100\s*LL\b", re.IGNORECASE),
    "JET_A1": re.compile(r"\bJET\s*A[-\s]?1\b", re.IGNORECASE),
}

# Carburants "essence" considérés équivalents UL91 pour le filtrage final.
UL91_EQUIVALENT = {"UL91", "UL_AERO", "SUPER_PLUS", "MOGAS"}

NAME_BLOCKLIST = {
    "APPROCHE A VUE",
    "VISUAL APPROACH",
    "PUBLIC AIR TRAFFIC",
    "OUVERT A LA CAP",
    "RESTREINT",
    "USAGE RESTREINT",
    "ATTERRISSAGE A VUE",
    "ATTERRISSAGE",
    "USAGE PRIVE",
    "USAGE PARTICULIER",
    "AERODROME",
    "AD",
}
NAME_LINE_RE = re.compile(r"^[A-ZÀÂÄÉÈÊËÎÏÔÖÙÛÜŸÇ’'\u2019\u2018 \-/.]{5,60}$")


def extract_text(pdf_path: Path) -> str:
    try:
        result = subprocess.run(
            ["pdftotext", "-layout", "-enc", "UTF-8", str(pdf_path), "-"],
            capture_output=True,
            text=True,
            check=True,
            timeout=30,
        )
        return _normalize(result.stdout)
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        print(f"[WARN] pdftotext échec sur {pdf_path.name}: {exc}")
        return ""


_CP1252_REPLACEMENTS = {
    "\x91": "'",  # left single quote
    "\x92": "'",  # right single quote
    "\x93": '"',  # left double quote
    "\x94": '"',  # right double quote
    "\x96": "-",  # en dash
    "\x97": "-",  # em dash
    "\u2019": "'",
    "\u2018": "'",
}


def _normalize(text: str) -> str:
    for src, dst in _CP1252_REPLACEMENTS.items():
        if src in text:
            text = text.replace(src, dst)
    return text


def extract_avt_section(text: str) -> str:
    match = SECTION_RE.search(text)
    return match.group(0) if match else text


def detect_fuels(section: str) -> list[str]:
    return sorted(name for name, pat in FUEL_PATTERNS.items() if pat.search(section))


def extract_aerodrome_name(text: str) -> str:
    """Cherche le nom du terrain dans l'en-tête du VAC.

    Le nom apparaît dans les ~10 premières lignes, en majuscules, comme un
    bloc texte aligné à droite (souvent précédé de beaucoup d'espaces).
    On ignore les en-têtes standards comme "APPROCHE A VUE".
    """
    for line in text.splitlines()[:12]:
        for chunk in re.split(r"\s{3,}", line.strip()):
            chunk = chunk.strip()
            if not chunk:
                continue
            upper = chunk.upper()
            if upper in NAME_BLOCKLIST:
                continue
            if upper.startswith(("AD ", "AD2", "FIS", "ATIS", "TWR", "APP")):
                continue
            if NAME_LINE_RE.match(chunk):
                return chunk
    return ""


def process_one(pdf_path: Path) -> dict[str, str] | None:
    icao_match = ICAO_RE.search(pdf_path.name)
    if not icao_match:
        return None
    icao = icao_match.group(1).upper()

    text = extract_text(pdf_path)
    if not text:
        return {"icao": icao, "name": "", "fuels": "", "avt_excerpt": "", "error": "no_text"}

    section = extract_avt_section(text)
    fuels = detect_fuels(section)
    name = extract_aerodrome_name(text)

    excerpt = re.sub(r"\s+", " ", section).strip()[:300]

    return {
        "icao": icao,
        "name": name,
        "fuels": "|".join(fuels),
        "avt_excerpt": excerpt,
        "error": "",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--vac-dir", type=Path, required=True)
    parser.add_argument("--out", type=Path, default=Path("avgas_full.csv"))
    parser.add_argument(
        "--ul91-out",
        type=Path,
        default=Path("avgas_ul91.csv"),
        help="Filtre sur carburants UL91-équivalents.",
    )
    parser.add_argument("--workers", type=int, default=8)
    args = parser.parse_args()

    pdfs = sorted(args.vac_dir.glob("AD-2.LF*.pdf"))
    print(f"{len(pdfs)} fichiers VAC à parser…")

    rows: list[dict[str, str]] = []
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(process_one, p): p for p in pdfs}
        for i, fut in enumerate(as_completed(futures), 1):
            row = fut.result()
            if row:
                rows.append(row)
            if i % 50 == 0:
                print(f"  …{i}/{len(pdfs)}")

    rows.sort(key=lambda r: r["icao"])

    with args.out.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f, fieldnames=["icao", "name", "fuels", "avt_excerpt", "error"]
        )
        writer.writeheader()
        writer.writerows(rows)

    ul91_rows = [r for r in rows if set(r["fuels"].split("|")) & UL91_EQUIVALENT]
    with args.ul91_out.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f, fieldnames=["icao", "name", "fuels", "avt_excerpt"]
        )
        writer.writeheader()
        for r in ul91_rows:
            writer.writerow({k: r[k] for k in writer.fieldnames})

    print(f"\nFichier complet : {args.out} ({len(rows)} terrains)")
    print(f"Filtre UL91     : {args.ul91_out} ({len(ul91_rows)} terrains)")
    print("\nAperçu UL91 (10 premiers) :")
    for r in ul91_rows[:10]:
        print(f"  {r['icao']:6} {r['fuels']:35} {r['name']}")


if __name__ == "__main__":
    main()
