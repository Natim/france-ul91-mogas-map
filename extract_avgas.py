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
import json
import re
import subprocess
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import date
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

# Libellés humains pour les sorties Markdown.
FUEL_LABELS = {
    "UL91": "UL91",
    "UL_AERO": "UL AERO",
    "SUPER_PLUS": "Super Plus",
    "MOGAS": "MOGAS",
    "100LL": "100LL",
    "JET_A1": "Jet A1",
}

AIRAC_DIR_RE = re.compile(r"AIRAC-(\d{4}-\d{2}-\d{2})")

LAT_RE = re.compile(
    r"LAT\s*:\s*(\d{1,3})\s+(\d{1,2})\s+(\d{1,2})\s*([NS])", re.IGNORECASE
)
LON_RE = re.compile(
    r"LONG\s*:\s*(\d{1,3})\s+(\d{1,2})\s+(\d{1,2})\s*([EW])", re.IGNORECASE
)

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


def _dms_to_decimal(deg: str, minutes: str, seconds: str, hemi: str) -> float:
    value = int(deg) + int(minutes) / 60 + int(seconds) / 3600
    return -value if hemi.upper() in ("S", "W") else round(value, 6)


def extract_coordinates(text: str) -> tuple[float | None, float | None]:
    """Extrait latitude/longitude depuis l'en-tête du VAC (DMS → décimal)."""
    head = "\n".join(text.splitlines()[:20])
    lat_match = LAT_RE.search(head)
    lon_match = LON_RE.search(head)
    if not (lat_match and lon_match):
        return None, None
    lat = _dms_to_decimal(*lat_match.groups())
    lon = _dms_to_decimal(*lon_match.groups())
    return round(lat, 6), round(lon, 6)


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
        return {
            "icao": icao,
            "name": "",
            "fuels": "",
            "lat": "",
            "lon": "",
            "avt_excerpt": "",
            "error": "no_text",
        }

    section = extract_avt_section(text)
    fuels = detect_fuels(section)
    name = extract_aerodrome_name(text)
    lat, lon = extract_coordinates(text)

    excerpt = re.sub(r"\s+", " ", section).strip()[:300]

    return {
        "icao": icao,
        "name": name,
        "fuels": "|".join(fuels),
        "lat": f"{lat:.6f}" if lat is not None else "",
        "lon": f"{lon:.6f}" if lon is not None else "",
        "avt_excerpt": excerpt,
        "error": "",
    }


def detect_airac(vac_dir: Path) -> str:
    """Cherche le dossier AIRAC le plus récent en remontant depuis vac_dir.

    Le paquet eAIP du SIA contient plusieurs sous-AIRAC (FRANCE, PAC-N,
    PAC-P, RUN, CAR-SAM-NAM) qui peuvent dater de cycles différents.
    On prend toujours le plus récent (max sur le nom YYYY-MM-DD).
    """
    found: set[str] = set()
    for ancestor in vac_dir.parents:
        for candidate in ancestor.glob("**/AIRAC-*"):
            m = AIRAC_DIR_RE.search(candidate.name)
            if m:
                found.add(m.group(1))
        if found:
            return max(found)
    return "unknown"


def render_markdown(
    ul91_rows: list[dict[str, str]],
    airac: str,
) -> str:
    """Génère le contenu d'un AERODROMES.md autonome."""
    from collections import Counter

    counts: Counter[str] = Counter()
    for r in ul91_rows:
        for f in r["fuels"].split("|"):
            if f:
                counts[f] += 1

    lines: list[str] = []
    lines.append("# Aérodromes français — UL91 / Super Plus")
    lines.append("")
    lines.append(
        f"**{len(ul91_rows)} aérodromes** publient une pompe essence "
        "(UL91, UL AERO SUPER+, Super Plus ou MOGAS) dans leur carte VAC "
        "officielle."
    )
    lines.append("")
    lines.append(f"- **Cycle AIRAC** : {airac}")
    lines.append(f"- **Dernière mise à jour du fichier** : {date.today().isoformat()}")
    lines.append("- **Source** : eAIP du SIA, Atlas-VAC")
    lines.append("")
    lines.append("## Répartition par carburant")
    lines.append("")
    lines.append("| Carburant | Nb terrains |")
    lines.append("|-----------|-------------|")
    for key in ("UL91", "UL_AERO", "SUPER_PLUS", "MOGAS", "100LL", "JET_A1"):
        if counts.get(key):
            lines.append(f"| {FUEL_LABELS[key]} | {counts[key]} |")
    lines.append("")
    lines.append(
        "> `UL91` et `UL AERO SUPER+` désignent en pratique le même carburant : "
        "`UL AERO SUPER+` est la dénomination commerciale TotalEnergies du UL91."
    )
    lines.append("")
    lines.append("## Liste complète")
    lines.append("")
    lines.append("| OACI | Nom | Carburants |")
    lines.append("|------|-----|-----------|")
    for r in sorted(ul91_rows, key=lambda x: x["icao"]):
        fuels = ", ".join(
            FUEL_LABELS.get(f, f) for f in r["fuels"].split("|") if f
        )
        lines.append(f"| {r['icao']} | {r['name']} | {fuels} |")
    lines.append("")
    lines.append(
        "_Fichier auto-généré par "
        "[`extract_avgas.py`](./extract_avgas.py). Ne pas éditer à la main._"
    )
    lines.append("")
    return "\n".join(lines)


