import hashlib
import json
import os
from datetime import datetime

import pandas as pd
from rapidfuzz import fuzz, process


CATALOGUE_TESTS = [
    "Creatinine Jaffe Cinétique",
    "Potassium Sanguin",
    "Sodium Sanguin",
    "Protéines Totales",
    "Crp",
    "Calcium",
    "Chlore",
    "Urée Sanguin",
    "Glucose",
    "% Pnn",
    "Bilirubine Totale",
    "Asat",
    "Alat",
    "Ggt",
]

# Seuil de similarité pour la normalisation fuzzy (80% = bon compromis précision/rappel)
SEUIL_NORMALISATION = 80

# Chemin du fichier de mapping persistant (pseudonymisation RGPD)
MAPPING_FILE = "data/processed/patient_id_map.json"

# Chemin du fichier source par défaut
FICHIER_SOURCE = "data/raw/synthetic_bloodwork (1).csv"




def extract(filepath: str) -> pd.DataFrame:
    """
    Charge le fichier CSV source.
    Tente UTF-8 en premier, bascule sur latin-1 si nécessaire
    (encodage courant des exports de logiciels de laboratoire).
    """
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"[EXTRACT] Fichier introuvable : {filepath}")

    try:
        df = pd.read_csv(filepath, encoding="utf-8")
        print("[EXTRACT] Encodage UTF-8 détecté.")
    except UnicodeDecodeError:
        df = pd.read_csv(filepath, encoding="latin-1")
        print("[EXTRACT] Encodage latin-1 détecté (export labo habituel).")

    print(f"[EXTRACT] {len(df):,} lignes chargées depuis : {filepath}")
    return df





def _normaliser_libelle(nom: str) -> str:
    """
    Normalisation intelligente par similarité floue (RapidFuzz WRatio).

    Si le score de similarité >= SEUIL_NORMALISATION :
        -> retourne la forme canonique du catalogue officiel
    Sinon :
        -> retourne le libellé en Title Case (conservé tel quel)

    Exemples :
        "creatinine jaffe"  -> "Creatinine Jaffe Cinétique"   (score ~90)
        "glucose sang"      -> "Glucose"                       (score ~85)
        "hémogramme NFS"    -> "Hémogramme Nfs"               (hors catalogue)
    """
    if not isinstance(nom, str) or nom.strip() == "":
        return "Inconnu"

    match = process.extractOne(nom.strip(), CATALOGUE_TESTS, scorer=fuzz.WRatio)
    if match and match[1] >= SEUIL_NORMALISATION:
        return match[0]
    return nom.strip().title()


