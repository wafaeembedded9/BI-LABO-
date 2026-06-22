# Documentation du Catalogue des Tests — Laboratoire BI

> Générée automatiquement par le module LLM (qwen3:0.6B via Ollama) — 100% offline
> Données : agrégats statistiques uniquement (principe de minimisation RGPD)
> Date de génération : Juin 2026

# DOCUMENTATION BIOLÓGIE ANIME – ANALYSE DESCRIPTIVE

## 1. TABLEAU RÉCAPITULATIF PAR CATÉGORIE  
- **Biochimie** : Calcium, Glucose, Protéines Totales, Urée Sanguin, % Pnn, Alat, Asat, Bilirubine Totale, Ggt, Crp Inflammation, Chlore, Potassium Sanguin  
- **Hépatologie** : Urée Sanguin, % Pnn, Alat, Asat, Bilirubine Totale, Ggt, Crp Inflammation, Chlore, Sodium Sanguin  
- **Ionométrie** : Calcium, Glucose, Protéines Totales, Urée Sanguin, % Pnn, Alat, Asat, Bilirubine Totale, Ggt, Crp Inflammation, Chlore, Potassium Sanguin  

## 2. DÉTAIL PAR TEST  
| Test | Catégorie | Rôle clinique général | P5 | Médiane | P95 | Nb mesures |  
|------|----------|------------------------|----|--------|--------|--------|  
| Calcium | Biochimie | Élimination des anomalies | 455.59 | 2348.74 | 11955.76 | 32270 |  
| Glucose | Biochimie | Mesure des métabolismes | 223.39 | 1165.61 | 6094.97 | 22055 |  
| Protéines Totales | Biochimie | Analyse des fonctions cellulaires | 200.04 | 1050.24 | 5378.35 | 32636 |  
| Urée Sanguin | Biochimie | Mesure de la glycémie | 142.60 | 756.00 | 4013.48 | 31066 |  
| % Pnn | Hématologie | Évaluation des cellules en fonctionnement | 112.64 | 603.08 | 3478.04 | 17285 |  
| Alat | Hépatologie | Surveillance du fonctionnement du foie | 112.52 | 585.87 | 2974.22 | 14461 |  
| Asat | Hépatologie | Évaluation des fonctions du foie | 57.64 | 294.16 | 1532.55 | 14205 |  
| Bilirubine Totale | Hépatologie | Mesure de la bilirubine globulaire | 250.13 | 1274.51 | 6579.08 | 9442 |  
| Ggt | Hépatologie | Évaluation du métabolisme du foie | 853.61 | 4218.58 | 23029.78 | 9938 |  
| Crp Inflammation | Ionométrie | Évaluation de la inflammation | 103.14 | 529.58 | 2746.36 | 32545 |  
| Chlore | Ionométrie | Mesure du chlore dans l'organisme | 330.49 | 1736.90 | 9067.39 | 32060 |  
| Potassium Sanguin | Ionométrie | Évaluation du potassium en sang | 574.67 | 2926.37 | 14947.81 | 33564 |  

## 3. APPROCHE DATA-DRIVEN  
- **Seuils statistiques** : Calculés sur un dataset synthétique, indiqués comme normaux, limites, ou sévères (ex : % P5 > 10/90, >P95).  
- **Statuts** :  
  - **Normal** : Valeurs entre P10-P90.  
  - **Limite Basse/Haute** : P5-P10 / P90-P95.  
  - **Anomalie Sévère** : <P5 ou >P95.  

## 4. RECOMMANDATIONS  
- **Surveillance** : Gérer les 29.6% de données hors catalogue.  
- **Intégration** : Développer une approche concrète pour les nouveaux tests.  
- **Audit** : Vérifier les données mensuelles pour un contrôle trimestriel.
