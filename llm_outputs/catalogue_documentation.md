# Documentation du Catalogue des Tests — Laboratoire BI

> Générée automatiquement par le module LLM (qwen3:0.6B via Ollama) — 100% offline
> Données : agrégats statistiques uniquement (principe de minimisation RGPD)
> Date de génération : Juin 2026

## 1. TABLEAU RÉCAPITULATIF PAR CATÉGORIE  
| Catégorie | Tests appartenant à cette catégorie |  
|-----------|-------------------------------------|  
| Biochimie | Calcium, Créatinine, Glucose, Protéines Totales |  
| Hépatologie | Urée, Bilirubine, % Pnn, Alat |  
| Ionométrie | Chlore, Sodium, Potassium |  
| Hématologie | % Pnn, Crp Inflammation |  
| Inflammation | % Pnn, Crp Inflammation |  

## 2. DÉTAIL PAR TEST  
| Test | Catégorie | Rôle clinique général | P5 | Médiane | P95 | Nb mesures |  
|------|-----------|-----------------------|----|---------|-----|------------|  
| Calcium | Biochimie | Taux équilibré du sang | 455.59 | 2348.74 | 11955.76 | 32270 |  
| Créatinine | Jaffe Cinétique | Indicateur de la fonction osmotique | 177.75 | 939.54 | 4736.01 | 33568 |  
| Glucose | Biochimie | Indicateur de l'isoéthanoate | 223.39 | 1165.61 | 6094.97 | 22055 |  
| Protéines Totales | Biochimie | Indicateur des métabolismes | 200.04 | 1050.24 | 5378.35 | 32636 |  
| Urée | Biochimie | Indicateur de la fonction osmotique | 142.60 | 756.00 | 4013.48 | 31066 |  

## 3. APPROCHE DATA-DRIVEN  
- Les seuils P5/P95 sont calculés statistiquement sur le dataset synthétique de 29.6% hors catalogue.  
- Ces seuils NE SONT PAS des normes médicales réelles — ce sont des références statistiques internes.  
- Statut Normal (entre P10 et P90) — exemple concret de gestion.  
- Statuts Limite Basse/Haute (entre P5-P10 ou P90-P95) — exemple concret de surveillance.  
- Statuts Anomalie Sévère (<P5 ou >P95) — exemple concret d'alerte.  

## 4. RECOMMANDATIONS DE PILOTAGE  
### 4.1 Surveillance du taux hors catalogue (29.6%)  
Ce taux précis de 29.6% mérite attention car il indique une faible qualité des données. Il permet de détecter les anomalies et d'optimiser la qualité des mesures.  

### 4.2 Processus d'intégration des nouveaux tests  
1. Établir une base de données cohérente et vérifier les indicateurs statistiques.  
2. Développer des algorithmes de filtrage pour les données hors catalogue.  
3. Intégrer les tests en alignant les seuils de filtrage avec les indicateurs clés.  

### 4.3 Audit trimestriel du catalogue  
- Vérifier la cohérence des seuils statistiques.  
- Assurer que les tests sont actuellement intégrés.  
- Évaluer les tests obsolètes pour les supprimer.
