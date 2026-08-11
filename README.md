# Carte des aérodromes UL91 / mogas en France

Où faire le plein d'essence **sans plomb** en France : liste et carte des
aérodromes distribuant de l'**AVGAS UL91** ou de l'essence **SP95 / SP98**
(**Super Plus**, **UL AERO SUPER+**), extraites automatiquement de
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

### UL91 n'est pas du SP98

Une distinction que ce dépôt prend au sérieux, parce que les deux carburants ne
sont pas interchangeables selon votre certification :

| Carburant | Nature | Noms rencontrés dans les VAC |
|---|---|---|
| **UL91** | Essence *aviation* sans plomb, norme ASTM D7547 | `UL91`, `UL 91` |
| **SP95 / SP98** | Essence sans plomb norme EN 228 | `SUPER PLUS`, `SP95`, `SP98`, `MOGAS`, `UL AERO SUPER+` |
| **100LL** | Essence aviation **plombée** | `100LL`, `100 LL`, `AVGAS 100LL` |

Le piège est l'`UL AERO SUPER+`. Malgré son préfixe « UL », ce **n'est pas** du
UL91 : c'est un [SP98 sans éthanol de qualité
aviation](https://aviation.totalenergies.com/fr/carburants-et-services-aviation/carburant-aviation/ul-aero-super-plus)
distribué par TotalEnergies, réservé aux moteurs ROTAX 912/914 homologués pour
le SP98 EN 228. TotalEnergies vend d'ailleurs l'UL91 et l'UL AERO SUPER+ comme
deux produits distincts. Il est donc classé ici avec le SP95/SP98, et pas avec
l'UL91 : l'inverse enverrait un pilote UL91 vers une pompe qui ne lui convient
pas, et ferait manquer sept terrains à un pilote de ROTAX.

## Lire la carte

Deux informations indépendantes sont encodées :

- **La forme donne le carburant** : ● UL91, ■ SP95/SP98 (dont UL AERO SUPER+).
  Un terrain qui vend les deux porte **deux marqueurs**, pour rester visible
  quel que soit le filtre actif.
- **La couleur donne les conditions d'accès** : 🟢 automate ou H24,
  🟠 HX / PPR / sur demande / horaires limités, ⚪ non précisé par la VAC.

### Pourquoi « automate » plutôt que « H24 »

Les VAC annoncent rarement des horaires nets. Elles disent plutôt « H24 par
carte TOTAL, sinon bureau de piste 0900-1600 » : c'est H24 *si vous avez la
carte*. Un simple drapeau H24/HX serait faux pour la moitié des lecteurs.

La question retenue est donc celle que se pose un pilote de passage : **puis-je
me servir seul, ou dois-je organiser quelque chose ?** Un terrain est vert
quand la carte annonce une pompe en libre-service ; orange dès qu'il faut un
PPR, un appel, être basé, ou tomber dans une plage horaire.

Les conditions peuvent différer d'un carburant à l'autre sur le même terrain —
Montceau-les-Mines publie le 100LL sur automate H24 mais l'UL91 seulement de
0800 à 1500 — donc l'analyse est faite carburant par carburant.

> Cette classification est **déduite automatiquement** d'un texte libre. Elle
> vous aide à trier, pas à décider : la carte VAC en vigueur fait foi, et un
> coup de téléphone reste la seule certitude. Le texte brut de la section
> « 10 - AVT » est affiché dans chaque popup pour que vous puissiez vérifier.

## Fichiers produits

| Fichier | Contenu |
|---|---|
| [`docs/index.html`](./docs/index.html) | Carte Leaflet/OSM, déployée sur GitHub Pages. Page statique, éditable à la main. |
| [`docs/aerodromes.json`](./docs/aerodromes.json) | Données consommées par la carte. **Généré.** |
| [`AERODROMES.md`](./AERODROMES.md) | Liste Markdown lisible. **Généré.** |
| [`data/aerodromes-unleaded.csv`](./data/aerodromes-unleaded.csv) | Terrains avec essence sans plomb. **Généré.** |
| [`data/aerodromes-all.csv`](./data/aerodromes-all.csv) | Les 420 terrains français et leur section avitaillement brute. **Généré.** |

Colonnes CSV : `icao`, `name`, `fuels` (séparés par `|`), `availability`
(`CARBURANT=niveau`, séparés par `|`), `lat`, `lon` (degrés décimaux),
`fuel_section` (texte brut de la section « 10 - AVT »), `error`.

Niveaux d'`availability` : `self_service`, `restricted`, `unknown`.

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
| `model.py` | Taxonomie des carburants, familles, `Aerodrome` |
| `parsing.py` | Regex et extraction pure depuis le texte des VAC |
| `availability.py` | Déduction des conditions d'accès, clause par clause |
| `overrides.py` | Données manuelles : corrections d'accès et terrains hors AIP |
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
   préalable la marque `UL AERO SUPER+` (aussi écrite `UL AEROSUPER +` ou
   `UL Aéro Super +`) pour ne pas créditer aussi le terrain d'un SP98 générique
   que sa VAC n'annonce pas.
4. Découpage de la section en clauses pour attribuer les conditions d'accès au
   carburant nommé dans la même phrase, avec repli sur les clauses générales.
5. Lecture des coordonnées `LAT`/`LONG` de l'en-tête (sexagésimal → décimal).
6. Normalisation des caractères Windows-1252 que Poppler laisse passer.
7. Application des données manuelles d'`overrides.py` — corrections d'accès et
   terrains hors AIP — uniquement sur la liste Markdown et la carte : les CSV
   gardent ce que dit la VAC, si bien qu'une entrée se retire en la supprimant.

## Ajouter une donnée manuelle

Tout ce qui ne vient pas de l'AIP vit dans un seul fichier,
[`src/fuelmap/overrides.py`](./src/fuelmap/overrides.py), pour rester auditable.
Deux cas, selon que le terrain figure ou non à l'AIP.

**Corriger un terrain existant** — sa VAC ne dit rien de ses conditions, ou il
dispose d'un carburant que l'AIP ignore. Ajoutez une entrée à `OVERRIDES`,
indexée par code OACI puis par carburant :

```python
"LFOF": Override(
    availability={UL91: AVAILABILITY_RESTRICTED, SUPER_PLUS: AVAILABILITY_SELF_SERVICE},
    reason="Pompe UL91 en HX. SP98 H24 à la station Total en face, nécessite un bidon.",
),
```

Nommer un carburant que la VAC ignore l'ajoute au terrain. C'est ce qui fait
entrer dans la carte un terrain qui ne vend aucun sans plomb, mais jouxte une
station-service : LFCF Figeac et LFCY Royan n'y figurent qu'à ce titre, et le
résumé d'[`AERODROMES.md`](./AERODROMES.md) les compte à part. Faute d'horaires
vérifiés, `AVAILABILITY_UNKNOWN` reste un choix légitime : il déclare le
carburant sans rien affirmer de sa disponibilité.

**Ajouter un terrain absent de l'AIP** — typiquement une plateforme ULM privée,
sans carte VAC. Ajoutez une entrée à `ADDITIONS` : tout est manuel, position
comprise. Les fiches [BASULM](https://basulm.ffplum.fr/) de la FFPLUM sont une
bonne source ; reproduisez la position en sexagésimal dans `details` pour
qu'elle reste vérifiable.

```python
CuratedAerodrome(
    code="LF4724",
    name="MONTPEZAT D'AGENAIS",
    latitude=44.364167,
    longitude=0.491389,
    availability={UL91: AVAILABILITY_RESTRICTED},
    source="Fiche BASULM LF4724 (FFPLUM), mise à jour du 24/10/2024",
    note="Aérodrome privé ouvert aux ULM : accord préalable du gestionnaire…",
    details="BASULM LF4724 — LAT : N 44 21 51 - LONG : E 000 29 29…",
),
```

Puis `fuelmap rebuild`. Trois règles :

1. **Les CSV ne bougent pas.** Ils restent le reflet fidèle des cartes VAC. Une
   donnée manuelle n'apparaît que dans la liste Markdown et sur la carte, si
   bien qu'elle se retire en supprimant son entrée. C'est pourquoi
   [`AERODROMES.md`](./AERODROMES.md) compte plus de terrains que
   [`aerodromes-unleaded.csv`](./data/aerodromes-unleaded.csv).
2. **`reason` et `note` sont obligatoires** et affichés au pilote. Un terrain
   privé doit rappeler que l'accord du gestionnaire est requis.
3. **Rien ne se rafraîchit tout seul.** Ces entrées n'ont pas d'amont : à
   revérifier à chaque cycle AIRAC, et à garder peu nombreuses.

## Limites connues

- **Couverture militaire** : 3 aérodromes militaires (LFOJ Orléans-Bricy,
  LFRJ Landivisiau, LFRL Lanvéoc-Poulmic) n'ont pas de section AVT publique.
- **Pompes non-AIP** : les pompes de clubs, ULM ou automates privés non
  déclarés en AIP n'apparaissent **pas** dans l'eAIP. Pour ces cas, voir les
  cartes communautaires citées plus haut.
- **Statut « NIL »** : Mauléon-Soule (LFJB) déclare `AVT : NIL`, malgré ce que
  des cartes communautaires peuvent affirmer.
- **Mention « Super » seule** : Buno-Bonnevaux (LFFB) annonce `100LL, Super`
  sans préciser d'indice. Faute de pouvoir en déduire un SP95 ou un SP98, le
  terrain n'est **pas** compté comme sans plomb. C'est le seul cas du cycle.
- **Périmètre géographique** : France métropolitaine + DOM (codes OACI `LF*`).
  L'outre-mer Pacifique (NTAA, NWWW…) n'est pas couvert.
- **Conditions d'accès déduites** : le niveau vert/orange/gris vient d'une
  analyse de texte libre, pas d'un champ structuré de l'AIP. Il est vérifié
  sur les 43 terrains du cycle courant, mais une tournure inédite peut le
  tromper. Le texte source est affiché dans la popup pour arbitrer.
- **Données manuelles** : voir [Ajouter une donnée manuelle](#ajouter-une-donnée-manuelle).
  Ces terrains et conditions ne viennent pas de l'AIP ; ils sont signalés « hors
  VAC » ou « hors AIP » dans la popup, et par un † ou un ‡ dans
  [`AERODROMES.md`](./AERODROMES.md). **Lisez la raison affichée** : elle précise
  notamment quand le carburant n'est pas au parking, ou quand l'atterrissage
  exige un accord préalable.
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