def _marker_category(fuels: set[str]) -> str:
    has_unleaded = bool(fuels & {"UL91", "UL_AERO"})
    has_super_plus = "SUPER_PLUS" in fuels
    if has_unleaded and has_super_plus:
        return "both"
    if has_unleaded:
        return "ul91"
    if has_super_plus:
        return "super_plus"
    return "other"


def render_map(ul91_rows: list[dict[str, str]], airac: str) -> str:
    """Génère une page HTML Leaflet/OSM autonome avec un marqueur par terrain."""
    points = []
    for r in ul91_rows:
        if not r.get("lat") or not r.get("lon"):
            continue
        fuels_set = {f for f in r["fuels"].split("|") if f}
        fuels_human = ", ".join(
            FUEL_LABELS.get(f, f) for f in sorted(fuels_set)
        )
        points.append(
            {
                "icao": r["icao"],
                "name": r["name"],
                "fuels": sorted(fuels_set),
                "fuels_human": fuels_human,
                "category": _marker_category(fuels_set),
                "lat": float(r["lat"]),
                "lon": float(r["lon"]),
            }
        )
    data_json = json.dumps(points, ensure_ascii=False, indent=2)
    updated = date.today().isoformat()
    return f"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>Aérodromes UL91 / Super Plus — France</title>
<link rel="stylesheet"
  href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"
  integrity="sha256-p4NxAoJBhIIN+hmNHrzRCf9tD/miZyoHS5obTRR9BMY="
  crossorigin="" />
