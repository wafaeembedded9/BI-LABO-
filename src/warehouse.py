import glob
import json
import os

import duckdb
import pandas as pd


FICHIER_CSV   = "data/processed/resultats_nettoyes.csv"
FICHIER_DB    = "data/labo.duckdb"

MOIS_FR = {
    1: "Janvier",   2: "Février",   3: "Mars",      4: "Avril",
    5: "Mai",       6: "Juin",      7: "Juillet",   8: "Août",
    9: "Septembre", 10: "Octobre",  11: "Novembre", 12: "Décembre",
}


def _mode_safe(serie: pd.Series):
    
    modes = serie.mode()
    return modes.iloc[0] if len(modes) > 0 else "Inconnu"

def build_warehouse(input_file: str = FICHIER_CSV):
    
    
    print("  WAREHOUSE :")
    

    # Vérification préalable du fichier source
    if not os.path.exists(input_file):
        raise FileNotFoundError(
            f"[WAREHOUSE] Fichier introuvable : {input_file}\n"
            "  -> Lancez d'abord etl.py pour générer les données nettoyées."
        )

  
    # Chargement du CSV nettoyé
  
    df = pd.read_csv(input_file, encoding="utf-8")
    df["date_prelevement"] = pd.to_datetime(
        df["date_prelevement"], errors="coerce"
    )
    df["valeur"] = pd.to_numeric(df["valeur"], errors="coerce")

    print(f"\n[WAREHOUSE] {len(df):,} lignes chargées depuis {input_file}")

    os.makedirs("data", exist_ok=True)
    conn = duckdb.connect(FICHIER_DB)

   
    dim_test = (
        df[["nom_test"]]
        .drop_duplicates()
        .reset_index(drop=True)
        .copy()
    )
    dim_test.insert(0, "id_test", range(1, len(dim_test) + 1))
    conn.execute("CREATE OR REPLACE TABLE DIM_TEST AS SELECT * FROM dim_test")
    print(f"[WAREHOUSE] DIM_TEST      : {len(dim_test):>5,} tests distincts")

   
    dim_service = (
        df[["service"]]
        .drop_duplicates()
        .reset_index(drop=True)
        .copy()
    )
    dim_service.insert(0, "id_service", range(1, len(dim_service) + 1))
    conn.execute(
        "CREATE OR REPLACE TABLE DIM_SERVICE AS SELECT * FROM dim_service"
    )
    print(f"[WAREHOUSE] DIM_SERVICE   : {len(dim_service):>5,} services")

    
    dates_series = (
        pd.Series(df["date_prelevement"].dropna().unique())
        .sort_values()
        .reset_index(drop=True)
    )
    dim_date = pd.DataFrame({
        "id_date":   range(1, len(dates_series) + 1),
        "date_full": dates_series.dt.strftime("%Y-%m-%d"),   # clé de jointure
        "annee":     dates_series.dt.year,
        "mois":      dates_series.dt.month,
        "nom_mois":  dates_series.dt.month.map(MOIS_FR),
        "trimestre": dates_series.dt.quarter,
        "semaine":   dates_series.dt.isocalendar().week.astype(int),
        "jour":      dates_series.dt.day,
    })
    conn.execute("CREATE OR REPLACE TABLE DIM_DATE AS SELECT * FROM dim_date")
    print(f"[WAREHOUSE] DIM_DATE      : {len(dim_date):>5,} dates")

  
    nb_patients_csv = df["id_patient"].nunique()
    dim_patient = (
        df[["id_patient", "sexe", "age"]]
        .groupby("id_patient", as_index=False)
        .agg(
            sexe=("sexe", _mode_safe),
            age=("age",  "median"),
        )
    )
    dim_patient["age"] = (
        dim_patient["age"].round(0).astype(pd.Int64Dtype())
    )
    nb_conflits = int(df.groupby("id_patient")["sexe"].nunique().gt(1).sum())
    conn.execute(
        "CREATE OR REPLACE TABLE DIM_PATIENT AS SELECT * FROM dim_patient"
    )
    print(
        f"[WAREHOUSE] DIM_PATIENT   : {len(dim_patient):>5,} patients "
        f"({nb_conflits} incohérences démographiques résolues)"
    )

   
    df["date_only"] = df["date_prelevement"].dt.strftime("%Y-%m-%d")

    fact = (
        df
        .merge(dim_test,    on="nom_test",                         how="left")
        .merge(dim_service, on="service",                          how="left")
        .merge(dim_date,    left_on="date_only", right_on="date_full", how="left")
    )

    cols_fact = ["id_patient", "id_test", "id_service", "id_date", "valeur"]
    if "score_qualite" in fact.columns:
        cols_fact.append("score_qualite")

    fact_table = fact[cols_fact].copy()

    
    nb_avant_dropna = len(fact_table)
    fact_table = fact_table.dropna(
        subset=["id_patient", "id_test", "id_service", "id_date"]
    )
    nb_orphelins = nb_avant_dropna - len(fact_table)
    if nb_orphelins > 0:
        print(
            f"[WAREHOUSE] Attention : {nb_orphelins:,} faits orphelins supprimés "
            "(clé de dimension manquante)"
        )

   
    if len(fact_table) == 0:
        raise RuntimeError(
            "[WAREHOUSE] ERREUR CRITIQUE : FACT_LABO est vide après les jointures.\n"
            "  -> Vérifiez les types de date_full dans DIM_DATE et date_only dans df.\n"
            "  -> Relancez etl.py puis warehouse.py dans l'ordre."
        )

    
    couverture = round(len(fact_table) / len(df) * 100, 1)
    if couverture < 95.0:
        print(
            f"[WAREHOUSE] Attention : couverture faible ({couverture}%) — "
            f"{len(df) - len(fact_table):,} lignes perdues aux jointures."
        )

    conn.execute(
        "CREATE OR REPLACE TABLE FACT_LABO AS SELECT * FROM fact_table"
    )
    print(
        f"[WAREHOUSE] FACT_LABO     : {len(fact_table):>7,} faits  "
        f"(couverture {couverture}%)"
    )

    
    conn.execute("""
        CREATE OR REPLACE VIEW V_DASHBOARD_BASE AS
        SELECT
            f.id_patient,
            f.valeur,
            f.score_qualite,
            t.nom_test,
            s.service,
            d.date_full,
            d.annee,
            d.mois,
            d.nom_mois,
            d.trimestre,
            d.semaine,
            p.sexe,
            p.age,
            CASE
                WHEN p.age < 18  THEN 'Enfant (< 18)'
                WHEN p.age < 40  THEN 'Adulte (18-39)'
                WHEN p.age < 60  THEN 'Adulte (40-59)'
                WHEN p.age < 75  THEN 'Senior (60-74)'
                ELSE                  'Grand senior (75+)'
            END AS tranche_age
        FROM FACT_LABO   f
        JOIN DIM_TEST    t ON f.id_test    = t.id_test
        JOIN DIM_SERVICE s ON f.id_service = s.id_service
        JOIN DIM_DATE    d ON f.id_date    = d.id_date
        JOIN DIM_PATIENT p ON f.id_patient = p.id_patient
    """)
    print("[WAREHOUSE] V_DASHBOARD_BASE : vue de base créée")

   
    conn.execute("""
        CREATE OR REPLACE VIEW V_DATA_QUALITY AS
        SELECT
            ROUND(AVG(score_qualite),  2)  AS score_moyen,
            ROUND(MIN(score_qualite),  2)  AS score_min,
            ROUND(MAX(score_qualite),  2)  AS score_max,
            COUNT(*)                       AS total_faits,
            ROUND(COUNT(valeur)       * 100.0 / COUNT(*), 1) AS pct_valeur_renseignee,
            ROUND(COUNT(score_qualite)* 100.0 / COUNT(*), 1) AS pct_score_renseigne,
            COUNT(*) FILTER (WHERE score_qualite = 100)               AS nb_score_parfait,
            COUNT(*) FILTER (WHERE score_qualite >= 80
                               AND score_qualite < 100)               AS nb_score_bon,
            COUNT(*) FILTER (WHERE score_qualite < 80)                AS nb_score_faible,
            ROUND(COUNT(*) FILTER (WHERE score_qualite = 100)
                  * 100.0 / COUNT(*), 1)                              AS pct_parfait,
            ROUND(COUNT(*) FILTER (WHERE score_qualite >= 80
                                    AND score_qualite < 100)
                  * 100.0 / COUNT(*), 1)                              AS pct_bon,
            ROUND(COUNT(*) FILTER (WHERE score_qualite < 80)
                  * 100.0 / COUNT(*), 1)                              AS pct_faible
        FROM FACT_LABO
    """)
    print("[WAREHOUSE] V_DATA_QUALITY   : vue qualité créée")

   
    # ETL_LINEAGE + V_LINEAGE  (traçabilité des transformations ETL)
   
    lineage_files = sorted(glob.glob("logs/lineage_*.json"))
    if lineage_files:
        dernier_fichier = lineage_files[-1]
        with open(dernier_fichier, encoding="utf-8") as lf:
            lineage_data = json.load(lf)
        df_lineage = pd.DataFrame(lineage_data["etapes"])
        df_lineage["run_id"] = lineage_data["run_id"]
        conn.execute(
            "CREATE OR REPLACE TABLE ETL_LINEAGE AS SELECT * FROM df_lineage"
        )
        conn.execute("""
            CREATE OR REPLACE VIEW V_LINEAGE AS
            SELECT
                run_id, etape, regle,
                lignes_entree, lignes_sortie, lignes_impactees,
                details, timestamp
            FROM ETL_LINEAGE
            ORDER BY etape ASC
        """)
        print(
            f"[WAREHOUSE] ETL_LINEAGE      : "
            f"{len(df_lineage)} étapes de lineage chargées depuis {dernier_fichier}"
        )
    else:
        print(
            "[WAREHOUSE] ETL_LINEAGE      : "
            "aucun fichier de lineage trouvé (normal au premier run)"
        )

    
    # Indicateurs de pilotage (affichés dans le terminal)
    
    print()
   
    print("  INDICATEURS DE PILOTAGE")
  

    print("\n  Top 5 analyses par volume :")
    print(conn.execute("""
        SELECT
            nom_test,
            COUNT(*)                  AS volume,
            ROUND(AVG(valeur), 2)     AS moyenne,
            ROUND(STDDEV(valeur), 2)  AS ecart_type        FROM V_DASHBOARD_BASE
        GROUP BY nom_test
        ORDER BY volume DESC
        LIMIT 5
    """).df().to_string(index=False))

    print("\n  Répartition par sexe :")
    print(conn.execute("""
        SELECT
            sexe,
            COUNT(DISTINCT id_patient) AS nb_patients,
            COUNT(*)                   AS nb_analyses
        FROM V_DASHBOARD_BASE
        GROUP BY sexe
        ORDER BY nb_patients DESC
    """).df().to_string(index=False))

    print("\n  Score qualité global :")
    print(conn.execute("""
        SELECT
            ROUND(AVG(score_qualite), 2) AS score_moyen,
            ROUND(MIN(score_qualite), 2) AS score_min,
            ROUND(MAX(score_qualite), 2) AS score_max
        FROM FACT_LABO
    """).df().to_string(index=False))

    conn.close()

    print()
    print(f"  Entrepôt prêt -> {FICHIER_DB}")
    
  
   
if __name__ == "__main__":
    build_warehouse()