def _pseudonymiser(df: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    """
    Pseudonymisation RGPD déterministe et sans collision.

    Algorithme :
        1. Charger le mapping existant (continuité entre runs)
        2. Identifier les nouveaux patients non encore mappés
        3. Les trier par hash SHA-256 (ordre stable, indépendant du CSV)
        4. Leur attribuer les prochains numéros PAT_XXXXX disponibles
        5. Persister le mapping mis à jour sur disque
        6. Vérifier l'absence de collision (assertion)

    Propriétés garanties :
        - Déterministe  : même patient -> même PAT_XXXXX à chaque run
        - Sans collision : N patients originaux -> N PAT distincts
        - Stable        : indépendant de l'ordre des lignes du CSV
        - Confidentiel  : aucun identifiant réel ne sort du pipeline
        - Incrémental   : les PAT_XXXXX existants ne sont jamais modifiés
    """
    os.makedirs(os.path.dirname(MAPPING_FILE), exist_ok=True)

    patients_uniques = df["id_patient"].astype(str).unique().tolist()

    # Charger le mapping persisté (ou créer un dictionnaire vide)
    if os.path.exists(MAPPING_FILE):
        with open(MAPPING_FILE, "r", encoding="utf-8") as f:
            id_map = json.load(f)
    else:
        id_map = {}

    # Identifier les patients nouveaux (absents du mapping)
    nouveaux_ids = [p for p in patients_uniques if p not in id_map]

    if nouveaux_ids:
        # Numéro de départ = dernier PAT_XXXXX existant + 1
        max_num = (
            max(int(v.replace("PAT_", "")) for v in id_map.values())
            if id_map
            else 0
        )

        # Trier les nouveaux par hash SHA-256 pour la stabilité inter-runs
        nouveaux_tries = sorted(
            nouveaux_ids,
            key=lambda x: hashlib.sha256(x.encode("utf-8")).hexdigest(),
        )

        # Attribuer les PAT_XXXXX en séquence
        for i, pid in enumerate(nouveaux_tries):
            id_map[pid] = f"PAT_{max_num + i + 1:05d}"

    # Persister le mapping (format JSON indenté pour auditabilité RGPD)
    with open(MAPPING_FILE, "w", encoding="utf-8") as f:
        json.dump(id_map, f, indent=2, ensure_ascii=False)

    # Appliquer la pseudonymisation
    df["id_patient"] = df["id_patient"].astype(str).map(id_map)

    # Vérification anti-collision (assertion bloquante)
    nb_pat_apres = df["id_patient"].nunique()
    nb_pat_avant = len(patients_uniques)
    assert nb_pat_apres == nb_pat_avant, (
        f"[PSEUDONYMISATION] COLLISION DETECTEE : "
        f"{nb_pat_avant} patients originaux -> "
        f"{nb_pat_apres} PAT distincts. "
        f"Supprimez {MAPPING_FILE} et relancez."
    )

    return df, len(nouveaux_ids)


def transform(df: pd.DataFrame) -> tuple[pd.DataFrame, dict, list]:
    """
    Pipeline de transformation en 9 étapes avec traçabilité complète (data lineage).

    Retourne :
        df_clean  (pd.DataFrame) : données nettoyées et enrichies
        rapport   (dict)         : résumé des actions effectuées
        lineage   (list)         : journal détaillé étape par étape
    """
    ts = datetime.now().isoformat()
    rapport = {
        "timestamp": ts,
        "lignes_entree": len(df),
        "actions": {},
    }
    lineage = []

   
    mapping_colonnes = {
        "numorden": "id_patient",
        "sexo":     "sexe",
        "edad":     "age",
        "nombre":   "nom_test",
        "textores": "valeur",
        "nombre2":  "service",
        "Date":     "date_prelevement",
    }
    df = df.rename(columns=mapping_colonnes)
    lineage.append({
        "etape": "01_renommage_colonnes",
        "regle": "Mapping colonnes espagnol -> français métier",
        "lignes_entree": len(df),
        "lignes_sortie": len(df),
        "lignes_impactees": 0,
        "details": "Colonnes renommées : " + ", ".join(mapping_colonnes.values()),
        "timestamp": ts,
    })

   
    df["date_prelevement"] = pd.to_datetime(
        df["date_prelevement"], dayfirst=True, errors="coerce"
    )

    # Conserver la valeur originale avant conversion numérique
    df["valeur_originale"] = df["valeur"].astype(str)

    # Détecter les valeurs textuelles (non convertibles en float)
    masque_textuel = df["valeur"].apply(
        lambda x: (not pd.isna(x))
        and pd.isna(pd.to_numeric(x, errors="coerce"))
    )
    nb_textuels = int(masque_textuel.sum())

    df["valeur"] = pd.to_numeric(df["valeur"], errors="coerce")
    df["age"]    = pd.to_numeric(df["age"],    errors="coerce")

    rapport["actions"]["valeurs_textuelles_tracees"] = nb_textuels
    lineage.append({
        "etape": "02_conversion_types",
        "regle": "date_prelevement -> datetime (dayfirst=True), valeur -> float, age -> float",
        "lignes_entree": len(df),
        "lignes_sortie": len(df),
        "lignes_impactees": nb_textuels,
        "details": f"{nb_textuels} valeurs non numériques tracées dans valeur_originale",
        "timestamp": ts,
    })

    
    nb_age_manquant = int(df["age"].isna().sum())
    df["age"] = df.groupby("sexe")["age"].transform(
        lambda x: x.fillna(x.median())
    )
    # Si age encore NaN (groupe entier vide), imputer avec la médiane globale
    mediane_globale = df["age"].median()
    nb_age_restant = int(df["age"].isna().sum())
    if nb_age_restant > 0:
        df["age"] = df["age"].fillna(mediane_globale)

    rapport["actions"]["age_impute_par_mediane"] = nb_age_manquant
    lineage.append({
        "etape": "03_imputation_age",
        "regle": "Médiane de l'âge par groupe sexe (M/F/I) ; médiane globale en fallback",
        "lignes_entree": len(df),
        "lignes_sortie": len(df),
        "lignes_impactees": nb_age_manquant,
        "details": (
            f"{nb_age_manquant} âges imputés par médiane du groupe sexe. "
            f"Fallback médiane globale utilisé pour {nb_age_restant} cas résiduels."
        ),
        "timestamp": ts,
    })

   
    nb_avant = len(df)
    df = df.dropna(
        subset=["id_patient", "valeur", "nom_test", "date_prelevement"]
    ).copy()
    nb_suppr = nb_avant - len(df)

    rapport["actions"]["lignes_invalides_supprimees"] = nb_suppr
    lineage.append({
        "etape": "04_suppression_invalides",
        "regle": "Suppression si id_patient, valeur, nom_test ou date_prelevement est vide",
        "lignes_entree": nb_avant,
        "lignes_sortie": len(df),
        "lignes_impactees": nb_suppr,
        "details": f"{nb_suppr} lignes supprimées (champs critiques manquants)",
        "timestamp": ts,
    })

   
    # Score de qualité multi-dimensionnel (calculé APRÈS dropna)
    
    champs_qualite = ["sexe", "age", "valeur", "service", "date_prelevement"]
    completude = df[champs_qualite].notnull().sum(axis=1) / len(champs_qualite)

    # Pénalité de 0.2 si la date de prélèvement est dans le futur
    aujourd_hui   = pd.Timestamp.today().normalize()
    date_invalide = df["date_prelevement"].notna() & (
        df["date_prelevement"] > aujourd_hui
    )
    penalite_date  = date_invalide.astype(float) * 0.2
    nb_dates_futures = int(date_invalide.sum())

    df["score_qualite"] = (
        (completude - penalite_date).clip(0, 1) * 100
    ).round(1)

    score_moyen = round(df["score_qualite"].mean(), 1)
    rapport["actions"]["score_qualite_moyen"] = score_moyen
    rapport["actions"]["dates_futures_detectees"] = nb_dates_futures
    lineage.append({
        "etape": "05_score_qualite",
        "regle": (
            "Score = complétude sur 5 champs - pénalité 0.2 si date future. "
            "Calculé après suppression des lignes invalides."
        ),
        "lignes_entree": len(df),
        "lignes_sortie": len(df),
        "lignes_impactees": nb_dates_futures,
        "details": (
            f"Score moyen = {score_moyen}/100. "
            f"{nb_dates_futures} dates futures détectées et pénalisées."
        ),
        "timestamp": ts,
    })

   
    #  Déduplication par clé composite
   
    nb_avant = len(df)
    df = df.drop_duplicates(
        subset=["id_patient", "nom_test", "date_prelevement", "valeur"]
    ).copy()
    nb_doublons = nb_avant - len(df)

    rapport["actions"]["doublons_supprimes"] = nb_doublons
    lineage.append({
        "etape": "06_deduplication",
        "regle": "Clé composite : id_patient + nom_test + date_prelevement + valeur",
        "lignes_entree": nb_avant,
        "lignes_sortie": len(df),
        "lignes_impactees": nb_doublons,
        "details": f"{nb_doublons} doublons exacts supprimés",
        "timestamp": ts,
    })

    
    # ici on a Normalisation intelligente des libellés (RapidFuzz)
   
    print("[TRANSFORM] Normalisation des libellés (RapidFuzz) en cours...")
    
    noms_avant_normalises = df["nom_test"].str.strip().str.title()
    df["nom_test"] = df["nom_test"].apply(_normaliser_libelle)
    nb_modifies = int((noms_avant_normalises != df["nom_test"]).sum())

    rapport["actions"]["libelles_normalises"] = nb_modifies
    lineage.append({
        "etape": "07_normalisation_libelles",
        "regle": (
            f"RapidFuzz WRatio >= {SEUIL_NORMALISATION}% "
            "-> forme canonique du catalogue officiel ; sinon Title Case"
        ),
        "lignes_entree": len(df),
        "lignes_sortie": len(df),
        "lignes_impactees": nb_modifies,
        "details": (
            f"{nb_modifies} libellés normalisés vers les 14 tests du catalogue. "
            f"Seuil de similarité : {SEUIL_NORMALISATION}%."
        ),
        "timestamp": ts,
    })

    
    # Uniformisation des services
 
    df["service"] = (
        df["service"]
        .fillna("NON RENSEIGNE")
        .astype(str)
        .str.strip()
        .str.upper()
    )
    # Uniformiser les variantes avec accent qui peuvent venir du CSV
    df["service"] = df["service"].str.replace(
        "NON RENSEIGN\u00c9", "NON RENSEIGNE", regex=False
    )
    nb_non_rens = int((df["service"] == "NON RENSEIGNE").sum())

    rapport["actions"]["services_manquants"] = nb_non_rens
    lineage.append({
        "etape": "08_uniformisation_services",
        "regle": "Service vide -> 'NON RENSEIGNE' ; strip() + upper() sur tous",
        "lignes_entree": len(df),
        "lignes_sortie": len(df),
        "lignes_impactees": nb_non_rens,
        "details": f"{nb_non_rens} services vides remplacés par 'NON RENSEIGNE'",
        "timestamp": ts,
    })

   
    # c est la Pseudonymisation RGPD
    
    df, nb_nouveaux = _pseudonymiser(df)
    nb_patients = df["id_patient"].nunique()

    rapport["actions"]["patients_pseudonymises"] = nb_patients
    rapport["actions"]["nouveaux_patients_ce_run"] = nb_nouveaux
    lineage.append({
        "etape": "09_pseudonymisation_rgpd",
        "regle": (
            "Tri SHA-256 + séquence stable. "
            "Mapping persisté dans patient_id_map.json. "
            "Assertion anti-collision vérifiée."
        ),
        "lignes_entree": len(df),
        "lignes_sortie": len(df),
        "lignes_impactees": nb_patients,
        "details": (
            f"{nb_patients} patients pseudonymisés au total. "
            f"{nb_nouveaux} nouveaux patients ajoutés ce run. "
            f"Zéro collision vérifiée par assertion. "
            f"Mapping persisté dans {MAPPING_FILE}."
        ),
        "timestamp": ts,
    })

    rapport["lignes_sortie"] = len(df)
    return df, rapport, lineage

# chargement 

def load(df: pd.DataFrame, rapport: dict, lineage: list) -> str:
    """
    Sauvegarde trois artefacts :
        1. CSV nettoyé (UTF-8)                -> data/processed/resultats_nettoyes.csv
        2. Log JSON horodaté (rapport global) -> logs/etl_log_YYYYMMDD_HHMMSS.json
        3. Lineage JSON horodaté (9 étapes)   -> logs/lineage_YYYYMMDD_HHMMSS.json
    """
    os.makedirs("data/processed", exist_ok=True)
    os.makedirs("logs", exist_ok=True)

    # CSV nettoyé
    csv_path = "data/processed/resultats_nettoyes.csv"
    df.to_csv(csv_path, index=False, encoding="utf-8")

   
    horodatage = datetime.now().strftime("%Y%m%d_%H%M%S")


    log_path = f"logs/etl_log_{horodatage}.json"
    rapport["lineage"] = lineage
    with open(log_path, "w", encoding="utf-8") as f:
        json.dump(rapport, f, indent=2, ensure_ascii=False)

    
    lineage_path = f"logs/lineage_{horodatage}.json"
    with open(lineage_path, "w", encoding="utf-8") as f:
        json.dump(
            {"run_id": horodatage, "etapes": lineage},
            f,
            indent=2,
            ensure_ascii=False,
        )

    print(f"[LOAD] Données nettoyées  -> {csv_path}")
    print(f"[LOAD] Log de traçabilité -> {log_path}")
    print(f"[LOAD] Lineage détaillé   -> {lineage_path}  ({len(lineage)} étapes)")

    return csv_path



def run_pipeline(filepath: str = FICHIER_SOURCE):
    
    
    print("  PIPELINE ETL :")
    

    df_raw                      = extract(filepath)
    df_clean, rapport, lineage  = transform(df_raw)
    csv_path                    = load(df_clean, rapport, lineage)

    print()
    
    print("  RÉSUMÉ DU PIPELINE")
   
    print(f"  Lignes en entrée       : {rapport['lignes_entree']:>10,}")
    print(f"  Lignes en sortie       : {rapport['lignes_sortie']:>10,}")
    print(f"  Lignes supprimées      : {rapport['actions']['lignes_invalides_supprimees']:>10,}")
    print(f"  Doublons supprimés     : {rapport['actions']['doublons_supprimes']:>10,}")
    print(f"  Libellés normalisés    : {rapport['actions']['libelles_normalises']:>10,}")
    print(f"  Patients uniques       : {rapport['actions']['patients_pseudonymises']:>10,}")
    print(f"  Âges imputés           : {rapport['actions']['age_impute_par_mediane']:>10,}")
    print(f"  Valeurs textuelles     : {rapport['actions']['valeurs_textuelles_tracees']:>10,}")
    print(f"  Score qualité moyen    : {rapport['actions']['score_qualite_moyen']:>9.1f}%")
    print(f"  Étapes de lineage      : {len(lineage):>10}")
   
    print("  Pipeline terminé avec succès.")
   

    return df_clean, rapport


if __name__ == "__main__":
    run_pipeline()