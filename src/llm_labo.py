import json
import os
import duckdb
import ollama



FICHIER_DB    = "data/labo.duckdb"
PROMPTS_DIR   = "prompts"
OUTPUTS_DIR   = "llm_outputs"

# Modèles hybrides
MODEL_DOC     = "qwen3:0.6b"          # Pour documentation et rapport (français)
MODEL_SQL     = "qwen2.5-coder:1.5b"  # Pour recherche guidée (SQL parfait)

SYSTEM_PROMPT = """Tu es un assistant BI spécialisé en gestion de données de laboratoire médical.
Tu travailles sur un entrepôt de données anonymisé (DuckDB) contenant des résultats d'analyses biologiques.
Tu ne reçois JAMAIS d'identifiants patients réels — uniquement des agrégats et indicateurs.
Tes réponses sont concises, professionnelles, et en français.
Tu ne formules AUCUNE conclusion médicale clinique — ton rôle est la gestion et le pilotage des données."""


# UTILITAIRES

def _charger_prompt(fichier: str, **variables) -> str:
    """Charge un template de prompt depuis prompts/ et injecte les variables."""
    chemin = os.path.join(PROMPTS_DIR, fichier)
    if not os.path.exists(chemin):
        raise FileNotFoundError(f"Prompt introuvable : {chemin}")
    with open(chemin, "r", encoding="utf-8") as f:
        template = f.read()
    return template.format(**variables)


def _appel_llm(prompt: str, model: str, system: str = SYSTEM_PROMPT) -> str:
    """Appelle le LLM spécifié via Ollama."""
    try:
        print(f"  ⏳ Envoi au LLM ({model})...")
        response = ollama.chat(
            model=model,
            messages=[
                {"role": "system",  "content": system},
                {"role": "user",    "content": prompt},
            ],
        )
        print(f"  ✅ Réponse reçue de {model}")
        return response["message"]["content"].strip()
    except Exception as e:
        return f"[ERREUR LLM] {e}\n→ Vérifiez qu'Ollama est lancé : 'ollama serve'"


def _sauvegarder(nom_fichier: str, contenu: str):
    """Sauvegarde un livrable dans llm_outputs/."""
    os.makedirs(OUTPUTS_DIR, exist_ok=True)
    chemin = os.path.join(OUTPUTS_DIR, nom_fichier)
    with open(chemin, "w", encoding="utf-8") as f:
        f.write(contenu)
    print(f"  → Sauvegardé : {chemin}")


# FONCTION 1 — Aide au Data Catalog (qwen3:0.6b)


def generer_documentation_catalogue() -> str:
    """
    Lit le catalogue depuis DuckDB avec les VRAIES valeurs calculées,
    génère documentation via qwen3:0.6b.
    """
    print("  📊 Chargement des données depuis DuckDB...")
    conn = duckdb.connect(FICHIER_DB, read_only=True)
    
    # Récupération des vraies données avec calculs DuckDB
    df_cat = conn.execute("""
        SELECT c.nom_test, c.categorie, c.unite,
               ROUND(s.p5, 2) AS p5,
               ROUND(s.mediane, 2) AS mediane,
               ROUND(s.p95, 2) AS p95,
               s.nb_mesures
        FROM   CATALOGUE_TESTS     c
        JOIN   SEUILS_STATISTIQUES s ON c.nom_test = s.nom_test
        ORDER  BY c.categorie, c.nom_test
    """).df()
    
    # Calcul du taux hors catalogue
    total = conn.execute("SELECT COUNT(*) FROM V_DASHBOARD").fetchone()[0]
    hors_cat = conn.execute("""
        SELECT COUNT(*) FROM V_DASHBOARD 
        WHERE couverture_catalogue = 'Hors catalogue'
    """).fetchone()[0]
    pct_hors = round(hors_cat / total * 100, 1) if total > 0 else 0
    
    conn.close()
    print(f"   {len(df_cat)} tests chargés, {pct_hors}% hors catalogue")

    contexte = df_cat.to_string(index=False)
    
    prompt = _charger_prompt(
        "catalogue_prompt.txt", 
        contexte=contexte,
        pct_hors_catalogue=pct_hors
    )
    
    print("   Génération de la documentation...")
    doc = _appel_llm(prompt, model=MODEL_DOC)

    contenu_final = f"""# Documentation du Catalogue des Tests — Laboratoire BI

> Générée automatiquement par le module LLM (qwen3:0.6B via Ollama) — 100% offline
> Données : agrégats statistiques uniquement (principe de minimisation RGPD)
> Date de génération : Juin 2026

{doc}
"""
    _sauvegarder("catalogue_documentation.md", contenu_final)
    return doc



