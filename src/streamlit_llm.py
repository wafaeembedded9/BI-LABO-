"""
streamlit_llm.py — Interface web pour le module LLM Laboratoire
PFA MGSI — ENSAO

Lancement : streamlit run src/streamlit_llm.py
"""

import os
import sys

import duckdb
import pandas as pd
import streamlit as st

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from llm_labo import (
    generer_documentation_catalogue,
    generer_rapport_dashboard,
    recherche_guidee,
    demo_recherche_guidee,
    FICHIER_DB,
    OUTPUTS_DIR,
)

# ==============================================================
# CONFIGURATION DE LA PAGE
# ==============================================================
st.set_page_config(
    page_title="LABO-BI — Assistant LLM",
    page_icon=":bar_chart:",
    layout="wide",
)

# ==============================================================
# STYLE — sobre, coherent avec le theme Power BI (bleu/blanc)
# ==============================================================
st.markdown("""
<style>
    .main-header {
        font-size: 1.8rem;
        font-weight: 600;
        color: #1A73E8;
        margin-bottom: 0.2rem;
    }
    .sub-header {
        font-size: 0.95rem;
        color: #64748B;
        margin-bottom: 1.5rem;
    }
    .kpi-box {
        background-color: #F8FAFC;
        border: 1px solid #E2E8F0;
        border-radius: 6px;
        padding: 1rem;
        text-align: center;
    }
    .kpi-value {
        font-size: 1.6rem;
        font-weight: 600;
        color: #1E293B;
    }
    .kpi-label {
        font-size: 0.8rem;
        color: #64748B;
    }
    .stButton>button {
        background-color: #1A73E8;
        color: white;
        border-radius: 5px;
    }
</style>
""", unsafe_allow_html=True)

# ==============================================================
# BARRE LATERALE — navigation
# ==============================================================
st.sidebar.markdown("### LABO-BI")
st.sidebar.caption("Assistant LLM — gestion des donnees de laboratoire")

page = st.sidebar.radio(
    "Navigation",
    ["Accueil", "Recherche guidee", "Documentation catalogue", "Rapport executif", "Diagnostics"],
)

st.sidebar.markdown("---")
st.sidebar.caption(
    "Architecture :\n"
    "- qwen3:0.6b -> documentation et rapports\n"
    "- qwen2.5-coder:1.5b -> generation SQL\n"
    "- 100% local via Ollama\n"
    "- Aucune donnee patient transmise au modele"
)

# ==============================================================
# UTILITAIRES
# ==============================================================

@st.cache_data
def charger_kpis():
    """Charge les indicateurs globaux depuis la vue V_DASHBOARD."""
    conn = duckdb.connect(FICHIER_DB, read_only=True)
    kpis = conn.execute("""
        SELECT
            COUNT(DISTINCT id_patient) AS nb_patients,
            COUNT(*) AS nb_analyses,
            ROUND(AVG(score_qualite), 1) AS score_qualite,
            COUNT(DISTINCT nom_test) AS nb_tests
        FROM V_DASHBOARD
    """).df().iloc[0]
    conn.close()
    return kpis


def afficher_kpis():
    kpis = charger_kpis()
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(f'<div class="kpi-box"><div class="kpi-value">{kpis["nb_patients"]:,}</div>'
                    f'<div class="kpi-label">Patients uniques</div></div>', unsafe_allow_html=True)
    with col2:
        st.markdown(f'<div class="kpi-box"><div class="kpi-value">{kpis["nb_analyses"]:,}</div>'
                    f'<div class="kpi-label">Analyses totales</div></div>', unsafe_allow_html=True)
    with col3:
        st.markdown(f'<div class="kpi-box"><div class="kpi-value">{kpis["score_qualite"]}%</div>'
                    f'<div class="kpi-label">Score qualite</div></div>', unsafe_allow_html=True)
    with col4:
        st.markdown(f'<div class="kpi-box"><div class="kpi-value">{kpis["nb_tests"]}</div>'
                    f'<div class="kpi-label">Tests distincts</div></div>', unsafe_allow_html=True)


