import os

import duckdb
import pandas as pd



CATALOGUE_TESTS = {
    "Creatinine Jaffe Cinétique": {"categorie": "Biochimie",    "unite": "u.a."},
    "Potassium Sanguin":          {"categorie": "Ionométrie",   "unite": "u.a."},
    "Sodium Sanguin":             {"categorie": "Ionométrie",   "unite": "u.a."},
    "Protéines Totales":          {"categorie": "Biochimie",    "unite": "u.a."},
    "Crp":                        {"categorie": "Inflammation", "unite": "u.a."},
    "Calcium":                    {"categorie": "Biochimie",    "unite": "u.a."},
    "Chlore":                     {"categorie": "Ionométrie",   "unite": "u.a."},
    "Urée Sanguin":               {"categorie": "Biochimie",    "unite": "u.a."},
    "Glucose":                    {"categorie": "Biochimie",    "unite": "u.a."},
    "% Pnn":                      {"categorie": "Hématologie",  "unite": "u.a."},
    "Bilirubine Totale":          {"categorie": "Hépatologie",  "unite": "u.a."},
    "Asat":                       {"categorie": "Hépatologie",  "unite": "u.a."},
    "Alat":                       {"categorie": "Hépatologie",  "unite": "u.a."},
    "Ggt":                        {"categorie": "Hépatologie",  "unite": "u.a."},
}

FICHIER_DB = "data/labo.duckdb"