<style>
  html, body {{ margin: 0; padding: 0; height: 100%; font-family: system-ui, sans-serif; }}
  #map {{ position: absolute; inset: 0; }}
  .info-panel {{
    position: absolute; top: 12px; right: 12px; z-index: 1000;
    background: rgba(255,255,255,0.95); padding: 12px 16px;
    border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.2);
    font-size: 13px; max-width: 280px;
  }}
  .info-panel h1 {{ margin: 0 0 6px; font-size: 15px; }}
  .info-panel .meta {{ color: #666; font-size: 11px; margin-bottom: 8px; }}
  .legend {{ margin-top: 8px; }}
  .legend label {{
    display: flex; align-items: center; gap: 8px;
    cursor: pointer; user-select: none; line-height: 1.6;
  }}
  .legend .dot {{
    display: inline-block; width: 14px; height: 14px; border-radius: 50%;
    border: 2px solid white; box-shadow: 0 0 0 1px rgba(0,0,0,0.3);
  }}
  .dot-ul91 {{ background: #2ecc71; }}
  .dot-super_plus {{ background: #f39c12; }}
  .dot-both {{ background: #3498db; }}
  .popup-icao {{ font-weight: bold; font-size: 14px; }}
  .popup-name {{ margin: 4px 0; }}
  .popup-fuels {{ font-size: 12px; color: #444; }}
  a {{ color: #3498db; }}
</style>
</head>
<body>
<div id="map"></div>
<div class="info-panel">
  <h1>Essence aviation en France</h1>
  <div class="meta">
    {len(points)} terrains · AIRAC {airac} · MAJ {updated}<br>
    Source : <a href="https://www.sia.aviation-civile.gouv.fr/" target="_blank" rel="noopener">eAIP SIA</a> ·
    <a href="https://github.com/Natim/french-ul91-superplus-aerodrome" target="_blank" rel="noopener">Code</a>
  </div>
  <div class="legend">
    <label><input type="checkbox" data-cat="ul91" checked>
      <span class="dot dot-ul91"></span>UL91 / UL AERO</label>
    <label><input type="checkbox" data-cat="super_plus" checked>
      <span class="dot dot-super_plus"></span>Super Plus uniquement</label>
    <label><input type="checkbox" data-cat="both" checked>
      <span class="dot dot-both"></span>UL91 + Super Plus</label>
  </div>
</div>

<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"
  integrity="sha256-20nQCchB9co0qIjJZRGuk2/Z9VM+kNiyxNV1lvTlZBo="
  crossorigin=""></script>
<script>
const AERODROMES = {data_json};

const COLORS = {{
  ul91: "#2ecc71",
  super_plus: "#f39c12",
  both: "#3498db",
}};

const map = L.map("map").setView([46.7, 2.3], 6);

L.tileLayer("https://tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png", {{
  maxZoom: 18,
  attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
}}).addTo(map);

const layers = {{ ul91: L.layerGroup(), super_plus: L.layerGroup(), both: L.layerGroup() }};

for (const a of AERODROMES) {{
  const color = COLORS[a.category] || "#888";
  const marker = L.circleMarker([a.lat, a.lon], {{
    radius: 7,
    weight: 2,
    color: "white",
    fillColor: color,
    fillOpacity: 0.95,
  }});
  marker.bindPopup(
    `<div class="popup-icao">${{a.icao}}</div>` +
    `<div class="popup-name">${{a.name}}</div>` +
    `<div class="popup-fuels">${{a.fuels_human}}</div>`
  );
  marker.bindTooltip(`${{a.icao}} — ${{a.name}}`, {{ direction: "top" }});
  (layers[a.category] || layers.ul91).addLayer(marker);
}}
Object.values(layers).forEach(g => g.addTo(map));

document.querySelectorAll(".legend input[type=checkbox]").forEach(cb => {{
  cb.addEventListener("change", () => {{
    const layer = layers[cb.dataset.cat];
    if (!layer) return;
    if (cb.checked) layer.addTo(map); else map.removeLayer(layer);
  }});
}});
</script>
</body>
</html>
"""


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
    parser.add_argument(
        "--md-out",
        type=Path,
        default=Path("AERODROMES.md"),
        help="Markdown listant les aérodromes UL91-équivalents.",
    )
    parser.add_argument(
        "--map-out",
        type=Path,
        default=Path("docs/index.html"),
        help="Page HTML autonome (Leaflet/OSM) prête pour GitHub Pages.",
    )
    parser.add_argument(
        "--airac",
        default=None,
        help="Cycle AIRAC (YYYY-MM-DD). Auto-détecté depuis --vac-dir si omis.",
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

    full_fields = ["icao", "name", "fuels", "lat", "lon", "avt_excerpt", "error"]
    ul91_fields = ["icao", "name", "fuels", "lat", "lon", "avt_excerpt"]

    with args.out.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=full_fields)
        writer.writeheader()
        writer.writerows(rows)

    ul91_rows = [r for r in rows if set(r["fuels"].split("|")) & UL91_EQUIVALENT]
    with args.ul91_out.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=ul91_fields)
        writer.writeheader()
        for r in ul91_rows:
            writer.writerow({k: r[k] for k in writer.fieldnames})

    airac = args.airac or detect_airac(args.vac_dir)
    args.md_out.write_text(render_markdown(ul91_rows, airac), encoding="utf-8")

    args.map_out.parent.mkdir(parents=True, exist_ok=True)
    args.map_out.write_text(render_map(ul91_rows, airac), encoding="utf-8")
    missing_coords = [r["icao"] for r in ul91_rows if not r["lat"]]

    print(f"\nFichier complet : {args.out} ({len(rows)} terrains)")
    print(f"Filtre UL91     : {args.ul91_out} ({len(ul91_rows)} terrains)")
    print(f"Markdown        : {args.md_out} (AIRAC {airac})")
    print(f"Carte HTML      : {args.map_out}")
    if missing_coords:
        print(f"  ⚠ {len(missing_coords)} terrains sans coordonnées : {missing_coords}")
    print("\nAperçu UL91 (10 premiers) :")
    for r in ul91_rows[:10]:
        print(f"  {r['icao']:6} {r['fuels']:35} {r['name']}")


if __name__ == "__main__":
    main()
