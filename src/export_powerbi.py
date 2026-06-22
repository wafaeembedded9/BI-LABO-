import os
import duckdb

FICHIER_DB = "data/labo.duckdb"
OUTPUT_DIR = "data/powerbi_export"
os.makedirs(OUTPUT_DIR, exist_ok=True)

conn = duckdb.connect(FICHIER_DB)

# Export principal (494K lignes)
df = conn.execute("SELECT * FROM V_DASHBOARD").df()
df.to_csv(f"{OUTPUT_DIR}/v_dashboard.csv", index=False)
print(f"[OK] v_dashboard.csv | {len(df):,} lignes")

# Export qualité (1 ligne)
df_q = conn.execute("SELECT * FROM V_DATA_QUALITY").df()
df_q.to_csv(f"{OUTPUT_DIR}/v_data_quality.csv", index=False)
print(f"[OK] v_data_quality.csv | {len(df_q):,} ligne(s)")

# Export lineage (9 étapes)
df_l = conn.execute("SELECT * FROM V_LINEAGE").df()
df_l.to_csv(f"{OUTPUT_DIR}/v_lineage.csv", index=False)
print(f"[OK] v_lineage.csv | {len(df_l):,} ligne(s)")

conn.close()
print(f"\n[OK] Export termine dans {OUTPUT_DIR}/")
print("[OK] Importez v_dashboard.csv dans Power BI Desktop")