# ==============================================================
# PAGE — ACCUEIL
# ==============================================================
if page == "Accueil":
    st.markdown('<div class="main-header">Assistant LLM — Laboratoire</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Module d\'assistance pour la documentation, le reporting '
                'et la recherche en langage naturel, connecte a l\'entrepot DuckDB du projet.</div>',
                unsafe_allow_html=True)

    afficher_kpis()
    st.markdown("---")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("""
        **Contexte du module**

        Ce projet combine un pipeline BI classique (ETL, entrepot DuckDB, dashboards Power BI)
        et un module d'assistance LLM qui repond a trois besoins du cahier des charges :

        1. Aide a la documentation du catalogue de tests (regroupement et clarification des libelles)
        2. Generation automatique d'un rapport de pilotage a partir des indicateurs du dashboard
        3. Recherche guidee : transformer une question en francais en requete SQL sur l'entrepot

        Le module fonctionne entierement en local via Ollama, avec deux modeles legers
        choisis pour des raisons pratiques (capacite materielle limitee) et de confidentialite
        (aucune donnee, meme agregee, ne quitte la machine).
        """)

    with col2:
        st.markdown("**Livrables du module LLM**")
        livrables = [
            ("Documentation catalogue", "catalogue_documentation.md"),
            ("Rapport executif", "rapport_pilotage.md"),
            ("Exemples recherche", "exemples_recherche.json"),
        ]
        for nom, fichier in livrables:
            chemin = f"{OUTPUTS_DIR}/{fichier}"
            statut = "✅ Genere" if os.path.exists(chemin) else "❌ Non genere"
            st.write(f"- {nom} : {statut}")

    st.markdown("---")
    st.caption("PFA — Management et Gouvernance des Systemes d'Information — ENSAO")


# ==============================================================
# PAGE — RECHERCHE GUIDEE
# ==============================================================
elif page == "Recherche guidee":
    st.markdown('<div class="main-header">Recherche guidee</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Question en langage naturel -> requete SQL generee '
                'et executee sur V_DASHBOARD.</div>', unsafe_allow_html=True)

    exemples = [
        "Quel est le volume d'analyses par service en 2024 ?",
        "Montre-moi les anomalies severes de Glucose",
        "Quelle est l'activite par tranche d'age au mois de mars ?",
        "Top 10 tests par volume",
    ]

    col1, col2 = st.columns([3, 1])

    with col2:
        st.caption("Exemples")
        for ex in exemples:
            if st.button(ex, key=f"ex_{ex[:15]}"):
                st.session_state["question"] = ex
                st.rerun()

    with col1:
        question = st.text_area(
            "Question :",
            value=st.session_state.get("question", ""),
            placeholder="Ex : volume d'analyses par service en 2024",
            height=80,
        )
        lancer = st.button("Executer")

        if lancer and question.strip():
            with st.spinner("Generation et execution de la requete..."):
                try:
                    resultat = recherche_guidee(question.strip())

                    st.write("**Interpretation :**", resultat.get("interpretation", "N/A"))
                    st.code(resultat.get("requete_finale", "N/A"), language="sql")

                    if resultat.get("resultats"):
                        df_result = pd.DataFrame(resultat["resultats"])
                        st.write(f"**Resultats** ({resultat.get('nb_resultats', 0)} lignes)")
                        st.dataframe(df_result, width='stretch')

                        csv = df_result.to_csv(index=False).encode('utf-8')
                        st.download_button(
                            "Telecharger CSV",
                            csv,
                            f"resultat_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.csv",
                            "text/csv"
                        )
                    else:
                        st.warning("Aucun resultat retourne.")

                    if "erreur_sql" in resultat:
                        st.error(f"Erreur SQL detectee : {resultat['erreur_sql']}")
                        st.info(
                            "Le modele leger a genere une requete invalide. "
                            "Le systeme a automatiquement bascule sur une requete de secours "
                            "(comportement attendu, mecanisme de robustesse du pipeline)."
                        )
                except Exception as e:
                    st.error(f"Erreur lors du traitement : {e}")

    st.markdown("---")
    st.caption(
        "Note : seules des requetes d'agregation sont autorisees. Les identifiants patients "
        "affiches (PAT_XXXXX) sont des pseudonymes issus du pipeline de pseudonymisation SHA-256."
    )