def run_catalogue():
   
    print("  DATA CATALOGUE  |  IA & BI Laboratoire  |  ENSAO MGSI")
   

    
    if not os.path.exists(FICHIER_DB):
        print(
            "[CATALOGUE] ERREUR : labo.duckdb introuvable.\n"
            "  -> Lancez d'abord warehouse.py."
        )
        return

    conn = duckdb.connect(FICHIER_DB)

    
    tables = conn.execute(
        "SELECT table_name FROM information_schema.tables "
        "WHERE table_schema = 'main'"
    ).df()["table_name"].tolist()

    if "FACT_LABO" not in tables:
        print(
            "[CATALOGUE] ERREUR : FACT_LABO introuvable.\n"
            "  -> Lancez d'abord warehouse.py."
        )
        conn.close()
        return

    
    vues = conn.execute(
        "SELECT table_name FROM information_schema.views "
        "WHERE table_schema = 'main'"
    ).df()["table_name"].tolist()

    if "V_DASHBOARD_BASE" not in vues:
        print(
            "[CATALOGUE] Attention : V_DASHBOARD_BASE absente.\n"
            "  -> Utilisez la version corrigée de warehouse.py."
        )

   
    df_cat = pd.DataFrame([
        {"nom_test": nom, **props}
        for nom, props in CATALOGUE_TESTS.items()
    ])
    conn.execute(
        "CREATE OR REPLACE TABLE CATALOGUE_TESTS AS SELECT * FROM df_cat"
    )
    print(f"\n[OK] CATALOGUE_TESTS      : {len(df_cat)} tests enregistrés")

    
    conn.execute("""
        CREATE OR REPLACE TABLE SEUILS_STATISTIQUES AS
        SELECT
            t.nom_test,
            ROUND(QUANTILE_CONT(f.valeur, 0.05), 4) AS p5,
            ROUND(QUANTILE_CONT(f.valeur, 0.10), 4) AS p10,
            ROUND(QUANTILE_CONT(f.valeur, 0.25), 4) AS q1,
            ROUND(QUANTILE_CONT(f.valeur, 0.50), 4) AS mediane,
            ROUND(QUANTILE_CONT(f.valeur, 0.75), 4) AS q3,
            ROUND(QUANTILE_CONT(f.valeur, 0.90), 4) AS p90,
            ROUND(QUANTILE_CONT(f.valeur, 0.95), 4) AS p95,
            ROUND(AVG(f.valeur), 4)                 AS moyenne,
            ROUND(STDDEV(f.valeur), 4)              AS ecart_type,
            COUNT(*)                                AS nb_mesures
        FROM FACT_LABO f
        JOIN DIM_TEST  t ON f.id_test = t.id_test
        GROUP BY t.nom_test
    """)
    print("[OK] SEUILS_STATISTIQUES  : P5/P10/Q1/Médiane/Q3/P90/P95 calculés")

  
    
    conn.execute("""
        CREATE OR REPLACE VIEW V_DASHBOARD AS
        SELECT
            f.id_patient,
            f.valeur,
            f.score_qualite,
            t.nom_test,
            p.sexe,
            p.age,
            s.service,
            d.date_full,
            d.annee,
            d.mois,
            d.nom_mois,
            d.trimestre,
            d.semaine,

            CASE
                WHEN p.age < 18  THEN 'Enfant (< 18)'
                WHEN p.age < 40  THEN 'Adulte (18-39)'
                WHEN p.age < 60  THEN 'Adulte (40-59)'
                WHEN p.age < 75  THEN 'Senior (60-74)'
                ELSE                  'Grand senior (75+)'
            END AS tranche_age,

            COALESCE(c.categorie, 'Autres analyses') AS categorie,
            COALESCE(c.unite,     'u.a.')            AS unite,

            ss.p5       AS seuil_anomalie_bas,
            ss.p10      AS seuil_limite_bas,
            ss.p90      AS seuil_limite_haut,
            ss.p95      AS seuil_anomalie_haut,
            ss.mediane  AS mediane_test,
            ss.moyenne  AS moyenne_test,
            ss.ecart_type,

            CASE
                WHEN ss.p5 IS NULL       THEN 'Non classe'
                WHEN f.valeur < ss.p5    THEN 'Anomalie Severe (Bas)'
                WHEN f.valeur < ss.p10   THEN 'Limite Basse'
                WHEN f.valeur > ss.p95   THEN 'Anomalie Severe (Haut)'
                WHEN f.valeur > ss.p90   THEN 'Limite Haute'
                ELSE                          'Normal'
            END AS statut_clinique,

            CASE
                WHEN c.nom_test IS NOT NULL THEN 'Dans catalogue'
                ELSE                             'Hors catalogue'
            END AS couverture_catalogue,

            CASE
                WHEN ss.ecart_type > 0
                    THEN ROUND((f.valeur - ss.moyenne) / ss.ecart_type, 2)
                ELSE 0
            END AS z_score

        FROM FACT_LABO                f
        JOIN DIM_TEST                 t  ON f.id_test    = t.id_test
        JOIN DIM_PATIENT              p  ON f.id_patient = p.id_patient
        JOIN DIM_SERVICE              s  ON f.id_service = s.id_service
        JOIN DIM_DATE                 d  ON f.id_date    = d.id_date
        LEFT JOIN CATALOGUE_TESTS     c  ON t.nom_test   = c.nom_test
        LEFT JOIN SEUILS_STATISTIQUES ss ON t.nom_test   = ss.nom_test
    """)
    print("[OK] V_DASHBOARD          : vue analytique enrichie créée")
    print("     -> Statut clinique : 4 niveaux (Normal / Limite / Anomalie Severe)")
    print("     -> Z-score inclus pour analyse avancée")
    print("     -> Power BI : connectez-vous a V_DASHBOARD dans data/labo.duckdb")

   
    print()
    print("-" * 60)
    print("  RAPPORTS DE PILOTAGE")
    print("-" * 60)

    # Rapport 1 — Répartition clinique globale
    print("\n  [1] Répartition clinique globale (tous tests) :")
    print(conn.execute("""
        SELECT
            statut_clinique,
            COUNT(*)                                             AS nb_cas,
            ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 1)  AS pct
        FROM V_DASHBOARD
        GROUP BY statut_clinique
        ORDER BY
            CASE statut_clinique
                WHEN 'Normal'               THEN 1
                WHEN 'Limite Basse'         THEN 2
                WHEN 'Limite Haute'         THEN 3
                WHEN 'Anomalie Severe (Bas)'  THEN 4
                WHEN 'Anomalie Severe (Haut)' THEN 5
                ELSE 6
            END
    """).df().to_string(index=False))

    # Rapport 2 — Répartition sur les 14 tests du catalogue
    print("\n  [2] Répartition sur les 14 tests catalogués uniquement :")
    print(conn.execute("""
        SELECT
            statut_clinique,
            COUNT(*)                                             AS nb_cas,
            ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 1)  AS pct
        FROM V_DASHBOARD
        WHERE couverture_catalogue = 'Dans catalogue'
        GROUP BY statut_clinique
        ORDER BY
            CASE statut_clinique
                WHEN 'Normal'               THEN 1
                WHEN 'Limite Basse'         THEN 2
                WHEN 'Limite Haute'         THEN 3
                WHEN 'Anomalie Severe (Bas)'  THEN 4
                WHEN 'Anomalie Severe (Haut)' THEN 5
                ELSE 6
            END
    """).df().to_string(index=False))

    
    print("\n  [3] Anomalies sévères par catégorie médicale :")
    print(conn.execute("""
        SELECT
            categorie,
            COUNT(*) FILTER (WHERE statut_clinique LIKE 'Anomalie Severe%') AS anomalies_severes,            COUNT(*) FILTER (WHERE statut_clinique LIKE 'Limite%')           AS limites,
            COUNT(*) FILTER (WHERE statut_clinique = 'Normal')               AS normal,
            ROUND(
                COUNT(*) FILTER (WHERE statut_clinique LIKE 'Anomalie Severe%')
                * 100.0 / COUNT(*), 1
            ) AS taux_anomalie_pct
        FROM V_DASHBOARD
        WHERE couverture_catalogue = 'Dans catalogue'
        GROUP BY categorie
        ORDER BY taux_anomalie_pct DESC
    """).df().to_string(index=False))

    # Rapport 4 — Seuils statistiques des 14 tests
    print("\n  [4] Seuils statistiques des 14 tests catalogués :")
    print(conn.execute("""
        SELECT
            ss.nom_test,
            c.categorie,
            ss.p5        AS p5_anomalie_bas,
            ss.p10       AS p10_limite_bas,
            ss.mediane,
            ss.p90       AS p90_limite_haut,
            ss.p95       AS p95_anomalie_haut,
            ss.nb_mesures
        FROM SEUILS_STATISTIQUES ss
        JOIN CATALOGUE_TESTS     c ON ss.nom_test = c.nom_test
        ORDER BY c.categorie, ss.nom_test
    """).df().to_string(index=False))

    # Rapport 5 — Couverture du catalogue
    print("\n  [5] Couverture du catalogue :")
    print(conn.execute("""
        SELECT
            couverture_catalogue,
            COUNT(*)                                             AS nb_cas,
            ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 1)  AS pct
        FROM V_DASHBOARD
        GROUP BY couverture_catalogue
        ORDER BY nb_cas DESC
    """).df().to_string(index=False))

    
    print("\n  [6] Top 10 valeurs extrêmes (anomalies sévères, par |z-score|) :")
    print(conn.execute("""
        SELECT
            id_patient,
            nom_test,
            ROUND(valeur, 2)   AS valeur,
            ROUND(z_score, 2)  AS z_score,
            statut_clinique,
            date_full
        FROM V_DASHBOARD
        WHERE statut_clinique LIKE 'Anomalie Severe%'
        ORDER BY ABS(z_score) DESC
        LIMIT 10
    """).df().to_string(index=False))

    conn.close()

    print()
    print("  Catalogue termine. V_DASHBOARD ready pour Power BI.")
    


if __name__ == "__main__":
    run_catalogue()