# FONCTION 2 — Rapport dashboard (qwen3:0.6b)


def generer_rapport_dashboard() -> str:
    """
    Lit les KPIs depuis DuckDB avec calculs réels,
    génère rapport via qwen3:0.6b.
    """
    print("  📊 Chargement des KPIs depuis DuckDB...")
    conn = duckdb.connect(FICHIER_DB, read_only=True)

    # KPIs globaux
    kpis = conn.execute("""
        SELECT COUNT(DISTINCT id_patient)   AS nb_patients,
               COUNT(*)                     AS nb_analyses,
               ROUND(AVG(score_qualite), 1) AS score_qualite_moyen,
               COUNT(DISTINCT nom_test)     AS nb_tests_distincts
        FROM V_DASHBOARD
    """).df().iloc[0].to_dict()

    # Répartition clinique
    repartition = conn.execute("""
        SELECT statut_clinique, COUNT(*) AS nb,
               ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 1) AS pct
        FROM   V_DASHBOARD GROUP BY statut_clinique ORDER BY nb DESC
    """).df().to_string(index=False)

    # Top 5 services
    top_services = conn.execute("""
        SELECT service, COUNT(*) AS volume
        FROM   V_DASHBOARD GROUP BY service ORDER BY volume DESC LIMIT 5
    """).df().to_string(index=False)

    # Saisonnalité
    saisonnalite = conn.execute("""
        SELECT nom_mois, mois, COUNT(*) AS volume
        FROM   V_DASHBOARD GROUP BY nom_mois, mois ORDER BY mois
    """).df().to_string(index=False)

    # Tranches d'âge
    tranches = conn.execute("""
        SELECT tranche_age, COUNT(DISTINCT id_patient) AS nb_patients
        FROM   V_DASHBOARD GROUP BY tranche_age ORDER BY nb_patients DESC
    """).df().to_string(index=False)

    # Répartition sexe
    sexe = conn.execute("""
        SELECT sexe, COUNT(DISTINCT id_patient) AS nb_patients, COUNT(*) AS nb_analyses
        FROM   V_DASHBOARD GROUP BY sexe ORDER BY nb_patients DESC
    """).df().to_string(index=False)

    conn.close()
    print("  KPIs chargés")

    contexte = f"""KPIs GLOBAUX :
- Patients pseudonymisés : {kpis['nb_patients']:,}
- Analyses totales       : {kpis['nb_analyses']:,}
- Score qualité moyen    : {kpis['score_qualite_moyen']}%
- Tests distincts        : {kpis['nb_tests_distincts']}

RÉPARTITION CLINIQUE :
{repartition}

RÉPARTITION PAR SEXE :
{sexe}

TOP 5 SERVICES PAR VOLUME :
{top_services}

SAISONNALITÉ MENSUELLE :
{saisonnalite}

TRANCHES D'ÂGE :
{tranches}"""

    prompt = _charger_prompt("rapport_prompt.txt", contexte=contexte)
    
    print("   Génération du rapport...")
    rapport = _appel_llm(prompt, model=MODEL_DOC)

    contenu_final = f"""# Rapport Exécutif — Dashboard BI Laboratoire

> Généré automatiquement par le module LLM (qwen3:0.6B via Ollama) — 100% offline
> Données : agrégats et indicateurs uniquement (principe de minimisation RGPD)
> Date de génération : Juin 2026

{rapport}
"""
    _sauvegarder("rapport_pilotage.md", contenu_final)
    return rapport



# FONCTION 3 — Recherche guidée (qwen2.5-coder:1.5b)


