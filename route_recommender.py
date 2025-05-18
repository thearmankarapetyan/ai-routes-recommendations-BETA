#!/usr/bin/env python3
# recommend_routes.py
#
# Charge les données de sorties de Tim et les routes disponibles,
# puis interroge GPT-4o-mini pour recommander 3 itinéraires qu’il
# n’a **pas** encore réalisés, avec plus de détails et en incluant
# impérativement les IDs fournis.

import os
import json
import re
import openai
from dotenv import load_dotenv

def strip_markdown(text: str) -> str:
    """Supprime les balises **markdown** tout en gardant le contenu."""
    return re.sub(r'\*\*(.*?)\*\*', r'\1', text)

def load_json(path: str):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

def build_outings_summary(outings: list[dict]) -> str:
    """Construit le résumé des sorties de Tim pour le prompt."""
    summary = "Historique des sorties de Tim :\n"
    for o in outings:
        rid  = o.get("route_id", "N/A")
        acts = o.get("activities") or ["Inconnu"]
        date = o.get("date", "N/A")
        summary += f"- Route ID : {rid}, Activité : {', '.join(acts)}, Date (ts UNIX) : {date}\n"
    return summary

def build_routes_list(routes: dict) -> str:
    """Construit la liste des routes disponibles pour le prompt."""
    lst = "Liste des routes disponibles pour recommandation :\n"
    for rid, r in routes.items():
        name    = r.get("name", "Sans nom")
        acts    = r.get("activities") or ["Inconnu"]
        props   = r.get("properties") or {}
        gain    = props.get("height_diff_up", "N/A")
        ratings = r.get("ratings") or {}
        diff    = ratings.get("global", "N/A")
        lst += (
            f"- Route ID : {rid}, Nom : {name}, Activité : {', '.join(acts)}, "
            f"Dénivelé : {gain} m, Difficulté : {diff}\n"
        )
    return lst

def main():
    # Chargement de la clé API
    load_dotenv()
    openai.api_key = os.getenv("OPENAI_API_KEY")
    if not openai.api_key:
        raise RuntimeError("Veuillez définir OPENAI_API_KEY dans votre environnement")

    # Chargement des données
    outings = load_json("data/outings_user15.json")
    routes  = load_json("data/routes_from_outings.json")

    # Préparation des chaînes pour le prompt
    outings_summary = build_outings_summary(outings)
    routes_list     = build_routes_list(routes)

    # Prompt système : rôle et consignes détaillées
    system_prompt = """
Vous êtes un guide de montagne virtuel, expert en recommandation d’itinéraires
de sports de montagne (escalade, via ferrata, alpinisme…).

Votre mission :
1. Analysez l’historique des sorties de l’utilisateur (Tim).
2. Sélectionnez **exactement 3 itinéraires** parmi **ceux qu’il n’a pas encore réalisés**.
3. Pour chaque itinéraire, donnez **5 à 6 phrases** détaillées :
   - Pourquoi cet itinéraire représente une nouveauté intéressante pour Tim.
   - Conditions idéales (saison, horaire, équipement conseillé).
   - Durée approximative et niveau d’engagement requis.
   - Une astuce ou un conseil perso pour en profiter au mieux.

Critères de sélection obligatoires :
- **ID Exact** : mentionnez impérativement l’ID de chaque route tel qu’il apparaît.
- **Diversité** : choisissez au moins une voie plus facile et une voie plus exigeante que sa moyenne.
- **Type d’activité** : variez les activités qu’il a déjà pratiquées, tout en introduisant une possible nouveauté.
- **Difficulté** : respectez ±1 niveau autour de sa difficulté moyenne.
- **Dénivelé** : respectez ±200 m autour de son dénivelé moyen.

Format de sortie (plain text) :
Pour chaque itinéraire :
1. Route ID – Nom de la voie (activité, difficulté, dénivelé m)  
   5–6 phrases détaillées.

Après les 3 recommandations, ajoutez une **conclusion de 4 à 5 phrases**
sur la stratégie de découverte et la façon dont ces itinéraires enrichissent
son historique de sorties. Ne fournissez **rien d’autre**.
""".strip()

    # Prompt utilisateur contenant les données
    user_prompt = f"""
{outings_summary}

{routes_list}
""".strip()

    # Appel à l'API GPT
    response = openai.ChatCompletion.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_prompt},
        ],
        temperature=0.7,
        max_tokens=1000,
    )

    # Affichage du résultat
    result = response.choices[0].message.content
    print(strip_markdown(result))

if __name__ == "__main__":
    main()
