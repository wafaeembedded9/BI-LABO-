# BI-LABO — IA & BI pour la Gestion Intelligente des Données de Laboratoire

> PFA — Filière MGSI — ENSAO 2025-2026 
> Réalisé par : Aanounou Salma & Allay Ouafae  
> Encadrant : M. Kerkri Abdelmounaim


 Description du projet

Plateforme intégrée combinant **Business Intelligence** et **Intelligence Artificielle** pour transformer des données brutes de laboratoire médical en indicateurs de pilotage actionnables.

 Architecture en 4 couches
1. ETL Pipeline — Ingestion, nettoyage, pseudonymisation (Python + RapidFuzz)
2. Entrepôt DuckDB** — Schéma en étoile (FACT_LABO + 4 dimensions)
3. **Dashboards Power BI** — 3 pages interactives (Vue Globale, Analyse Détaillée, Data Quality)
4. **Module LLM local** — Documentation, rapports, recherche guidée NL→SQL (Ollama)


Structure du projet


PFA_LABORATOIRE/
├── data/
│   ├── raw/                    # Fichier CSV source brut
│   └── processed/              # Données nettoyées + patient_id_map.json
├── logs/                       # Logs ETL horodatés + lineage JSON
├── llm_outputs/                # Livrables générés par le LLM
│   ├── catalogue_documentation.md
│   ├── rapport_pilotage.md
│   └── exemples_recherche.json
├── prompts/                    # Templates de prompts modulaires
│   ├── catalogue_prompt.txt
│   ├── rapport_prompt.txt
│   └── recherche_prompt.txt
├── src/
│   ├── etl.py                  # Pipeline ETL (9 étapes tracées)
│   ├── warehouse.py            # Construction entrepôt DuckDB
│   ├── catalogue.py            # Catalogue + seuils statistiques
│   ├── llm_labo.py             # Module LLM (ligne de commande)
│   └── streamlit_llm.py        # Interface web Streamlit
├── requirements.txt
├── .gitignore
└── README.md
```

---

## Installation

### Prérequis
- Python 3.12+
- [Ollama](https://ollama.com/) installé sur la machine

### 1. Cloner le projet

```bash
git clone https://github.com/wafaeembedded9/BI-LABO-.git
cd BI-LABO-
```
2. Installer les dépendances Python

```bash
pip install -r requirements.txt
```

3. Télécharger les modèles LLM (une seule fois)

```bash
ollama pull qwen3:0.6b
ollama pull qwen2.5-coder:1.5b
```

4. Lancer Ollama (en arrière-plan)

```bash
ollama serve


Utilisation — Ordre d'exécution

Étape 1 — Pipeline ETL

```bash
python src/etl.py
```
> Produit : `data/processed/resultats_nettoyes.csv` + logs JSON dans `logs/`

Étape 2 — Construction de l'entrepôt

```bash
python src/warehouse.py
```
> Produit : `data/labo.duckdb` avec schéma en étoile

Étape 3 — Catalogue et vue analytique

```bash
python src/catalogue.py
```
> Produit : table `CATALOGUE_TESTS`, `SEUILS_STATISTIQUES`, vue `V_DASHBOARD`

### Étape 4 — Module LLM (ligne de commande)

```bash
python src/llm_labo.py
```
> Menu interactif avec 5 options :
> - [1] Générer la documentation du catalogue
> - [2] Générer le rapport exécutif
> - [3] Démonstration recherche guidée
> - [4] TOUT GÉNÉRER
> - [5] Poser une question personnalisée

 Étape 5 — Interface web Streamlit

```bash
streamlit run src/streamlit_llm.py
```
> Ouvre automatiquement dans le navigateur : `http://localhost:8501`

---

Pages de l'interface Streamlit

| Page | Description |
|------|-------------|
| **Accueil** | KPIs globaux + état des livrables |
| **Recherche guidée** | Question en français → SQL → résultats |
| **Documentation catalogue** | Markdown généré par qwen3:0.6b |
| **Rapport exécutif** | Rapport de pilotage en 6 sections |
| **Diagnostics** | État de la base + génération complète |

---

## Modèles LLM utilisés

| Modèle | Taille | Rôle |
|--------|--------|------|
| `qwen3:0.6b` | 600M paramètres | Documentation catalogue + rapports en français |
| `qwen2.5-coder:1.5b` | 1.5B paramètres | Génération SQL DuckDB (recherche guidée) |

> **100% offline via Ollama** — aucune donnée ne quitte la machine locale (conformité RGPD)

---

Sécurité et conformité RGPD

- **Pseudonymisation SHA-256** déterministe et irréversible
- **Minimisation des données** : le LLM ne reçoit que des agrégats statistiques, jamais d'identifiants patients
- **Fonctionnement 100% local** : aucune API externe
- **Traçabilité complète** : logs JSON horodatés pour chaque transformation ETL

---

 Dashboards Power BI

Ouvrir le fichier `.pbix` dans Power BI Desktop.  
Les données sont exportées automatiquement depuis DuckDB via `src/export_powerbi.py`.

**3 pages disponibles :**
- **Vue Globale** — KPIs, volumes par service, saisonnalité, démographie
- **Analyse Détaillée** — Profil patient, évolution temporelle, comparaison aux seuils
- **Data Quality** — Score qualité, traçabilité des 9 étapes ETL


 Technologies utilisées

| Technologie | Usage |
|-------------|-------|
| Python 3.12 | Pipeline ETL, module LLM |
| DuckDB | Entrepôt de données embarqué |
| RapidFuzz | Normalisation des libellés (matching flou ≥ 80%) |
| Ollama | Exécution locale des LLM |
| Streamlit | Interface web du module LLM |
| Power BI | Dashboards de pilotage |
| SHA-256 | Pseudonymisation RGPD |






Année universitaire : 2025-2026