def recherche_guidee(question: str) -> dict:
    """
    Transforme une question NL en requête SQL DuckDB via qwen2.5-coder:1.5b.
    Ce modèle est spécialisé en code et génère du SQL parfait.
    """
    schema = """Vue V_DASHBOARD — colonnes disponibles :
    id_patient (TEXT, pseudonymisé PAT_XXXXX), valeur (FLOAT), score_qualite (FLOAT),
    nom_test (TEXT), sexe (TEXT M/F/I), age (INT), service (TEXT),
    date_full (TEXT YYYY-MM-DD), annee (INT), mois (INT 1-12), nom_mois (TEXT),
    trimestre (INT 1-4), tranche_age (TEXT), categorie (TEXT),
    statut_clinique (TEXT), z_score (FLOAT), couverture_catalogue (TEXT)"""

    # Exemples few-shot pour guider le modèle SQL
    exemples_sql = """EXEMPLES DE REQUÊTES VALIDE DUCKDB :

Exemple 1 :
Question: "Volume par service en 2024"
SQL: SELECT service, COUNT(*) AS volume FROM V_DASHBOARD WHERE annee = 2024 GROUP BY service ORDER BY volume DESC

Exemple 2 :
Question: "Anomalies sévères de Glucose"
SQL: SELECT nom_test, valeur, statut_clinique, z_score FROM V_DASHBOARD WHERE nom_test = 'Glucose' AND statut_clinique LIKE 'Anomalie Severe%' ORDER BY ABS(z_score) DESC

Exemple 3 :
Question: "Activité par tranche d'âge en mars"
SQL: SELECT tranche_age, COUNT(DISTINCT id_patient) AS nb_patients, COUNT(*) AS nb_analyses FROM V_DASHBOARD WHERE nom_mois = 'Mars' GROUP BY tranche_age ORDER BY nb_patients DESC

Exemple 4 :
Question: "Top 10 tests par volume"
SQL: SELECT nom_test, COUNT(*) AS volume FROM V_DASHBOARD GROUP BY nom_test ORDER BY volume DESC LIMIT 10

RÈGLES STRICTES :
- Utilise UNIQUEMENT V_DASHBOARD
- Jamais de "..." ou "SELECT *" dans la requête finale
- Préfère COUNT(*), AVG(), SUM() pour les agrégats
- GROUP BY doit inclure TOUTES les colonnes non-agrégées du SELECT
- ORDER BY doit utiliser une colonne du SELECT ou un alias
- Pour les filtres texte, utilise = 'valeur' ou LIKE 'pattern%'
- N'utilise jamais "z_score != NULL" — utilise "z_score IS NOT NULL"
- La requête doit être exécutable sans modification"""

    prompt = f"""{schema}

{exemples_sql}

Question de l'utilisateur : "{question}"

Génère UNIQUEMENT un objet JSON valide avec cette structure exacte :
{{
  "interpretation": "ce que tu as compris de la question en 1 phrase",
  "requete_finale": "SELECT ... FROM V_DASHBOARD ... (requête complète et valide)"
}}

IMPORTANT : 
- La requête finale doit être 100% exécutable dans DuckDB
- Pas de points de suspension "..."
- Pas de syntaxe invalide
- Utilise les exemples ci-dessus comme modèle"""
    
    print("   Analyse de la question (modèle SQL)...")
    reponse_brute = _appel_llm(prompt, model=MODEL_SQL)

    # Parsing JSON
    try:
        reponse_propre = reponse_brute.strip()
        if reponse_propre.startswith("```"):
            reponse_propre = reponse_propre.split("```")[1]
            if reponse_propre.startswith("json"):
                reponse_propre = reponse_propre[4:]
        resultat = json.loads(reponse_propre)
    except json.JSONDecodeError:
        # Fallback avec requête par défaut sécurisée
        resultat = {
            "interpretation": "Parsing échoué — requête par défaut",
            "requete_finale": "SELECT nom_test, COUNT(*) AS volume FROM V_DASHBOARD GROUP BY nom_test ORDER BY volume DESC LIMIT 10",
            "reponse_brute_llm": reponse_brute,
        }

    # Exécution SQL
    try:
        conn = duckdb.connect(FICHIER_DB, read_only=True)
        df_result = conn.execute(resultat["requete_finale"]).df()
        conn.close()
        resultat["resultats"] = df_result.to_dict(orient="records")
        resultat["nb_resultats"] = len(df_result)
        print(f"   {len(df_result)} résultats trouvés")
    except Exception as e:
        resultat["erreur_sql"] = str(e)
        resultat["resultats"] = []
        print(f"  ❌ Erreur SQL : {e}")

    return resultat


