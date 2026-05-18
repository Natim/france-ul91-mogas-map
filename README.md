# French UL91 / Super Plus Aerodromes

Liste des aérodromes français disposant d'une pompe d'avitaillement en
**UL91**, **UL AERO SUPER+** ou **Super Plus / SP95**, extraite automatiquement
depuis l'[eAIP du SIA](https://www.sia.aviation-civile.gouv.fr/) (cartes VAC,
Atlas-VAC).

## Pourquoi

Les pilotes d'aéronefs certifiés pour rouler à l'essence sans plomb
(UL91 — équivalent commercial : UL AERO SUPER+ de TotalEnergies — ou
SP95 « Super Plus ») ont besoin de savoir où s'avitailler en France.

Des cartes communautaires existent
([avionsgardan.org](https://www.avionsgardan.org/map/avgasul91.html),
[Air Total](https://www.total.fr/mes-deplacements/aviation/carte-air-total-france),
[Air BP](https://customers.airbp.com/where-to-find)), mais aucune ne se base
directement sur la source officielle (les cartes VAC du SIA) ni n'est
auto-régénérable à chaque cycle AIRAC.

Ce dépôt comble ce vide.

## Résultats

- **Carte interactive** : <https://natim.github.io/french-ul91-superplus-aerodrome/>
- **[AERODROMES.md](./AERODROMES.md)** — Liste lisible avec répartition par
  carburant et cycle AIRAC.

### Fichiers produits par le script

| Fichier | Contenu |
|---|---|
| [`docs/index.html`](./docs/index.html) | Carte Leaflet/OSM autonome, déployée sur GitHub Pages. |
| [`AERODROMES.md`](./AERODROMES.md) | Liste Markdown des terrains UL91/Super Plus. |
| [`avgas_ul91.csv`](./avgas_ul91.csv) | Terrains filtrés UL91-équivalent (avec coordonnées). |
| [`avgas_full.csv`](./avgas_full.csv) | Les 420 terrains français avec leur section avitaillement brute. |

Colonnes CSV : `icao`, `name`, `fuels` (pipe-séparé), `lat`, `lon` (degrés
décimaux), `avt_excerpt` (texte brut de la section « 10 - AVT »).

Tous ces fichiers sont régénérés à chaque exécution du script — voir la
section [Régénérer les données](#régénérer-les-données).

### Activer GitHub Pages

1. Sur GitHub, ouvrir **Settings → Pages**.
2. **Source** : `Deploy from a branch`.
3. **Branch** : `main` · **Folder** : `/docs`.
4. Sauvegarder. La carte sera servie à
   `https://<owner>.github.io/french-ul91-superplus-aerodrome/`.

La page est entièrement statique (HTML autonome, Leaflet via CDN, tuiles
OpenStreetMap), aucun build step nécessaire.

## Méthodologie

1. Téléchargement du paquet eAIP du SIA (`eaip_<date>.zip`).
2. Extraction des cartes VAC PDF (`Atlas-VAC/PDF_AIPparSSection/VAC/AD/AD-2.*.pdf`).
3. Pour chaque PDF, extraction texte via
   [`pdftotext -layout`](https://poppler.freedesktop.org/) (Poppler).
4. Isolation de la section `10 - AVT` (Carburants / Fuel) via regex, avec
   fallback sur le document complet.
5. Détection des variantes orthographiques :
   - `UL91` / `UL 91`
   - `UL AERO` (marque TotalEnergies)
   - `SUPER+` / `SUPER PLUS` / `SP95` / `SP98`
   - `MOGAS`
6. Normalisation des caractères Windows-1252 mal encodés que Poppler ne
   convertit pas (`\x91`–`\x97`).

## Régénérer les données

### Prérequis

- Python ≥ 3.10 (stdlib uniquement, aucune dépendance externe).
- `pdftotext` (paquet `poppler-utils` sur Debian/Ubuntu).

### Étapes

1. Télécharger le ZIP eAIP courant depuis le SIA :
   <https://www.sia.aviation-civile.gouv.fr/produits-numeriques-en-libre-disposition/eaip.html>
2. Dézipper le paquet quelque part :
   ```bash
   unzip eaip_<date>.zip -d ./extracted
   ```
3. Lancer le script en pointant sur le dossier des VAC PDF :
   ```bash
   python3 extract_avgas.py \
       --vac-dir ./extracted/Atlas-VAC/PDF_AIPparSSection/VAC/AD
   ```

Le script produit quatre fichiers (chemins surchargeables via `--out`,
`--ul91-out`, `--md-out`, `--map-out`) :

- `avgas_full.csv` — données brutes complètes
- `avgas_ul91.csv` — filtre UL91-équivalent
- `AERODROMES.md` — version Markdown lisible
- `docs/index.html` — carte Leaflet pour GitHub Pages

Le cycle AIRAC est auto-détecté depuis l'arborescence du paquet eAIP
(on peut le forcer avec `--airac YYYY-MM-DD`).

Temps d'exécution : ~2 s sur les 420 VAC (avec 8 workers).

## Limites connues

- **Couverture militaire** : 3 aérodromes militaires (LFOJ Orléans-Bricy,
  LFRJ Landivisiau, LFRL Lanvéoc-Poulmic) n'ont pas de section AVT publique.
- **Pompes non-AIP** : certaines pompes (clubs, ULM, automates privés
  non déclarés en AIP) n'apparaissent **pas** dans l'eAIP. Pour ces cas, voir
  les cartes communautaires citées en introduction.
- **Statut « NIL »** : Mauléon-Soule (LFJB) déclare `AVT : NIL` dans
  l'AIRAC en cours, malgré ce que des cartes communautaires peuvent affirmer.
- **Périmètre géographique** : ce dépôt couvre uniquement la France
  métropolitaine + DOM (codes OACI `LF*`). Outre-mer Pacifique (NTAA, NWWW,
  etc.) non inclus.
- **Données périssables** : l'eAIP est mis à jour à chaque cycle AIRAC
  (28 jours). Pour rester à jour, relancer le script à chaque cycle.

## Cycle AIRAC actuel

Indiqué en tête de [`AERODROMES.md`](./AERODROMES.md).

## Licence

- **Code** (`extract_avgas.py`) : MIT.
- **Données** (`avgas_*.csv`) : dérivées de l'eAIP du Service de l'Information
  Aéronautique français, soumises aux conditions d'utilisation du SIA. Voir
  <https://www.sia.aviation-civile.gouv.fr/>.