# ==============================================================
# PAGE — DOCUMENTATION CATALOGUE
# ==============================================================
elif page == "Documentation catalogue":
    st.markdown('<div class="main-header">Documentation du catalogue</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Generee a partir des agregats CATALOGUE_TESTS et '
                'SEUILS_STATISTIQUES.</div>', unsafe_allow_html=True)

    chemin_doc = f"{OUTPUTS_DIR}/catalogue_documentation.md"

    col1, col2 = st.columns([1, 3])

    with col1:
        if st.button("Regenerer la documentation"):
            with st.spinner("Generation en cours..."):
                try:
                    generer_documentation_catalogue()
                    st.success("Documentation regeneree.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Erreur : {e}")

        if os.path.exists(chemin_doc):
            with open(chemin_doc, "r", encoding="utf-8") as f:
                contenu = f.read()
            st.download_button("Telecharger (.md)", contenu, "catalogue_documentation.md")

    with col2:
        if os.path.exists(chemin_doc):
            with open(chemin_doc, "r", encoding="utf-8") as f:
                st.markdown(f.read())
        else:
            st.info("Aucune documentation generee pour le moment. Cliquez sur le bouton a gauche.")


# ==============================================================
# PAGE — RAPPORT EXECUTIF
# ==============================================================
elif page == "Rapport executif":
    st.markdown('<div class="main-header">Rapport executif</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Resume automatique des indicateurs du dashboard.</div>',
                unsafe_allow_html=True)

    chemin_rapport = f"{OUTPUTS_DIR}/rapport_pilotage.md"

    col1, col2 = st.columns([1, 3])

    with col1:
        if st.button("Regenerer le rapport"):
            with st.spinner("Generation en cours..."):
                try:
                    generer_rapport_dashboard()
                    st.success("Rapport regenere.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Erreur : {e}")

        if os.path.exists(chemin_rapport):
            with open(chemin_rapport, "r", encoding="utf-8") as f:
                contenu = f.read()
            st.download_button("Telecharger (.md)", contenu, "rapport_pilotage.md")

    with col2:
        if os.path.exists(chemin_rapport):
            with open(chemin_rapport, "r", encoding="utf-8") as f:
                st.markdown(f.read())
        else:
            st.info("Aucun rapport genere pour le moment. Cliquez sur le bouton a gauche.")


# ==============================================================
# PAGE — DIAGNOSTICS
# ==============================================================
elif page == "Diagnostics":
    st.markdown('<div class="main-header">Diagnostics</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Etat de la base de donnees et des fichiers generes.</div>',
                unsafe_allow_html=True)

    col1, col2 = st.columns(2)

    with col1:
        st.write("**Base de donnees**")
        if os.path.exists(FICHIER_DB):
            st.success(f"{FICHIER_DB} trouve")
            conn = duckdb.connect(FICHIER_DB, read_only=True)
            nb_lignes = conn.execute("SELECT COUNT(*) FROM V_DASHBOARD").fetchone()[0]
            conn.close()
            st.write(f"Lignes dans V_DASHBOARD : {nb_lignes:,}")
        else:
            st.error(f"{FICHIER_DB} introuvable — lancer warehouse.py et catalogue.py au prealable.")

    with col2:
        st.write("**Fichiers generes par le module LLM**")
        for f in ["catalogue_documentation.md", "rapport_pilotage.md", "exemples_recherche.json"]:
            chemin = f"{OUTPUTS_DIR}/{f}"
            statut = "present" if os.path.exists(chemin) else "absent"
            st.write(f"- {f} : {statut}")

    st.markdown("---")
    st.write("**Generation complete**")
    if st.button("TOUT GENERER (doc + rapport + exemples)", type="primary"):
        progress = st.progress(0)

        with st.spinner("1/3 — Documentation du catalogue..."):
            try:
                generer_documentation_catalogue()
                progress.progress(33)
            except Exception as e:
                st.error(f"Erreur documentation : {e}")

        with st.spinner("2/3 — Rapport executif..."):
            try:
                generer_rapport_dashboard()
                progress.progress(66)
            except Exception as e:
                st.error(f"Erreur rapport : {e}")

        with st.spinner("3/3 — Exemples de recherche guidee..."):
            try:
                demo_recherche_guidee()
                progress.progress(100)
            except Exception as e:
                st.error(f"Erreur recherche : {e}")

        st.success("Tous les livrables LLM ont ete generes !")
        st.balloons()