def demo_recherche_guidee():
    """Démonstration de la recherche guidée avec 3 exemples."""
    questions = [
        "Quel est le volume d'analyses par service en 2024 ?",
        "Montre-moi les anomalies sévères de Glucose",
        "Quelle est l'activité par tranche d'âge au mois de mars ?",
    ]

    exemples = []
    for q in questions:
        print(f"\n  ❓ Question : « {q} »")
        res = recherche_guidee(q)
        print(f"  Interprétation : {res.get('interpretation', 'N/A')}")
        print(f"   SQL : {res.get('requete_finale', 'N/A')}")
        if res.get("resultats"):
            import pandas as pd
            print(f"  📊 Résultats ({res['nb_resultats']} lignes) :")
            print(pd.DataFrame(res["resultats"]).head(5).to_string(index=False))
        exemples.append({"question": q, "resultat": res})

    os.makedirs(OUTPUTS_DIR, exist_ok=True)
    chemin = os.path.join(OUTPUTS_DIR, "exemples_recherche.json")
    with open(chemin, "w", encoding="utf-8") as f:
        json.dump(exemples, f, indent=2, ensure_ascii=False)
    print(f"\n  → Sauvegardé : {chemin}")




def afficher_menu():
    print("\n" + "=" * 65)
    print("  ASSISTANT LLM  |  IA & BI Laboratoire  |  ENSAO MGSI")
    print("=" * 65)
    print("  Architecture : Prompts modulaires (prompts/*.txt)")
    print("  Modèles      : qwen3:0.6b (doc/rapport) + qwen2.5-coder:1.5b (SQL)")
    print("  Données      : Agrégats uniquement (minimisation RGPD)")
    print("  Mode         : 100% offline via Ollama")
    print("=" * 65)
    print("\n  [1]   Générer la documentation du catalogue")
    print("  [2]  📊  Générer le rapport exécutif")
    print("  [3]    Démonstration recherche guidée (3 exemples)")
    print("  [4]    TOUT GÉNÉRER (doc + rapport + recherche)")
    print("  [5]    Poser une question personnalisée")
    print("  [0]  ❌  Quitter")
    print("-" * 65)


def main():
    while True:
        afficher_menu()
        choix = input("  Votre choix : ").strip()

        if choix == "1":
            print("\n[1] GÉNÉRATION DE LA DOCUMENTATION DU CATALOGUE...")
            generer_documentation_catalogue()

        elif choix == "2":
            print("\n[2] GÉNÉRATION DU RAPPORT EXÉCUTIF...")
            generer_rapport_dashboard()

        elif choix == "3":
            print("\n[3] DÉMONSTRATION RECHERCHE GUIDÉE...")
            demo_recherche_guidee()

        elif choix == "4":
            print("\n[4] GÉNÉRATION COMPLÈTE...")
            generer_documentation_catalogue()
            generer_rapport_dashboard()
            demo_recherche_guidee()
            print("\n✅ Tous les livrables LLM ont été générés dans llm_outputs/")

        elif choix == "5":
            q = input("\n  Votre question : ").strip()
            if q:
                print(f"\n  Traitement de : « {q} »")
                res = recherche_guidee(q)
                print(f"  → SQL : {res.get('requete_finale', 'N/A')}")
                print(f"  → {res.get('nb_resultats', 0)} résultats")
                if res.get("resultats"):
                    import pandas as pd
                    print(pd.DataFrame(res["resultats"]).head(10).to_string(index=False))

        elif choix == "0":
            print("\n  Au revoir. Bonne soutenance ! 🎯")
            break
        else:
            print("\n  Choix invalide. Réessayez.")


if __name__ == "__main__":
    main()