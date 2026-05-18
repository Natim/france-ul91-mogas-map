# French UL91 / Super Plus Aerodromes

Liste des aérodromes français disposant d'une pompe d'avitaillement en
**UL91**, **UL AERO SUPER+** ou **Super Plus / SP95**, extraite automatiquement
depuis l'[eAIP du SIA](https://www.sia.aviation-civile.gouv.fr/) (cartes VAC,
Atlas-VAC AIRAC 2026-05-14).

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

## Résultats — AIRAC 2026-05-14

**41 aérodromes** publient une pompe essence (UL91 / UL AERO / Super Plus) dans
leur carte VAC officielle :

| OACI | Nom | Carburants |
|------|-----|-----------|
| LFAE | EU MERS LE TREPORT | UL91 |
| LFBY | DAX SEYRESSE | 100LL, UL91 |
| LFCH | ARCACHON LA TESTE DE BUCH | 100LL, Jet A1, Super Plus, UL AERO |
| LFCS | BORDEAUX LEOGNAN SAUCATS | 100LL, UL91 |
| LFCU | USSEL THALAMY | 100LL, Super Plus |
| LFCV | VILLEFRANCHE DE ROUERGUE | 100LL, Super Plus |
| LFDA | AIRE SUR L'ADOUR | UL91 |
| LFDC | MONTENDRE MARCILLAC | UL91 |
| LFDE | EGLETONS | UL91 |
| LFDP | SAINT PIERRE D'OLERON | 100LL, Super Plus |
| LFDT | TARBES LALOUBERE | 100LL, UL91 |
| LFDV | COUHE VERAC | 100LL, Super Plus |
| LFFL | BAILLEAU ARMENONVILLE | 100LL, UL91 |
| LFFZ | SEZANNE SAINT REMY | 100LL, UL91 |
| LFGI | DIJON DAROIS | 100LL, Jet A1, Super Plus |
| LFGM | MONTCEAU LES MINES POUILLOUX | 100LL, UL91 |
| LFHC | PEROUGES MEXIMIEUX | UL91 |
| LFHN | BELLEGARDE VOUVRAY | 100LL, UL91 |
| LFHS | BOURG CEYZERIAT | 100LL, UL91 |
| LFIT | TOULOUSE BOURG SAINT BERNARD | UL91 |
| LFJY | CHAMBLEY | 100LL, Jet A1, UL91 |
| LFLG | GRENOBLE LE VERSOUD | 100LL, Jet A1, UL91 |
| LFLO | ROANNE | 100LL, Jet A1, UL91 |
| LFLQ | MONTELIMAR ANCONE | UL91 |
| LFLY | LYON BRON | 100LL, Jet A1, Super Plus, UL AERO |
| LFMP | PERPIGNAN RIVESALTES | 100LL, Jet A1, Super Plus, UL AERO |
| LFMV | AVIGNON CAUMONT | 100LL, Jet A1, Super Plus, UL AERO |
| LFMW | CASTELNAUDARY VILLENEUVE | Super Plus, UL91 |
| LFNA | GAP TALLARD | 100LL, Jet A1, UL91 |
| LFNE | SALON EYGUIERES | 100LL, Super Plus |
| LFNH | CARPENTRAS | 100LL, UL91 |
| LFNJ | ASPRES SUR BUECH | UL91 |
| LFOF | ALENCON VALFRAMBERT | UL91 |
| LFOI | ABBEVILLE | 100LL, UL91 |
| LFPE | MEAUX ESBLY | 100LL, UL91 |
| LFPF | BEYNES THIVERVAL | UL91 |
| LFPL | LOGNES EMERAINVILLE | 100LL, Jet A1, Super Plus, UL AERO |
| LFQD | ARRAS ROCLINCOURT | 100LL, Super Plus |
| LFSA | BESANCON THISE | Super Plus |
| LFSH | HAGUENAU | 100LL, UL91 |
| LFXU | LES MUREAUX | 100LL, UL91 |

### Répartition par carburant

| Carburant | Nb terrains |
|-----------|-------------|
| UL91 (explicite) | 28 |
| Super Plus / SP95 | 14 |
| UL AERO SUPER+ (TotalEnergies) | 5 |
| dont aussi 100LL | 29 |
| dont aussi Jet A1 | 10 |

> **Note** : `UL91` et `UL AERO SUPER+` désignent en pratique le même
> carburant. `UL AERO SUPER+` est la dénomination commerciale TotalEnergies
> du UL91. En agrégeant, **33 terrains** ont du UL91 et **14** du Super Plus
> (certains ont les deux, comme LFMW Castelnaudary).

### Fichiers de données

- [`avgas_ul91.csv`](./avgas_ul91.csv) — Les 41 terrains filtrés.
- [`avgas_full.csv`](./avgas_full.csv) — Les 420 terrains avec leur section
  avitaillement complète (utile pour requêter d'autres carburants ou détecter
  des changements entre cycles AIRAC).

Colonnes : `icao`, `name`, `fuels` (pipe-séparé), `avt_excerpt` (le texte brut
de la section « 10 - AVT »).

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
       --vac-dir ./extracted/Atlas-VAC/PDF_AIPparSSection/VAC/AD \
       --out avgas_full.csv \
       --ul91-out avgas_ul91.csv
   ```

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

Données extraites depuis l'eAIP **AIRAC 2026-05-14**.

## Licence

- **Code** (`extract_avgas.py`) : MIT.
- **Données** (`avgas_*.csv`) : dérivées de l'eAIP du Service de l'Information
  Aéronautique français, soumises aux conditions d'utilisation du SIA. Voir
  <https://www.sia.aviation-civile.gouv.fr/>.
