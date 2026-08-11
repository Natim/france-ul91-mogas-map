# Carte des aérodromes UL91 / mogas en France

Où faire le plein d'essence **sans plomb** en France : liste et carte des
aérodromes distribuant du **UL91** (alias **UL AERO SUPER+**) ou du **mogas**
(**Super Plus**, **SP95**, **SP98**), extraites automatiquement de
l'[eAIP du SIA](https://www.sia.aviation-civile.gouv.fr/) (cartes VAC,
Atlas-VAC).

**➡️ [Carte interactive](https://natim.github.io/france-ul91-mogas-map/)** ·
**[Liste complète](./AERODROMES.md)**

## Pourquoi

Les pilotes d'aéronefs certifiés pour l'essence sans plomb ont besoin de savoir
où s'avitailler. Des cartes communautaires existent
([avionsgardan.org](https://www.avionsgardan.org/map/avgasul91.html),
[Air Total](https://www.total.fr/mes-deplacements/aviation/carte-air-total-france),
[Air BP](https://customers.airbp.com/where-to-find)), mais aucune ne se base
directement sur la source officielle — les cartes VAC du SIA — ni ne se
régénère à chaque cycle AIRAC. Ce dépôt comble ce vide.

### UL91 n'est pas du mogas

Une distinction que ce dépôt prend au sérieux, parce que les deux carburants ne
sont pas interchangeables selon votre certification :

| Carburant | Nature | Noms rencontrés dans les VAC |
|---|---|---|
| **UL91** | Essence *aviation* sans plomb (ASTM D7547) | `UL91`, `UL 91`, `UL AERO SUPER+` |
| **Mogas** | Essence *routière* sans plomb | `SUPER PLUS`, `SUPER+`, `SP95`, `SP98`, `MOGAS` |
| **100LL** | Essence aviation **plombée** | `100LL`, `100 LL`, `AVGAS 100LL` |

`UL AERO SUPER+` est la marque TotalEnergies du UL91 : malgré le « SUPER+ » de
son nom, ce n'est **pas** du mogas. La carte les distingue par couleur.

## Fichiers produits

| Fichier | Contenu |
|---|---|
| [`docs/index.html`](./docs/index.html) | Carte Leaflet/OSM, déployée sur GitHub Pages. Page statique, éditable à la main. |
| [`docs/aerodromes.json`](./docs/aerodromes.json) | Données consommées par la carte. **Généré.** |
| [`AERODROMES.md`](./AERODROMES.md) | Liste Markdown lisible. **Généré.** |
| [`data/aerodromes-unleaded.csv`](./data/aerodromes-unleaded.csv) | Terrains avec essence sans plomb. **Généré.** |
| [`data/aerodromes-all.csv`](./data/aerodromes-all.csv) | Les 420 terrains français et leur section avitaillement brute. **Généré.** |

Colonnes CSV : `icao`, `name`, `fuels` (séparés par `|`), `lat`, `lon` (degrés
décimaux), `fuel_section` (texte brut de la section « 10 - AVT »), `error`.

## Installation

Prérequis : Python ≥ 3.10 et `pdftotext` (paquet `poppler-utils` sur
Debian/Ubuntu). Aucune dépendance Python à l'exécution.

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e .
```

## Régénérer les données

### Depuis l'eAIP (cycle AIRAC complet)

1. Télécharger le ZIP eAIP courant depuis le
   [SIA](https://www.sia.aviation-civile.gouv.fr/produits-numeriques-en-libre-disposition/eaip.html).
2. Le dézipper, puis lancer l'extraction :

```bash
unzip eaip_<date>.zip -d ./extracted
fuelmap extract --vac-dir ./extracted/Atlas-VAC/PDF_AIPparSSection/VAC/AD
```

Le cycle AIRAC est auto-détecté depuis l'arborescence du paquet (forçable avec
`--airac YYYY-MM-DD`). Comptez ~2 s pour les 420 cartes avec 8 processus.

C'est aussi ce que fait le workflow **Rafraîchir les données AIRAC**, qui ouvre
une pull request avec le diff.

### Depuis le CSV commité (sans les PDF)

Pour retoucher la présentation sans avoir le paquet eAIP sous la main :

```bash
fuelmap rebuild
```

Régénère `AERODROMES.md`, `docs/aerodromes.json` et le CSV filtré à partir de
`data/aerodromes-all.csv`. La CI vérifie que ces fichiers dérivés sont à jour.

### Retoucher la carte

`docs/index.html` est une page statique ordinaire : éditez-la directement, elle
charge ses données via `fetch()`. Pour la prévisualiser il faut un serveur HTTP
(`file://` bloque la requête) :

```bash
python3 -m http.server --directory docs 8000
```

## Développement

```bash
pip install -e ".[dev]"
pytest
ruff check .
```

Le code vit dans `src/fuelmap/` :

| Module | Rôle |
|---|---|
| `model.py` | Taxonomie des carburants, `Aerodrome`, catégories de la carte |
| `parsing.py` | Regex et extraction pure depuis le texte des VAC |
| `vac.py` | Appel à `pdftotext`, détection du cycle AIRAC |
| `pipeline.py` | Parcours parallèle du dossier VAC |
| `render/` | Sorties CSV, Markdown et données de la carte |
| `cli.py` | Sous-commandes `extract` et `rebuild` |

Les tests tournent sur des extraits de texte VAC stockés dans
[`tests/fixtures/`](./tests/fixtures/), donc sans le paquet eAIP.

## Méthodologie

1. Extraction texte de chaque `AD-2.LF*.pdf` via
   [`pdftotext -layout`](https://poppler.freedesktop.org/).
2. Isolation de la section `10 - AVT` (Carburants / Fuel), qui se termine à la
   section 11 ou 12. Repli sur le document entier si les marqueurs manquent.
3. Détection des variantes orthographiques de chaque carburant, en masquant au
   préalable la marque `UL AERO SUPER+` pour ne pas la compter comme du mogas.
4. Lecture des coordonnées `LAT`/`LONG` de l'en-tête (sexagésimal → décimal).
5. Normalisation des caractères Windows-1252 que Poppler laisse passer.

## Limites connues

- **Couverture militaire** : 3 aérodromes militaires (LFOJ Orléans-Bricy,
  LFRJ Landivisiau, LFRL Lanvéoc-Poulmic) n'ont pas de section AVT publique.
- **Pompes non-AIP** : les pompes de clubs, ULM ou automates privés non
  déclarés en AIP n'apparaissent **pas** dans l'eAIP. Pour ces cas, voir les
  cartes communautaires citées plus haut.
- **Statut « NIL »** : Mauléon-Soule (LFJB) déclare `AVT : NIL`, malgré ce que
  des cartes communautaires peuvent affirmer.
- **Périmètre géographique** : France métropolitaine + DOM (codes OACI `LF*`).
  L'outre-mer Pacifique (NTAA, NWWW…) n'est pas couvert.
- **Données périssables** : l'eAIP change tous les 28 jours. Le cycle publié est
  indiqué en tête d'[`AERODROMES.md`](./AERODROMES.md) et sur la carte.
- **Aucune valeur opérationnelle** : ces données sont indicatives. Consultez la
  carte VAC en vigueur et appelez le terrain avant de compter sur une pompe.

## Déploiement

GitHub Pages, servi depuis `/docs` sur `main` (**Settings → Pages → Deploy from
a branch**). Page entièrement statique : Leaflet via CDN, tuiles OpenStreetMap,
aucune étape de build.

## Licence

- **Code** : MIT, voir [LICENSE](./LICENSE).
- **Données** : dérivées de l'eAIP du Service de l'Information Aéronautique,
  soumises aux [conditions d'utilisation du
  SIA](https://www.sia.aviation-civile.gouv.fr/).
